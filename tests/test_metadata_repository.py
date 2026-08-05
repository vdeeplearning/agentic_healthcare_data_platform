from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone

import pytest

from src.agent.workflow import Analyst
from src.audit.repository import SQLiteAuditStore
from src.database.generator import SyntheticRecordGenerator
from src.database.lifecycle import (
    LOADER_VERSION, SCHEMA_VERSION, DatasetSnapshot, VersionCompatibilityPolicy,
    manifest_identity, new_manifest, snapshot_identity,
)
from src.database.seed import generate_dataset
from src.database.sqlite_loader import SQLiteSyntheticDatasetLoader
from src.metadata.lineage import LineageResolver
from src.metadata.migrations import (
    METADATA_MIGRATIONS, MetadataMigrationError, Migration,
    UnsupportedMetadataVersion, apply_metadata_migrations,
)
from src.metadata.repository import MetadataConflictError, SQLiteManifestStore, metadata_path_for


def completed_manifest(seed: int = 17):
    manifest=new_manifest(seed,300,1200).model_copy(update={
        "entity_row_counts":{"patients":300,"encounters":1200},
        "stable_summaries":{"encounter_total_cost":9387801.31},
        "load_complete":True,"validation_summary":{"foreign_key_errors":0},
        "load_timestamp":datetime.now(timezone.utc),"loader_backend":"sqlite",
    })
    return manifest.model_copy(update={"manifest_id":manifest_identity(manifest)})


def snapshot_for(manifest, *, loader_version=LOADER_VERSION, backend="sqlite", storage="clinical.db", status="validated"):
    snapshot_id=snapshot_identity(dataset_id=manifest.dataset_id,manifest_id=manifest.manifest_id,backend_name=backend,schema_version=SCHEMA_VERSION,loader_name="sqlite",loader_version=loader_version,storage_identity=storage)
    return DatasetSnapshot(snapshot_id=snapshot_id,dataset_id=manifest.dataset_id,manifest_id=manifest.manifest_id,loader_name="sqlite",loader_version=loader_version,backend_name=backend,schema_version=SCHEMA_VERSION,load_timestamp=datetime.now(timezone.utc),load_status=status,storage_identity=storage,table_row_counts=manifest.entity_row_counts,validation_summary={"foreign_key_errors":0})


def test_fresh_repeated_and_prior_version_migrations(tmp_path):
    fresh=tmp_path/"fresh.db"
    assert apply_metadata_migrations(fresh)==2
    assert apply_metadata_migrations(fresh)==2
    with sqlite3.connect(fresh) as connection:
        assert [row[0] for row in connection.execute("SELECT version FROM platform_metadata_migrations ORDER BY version")]==[1,2]
    prior=tmp_path/"prior.db"
    assert apply_metadata_migrations(prior,(METADATA_MIGRATIONS[0],))==1
    with sqlite3.connect(prior) as connection:
        assert connection.execute("SELECT name FROM sqlite_master WHERE name='dataset_snapshots'").fetchone() is None
    assert apply_metadata_migrations(prior)==2


def test_failed_migration_rolls_back_and_future_version_is_rejected(tmp_path):
    path=tmp_path/"rollback.db"
    broken=METADATA_MIGRATIONS+(Migration(3,("CREATE TABLE rollback_probe(x INTEGER)","THIS IS NOT SQL")),)
    with pytest.raises(MetadataMigrationError): apply_metadata_migrations(path,broken)
    with sqlite3.connect(path) as connection:
        assert connection.execute("SELECT name FROM sqlite_master WHERE name='rollback_probe'").fetchone() is None
        assert connection.execute("SELECT COUNT(*) FROM platform_metadata_migrations WHERE version=3").fetchone()[0]==0
        connection.execute("INSERT INTO platform_metadata_migrations VALUES (999,'future')"); connection.commit()
    with pytest.raises(UnsupportedMetadataVersion): apply_metadata_migrations(path)


