from __future__ import annotations

import json
import sys
from types import SimpleNamespace
from datetime import datetime,timezone

import pytest

from src.agent.workflow import Analyst
from src.audit.repository import SQLiteAuditStore
from src.lake.models import DataObject,LakeLayer,LayerManifest,PublishedSnapshot,ValidationResult
from src.lake.pipeline import LocalLakePipeline
from src.lake.serving import publish_gold_to_sqlite
from src.lake import serving
from src.database.lifecycle import LoadResult
from src.database.seed import generate_dataset
from src.lake.store import LakeConflictError,LocalFilesystemLakeStore
from src.metadata.lineage import LineageResolver
from src.metadata.repository import SQLiteManifestStore,metadata_path_for
from src.lake import cli as lake_cli
from src.evaluation import backend_parity


@pytest.fixture
def store(tmp_path): return LocalFilesystemLakeStore(tmp_path/"lake")


@pytest.fixture
def completed(store): return LocalLakePipeline(store).run("test",17)


def test_lake_layer_has_exact_medallion_values():
    assert [item.value for item in LakeLayer]==["raw","bronze","silver","gold"]


def test_store_rejects_path_traversal_and_unsafe_identities(store):
    with pytest.raises(ValueError,match="Unsafe"): store._safe("objects","..","outside")
    with pytest.raises(ValueError,match="Unsafe"): store.write_object(LakeLayer.raw,"../patients","safe",b"{}\n",1)


def test_atomic_raw_write_checksum_and_immutability(store):
    item=store.write_object(LakeLayer.raw,"patients","object-safe",b'{"patient_id":1}\n',1)
    assert store.object_exists(item) and store.validate_checksum(item)
    assert store.write_object(LakeLayer.raw,"patients","object-safe",b'{"patient_id":1}\n',1)==item
    with pytest.raises(LakeConflictError): store.write_object(LakeLayer.raw,"patients","object-safe",b'{"patient_id":2}\n',1)
    assert not any((store.root/"staging").iterdir())


def test_checksum_detects_tampering(store):
    item=store.write_object(LakeLayer.bronze,"patients","object-safe",b"{}\n",1)
    (store.root/item.relative_path).write_bytes(b"changed")
    assert not store.validate_checksum(item)


def test_source_generation_is_idempotent_and_supports_incremental_batches(store):
    pipeline=LocalLakePipeline(store); first=pipeline.generate_source(); again=pipeline.generate_source()
    incremental=pipeline.generate_source(kind="incremental",parent_batch_id=first.batch_id)
    assert first.batch_id==again.batch_id and first.objects==again.objects
    assert incremental.parent_batch_id==first.batch_id and incremental.batch_id!=first.batch_id
    assert store.get_source_batch(first.batch_id)==first


def test_complete_pipeline_is_deterministic_and_versioned(store):
    pipeline=LocalLakePipeline(store); first=pipeline.run(); second=pipeline.run()
    assert first["gold"].snapshot_id==second["gold"].snapshot_id
    raw=first["raw"]; changed=pipeline.transform(raw.snapshot_id,LakeLayer.bronze,"2.0.0")
    assert changed.output_manifest_id!=first["bronze_run"].output_manifest_id
    assert changed.definition.version=="2.0.0"


def test_layer_semantics_and_parent_lineage(completed,store):
    gold=completed["gold"]; lineage=store.resolve_parent_lineage(gold.snapshot_id)
    assert [item.layer for item in lineage]==[LakeLayer.gold,LakeLayer.silver,LakeLayer.bronze,LakeLayer.raw]
    assert all(store.get_layer_manifest(item.layer_manifest_id).validation.passed for item in lineage)
    assert store.list_layer_manifests(LakeLayer.gold)[0].row_counts["encounters"]==1200


def test_silver_deduplication_preserves_composite_rows(completed,store):
    silver=store.get_active_snapshot(LakeLayer.silver); manifest=store.get_layer_manifest(silver.layer_manifest_id)
    assert manifest.rejected_row_counts["encounter_diagnoses"]==0
    assert manifest.row_counts["encounter_diagnoses"]>manifest.row_counts["encounters"]
    assert manifest.validation.checks["foreign_key_consistency"]


def test_malformed_batch_fails_gate_without_replacing_active_raw(store):
    pipeline=LocalLakePipeline(store); good=pipeline.publish_raw(pipeline.generate_source())
    malformed=pipeline.publish_raw(pipeline.generate_source(seed=18,malformed=True))
    assert malformed.status=="active"  # raw preserves malformed source exactly
    failed=pipeline.transform(malformed.snapshot_id,LakeLayer.bronze)
    assert failed.status=="failed" and failed.validation.rejected_rows==1
    assert store.get_active_snapshot(LakeLayer.bronze) is None
    assert store.get_active_snapshot(LakeLayer.raw).snapshot_id==malformed.snapshot_id
    assert good.snapshot_id!=malformed.snapshot_id


def test_failed_candidate_preserves_prior_published_bronze(store):
    pipeline=LocalLakePipeline(store); good=pipeline.run(); prior=store.get_active_snapshot(LakeLayer.bronze)
    malformed=pipeline.publish_raw(pipeline.generate_source(seed=18,malformed=True)); failed=pipeline.transform(malformed.snapshot_id,LakeLayer.bronze)
    assert failed.status=="failed"
    assert store.get_active_snapshot(LakeLayer.bronze).snapshot_id==prior.snapshot_id
    assert store.get_active_snapshot(LakeLayer.gold).snapshot_id==good["gold"].snapshot_id


