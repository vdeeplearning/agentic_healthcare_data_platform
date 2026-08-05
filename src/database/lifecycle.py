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


class LoadResult(BaseModel):
    manifest: DatasetManifest
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


# Imported last to avoid a lifecycle/generator/loader import cycle while retaining
# the public class location introduced in the previous milestone.
def _sqlite_loader_class():
    from src.database.sqlite_loader import SQLiteSyntheticDatasetLoader
    return SQLiteSyntheticDatasetLoader


class SQLiteSyntheticDatasetLoader:
    """Compatibility constructor forwarding to the SQLite loader implementation."""
    def __new__(cls, *args, **kwargs):
        return _sqlite_loader_class()(*args, **kwargs)
