"""SQLite persistence for engine-neutral synthetic record batches."""
from __future__ import annotations

import sqlite3
import os
import uuid
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from src.database.connection import connect_writable
from src.database.generator import SyntheticRecordGenerator
from src.database.lifecycle import (
    LOADER_VERSION, SCHEMA_VERSION, DatasetManifest, DatasetSnapshot, FixtureProfile,
    LoadResult, LogicalRecordBatch, manifest_identity, snapshot_identity,
)
from src.metadata.repository import ManifestStore, SQLiteManifestStore, metadata_path_for


ROOT = Path(__file__).resolve().parents[2]
INSERTS = {
    "patients": "INSERT INTO patients VALUES (?,?,?,?,?,?,?)",
    "hospitals": "INSERT INTO hospitals VALUES (?,?,?,?,?,?,?)",
    "providers": "INSERT INTO providers VALUES (?,?,?,?)",
    "encounters": "INSERT INTO encounters VALUES (?,?,?,?,?,?,?,?,?,?,?)",
    "diagnoses": "INSERT INTO diagnoses VALUES (?,?,?,?)",
    "encounter_diagnoses": "INSERT INTO encounter_diagnoses VALUES (?,?,?,?)",
    "procedures": "INSERT INTO procedures VALUES (?,?,?,?)",
    "encounter_procedures": "INSERT OR IGNORE INTO encounter_procedures VALUES (?,?,?)",
    "lab_results": "INSERT INTO lab_results VALUES (?,?,?,?,?,?,?,?)",
    "readmissions": "INSERT INTO readmissions VALUES (?,?,?,?,?)",
    "quality_measures": "INSERT INTO quality_measures VALUES (?,?,?,?,?,?,?,?)",
}


def _script(connection: sqlite3.Connection, name: str) -> None:
    connection.executescript((ROOT / "sql" / name).read_text(encoding="utf-8"))


def _transactional_script(connection: sqlite3.Connection, name: str) -> None:
    """Execute the simple project DDL without `executescript`'s implicit commit."""
    for statement in (ROOT / "sql" / name).read_text(encoding="utf-8").split(";"):
        if statement.strip():
            connection.execute(statement)


