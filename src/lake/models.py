"""Focused, versioned models for the project's medallion data lifecycle."""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


LAKE_SCHEMA_VERSION = "1.0"


class LakeLayer(str, Enum):
    raw = "raw"
    bronze = "bronze"
    silver = "silver"
    gold = "gold"


class SourceSystem(BaseModel):
    source_system_id: str
    name: str
    source_type: str = "synthetic"
    version: str = "1.0"


class DataObject(BaseModel):
    object_id: str
    layer: LakeLayer
    entity: str
    relative_path: str
    format: str = "jsonl"
    checksum: str
    row_count: int
    size_bytes: int
    schema_version: str = LAKE_SCHEMA_VERSION


class SourceBatch(BaseModel):
    batch_id: str
    source_system: SourceSystem
    generator_version: str
    generation_parameters: dict[str, int]
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    dataset_id: str
    random_seed: int
    fixture_profile: str
    objects: list[DataObject]
    row_counts: dict[str, int]
    schema_version: str = LAKE_SCHEMA_VERSION
    disclaimer: str
    parent_batch_id: str | None = None
    batch_kind: str = "initial"


class ValidationResult(BaseModel):
    passed: bool
    checks: dict[str, bool] = Field(default_factory=dict)
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    rejected_rows: int = 0


class LayerManifest(BaseModel):
    manifest_id: str
    layer: LakeLayer
    dataset_id: str
    transformation_name: str
    transformation_version: str
    parent_ids: list[str]
    objects: list[DataObject]
    row_counts: dict[str, int]
    rejected_row_counts: dict[str, int] = Field(default_factory=dict)
    validation: ValidationResult
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    schema_version: str = LAKE_SCHEMA_VERSION


class TransformationDefinition(BaseModel):
    name: str
    version: str
    input_layer: LakeLayer | None
    output_layer: LakeLayer


class TransformationRun(BaseModel):
    run_id: str
    definition: TransformationDefinition
    input_ids: list[str]
    output_manifest_id: str | None = None
    status: str
    validation: ValidationResult
    started_at: datetime
    completed_at: datetime
    orchestration_run_id: str | None = None
    distributed_job_id: str | None = None


class PublicationCandidate(BaseModel):
    candidate_id: str
    layer_manifest_id: str
    layer: LakeLayer
    validation: ValidationResult


class PublishedSnapshot(BaseModel):
    snapshot_id: str
    layer: LakeLayer
    layer_manifest_id: str
    dataset_id: str
    parent_snapshot_ids: list[str]
    object_ids: list[str]
    active: bool = False
    status: str = "validated"
    replaces_snapshot_id: str | None = None
    published_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = Field(default_factory=dict)


class LineageEdge(BaseModel):
    parent_id: str
    child_id: str
    relationship: str
    transformation_name: str
    transformation_version: str
    checksums: list[str] = Field(default_factory=list)
    validation_passed: bool
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
