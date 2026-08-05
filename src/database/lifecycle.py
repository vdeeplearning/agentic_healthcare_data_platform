"""Synthetic dataset lifecycle seams; SQLite remains the only loader."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True)
class FixtureProfile:
    name: str
    patients: int
    encounters: int


@dataclass(frozen=True)
class DatasetIdentity:
    dataset_id: str
    seed: int
    profile: str
    backend: str = "sqlite"
    schema_version: str = "1.0"


FIXTURE_PROFILES = {
    "test": FixtureProfile("test", 300, 1_200),
    "demo": FixtureProfile("demo", 2_500, 10_000),
    "full": FixtureProfile("full", 25_000, 100_000),
}


class SyntheticDatasetLoader(Protocol):
    """Future loaders may target files or serving stores using the same records."""

    def load(self, path: Path, seed: int, profile: FixtureProfile) -> dict[str, int]: ...


class SQLiteSyntheticDatasetLoader:
    """Compatibility loader delegating to the established deterministic generator."""

    def load(self, path: Path, seed: int, profile: FixtureProfile) -> dict[str, int]:
        from src.database.seed import generate_database

        return generate_database(path, seed, profile.patients, profile.encounters)


def dataset_identity(seed: int, profile: str = "custom") -> DatasetIdentity:
    return DatasetIdentity(dataset_id=f"synthetic-clinical-seed-{seed}", seed=seed, profile=profile)
