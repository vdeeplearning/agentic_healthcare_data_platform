"""Publish a validated gold snapshot through the existing serving loaders."""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

from src.database.lifecycle import DatasetSnapshot, LogicalRecordBatch, SCHEMA_VERSION, manifest_identity, new_manifest, snapshot_identity
from src.database.postgres_loader import PostgresLoader
from src.database.records import (
    DiagnosisRecord, EncounterDiagnosisRecord, EncounterProcedureRecord, EncounterRecord,
    HospitalRecord, LabResultRecord, PatientRecord, ProcedureRecord, ProviderRecord,
    QualityMeasureRecord, ReadmissionRecord,
)
from src.database.sqlite_loader import SQLiteSyntheticDatasetLoader
from src.lake.models import LakeLayer, LineageEdge
from src.lake.store import LocalFilesystemLakeStore
from src.metadata.repository import ManifestStore, SQLiteManifestStore, metadata_path_for


RECORD_TYPES={
    "patients":PatientRecord,"hospitals":HospitalRecord,"providers":ProviderRecord,"encounters":EncounterRecord,
    "diagnoses":DiagnosisRecord,"encounter_diagnoses":EncounterDiagnosisRecord,"procedures":ProcedureRecord,
    "encounter_procedures":EncounterProcedureRecord,"lab_results":LabResultRecord,"readmissions":ReadmissionRecord,
    "quality_measures":QualityMeasureRecord,
}
LOAD_ORDER=("hospitals","providers","patients","diagnoses","procedures","encounters","encounter_diagnoses","encounter_procedures","lab_results","readmissions","quality_measures")


def gold_batches(store:LocalFilesystemLakeStore,gold_snapshot_id:str):
    snapshot=store.get_snapshot(gold_snapshot_id)
    if not snapshot or snapshot.layer!=LakeLayer.gold or not snapshot.active: raise ValueError("Serving publication requires an active gold snapshot.")
    manifest=store.get_layer_manifest(snapshot.layer_manifest_id)
    if not manifest or not manifest.validation.passed: raise ValueError("Gold manifest is not validated.")
    import json
    by_entity={item.entity:item for item in manifest.objects}
    for entity in LOAD_ORDER:
        item=by_entity[entity]
        record_type=RECORD_TYPES[item.entity]
        rows=[record_type(**json.loads(line)) for line in store.read_object(item).splitlines()]
        yield LogicalRecordBatch(entity=item.entity,records=tuple(rows))


def _logical_manifest(gold):
    parameters=gold.metadata["generation_parameters"]
    manifest=new_manifest(gold.metadata["random_seed"],parameters["patients"],parameters["encounters"])
    return manifest.model_copy(update={"dataset_id":gold.dataset_id,"generator_version":gold.metadata["generator_version"],"fixture_profile":gold.metadata["fixture_profile"]})


def _register(result,gold,backend_name,storage_identity,store:ManifestStore):
    manifest_id=manifest_identity(result.manifest); manifest=store.register_manifest(result.manifest.model_copy(update={"manifest_id":manifest_id}))
    previous=store.get_active_snapshot(backend_name,storage_identity)
    snapshot_id=snapshot_identity(dataset_id=manifest.dataset_id,manifest_id=manifest_id,backend_name=backend_name,schema_version=SCHEMA_VERSION,loader_name=backend_name,loader_version="1.0.0",storage_identity=storage_identity,materialization_parameters={"gold_snapshot_id":gold.snapshot_id})
    snapshot=DatasetSnapshot(snapshot_id=snapshot_id,dataset_id=manifest.dataset_id,manifest_id=manifest_id,loader_name=backend_name,loader_version="1.0.0",backend_name=backend_name,schema_version=SCHEMA_VERSION,load_timestamp=result.manifest.load_timestamp or datetime.now(timezone.utc),load_status="validated" if result.completed else "failed",storage_identity=storage_identity,materialization_parameters={"gold_snapshot_id":gold.snapshot_id},source_batch_ids=[gold.metadata["source_batch_id"]],table_row_counts=result.row_counts,validation_summary=result.validation_summary,replaces_snapshot_id=previous.snapshot_id if previous else None,provenance_metadata={"source_type":"lake-gold","gold_snapshot_id":gold.snapshot_id,"gold_manifest_id":gold.layer_manifest_id})
    return manifest,store.register_snapshot(snapshot)


def publish_gold_to_sqlite(lake:LocalFilesystemLakeStore,gold_snapshot_id:str,target:Path,manifest_store:ManifestStore|None=None):
    gold=lake.get_snapshot(gold_snapshot_id)
    if not gold: raise KeyError(gold_snapshot_id)
    target=Path(target); target.parent.mkdir(parents=True,exist_ok=True); metadata=manifest_store or SQLiteManifestStore(metadata_path_for(target)); loader=SQLiteSyntheticDatasetLoader(metadata)
    staging=target.with_name(f".{target.name}.{uuid.uuid4().hex}.lake-loading"); backup=target.with_name(f".{target.name}.{uuid.uuid4().hex}.previous")
    try:
        loader.create_schema(staging); result=loader.load_batches(staging,gold_batches(lake,gold_snapshot_id),_logical_manifest(gold)); manifest,snapshot=_register(result,gold,"sqlite",target.name,metadata)
        if not result.completed: return result.model_copy(update={"manifest":manifest,"snapshot":snapshot})
        had_previous=target.exists()
        if had_previous: os.replace(target,backup)
        os.replace(staging,target)
        try: snapshot=metadata.activate_snapshot(snapshot.snapshot_id)
        except Exception:
            if target.exists(): target.unlink()
            if had_previous: os.replace(backup,target)
            raise
        if backup.exists(): backup.unlink()
        lake.register_edge(LineageEdge(parent_id=gold.snapshot_id,child_id=snapshot.snapshot_id,relationship="served_as",transformation_name="gold-to-sqlite",transformation_version="1.0.0",validation_passed=True))
        return result.model_copy(update={"manifest":manifest,"snapshot":snapshot})
    finally:
        if staging.exists(): staging.unlink()


def publish_gold_to_postgres(lake:LocalFilesystemLakeStore,gold_snapshot_id:str,dsn:str,metadata:ManifestStore,schema:str="public",storage_identity:str|None=None):
    gold=lake.get_snapshot(gold_snapshot_id)
    if not gold: raise KeyError(gold_snapshot_id)
    identity=storage_identity or f"postgres:{schema}"; loader=PostgresLoader(dsn,metadata,schema,identity)
    result=loader.load_batches(gold_batches(lake,gold_snapshot_id),_logical_manifest(gold)); manifest,snapshot=_register(result,gold,"postgres",identity,metadata)
    if result.completed: snapshot=metadata.activate_snapshot(snapshot.snapshot_id); lake.register_edge(LineageEdge(parent_id=gold.snapshot_id,child_id=snapshot.snapshot_id,relationship="served_as",transformation_name="gold-to-postgres",transformation_version="1.0.0",validation_passed=True))
    return result.model_copy(update={"manifest":manifest,"snapshot":snapshot})
