"""Logical Python-versus-Spark lake parity, independent of Parquet part names."""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

from src.lake.engines import LocalPythonTransformationEngine,PySparkTransformationEngine
from src.lake.models import LakeLayer
from src.lake.pipeline import LocalLakePipeline
from src.lake.store import LocalFilesystemLakeStore


def _logical_hash(store,manifest)->str:
    records=[]
    for item in manifest.objects:
        for line in store.read_object(item).splitlines(): records.append(f"{item.entity}:"+json.dumps(json.loads(line),sort_keys=True,separators=(",",":")))
    return hashlib.sha256("\n".join(sorted(records)).encode()).hexdigest()


def compare_snapshots(python_store,spark_store,python_snapshot,spark_snapshot)->dict:
    left=python_store.get_layer_manifest(python_snapshot.layer_manifest_id); right=spark_store.get_layer_manifest(spark_snapshot.layer_manifest_id)
    left_hash=_logical_hash(python_store,left); right_hash=_logical_hash(spark_store,right)
    return {"layer":left.layer.value,"python_status":python_snapshot.status,"spark_status":spark_snapshot.status,"dataset_identity_equal":left.dataset_id==right.dataset_id,"logical_schema_equal":sorted((item.entity for item in left.objects))==sorted((item.entity for item in right.objects)),"row_counts_equal":left.row_counts==right.row_counts,"logical_content_hash_equal":left_hash==right_hash,"python_logical_hash":left_hash,"spark_logical_hash":right_hash,"rejected_rows_equal":left.rejected_row_counts==right.rejected_row_counts,"warnings_equal":left.validation.warnings==right.validation.warnings,"validation_equal":left.validation.model_dump()==right.validation.model_dump(),"parent_dataset_equal":python_snapshot.dataset_id==spark_snapshot.dataset_id,"physical_difference":{"python_format":sorted({item.format for item in left.objects}),"spark_format":sorted({item.format for item in right.objects}),"python_snapshot_id":python_snapshot.snapshot_id,"spark_snapshot_id":spark_snapshot.snapshot_id,"allowed":True}}


def run_engine_parity(root:Path,profile:str,seed:int,spark_engine:PySparkTransformationEngine)->dict:
    root=Path(root); python_store=LocalFilesystemLakeStore(root/"python"); spark_store=LocalFilesystemLakeStore(root/"spark")
    started=time.perf_counter(); python_result=LocalLakePipeline(python_store).run(profile,seed,LocalPythonTransformationEngine()); python_ms=(time.perf_counter()-started)*1000
    try:
        started=time.perf_counter(); spark_result=LocalLakePipeline(spark_store).run(profile,seed,spark_engine); spark_ms=(time.perf_counter()-started)*1000
    finally: spark_engine.close()
    layers=[]
    for layer in LakeLayer:
        layers.append(compare_snapshots(python_store,spark_store,python_store.get_active_snapshot(layer),spark_store.get_active_snapshot(layer)))
    passed=all(all(item[key] for key in ("dataset_identity_equal","logical_schema_equal","row_counts_equal","logical_content_hash_equal","rejected_rows_equal","warnings_equal","validation_equal","parent_dataset_equal")) for item in layers)
    return {"schema_version":"1.0","profile":profile,"seed":seed,"passed":passed,"python_execution_ms":python_ms,"spark_execution_ms":spark_ms,"layers":layers,"allowed_differences":["physical Parquet paths and part names","partition layout","execution time","engine runtime metadata","Spark application ID","backend-specific snapshot identity"]}


def write_report(report:dict,path:Path)->Path:
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True); temporary=path.with_suffix(path.suffix+".tmp"); temporary.write_text(json.dumps(report,indent=2,sort_keys=True),encoding="utf-8"); temporary.replace(path); return path
