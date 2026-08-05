from __future__ import annotations

import json
import sys
from pathlib import Path
from types import ModuleType,SimpleNamespace

import pytest

from src.agent.workflow import Analyst
from src.lake.engines import LocalPythonTransformationEngine,PySparkTransformationEngine,create_transformation_engine
from src.lake.models import LakeLayer
from src.lake.parity import run_engine_parity,write_report
from src.lake.pipeline import LocalLakePipeline
from src.lake.serving import publish_gold_to_sqlite
from src.lake.spark_session import SparkSessionFactory,SparkSessionSettings,SparkUnavailableError
from src.lake.store import LocalFilesystemLakeStore
from src.config import Settings
from src.lake import spark_schemas


class FakePredicate:
    def __init__(self,function): self.function=function
    def __and__(self,other): return FakePredicate(lambda row:self.function(row) and other.function(row))


class FakeColumn:
    def __init__(self,name): self.name=name
    def isNotNull(self): return FakePredicate(lambda row:row.get(self.name) is not None)


class FakeRow(dict):
    def asDict(self,recursive=True): return dict(self)


class FakeWriter:
    def __init__(self,frame): self.frame=frame
    def mode(self,_): return self
    def parquet(self,path):
        target=Path(path); target.mkdir(parents=True,exist_ok=True); (target/"part-00000.parquet").write_bytes(b"PAR1fake"); (target/"_SUCCESS").write_bytes(b""); FAKE_PARQUET[str(target.resolve())]=self.frame.rows


class FakeFrame:
    def __init__(self,rows,partitions=1): self.rows=[dict(row) for row in rows]; self.partitions=partitions
    @property
    def rdd(self): return SimpleNamespace(getNumPartitions=lambda:self.partitions)
    @property
    def write(self): return FakeWriter(self)
    def select(self,*fields): return FakeFrame([{field:row.get(field) for field in fields} for row in self.rows],self.partitions)
    def collect(self): return [FakeRow(row) for row in self.rows]
    def count(self): return len(self.rows)
    def filter(self,predicate): return FakeFrame([row for row in self.rows if predicate.function(row)],self.partitions)
    def dropDuplicates(self,keys):
        seen=set(); rows=[]
        for row in self.rows:
            identity=tuple(row.get(key) for key in keys)
            if identity not in seen: seen.add(identity); rows.append(row)
        return FakeFrame(rows,self.partitions)
    def repartition(self,count): return FakeFrame(self.rows,count)


class FakeSpark:
    version="3.5.5"
    sparkContext=SimpleNamespace(applicationId="local-test-app",master="local[2]")
    def createDataFrame(self,rows,schema): return FakeFrame(rows)
    @property
    def read(self): return FakeReader()


FAKE_PARQUET={}


class FakeReader:
    def schema(self,_): return self
    def parquet(self,path):
        target=Path(path).resolve()
        if str(target) in FAKE_PARQUET: return FakeFrame(FAKE_PARQUET[str(target)])
        rows=[json.loads(line) for line in (target/"_logical.jsonl").read_text().splitlines()]
        return FakeFrame(PySparkTransformationEngine._physical_rows(rows,None))


class FakeSessionFactory:
    def __init__(self): self.spark=FakeSpark(); self.stopped=False
    def create(self): return self.spark
    def stop(self): self.stopped=True


@pytest.fixture(autouse=True)
def fake_pyspark_functions(monkeypatch):
    pyspark=ModuleType("pyspark"); sql=ModuleType("pyspark.sql"); functions=ModuleType("pyspark.sql.functions"); functions.col=lambda name:FakeColumn(name); sql.functions=functions; pyspark.sql=sql
    monkeypatch.setitem(sys.modules,"pyspark",pyspark); monkeypatch.setitem(sys.modules,"pyspark.sql",sql); monkeypatch.setitem(sys.modules,"pyspark.sql.functions",functions)
    monkeypatch.setattr("src.lake.engines.physical_schema_for",lambda *args:None)


def spark_engine(): return PySparkTransformationEngine(session_factory=FakeSessionFactory(),output_partitions=2)


def test_python_engine_is_default_and_preserves_frozen_snapshot(tmp_path):
    store=LocalFilesystemLakeStore(tmp_path/"lake"); settings=Settings(_env_file=None)
    engine=create_transformation_engine(settings,store)
    assert isinstance(engine,LocalPythonTransformationEngine)
    result=LocalLakePipeline(store).run("test",17,engine)
    assert result["gold"].snapshot_id=="lake-snapshot-29b86c56c03d0fc55350"


def test_fake_spark_pipeline_writes_parquet_metadata_and_serves_sqlite(tmp_path):
    store=LocalFilesystemLakeStore(tmp_path/"spark"); engine=spark_engine(); result=LocalLakePipeline(store).run("test",17,engine)
    gold=result["gold"]; manifest=store.get_layer_manifest(gold.layer_manifest_id)
    assert all(item.format=="parquet" and (store.root/item.relative_path/"_logical.jsonl").exists() for item in manifest.objects)
    assert gold.metadata["execution_engine"]=="spark" and result["gold_run"].spark_application_id=="local-test-app"
    serving=publish_gold_to_sqlite(store,gold.snapshot_id,tmp_path/"serving.db")
    answer=Analyst(tmp_path/"serving.db",dataset_snapshot=serving.snapshot).analyze("How many patients are in the dataset?")
    assert serving.row_counts["encounters"]==1200 and answer.rows==[{"patient_count":300}]
    assert serving.snapshot.provenance_metadata["gold_snapshot_id"]==gold.snapshot_id


