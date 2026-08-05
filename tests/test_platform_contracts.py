import hashlib
import json
import sqlite3
from pathlib import Path

import pytest

from src.agent.schemas import AnalysisPlan, AnalysisResponse
from src.agent.live_planner import LiveProposal
from src.agent.workflow import Analyst
from src.api.main import app
from src.audit.repository import SQLiteAuditStore
from src.config import Settings
from src.database.backend import SQLiteQueryBackend
from src.database.lifecycle import FIXTURE_PROFILES, SQLiteSyntheticDatasetLoader, dataset_identity
from src.database.models import ExecutionContext
from src.metrics.registry import METRICS


OPENAPI_SHA256 = "c7c894e32a16f4008cdc7f1a7b0b0dfae3cbd7728d7e3dae0ce0d34ed3b69fbc"
STATUS_VALUES = {"completed", "clarification_required", "denied", "failed"}
FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "compatibility_contract.json").read_text())


def _stable_response(response: AnalysisResponse) -> dict:
    value = response.model_dump(mode="json")
    value["run_id"] = "<run_id>"
    value["execution_time_ms"] = "<latency>" if value["execution_time_ms"] is not None else None
    return value


def test_generated_openapi_schema_is_frozen():
    encoded = json.dumps(app.openapi(), sort_keys=True, separators=(",", ":")).encode()
    assert hashlib.sha256(encoded).hexdigest() == OPENAPI_SHA256


def test_public_status_enum_is_frozen():
    status_schema = AnalysisResponse.model_json_schema()["properties"]["status"]
    assert set(status_schema["enum"]) == STATUS_VALUES == set(FIXTURE["statuses"])


def test_representative_response_contracts(db_path):
    analyst = Analyst(db_path)
    completed = _stable_response(analyst.analyze("How many hospitals are in the dataset?"))
    clarification = _stable_response(analyst.analyze("Which hospital is worst?"))
    denied = _stable_response(analyst.analyze("Export all patient-level records and patient IDs"))
    statistic = _stable_response(analyst.analyze("Is the readmission rate significantly different between urban and rural hospitals?"))
    assert completed["status"] == "completed" and completed["answer"] == FIXTURE["completed_hospital_answer"]
    assert clarification["status"] == "clarification_required" and clarification["sql"] is None
    assert denied["status"] == "denied" and denied["rows"] == []
    assert statistic["statistics"]["tool"] == "chi_square"
    assert list(completed) == list(AnalysisResponse.model_fields)


def test_trace_ordering_is_frozen(db_path):
    result = Analyst(db_path).analyze("How many hospitals are in the dataset?")
    assert [event.step for event in result.trace] == FIXTURE["completed_trace"]


class FixedPlanner:
    def __init__(self, sql): self.sql = sql
    def curated(self, question):
        return AnalysisPlan(normalized_question=question.lower(), analysis_intent="contract fixture", required_tables=["hospitals"]), self.sql
    def live(self, *args, **kwargs): raise AssertionError("live planner should not run")


def test_failure_and_empty_result_contracts(db_path):
    failed = Analyst(db_path, planner=FixedPlanner("SELECT imaginary FROM hospitals")).analyze("contract failure")
    empty = Analyst(db_path, planner=FixedPlanner("SELECT hospital_id FROM hospitals WHERE 1=0")).analyze("contract empty")
    assert failed.status == "failed" and failed.answer == "SQL validation failed safely."
    assert empty.status == "completed" and empty.answer == FIXTURE["empty_answer"] and empty.rows == []


def test_injected_planner_parity(db_path):
    plan = AnalysisPlan(normalized_question="count hospitals", analysis_intent="count synthetic hospitals", required_tables=["hospitals"], expected_columns=["hospital_count"])
    class PlannerAdapter:
        def curated(self, question): return plan, "SELECT COUNT(*) AS hospital_count FROM hospitals"
        def live(self, *args, **kwargs): return LiveProposal(plan=plan, sql="SELECT COUNT(*) AS hospital_count FROM hospitals")
    result = Analyst(db_path, planner=PlannerAdapter()).analyze("anything deterministic")
    assert result.status == "completed" and result.answer == FIXTURE["completed_hospital_answer"]


