"""Opt-in PostgreSQL parity suite. Set CLINICAL_SQL_TEST_POSTGRES_DSN to run."""
from __future__ import annotations

import os
import uuid

import pytest
from fastapi.testclient import TestClient

from src.agent.workflow import Analyst
from src.database.postgres_backend import PostgresQueryBackend,_driver
from src.database.postgres_loader import PostgresLoader
from src.database.lifecycle import LogicalRecordBatch
from src.database.models import ExecutionContext
from src.database.seed import generate_dataset
from src.metadata.repository import SQLiteManifestStore
from src.metadata.lineage import LineageResolver
from src.audit.repository import SQLiteAuditStore
from src.evaluation.backend_parity import run_backend_parity
from .backend_contract import QueryBackendContract


@pytest.fixture(scope="session")
def postgres_environment(tmp_path_factory):
    dsn=os.getenv("CLINICAL_SQL_TEST_POSTGRES_DSN")
    if not dsn: pytest.skip("CLINICAL_SQL_TEST_POSTGRES_DSN is not configured")
    schema=f"clinical_contract_{uuid.uuid4().hex[:12]}"
    metadata=SQLiteManifestStore(tmp_path_factory.mktemp("postgres-metadata")/"metadata.db")
    loader=PostgresLoader(dsn,metadata,schema,storage_identity=f"postgres-test:{schema}")
    result=loader.generate(17,300,1200)
    backend=PostgresQueryBackend(dsn,schema,loader.storage_identity)
    try:
        yield {"dsn":dsn,"schema":schema,"metadata":metadata,"loader":loader,"result":result,"backend":backend}
    finally:
        psycopg,sql,dict_row=_driver()
        connection=psycopg.connect(dsn,row_factory=dict_row,autocommit=True)
        try: connection.execute(sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(sql.Identifier(schema)))
        finally: connection.close()


@pytest.fixture
def backend(postgres_environment):
    return postgres_environment["backend"]


@pytest.fixture
def catalog(backend):
    return backend.discover_catalog()


@pytest.fixture
def timeout_sql():
    return "SELECT pg_sleep(1)"


class TestPostgresQueryBackendContract(QueryBackendContract):
    pass


def test_sqlite_postgres_snapshot_and_analytical_parity(postgres_environment,tmp_path):
    postgres_result=postgres_environment["result"]
    audit_path=tmp_path/"audit.db"
    sqlite_result=generate_dataset(audit_path,17,300,1200)
    assert sqlite_result.manifest.dataset_id==postgres_result.manifest.dataset_id
    assert sqlite_result.manifest.manifest_id==postgres_result.manifest.manifest_id
    assert sqlite_result.snapshot.snapshot_id!=postgres_result.snapshot.snapshot_id
    postgres_analyst=Analyst(audit_path,query_backend=postgres_environment["backend"],dataset_snapshot=postgres_result.snapshot)
    for question in ("How many hospitals are in the dataset?","How many patients are in the dataset?","Which diagnoses account for the highest total cost?"):
        sqlite=Analyst(audit_path).analyze(question)
        postgres=postgres_analyst.analyze(question)
        assert postgres.status==sqlite.status=="completed"
        assert postgres.columns==sqlite.columns and postgres.rows==sqlite.rows and postgres.answer==sqlite.answer


def test_machine_readable_live_parity_report(postgres_environment,tmp_path):
    sqlite_result=generate_dataset(tmp_path/"parity.db",17,300,1200)
    report=run_backend_parity(tmp_path/"parity.db",postgres_environment["backend"],sqlite_result.snapshot,postgres_environment["result"].snapshot)
    assert report["summary"]=={"questions":7,"status_matches":7,"exact_result_matches":7,"numeric_matches":7,"warning_matches":7,"answer_matches":7}
    assert all(item["dataset_id"]==sqlite_result.manifest.dataset_id for item in report["items"])


def test_live_postgres_failed_load_rolls_back_to_prior_snapshot(postgres_environment):
    environment=postgres_environment; before=environment["backend"].execute("SELECT COUNT(*) AS count FROM encounters",ExecutionContext(run_id="before"),10).rows[0]["count"]
    with pytest.raises(ValueError,match="Unsupported logical entity"):
        environment["loader"].load_batches([LogicalRecordBatch(entity="unknown",records=())],environment["result"].manifest)
    after=environment["backend"].execute("SELECT COUNT(*) AS count FROM encounters",ExecutionContext(run_id="after"),10).rows[0]["count"]
    assert before==after==1200
    assert environment["metadata"].get_active_snapshot("postgres",environment["loader"].storage_identity).snapshot_id==environment["result"].snapshot.snapshot_id


def test_live_postgres_api_audit_and_lineage_without_contract_changes(postgres_environment,tmp_path,monkeypatch):
    from src.api import main as api_main
    audit_path=tmp_path/"api-audit.db"; generate_dataset(audit_path,17,300,1200)
    monkeypatch.setattr(api_main.settings,"db_path",audit_path); monkeypatch.setattr(api_main,"_backend",lambda:postgres_environment["backend"]); monkeypatch.setattr(api_main,"_active_snapshot",lambda:postgres_environment["result"].snapshot)
    client=TestClient(api_main.app)
    assert client.get("/health").status_code==200 and "patients" in client.get("/schema").json()
    assert client.get("/metrics").status_code==200
    response=client.post("/analyze",json={"question":"How many patients are in the dataset?"}); assert response.status_code==200
    run_id=response.json()["run_id"]; assert client.get("/runs").status_code==200 and client.get(f"/runs/{run_id}").status_code==200
    lineage=LineageResolver(SQLiteAuditStore(audit_path),postgres_environment["metadata"]).resolve_run(run_id)
    assert lineage["snapshot"]["backend_name"]=="postgres" and lineage["manifest"]["dataset_id"]==postgres_environment["result"].manifest.dataset_id


def test_live_postgres_demo_fixture_profile(postgres_environment,tmp_path):
    dsn=postgres_environment["dsn"]; schema=f"clinical_demo_{uuid.uuid4().hex[:12]}"; store=SQLiteManifestStore(tmp_path/"demo.metadata.db"); loader=PostgresLoader(dsn,store,schema,f"postgres-test:{schema}")
    try:
        result=loader.generate(42,2500,10000)
        assert result.completed and result.row_counts["patients"]==2500 and result.row_counts["encounters"]==10000
        assert result.snapshot.active and store.get_active_snapshot("postgres",loader.storage_identity).snapshot_id==result.snapshot.snapshot_id
        sqlite=generate_dataset(tmp_path/"demo.db",42,2500,10000)
        assert result.manifest.dataset_id==sqlite.manifest.dataset_id and result.manifest.manifest_id==sqlite.manifest.manifest_id and result.snapshot.snapshot_id!=sqlite.snapshot.snapshot_id
    finally:
        psycopg,sql,dict_row=_driver(); connection=psycopg.connect(dsn,row_factory=dict_row,autocommit=True)
        try: connection.execute(sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(sql.Identifier(schema)))
        finally: connection.close()