def test_fake_spark_demo_profile_reaches_validated_gold(tmp_path):
    store=LocalFilesystemLakeStore(tmp_path/"spark-demo"); result=LocalLakePipeline(store).run("demo",42,spark_engine()); manifest=store.get_layer_manifest(result["gold"].layer_manifest_id)
    assert manifest.validation.passed and manifest.row_counts["patients"]==2500 and manifest.row_counts["encounters"]==10000


def test_python_spark_logical_parity_report(tmp_path):
    report=run_engine_parity(tmp_path/"parity","test",17,spark_engine())
    assert report["passed"] and all(layer["logical_content_hash_equal"] for layer in report["layers"])
    assert report["layers"][1]["physical_difference"]["spark_format"]==["parquet"]
    target=write_report(report,tmp_path/"report.json"); assert json.loads(target.read_text())["passed"]


def test_spark_malformed_failure_preserves_previous_active_snapshot(tmp_path):
    store=LocalFilesystemLakeStore(tmp_path/"lake"); pipeline=LocalLakePipeline(store); engine=spark_engine(); pipeline.run("test",17,engine); previous=store.get_active_snapshot(LakeLayer.bronze)
    malformed=pipeline.publish_raw(pipeline.generate_source(seed=18,malformed=True)); failed=pipeline.transform(malformed.snapshot_id,LakeLayer.bronze,engine=engine)
    assert failed.status=="failed" and failed.validation.rejected_rows==1
    assert store.get_active_snapshot(LakeLayer.bronze).snapshot_id==previous.snapshot_id


def test_spark_retry_is_idempotent_and_incremental_batch_is_stable(tmp_path):
    store=LocalFilesystemLakeStore(tmp_path/"lake"); pipeline=LocalLakePipeline(store); engine=spark_engine(); raw=pipeline.publish_raw(pipeline.generate_source())
    first=pipeline.transform(raw.snapshot_id,LakeLayer.bronze,engine=engine); second=pipeline.transform(raw.snapshot_id,LakeLayer.bronze,engine=engine)
    initial=pipeline.generate_source(); incremental=pipeline.generate_source(kind="incremental",parent_batch_id=initial.batch_id)
    assert first.output_manifest_id==second.output_manifest_id
    assert incremental.parent_batch_id==initial.batch_id and incremental.batch_id=="batch-c1b2a843f5cb94febe24"
    assert not any((store.root/"staging").glob("spark-object-*"))


def test_spark_capability_and_configuration_failures_are_actionable(monkeypatch,tmp_path):
    settings=SparkSessionSettings(master="",shuffle_partitions=0,warehouse_dir=tmp_path)
    with pytest.raises(ValueError,match="master"): settings.validate()
    monkeypatch.setattr(SparkSessionFactory,"capability",staticmethod(lambda:{"available":False,"pyspark_version":None,"java":None,"reason":"Install `.[spark]`."}))
    with pytest.raises(SparkUnavailableError,match="spark"): SparkSessionFactory(SparkSessionSettings()).create()
    capability=SparkSessionFactory.capability(); assert not capability["available"]


def test_explicit_schemas_cover_every_entity_and_physical_metadata(monkeypatch):
    types=ModuleType("pyspark.sql.types")
    class DataType: pass
    class StructField:
        def __init__(self,name,data_type,nullable): self.name=name; self.dataType=data_type; self.nullable=nullable
    class StructType:
        def __init__(self,fields): self.fields=fields
    for name in ("DoubleType","IntegerType","LongType","StringType"): setattr(types,name,type(name,(DataType,),{}))
    types.ArrayType=lambda value:("array",value); types.StructField=StructField; types.StructType=StructType
    monkeypatch.setitem(sys.modules,"pyspark.sql.types",types)
    for entity,fields in spark_schemas.ENTITY_FIELDS.items():
        logical=spark_schemas.schema_for(entity,LakeLayer.silver); physical=spark_schemas.physical_schema_for(entity,LakeLayer.gold)
        assert [field.name for field in logical.fields]==[field[0] for field in fields]
        assert {field.name for field in physical.fields}.issuperset({"_lake_row_order","_lake_source_batch_id","_lake_record_hash","_lake_quality_flags","_lake_rejection_reason"})


def test_quality_policy_rejects_semantically_invalid_date(tmp_path):
    store=LocalFilesystemLakeStore(tmp_path/"lake"); pipeline=LocalLakePipeline(store)
    patient=store.write_object(LakeLayer.silver,"patients","object-invalid-date",b'{"patient_id":1,"birth_date":"2025-99-99","sex":"F"}\n',1)
    checks=pipeline._silver_checks([patient])
    assert not checks["date_parse_success"]


def test_failed_parquet_write_cleans_staging_and_does_not_publish(monkeypatch,tmp_path):
    store=LocalFilesystemLakeStore(tmp_path/"lake"); pipeline=LocalLakePipeline(store); raw=pipeline.publish_raw(pipeline.generate_source()); engine=spark_engine()
    monkeypatch.setattr(FakeWriter,"parquet",lambda self,path:(_ for _ in ()).throw(OSError("disk full")))
    with pytest.raises(OSError,match="disk full"): pipeline.transform(raw.snapshot_id,LakeLayer.bronze,engine=engine)
    assert store.get_active_snapshot(LakeLayer.bronze) is None
    assert not list((store.root/"staging").glob("spark-*"))