def test_manifest_registration_is_durable_idempotent_and_conflict_aware(tmp_path):
    store=SQLiteManifestStore(tmp_path/"metadata.db"); manifest=completed_manifest()
    first=store.register_manifest(manifest)
    later=manifest.model_copy(update={"generation_timestamp":manifest.generation_timestamp+timedelta(days=1),"load_timestamp":datetime.now(timezone.utc)+timedelta(days=2)})
    assert store.register_manifest(later).manifest_id==first.manifest_id
    assert store.get_manifest(manifest.dataset_id).manifest_id==manifest.manifest_id
    assert [item.manifest_id for item in store.list_manifests()]==[manifest.manifest_id]
    conflict=manifest.model_copy(update={"stable_summaries":{"encounter_total_cost":1.0}})
    with pytest.raises(MetadataConflictError): store.register_manifest(conflict)


def test_snapshot_identity_registration_and_conflicts(tmp_path):
    store=SQLiteManifestStore(tmp_path/"metadata.db"); manifest=store.register_manifest(completed_manifest())
    first=snapshot_for(manifest); store.register_snapshot(first)
    same_different_time=first.model_copy(update={"load_timestamp":first.load_timestamp+timedelta(hours=1)})
    assert store.register_snapshot(same_different_time).snapshot_id==first.snapshot_id
    assert snapshot_for(manifest,backend="future-postgresql").snapshot_id!=first.snapshot_id
    assert snapshot_for(manifest,loader_version="1.1.0").snapshot_id!=first.snapshot_id
    conflict=first.model_copy(update={"table_row_counts":{"patients":1}})
    with pytest.raises(MetadataConflictError): store.register_snapshot(conflict)


def test_active_snapshot_replacement_is_transactional(tmp_path):
    store=SQLiteManifestStore(tmp_path/"metadata.db")
    first_manifest=store.register_manifest(completed_manifest(17)); first=store.register_snapshot(snapshot_for(first_manifest)); first=store.activate_snapshot(first.snapshot_id)
    second_manifest=store.register_manifest(completed_manifest(18)); second=store.register_snapshot(snapshot_for(second_manifest,loader_version="1.1.0")); second=store.activate_snapshot(second.snapshot_id)
    assert store.get_active_snapshot("sqlite","clinical.db").snapshot_id==second.snapshot_id
    assert not store.get_snapshot(first.snapshot_id).active
    assert store.get_snapshot(first.snapshot_id).load_status=="superseded"
    assert second.replaces_snapshot_id==first.snapshot_id


def test_failed_snapshot_cannot_activate_or_replace_prior(tmp_path):
    store=SQLiteManifestStore(tmp_path/"metadata.db")
    manifest=store.register_manifest(completed_manifest()); active=store.activate_snapshot(store.register_snapshot(snapshot_for(manifest)).snapshot_id)
    other=store.register_manifest(completed_manifest(18)); failed=snapshot_for(other,status="failed").model_copy(update={"validation_summary":{"foreign_key_errors":1}})
    store.register_snapshot(failed)
    with pytest.raises(ValueError): store.activate_snapshot(failed.snapshot_id)
    assert store.get_active_snapshot("sqlite","clinical.db").snapshot_id==active.snapshot_id


def test_loader_registers_manifest_snapshot_and_preserves_active_on_validation_failure(tmp_path):
    target=tmp_path/"clinical.db"; metadata=SQLiteManifestStore(metadata_path_for(target))
    successful=SQLiteSyntheticDatasetLoader(metadata).generate(target,17,300,1200)
    old_snapshot=successful.snapshot; old_total=sqlite3.connect(target).execute("SELECT ROUND(SUM(total_cost),2) FROM encounters").fetchone()[0]
    class InvalidLoader(SQLiteSyntheticDatasetLoader):
        def load_batches(self,*args,**kwargs):
            result=super().load_batches(*args,**kwargs)
            validation={"foreign_key_errors":1,"quality_measure_errors":0,"row_count_mismatches":{}}
            return result.model_copy(update={"completed":False,"validation_summary":validation,"manifest":result.manifest.model_copy(update={"load_complete":False,"validation_summary":validation})})
    failed=InvalidLoader(metadata).generate(target,18,300,1200)
    assert not failed.completed and not failed.snapshot.active and failed.snapshot.load_status=="failed"
    assert metadata.get_active_snapshot("sqlite",target.name).snapshot_id==old_snapshot.snapshot_id
    with sqlite3.connect(target) as connection: assert connection.execute("SELECT ROUND(SUM(total_cost),2) FROM encounters").fetchone()[0]==old_total


