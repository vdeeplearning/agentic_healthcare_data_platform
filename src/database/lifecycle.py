"""Versioned synthetic dataset identity, manifest, and loader contracts."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Protocol

from pydantic import BaseModel, Field

from src.database.records import LogicalRecord


GENERATOR_VERSION = "1.0.0"
SCHEMA_VERSION = "1.0"
LOADER_VERSION = "1.0.0"
MANIFEST_SCHEMA_VERSION = "1.0"
SNAPSHOT_SCHEMA_VERSION = "1.0"
DISCLAIMER = "Synthetic data only; not for clinical decisions or patient care."


@dataclass(frozen=True)
class FixtureProfile:
    name: str
    patients: int
    encounters: int


FIXTURE_PROFILES = {
    "test": FixtureProfile("test", 300, 1_200),
    "demo": FixtureProfile("demo", 2_500, 10_000),
    "full": FixtureProfile("full", 25_000, 100_000),
}


class DatasetIdentity(BaseModel):
    dataset_id: str
    seed: int
    profile: str
    generator_version: str = GENERATOR_VERSION
    schema_version: str = SCHEMA_VERSION
    parameters: dict[str, int]
    backend: str = "logical"


class DatasetManifest(BaseModel):
    manifest_id: str | None = None
    manifest_schema_version: str = MANIFEST_SCHEMA_VERSION
    dataset_id: str
    generator_version: str
    schema_version: str
    fixture_profile: str
    random_seed: int
    generation_parameters: dict[str, int]
    entity_row_counts: dict[str, int] = Field(default_factory=dict)
    generation_timestamp: datetime
    load_timestamp: datetime | None = None
    loader_backend: str | None = None
    stable_summaries: dict[str, Any] = Field(default_factory=dict)
    source_type: str = "synthetic"
    clinical_use_disclaimer: str = DISCLAIMER
    load_complete: bool = False
    validation_summary: dict[str, Any] = Field(default_factory=dict)


@dataclass(frozen=True)
class LogicalRecordBatch:
    entity: str
    records: tuple[LogicalRecord, ...]


class DatasetSnapshot(BaseModel):
    snapshot_id: str
    dataset_id: str
    manifest_id: str
    loader_name: str
    loader_version: str
    backend_name: str
    schema_version: str
    snapshot_schema_version: str = SNAPSHOT_SCHEMA_VERSION
    load_timestamp: datetime
    load_status: str
    storage_identity: str
    materialization_parameters: dict[str, Any] = Field(default_factory=dict)
    source_batch_ids: list[str] = Field(default_factory=list)
    table_row_counts: dict[str, int] = Field(default_factory=dict)
    validation_summary: dict[str, Any] = Field(default_factory=dict)
    active: bool = False
    replaces_snapshot_id: str | None = None
    provenance_metadata: dict[str, Any] = Field(default_factory=dict)


class LoadResult(BaseModel):
    manifest: DatasetManifest
    snapshot: DatasetSnapshot | None = None
    row_counts: dict[str, int]
    completed: bool
    validation_summary: dict[str, Any] = Field(default_factory=dict)


class SyntheticDatasetLoader(Protocol):
    name: str
    def create_schema(self, target: Path) -> None: ...
    def load_batches(self, target: Path, batches: Iterable[LogicalRecordBatch], manifest: DatasetManifest) -> LoadResult: ...
    def load(self, path: Path, seed: int, profile: FixtureProfile) -> dict[str, int]: ...


def profile_name(patients: int, encounters: int) -> str:
    for profile in FIXTURE_PROFILES.values():
        if (patients, encounters) == (profile.patients, profile.encounters):
            return profile.name
    return "custom"


def dataset_identity(seed: int, profile: str = "custom", *, patients: int | None = None, encounters: int | None = None) -> DatasetIdentity:
    if profile in FIXTURE_PROFILES:
        selected = FIXTURE_PROFILES[profile]
        patients = selected.patients if patients is None else patients
        encounters = selected.encounters if encounters is None else encounters
    parameters = {"patients": int(patients or 0), "encounters": int(encounters or 0), "hospitals": 30, "providers": 200}
    payload = {"seed": seed, "profile": profile, "generator_version": GENERATOR_VERSION, "schema_version": SCHEMA_VERSION, "parameters": parameters}
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()[:20]
    return DatasetIdentity(dataset_id=f"synthetic-clinical-{digest}", seed=seed, profile=profile, parameters=parameters)


def new_manifest(seed: int, patients: int, encounters: int) -> DatasetManifest:
    profile = profile_name(patients, encounters)
    identity = dataset_identity(seed, profile, patients=patients, encounters=encounters)
    return DatasetManifest(
        dataset_id=identity.dataset_id,
        generator_version=identity.generator_version,
        schema_version=identity.schema_version,
        fixture_profile=profile,
        random_seed=seed,
        generation_parameters=identity.parameters,
        generation_timestamp=datetime.now(timezone.utc),
    )


def _stable_hash(prefix: str, payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()
    return f"{prefix}-{hashlib.sha256(encoded).hexdigest()[:20]}"


def manifest_identity(manifest: DatasetManifest) -> str:
    """Identify logical manifest content; timestamps and load-event fields are excluded."""
    return _stable_hash("manifest", {
        "dataset_id": manifest.dataset_id,
        "generator_version": manifest.generator_version,
        "schema_version": manifest.schema_version,
        "fixture_profile": manifest.fixture_profile,
        "random_seed": manifest.random_seed,
        "generation_parameters": manifest.generation_parameters,
        "entity_row_counts": manifest.entity_row_counts,
        "stable_summaries": manifest.stable_summaries,
        "source_type": manifest.source_type,
        "clinical_use_disclaimer": manifest.clinical_use_disclaimer,
        "manifest_schema_version": manifest.manifest_schema_version,
    })


def snapshot_identity(*, dataset_id: str, manifest_id: str, backend_name: str, schema_version: str, loader_name: str, loader_version: str, storage_identity: str, materialization_parameters: dict[str, Any] | None = None) -> str:
    """Identify a materialization; load timestamps deliberately do not participate."""
    return _stable_hash("snapshot", {
        "dataset_id": dataset_id,
        "manifest_id": manifest_id,
        "backend_name": backend_name,
        "schema_version": schema_version,
        "loader_name": loader_name,
        "loader_version": loader_version,
        "storage_identity": storage_identity,
        "materialization_parameters": materialization_parameters or {},
        "snapshot_schema_version": SNAPSHOT_SCHEMA_VERSION,
    })


class CompatibilityDecision(BaseModel):
    compatible: bool
    requires_regeneration: bool = False
    requires_rematerialization: bool = False
    reason: str


class VersionCompatibilityPolicy:
    """Small current-major policy, not a general-purpose schema registry."""

    @staticmethod
    def _major(version: str) -> int:
        try: return int(version.split(".", 1)[0])
        except (ValueError, AttributeError): raise ValueError(f"Invalid version: {version}")

    def check(self, *, generator_version: str, logical_schema_version: str, loader_version: str, manifest_schema_version: str = MANIFEST_SCHEMA_VERSION, snapshot_schema_version: str = SNAPSHOT_SCHEMA_VERSION) -> CompatibilityDecision:
        if self._major(manifest_schema_version) != self._major(MANIFEST_SCHEMA_VERSION):
            return CompatibilityDecision(compatible=False, reason="Manifest schema major version is incompatible.")
        if self._major(snapshot_schema_version) != self._major(SNAPSHOT_SCHEMA_VERSION):
            return CompatibilityDecision(compatible=False, requires_rematerialization=True, reason="Snapshot schema major version is incompatible.")
        if self._major(generator_version) != self._major(GENERATOR_VERSION):
            return CompatibilityDecision(compatible=False, requires_regeneration=True, reason="Generator major version is incompatible.")
        if self._major(logical_schema_version) != self._major(SCHEMA_VERSION):
            return CompatibilityDecision(compatible=False, requires_regeneration=True, requires_rematerialization=True, reason="Logical schema major version is incompatible.")
        if self._major(loader_version) != self._major(LOADER_VERSION):
            return CompatibilityDecision(compatible=False, requires_rematerialization=True, reason="Loader major version is incompatible.")
        rematerialize = loader_version != LOADER_VERSION
        return CompatibilityDecision(compatible=True, requires_rematerialization=rematerialize, reason="Versions share supported major compatibility.")


# Imported last to avoid a lifecycle/generator/loader import cycle while retaining
# the public class location introduced in the previous milestone.
def _sqlite_loader_class():
    from src.database.sqlite_loader import SQLiteSyntheticDatasetLoader
    return SQLiteSyntheticDatasetLoader


class SQLiteSyntheticDatasetLoader:
    """Compatibility constructor forwarding to the SQLite loader implementation."""
    def __new__(cls, *args, **kwargs):
        return _sqlite_loader_class()(*args, **kwargs)
