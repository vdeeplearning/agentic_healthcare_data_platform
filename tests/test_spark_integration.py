"""Real local-mode Spark verification; skipped only when PySpark or Java is unavailable."""
from __future__ import annotations

import pytest

from src.lake.engines import PySparkTransformationEngine
from src.lake.parity import run_engine_parity
from src.lake.spark_session import SparkSessionFactory,SparkSessionSettings
from src.lake.pipeline import LocalLakePipeline
from src.lake.store import LocalFilesystemLakeStore
from src.lake.serving import publish_gold_to_sqlite
from src.lake.models import LakeLayer
from src.agent.workflow import Analyst


capability=SparkSessionFactory.capability()
pytestmark=pytest.mark.skipif(not capability["available"],reason=str(capability["reason"]))


def test_real_local_spark_test_profile_parity_and_parquet(tmp_path):
    engine=PySparkTransformationEngine(SparkSessionSettings(master="local[2]",shuffle_partitions=2,warehouse_dir=tmp_path/"warehouse"),output_partitions=2)
    report=run_engine_parity(tmp_path/"parity","test",17,engine)
    assert report["passed"] and report["layers"][-1]["physical_difference"]["spark_format"]==["parquet"]


def test_real_local_spark_demo_gold_serves_bounded_analysis(tmp_path):
    store=LocalFilesystemLakeStore(tmp_path/"lake"); engine=PySparkTransformationEngine(SparkSessionSettings(master="local[2]",shuffle_partitions=2,warehouse_dir=tmp_path/"warehouse"),output_partitions=2)
    try: result=LocalLakePipeline(store).run("demo",42,engine)
    finally: engine.close()
    manifest=store.get_layer_manifest(result["gold"].layer_manifest_id); assert manifest.row_counts["encounters"]==10000
    serving=publish_gold_to_sqlite(store,result["gold"].snapshot_id,tmp_path/"serving.db")
    assert Analyst(tmp_path/"serving.db",dataset_snapshot=serving.snapshot).analyze("How many patients are in the dataset?").rows==[{"patient_count":2500}]


def test_real_spark_malformed_gate_preserves_active_bronze(tmp_path):
    store=LocalFilesystemLakeStore(tmp_path/"lake"); pipeline=LocalLakePipeline(store); engine=PySparkTransformationEngine(SparkSessionSettings(master="local[2]",warehouse_dir=tmp_path/"warehouse"),output_partitions=1)
    try:
        pipeline.run("test",17,engine); previous=store.get_active_snapshot(LakeLayer.bronze)
        malformed=pipeline.publish_raw(pipeline.generate_source(seed=18,malformed=True)); failed=pipeline.transform(malformed.snapshot_id,LakeLayer.bronze,engine=engine)
    finally: engine.close()
    assert failed.status=="failed" and store.get_active_snapshot(LakeLayer.bronze).snapshot_id==previous.snapshot_id