def test_generation_failure_registers_nothing(tmp_path,monkeypatch):
    target=tmp_path/"clinical.db"; store=SQLiteManifestStore(metadata_path_for(target))
    def fail(self): raise RuntimeError("generation failed")
    monkeypatch.setattr(SyntheticRecordGenerator,"batches",fail)
    with pytest.raises(RuntimeError,match="generation failed"): SQLiteSyntheticDatasetLoader(store).generate(target,17,300,1200)
    assert store.list_manifests()==[] and store.list_snapshots()==[]


def test_version_compatibility_policy():
    policy=VersionCompatibilityPolicy()
    assert policy.check(generator_version="1.1.0",logical_schema_version="1.2",loader_version="1.0.0").compatible
    assert policy.check(generator_version="1.0.0",logical_schema_version="1.0",loader_version="1.1.0").requires_rematerialization
    assert policy.check(generator_version="2.0.0",logical_schema_version="1.0",loader_version="1.0.0").requires_regeneration
    assert not policy.check(generator_version="1.0.0",logical_schema_version="2.0",loader_version="1.0.0").compatible
    assert not policy.check(generator_version="1.0.0",logical_schema_version="1.0",loader_version="1.0.0",manifest_schema_version="2.0").compatible
    assert policy.check(generator_version="1.0.0",logical_schema_version="1.0",loader_version="1.0.0",snapshot_schema_version="2.0").requires_rematerialization


def test_legacy_audit_upgrade_and_new_provenance_lineage(tmp_path):
    legacy=tmp_path/"legacy.db"
    with sqlite3.connect(legacy) as connection:
        connection.execute("CREATE TABLE audit_runs (run_id TEXT PRIMARY KEY,user_question TEXT,normalized_question TEXT,model_name TEXT,schema_version TEXT,analysis_plan_json TEXT,generated_sql TEXT,validation_status TEXT,execution_status TEXT,result_row_count INTEGER,execution_time_ms REAL,statistical_tools_json TEXT,warnings_json TEXT,final_answer TEXT,created_at TEXT)")
        connection.execute("INSERT INTO audit_runs VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",("old","q","q","demo","1.0",None,None,"denied","denied",0,None,"null","[]","no","2025-01-01"))
    old=SQLiteAuditStore(legacy).get("old")
    assert old["run_id"]=="old" and old["provenance_json"] is None

    target=tmp_path/"lineage.db"; loaded=generate_dataset(target,17,300,1200)
    analysis=Analyst(target).analyze("How many hospitals are in the dataset?")
    audit=SQLiteAuditStore(target); row=audit.get(analysis.run_id); provenance=json.loads(row["provenance_json"])
    assert provenance["snapshot_id"]==loaded.snapshot.snapshot_id
    lineage=LineageResolver(audit,SQLiteManifestStore(metadata_path_for(target))).resolve_run(analysis.run_id)
    assert lineage["snapshot"]["snapshot_id"]==loaded.snapshot.snapshot_id
    assert lineage["manifest"]["random_seed"]==17 and lineage["manifest"]["fixture_profile"]=="test"


def test_analysis_without_or_with_corrupt_metadata_remains_legacy_safe(tmp_path):
    target=tmp_path/"legacy-analysis.db"
    generate_dataset(target,17,300,1200)
    metadata_path_for(target).unlink()
    assert Analyst(target).analyze("How many hospitals are in the dataset?").status=="completed"
    metadata_path_for(target).write_bytes(b"not sqlite")
    assert Analyst(target).analyze("How many hospitals are in the dataset?").status=="completed"
