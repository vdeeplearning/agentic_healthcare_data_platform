from __future__ import annotations

import hashlib
import sqlite3

from src.agent.workflow import Analyst
from src.database.generator import SyntheticRecordGenerator
from src.database.lifecycle import GENERATOR_VERSION, dataset_identity
from src.database.backend import SQLiteQueryBackend
from src.database.records import EncounterRecord, PatientRecord
from src.database.seed import generate_dataset


def _logical_digest(seed: int, patients: int = 50, encounters: int = 200) -> str:
    digest = hashlib.sha256()
    for batch in SyntheticRecordGenerator(seed, patients, encounters, batch_size=23).batches():
        digest.update(batch.entity.encode())
        for record in batch.records:
            digest.update(repr(tuple(record)).encode())
    return digest.hexdigest()


def test_logical_generation_is_typed_streamed_and_deterministic():
    generator = SyntheticRecordGenerator(9, 50, 200, batch_size=17)
    batches = list(generator.batches())
    assert any(isinstance(record, PatientRecord) for batch in batches for record in batch.records)
    assert any(isinstance(record, EncounterRecord) for batch in batches for record in batch.records)
    assert max(len(batch.records) for batch in batches if batch.entity in {"patients", "encounters"}) <= 17
    assert _logical_digest(9) == _logical_digest(9) != _logical_digest(10)


def test_dataset_identity_is_versioned_and_parameter_sensitive():
    base = dataset_identity(17, "test")
    assert base.generator_version == GENERATOR_VERSION
    assert base.dataset_id == dataset_identity(17, "test").dataset_id
    assert base.dataset_id != dataset_identity(18, "test").dataset_id
    assert base.dataset_id != dataset_identity(17, "test", encounters=1201).dataset_id


def test_manifest_and_loader_validation(tmp_path):
    target = tmp_path / "manifest.db"
    result = generate_dataset(target, 17, 300, 1200)
    manifest = result.manifest
    assert result.completed and manifest.load_complete
    assert manifest.dataset_id == dataset_identity(17, "test").dataset_id
    assert manifest.fixture_profile == "test" and manifest.loader_backend == "sqlite"
    assert manifest.entity_row_counts["patients"] == 300 and manifest.entity_row_counts["encounters"] == 1200
    assert manifest.validation_summary == {"foreign_key_errors": 0, "quality_measure_errors": 0}
    assert manifest.stable_summaries["encounter_total_cost"] == 9387801.31
    assert manifest.source_type == "synthetic" and "not for clinical" in manifest.clinical_use_disclaimer


def test_loaded_dataset_invariants_and_curated_output(tmp_path):
    target = tmp_path / "invariants.db"
    generate_dataset(target, 17, 300, 1200)
    with sqlite3.connect(target) as connection:
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
        assert connection.execute("SELECT COUNT(*)=COUNT(DISTINCT patient_id) FROM patients").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM patients WHERE sex NOT IN ('F','M','X')").fetchone()[0] == 0
        assert connection.execute("SELECT COUNT(*) FROM encounters WHERE encounter_type NOT IN ('inpatient','emergency','outpatient')").fetchone()[0] == 0
        assert connection.execute("SELECT COUNT(*) FROM encounters WHERE discharge_date<admission_date").fetchone()[0] == 0
        assert connection.execute("SELECT COUNT(*) FROM quality_measures WHERE numerator>denominator OR measure_value NOT BETWEEN 0 AND 1").fetchone()[0] == 0
    result = Analyst(target).analyze("How many hospitals are in the dataset?")
    assert result.status == "completed" and result.answer == "The synthetic dataset contains 30 hospitals."


def test_analyst_attaches_injected_dataset_identity_internally(tmp_path):
    target = tmp_path / "context.db"
    generate_dataset(target, 17, 300, 1200)
    class CapturingBackend(SQLiteQueryBackend):
        def execute(self, sql, context, max_rows):
            self.context = context
            return super().execute(sql, context, max_rows)
    backend = CapturingBackend(target)
    identity = dataset_identity(17, "test")
    result = Analyst(target, query_backend=backend, dataset_identity=identity).analyze("How many hospitals are in the dataset?")
    assert result.status == "completed"
    assert backend.context.dataset_id == identity.dataset_id
    assert backend.context.fixture_profile == "test" and backend.context.generator_version == GENERATOR_VERSION


def test_same_seed_loads_equivalent_databases(tmp_path):
    first, second = tmp_path / "first.db", tmp_path / "second.db"
    one = generate_dataset(first, 9, 50, 200)
    two = generate_dataset(second, 9, 50, 200)
    assert one.manifest.dataset_id == two.manifest.dataset_id
    with sqlite3.connect(first) as left, sqlite3.connect(second) as right:
        for table in ("patients", "hospitals", "providers", "encounters", "encounter_diagnoses", "readmissions", "quality_measures"):
            assert left.execute(f"SELECT * FROM {table} ORDER BY 1").fetchall() == right.execute(f"SELECT * FROM {table} ORDER BY 1").fetchall()