class SQLiteSyntheticDatasetLoader:
    """Transactional, batched loader; unrelated to analytical query execution."""

    name = "sqlite"
    version = LOADER_VERSION

    def __init__(self, manifest_store: ManifestStore | None = None):
        self.manifest_store = manifest_store

    def create_schema(self, target: Path) -> None:
        target.parent.mkdir(parents=True, exist_ok=True)
        connection=connect_writable(target)
        try: _script(connection, "schema.sql")
        finally: connection.close()

    def load_batches(self, target: Path, batches: Iterable[LogicalRecordBatch], manifest: DatasetManifest) -> LoadResult:
        counts: Counter[str] = Counter({entity: 0 for entity in INSERTS})
        connection = connect_writable(target)
        try:
            connection.execute("BEGIN")
            for batch in batches:
                if batch.entity not in INSERTS:
                    raise ValueError(f"Unsupported logical entity: {batch.entity}")
                if batch.records:
                    connection.executemany(INSERTS[batch.entity], batch.records)
                    counts[batch.entity] += len(batch.records)
            _transactional_script(connection, "indexes.sql")
            _transactional_script(connection, "views.sql")
            connection.commit()
            connection.execute("PRAGMA optimize")
            foreign_key_errors = len(connection.execute("PRAGMA foreign_key_check").fetchall())
            total_cost = connection.execute("SELECT ROUND(SUM(total_cost),2) FROM encounters").fetchone()[0]
            quality_errors = connection.execute(
                "SELECT COUNT(*) FROM quality_measures WHERE numerator>denominator OR measure_value<0 OR measure_value>1"
            ).fetchone()[0]
            actual_counts={entity:connection.execute(f'SELECT COUNT(*) FROM "{entity}"').fetchone()[0] for entity in INSERTS}
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()
        row_count_mismatches={entity:{"expected":counts[entity],"actual":actual_counts[entity]} for entity in INSERTS if counts[entity]!=actual_counts[entity]}
        validation = {"foreign_key_errors": foreign_key_errors, "quality_measure_errors": quality_errors, "row_count_mismatches":row_count_mismatches}
        completed = not foreign_key_errors and not quality_errors and not row_count_mismatches
        loaded_manifest = manifest.model_copy(update={
            "entity_row_counts": dict(sorted(counts.items())),
            "load_timestamp": datetime.now(timezone.utc),
            "loader_backend": self.name,
            "stable_summaries": {"encounter_total_cost": total_cost},
            "load_complete": completed,
            "validation_summary": validation,
        })
        return LoadResult(manifest=loaded_manifest, row_counts=actual_counts, completed=completed, validation_summary=validation)

    def generate(self, path: Path, seed: int, patients: int, encounters: int) -> LoadResult:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        store = self.manifest_store or SQLiteManifestStore(metadata_path_for(path))
        generator = SyntheticRecordGenerator(seed, patients, encounters)
        staging = path.with_name(f".{path.name}.{uuid.uuid4().hex}.loading")
        backup = path.with_name(f".{path.name}.{uuid.uuid4().hex}.previous")
        try:
            self.create_schema(staging)
            result = self.load_batches(staging, generator.batches(), generator.manifest)
            manifest_id = manifest_identity(result.manifest)
            manifest = store.register_manifest(result.manifest.model_copy(update={"manifest_id":manifest_id}))
            previous = store.get_active_snapshot(self.name, path.name)
            snapshot_id = snapshot_identity(
                dataset_id=manifest.dataset_id, manifest_id=manifest_id, backend_name=self.name,
                schema_version=SCHEMA_VERSION, loader_name=self.name, loader_version=self.version,
                storage_identity=path.name,
                materialization_parameters={"fixture_profile":manifest.fixture_profile,"patients":patients,"encounters":encounters},
            )
            snapshot = DatasetSnapshot(
                snapshot_id=snapshot_id,dataset_id=manifest.dataset_id,manifest_id=manifest_id,
                loader_name=self.name,loader_version=self.version,backend_name=self.name,
                schema_version=SCHEMA_VERSION,load_timestamp=result.manifest.load_timestamp or datetime.now(timezone.utc),
                load_status="validated" if result.completed else "failed",storage_identity=path.name,
                materialization_parameters={"fixture_profile":manifest.fixture_profile,"patients":patients,"encounters":encounters},
                table_row_counts=result.row_counts,validation_summary=result.validation_summary,
                replaces_snapshot_id=previous.snapshot_id if previous else None,
                provenance_metadata={"source_type":"synthetic","generator_version":manifest.generator_version},
            )
            snapshot = store.register_snapshot(snapshot)
            if not result.completed:
                return result.model_copy(update={"manifest":manifest,"snapshot":snapshot})
            had_previous = path.exists()
            if had_previous: os.replace(path, backup)
            os.replace(staging, path)
            try:
                snapshot = store.activate_snapshot(snapshot.snapshot_id)
            except Exception:
                if path.exists(): path.unlink()
                if had_previous and backup.exists(): os.replace(backup, path)
                raise
            if backup.exists(): backup.unlink()
            return result.model_copy(update={"manifest":manifest,"snapshot":snapshot})
        except Exception:
            if backup.exists():
                if path.exists(): path.unlink()
                os.replace(backup, path)
            raise
        finally:
            if staging.exists(): staging.unlink()
            if backup.exists() and path.exists(): backup.unlink()

    def load(self, path: Path, seed: int, profile: FixtureProfile) -> dict[str, int]:
        result = self.generate(path, seed, profile.patients, profile.encounters)
        return legacy_counts(result.row_counts)


def legacy_counts(counts: dict[str, int]) -> dict[str, int]:
    """Preserve the exact historical `generate_database` return shape."""
    return {
        "patients": counts.get("patients", 0),
        "hospitals": counts.get("hospitals", 0),
        "providers": counts.get("providers", 0),
        "encounters": counts.get("encounters", 0),
        "readmissions": counts.get("readmissions", 0),
    }
