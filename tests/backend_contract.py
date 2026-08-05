"""Reusable query-backend contract; subclass this for every future backend."""
from __future__ import annotations

from src.database.models import ExecutionContext, QueryBackendError
from src.safety.sql_validator import validate_sql


class QueryBackendContract:
    """Backend-agnostic assertions supplied with `backend` and `catalog` fixtures."""

    def test_catalog_contract(self, backend, catalog):
        relations = {relation.name: relation for relation in catalog.relations}
        assert {"patients", "hospitals", "encounters", "encounter_facts", "hospital_readmission_summary"} <= set(relations)
        assert relations["patients"].kind == "table" and relations["encounter_facts"].kind == "view"
        assert {column.name for column in relations["encounters"].columns} >= {"encounter_id", "hospital_id", "total_cost"}
        assert all(column.data_type == column.data_type.lower() for relation in catalog.relations for column in relation.columns)
        assert catalog.schema_version and catalog.sql_dialect
        assert {"audit_runs", "sqlite_schema"} <= set(catalog.prohibited_objects)
        assert catalog.capabilities.read_only and catalog.capabilities.result_limit
        assert backend.name

    def test_central_policy_retains_authority(self, catalog):
        prohibited = [
            "INSERT INTO hospitals(hospital_id) VALUES(99)", "UPDATE hospitals SET state='XX'",
            "DELETE FROM encounters", "CREATE TABLE bad(x INT)", "DROP TABLE patients",
            "ALTER TABLE patients ADD COLUMN x INT", "PRAGMA table_info(patients)",
            "SELECT 1; SELECT 2",
        ]
        assert all(not validate_sql(sql, catalog=catalog).valid for sql in prohibited)

    def test_backend_read_only_boundary(self, backend):
        context = ExecutionContext(run_id="backend-write-contract")
        for sql in ("INSERT INTO hospitals(hospital_id) VALUES(99)", "UPDATE hospitals SET state='XX'", "DELETE FROM encounters", "CREATE TABLE bad(x INT)", "DROP TABLE patients", "ALTER TABLE patients ADD COLUMN x INT"):
            try:
                backend.execute(sql, context, 10)
                raise AssertionError(f"backend executed mutation: {sql}")
            except QueryBackendError as exc:
                assert exc.backend_name == backend.name and exc.code == "execution_failed"

    def test_normalized_execution_contract(self, backend):
        context = ExecutionContext(run_id="normalize", dataset_id="dataset-x", snapshot_id="snapshot-x", fixture_profile="test", generator_version="1.0.0")
        result = backend.execute(
            "SELECT patient_id, race_ethnicity, 1 AS integer_value, 1.5 AS real_value FROM patients ORDER BY patient_id",
            context,
            10,
        )
        assert result.columns == ["patient_id", "race_ethnicity", "integer_value", "real_value"]
        assert isinstance(result.rows[0]["integer_value"], int) and isinstance(result.rows[0]["real_value"], float)
        assert result.execution_time_ms >= 0 and result.backend_name == backend.name and result.truncated
        assert result.query_plan or not backend.discover_catalog().capabilities.query_plan
        assert result.provenance["dataset_id"] == "dataset-x"
        assert result.provenance["snapshot_id"] == "snapshot-x"
        assert result.provenance["fixture_profile"] == "test"
        assert result.provenance["generator_version"] == "1.0.0"
        assert result.provenance["schema_version"]

    def test_null_normalization(self, backend):
        result = backend.execute(
            "SELECT race_ethnicity FROM patients WHERE race_ethnicity IS NULL LIMIT 1",
            ExecutionContext(run_id="null"), 1,
        )
        assert result.rows and result.rows[0]["race_ethnicity"] is None

    def test_row_growth_is_bounded(self, backend):
        result = backend.execute(
            "SELECT h.hospital_id, p.patient_id FROM hospitals h CROSS JOIN patients p",
            ExecutionContext(run_id="growth"), 7,
        )
        assert len(result.rows) == 7 and result.truncated

    def test_excessive_joins_are_rejected_centrally(self, catalog):
        sql = "SELECT COUNT(*) FROM hospitals h0 " + " ".join(
            f"JOIN hospitals h{i} ON h{i}.hospital_id=h0.hospital_id" for i in range(1, 10)
        )
        report = validate_sql(sql, catalog=catalog)
        assert not report.valid and any("maximum of 8 joins" in error for error in report.errors)

