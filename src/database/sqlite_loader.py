"""SQLite persistence for engine-neutral synthetic record batches."""
from __future__ import annotations

import sqlite3
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from src.database.connection import connect_writable
from src.database.generator import SyntheticRecordGenerator
from src.database.lifecycle import DatasetManifest, FixtureProfile, LoadResult, LogicalRecordBatch


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

    def create_schema(self, target: Path) -> None:
        target.parent.mkdir(parents=True, exist_ok=True)
        with connect_writable(target) as connection:
            _script(connection, "schema.sql")

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
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()
        validation = {"foreign_key_errors": foreign_key_errors, "quality_measure_errors": quality_errors}
        completed = not foreign_key_errors and not quality_errors
        loaded_manifest = manifest.model_copy(update={
            "entity_row_counts": dict(sorted(counts.items())),
            "load_timestamp": datetime.now(timezone.utc),
            "loader_backend": self.name,
            "stable_summaries": {"encounter_total_cost": total_cost},
            "load_complete": completed,
            "validation_summary": validation,
        })
        return LoadResult(manifest=loaded_manifest, row_counts=dict(counts), completed=completed, validation_summary=validation)

    def generate(self, path: Path, seed: int, patients: int, encounters: int) -> LoadResult:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            path.unlink()
        generator = SyntheticRecordGenerator(seed, patients, encounters)
        self.create_schema(path)
        return self.load_batches(path, generator.batches(), generator.manifest)

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
