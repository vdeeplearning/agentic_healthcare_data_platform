"""Opt-in PostgreSQL parity suite. Set CLINICAL_SQL_TEST_POSTGRES_DSN to run."""
from __future__ import annotations

import os
import uuid

import pytest

from src.agent.workflow import Analyst
from src.database.postgres_backend import PostgresQueryBackend,_driver
from src.database.postgres_loader import PostgresLoader
from src.database.seed import generate_dataset
from src.metadata.repository import SQLiteManifestStore
from tests.backend_contract import QueryBackendContract


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