def test_manifest_conflicting_identifier_is_rejected(store):
    validation=ValidationResult(passed=True)
    first=LayerManifest(manifest_id="same",layer=LakeLayer.raw,dataset_id="one",transformation_name="x",transformation_version="1",parent_ids=[],objects=[],row_counts={},validation=validation)
    store.register_layer_manifest(first)
    with pytest.raises(LakeConflictError): store.register_layer_manifest(first.model_copy(update={"dataset_id":"two"}))


def test_unvalidated_snapshot_cannot_publish(store):
    snapshot=PublishedSnapshot(snapshot_id="failed",layer=LakeLayer.gold,layer_manifest_id="missing",dataset_id="d",parent_snapshot_ids=[],object_ids=[],status="failed")
    with pytest.raises(ValueError,match="validated"): store.publish_snapshot(snapshot)


def test_gold_publishes_to_sqlite_with_identity_and_lineage(completed,store,tmp_path):
    target=tmp_path/"serving.db"; result=publish_gold_to_sqlite(store,completed["gold"].snapshot_id,target)
    assert result.completed and result.row_counts["patients"]==300 and result.row_counts["encounters"]==1200
    assert result.snapshot.active and result.snapshot.provenance_metadata["gold_snapshot_id"]==completed["gold"].snapshot_id
    assert result.snapshot.dataset_id==completed["gold"].dataset_id
    analysis=Analyst(target,dataset_snapshot=result.snapshot).analyze("How many patients are in the dataset?")
    lineage=LineageResolver(SQLiteAuditStore(target),SQLiteManifestStore(metadata_path_for(target)),store).resolve_run(analysis.run_id)
    assert lineage["lake_lineage"][0]["snapshot_id"]==completed["gold"].snapshot_id
    assert lineage["lake_lineage"][-1]["layer"]=="raw"
    direct=generate_dataset(tmp_path/"direct.db",17,300,1200)
    assert result.manifest.manifest_id==direct.manifest.manifest_id
    assert result.snapshot.snapshot_id!=direct.snapshot.snapshot_id


def test_data_object_and_manifest_serialization_round_trip(completed,store):
    manifest=store.get_layer_manifest(completed["gold"].layer_manifest_id)
    assert LayerManifest.model_validate_json(manifest.model_dump_json())==manifest
    assert DataObject.model_validate_json(manifest.objects[0].model_dump_json())==manifest.objects[0]


def test_store_lists_objects_and_hides_filesystem_from_models(completed,store):
    objects=store.list_objects(LakeLayer.gold)
    assert len(objects)==11 and all(not item.relative_path.startswith(("/","C:")) for item in objects)
    assert json.loads(store.get_layer_manifest(completed["gold"].layer_manifest_id).model_dump_json())["layer"]=="gold"


def test_lake_cli_read_workflows_and_sqlite_publication(completed,store,tmp_path,monkeypatch,capsys):
    gold=completed["gold"]; manifest=store.get_layer_manifest(gold.layer_manifest_id)
    commands=(("list","--layer","gold"),("validate","--manifest-id",manifest.manifest_id),("lineage","--snapshot-id",gold.snapshot_id),("publish-sqlite","--gold-snapshot-id",gold.snapshot_id,"--path",str(tmp_path/"cli.db")))
    for command in commands:
        monkeypatch.setattr(sys,"argv",["lake","--root",str(store.root),*command]); lake_cli.main()
        assert capsys.readouterr().out.strip().startswith(("[","{"))
    assert (tmp_path/"cli.db").exists()


def test_machine_parity_report_shape_and_numeric_tolerance(monkeypatch,tmp_path):
    class FakeAnalyst:
        def __init__(self,*args,**kwargs): self.postgres="query_backend" in kwargs
        def analyze(self,question):
            value=1.0000000001 if self.postgres else 1.0
            return SimpleNamespace(status="completed",rows=[{"value":value}],warnings=[],answer="same")
    monkeypatch.setattr(backend_parity,"Analyst",FakeAnalyst)
    snapshot=SimpleNamespace(snapshot_id="sqlite-snapshot",dataset_id="dataset",manifest_id="manifest")
    postgres_snapshot=SimpleNamespace(snapshot_id="postgres-snapshot",dataset_id="dataset",manifest_id="manifest")
    report=backend_parity.run_backend_parity(tmp_path/"unused.db",object(),snapshot,postgres_snapshot)
    assert report["summary"]["numeric_matches"]==7 and report["summary"]["exact_result_matches"]==0
    path=backend_parity.write_parity_report(report,tmp_path/"parity.json")
    assert json.loads(path.read_text())["schema_version"]=="1.0"


def test_gold_postgres_publication_uses_existing_loader_boundary(completed,store,tmp_path,monkeypatch):
    class FakePostgresLoader:
        def __init__(self,*args,**kwargs): pass
        def load_batches(self,batches,manifest):
            counts={batch.entity:len(batch.records) for batch in batches}
            loaded=manifest.model_copy(update={"entity_row_counts":counts,"load_timestamp":datetime.now(timezone.utc),"loader_backend":"postgres","stable_summaries":{"encounter_total_cost":0.0},"load_complete":True,"validation_summary":{"foreign_key_errors":0,"quality_measure_errors":0,"row_count_mismatches":{}}})
            return LoadResult(manifest=loaded,row_counts=counts,completed=True,validation_summary=loaded.validation_summary)
    monkeypatch.setattr(serving,"PostgresLoader",FakePostgresLoader)
    metadata=SQLiteManifestStore(tmp_path/"postgres.metadata.db")
    result=serving.publish_gold_to_postgres(store,completed["gold"].snapshot_id,"postgresql://unused",metadata,"analytics","postgres:analytics")
    assert result.completed and result.snapshot.active and result.snapshot.backend_name=="postgres"
    assert result.snapshot.provenance_metadata["gold_snapshot_id"]==completed["gold"].snapshot_id