def test_configuration_defaults_and_environment_names(monkeypatch):
    for name in list(__import__("os").environ):
        if name.startswith("CLINICAL_SQL_"): monkeypatch.delenv(name, raising=False)
    settings = Settings(_env_file=None)
    assert settings.db_path.as_posix() == "data/generated/clinical.db"
    assert (settings.demo_mode, settings.seed, settings.max_rows, settings.small_cell_threshold) == (True, 42, 1000, 10)
    monkeypatch.setenv("CLINICAL_SQL_MAX_ROWS", "77")
    assert Settings(_env_file=None).max_rows == 77


def test_metric_snapshot_is_stable():
    assert sorted(METRICS) == sorted([
        "30-day readmission rate", "mortality rate", "complication rate", "average length of stay",
        "median length of stay", "emergency admission conversion rate", "average encounter cost",
        "total encounter cost", "encounter volume", "diagnosis prevalence",
    ])
    assert all(metric.minimum_sample_size >= 10 for metric in METRICS.values())


def test_sqlite_backend_catalog_plan_limit_and_provenance(db_path):
    backend = SQLiteQueryBackend(db_path)
    catalog = backend.discover_catalog()
    assert catalog.sql_dialect == "sqlite"
    assert {relation.kind for relation in catalog.relations} == {"table", "view"}
    assert "audit_runs" in catalog.prohibited_objects
    result = backend.execute(
        "SELECT hospital_id FROM hospitals ORDER BY hospital_id",
        ExecutionContext(run_id="contract", timeout_seconds=5, dataset_id="fixture"),
        max_rows=3,
    )
    assert result.columns == ["hospital_id"] and len(result.rows) == 3 and result.truncated
    assert result.query_plan and result.backend_name == "sqlite"
    assert result.provenance["read_only"] is True


def test_sqlite_schema_views_indexes_and_seed_invariants(db_path):
    with sqlite3.connect(db_path) as connection:
        objects = dict(connection.execute("SELECT name,type FROM sqlite_schema WHERE name NOT LIKE 'sqlite_%'"))
        assert objects["encounter_facts"] == "view" and objects["hospital_readmission_summary"] == "view"
        assert {"idx_encounters_dates", "idx_encounters_hospital", "idx_ed_diagnosis", "idx_readmissions_index"} <= set(objects)
        assert connection.execute("SELECT COUNT(*) FROM patients").fetchone()[0] == 300
        assert connection.execute("SELECT COUNT(*) FROM encounters").fetchone()[0] == 1200
        assert connection.execute("SELECT COUNT(*) FROM hospitals").fetchone()[0] == 30
        assert connection.execute("SELECT ROUND(SUM(total_cost), 2) FROM encounters").fetchone()[0] == 9387801.31


def test_sqlite_backend_cooperative_timeout(db_path):
    backend = SQLiteQueryBackend(db_path)
    sql = "WITH RECURSIVE x(n) AS (SELECT 1 UNION ALL SELECT n+1 FROM x WHERE n<100000000) SELECT SUM(n) FROM x"
    with pytest.raises(sqlite3.OperationalError, match="interrupted"):
        backend.execute(sql, ExecutionContext(run_id="timeout", timeout_seconds=0), 1)


def test_audit_store_is_idempotent_and_serializes(db_path):
    store = SQLiteAuditStore(db_path)
    record = {"run_id": "fixed-contract-run", "question": "q", "warnings": ["w"], "final_answer": "a"}
    store.write(record); store.write({**record, "final_answer": "changed"})
    row = store.get("fixed-contract-run")
    assert row["final_answer"] == "a" and json.loads(row["warnings_json"]) == ["w"]
    assert sum(item["run_id"] == "fixed-contract-run" for item in store.list(100)) == 1


def test_fixture_profiles_and_sqlite_loader(tmp_path):
    profile = FIXTURE_PROFILES["test"]
    path = tmp_path / "profile.db"
    counts = SQLiteSyntheticDatasetLoader().load(path, 17, profile)
    assert counts["patients"] == 300 and counts["encounters"] == 1200
    identity = dataset_identity(17, "test")
    assert identity.backend == "sqlite" and identity.dataset_id == "synthetic-clinical-seed-17"
