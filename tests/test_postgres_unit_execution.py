from __future__ import annotations

import re
from types import SimpleNamespace

import psycopg
import pytest

from src.database.models import ExecutionContext,QueryBackendError
from src.database.lifecycle import LogicalRecordBatch
from src.database.postgres_backend import PostgresQueryBackend
from src.database.postgres_loader import PostgresLoader
from src.database.seed import generate_dataset
from src.metadata.repository import SQLiteManifestStore


class FakeDriverError(Exception):
    sqlstate="57014"


class FakeTransaction:
    def __enter__(self): return self
    def __exit__(self,*args): return False


class FakeDescription:
    def __init__(self,name): self.name=name


class FakeCursor:
    def __init__(self,rows=None,columns=None,connection=None):
        self.rows=list(rows or []); self.description=[FakeDescription(name) for name in (columns or [])]; self.connection=connection
    def fetchone(self): return self.rows[0] if self.rows else None
    def fetchall(self): return self.rows
    def fetchmany(self,count): return self.rows[:count]
    def executemany(self,query,records):
        match=re.search(r"Identifier\('([^']+)'\)",str(query)); table=match.group(1)
        self.connection.counts[table]=self.connection.counts.get(table,0)+len(records)
    def __enter__(self): return self
    def __exit__(self,*args): return False


class FakeConnection:
    def __init__(self,fail=False,total_cost=123.45):
        self.fail=fail; self.total_cost=total_cost; self.info=SimpleNamespace(dbname="clinical_test"); self.counts={}; self.committed=False; self.rolled_back=False
    def transaction(self): return FakeTransaction()
    def cursor(self): return FakeCursor(connection=self)
    def execute(self,query,params=None):
        text=str(query)
        if self.fail and text.startswith("EXPLAIN"): raise FakeDriverError("canceling statement due to statement timeout")
        if "information_schema.tables" in text:
            return FakeCursor([{"table_name":"patients","table_type":"BASE TABLE"},{"table_name":"encounter_facts","table_type":"VIEW"}])
        if "table_constraints" in text: return FakeCursor([{"table_name":"patients","column_name":"patient_id"}])
        if "information_schema.columns" in text:
            table=params[1]
            rows=[{"column_name":"patient_id","data_type":"bigint","is_nullable":"NO"}]
            if table=="patients": rows.append({"column_name":"race_ethnicity","data_type":"text","is_nullable":"YES"})
            return FakeCursor(rows)
        if text.startswith("EXPLAIN"): return FakeCursor([{"QUERY PLAN":[{"Plan":{"Node Type":"Seq Scan"}}]}])
        if text.startswith("SELECT patient_id"):
            rows=[{"patient_id":index,"race_ethnicity":None,"integer_value":1,"real_value":1.5} for index in range(1,12)]
            return FakeCursor(rows,["patient_id","race_ethnicity","integer_value","real_value"])
        if "quality_measures WHERE" in text: return FakeCursor([{"count":0}])
        if "ROUND(SUM(total_cost)" in text: return FakeCursor([{"total":self.total_cost}])
        if "SELECT COUNT(*) AS count" in text:
            match=re.search(r"Identifier\('([^']+)'\)",text); return FakeCursor([{"count":self.counts.get(match.group(1),0)}])
        return FakeCursor([{}])
    def commit(self): self.committed=True
    def rollback(self): self.rolled_back=True
    def close(self): pass


class FakePsycopg:
    Error=FakeDriverError
    def __init__(self,connection): self.connection=connection
    def connect(self,*args,**kwargs): return self.connection


def fake_driver(connection):
    from psycopg import sql
    from psycopg.rows import dict_row
    return FakePsycopg(connection),sql,dict_row


def test_postgres_backend_catalog_and_execution_without_server(monkeypatch):
    connection=FakeConnection()
    monkeypatch.setattr("src.database.postgres_backend._driver",lambda:fake_driver(connection))
    backend=PostgresQueryBackend("postgresql://unused/db")
    catalog=backend.discover_catalog()
    assert catalog.sql_dialect=="postgres" and catalog.relations[0].name=="patients"
    result=backend.execute("SELECT patient_id, race_ethnicity, 1 AS integer_value, 1.5 AS real_value FROM patients",ExecutionContext(run_id="fake",dataset_id="dataset"),10)
    assert len(result.rows)==10 and result.truncated and result.query_plan
    assert result.provenance["database"]=="postgresql:clinical_test"


def test_postgres_backend_structures_timeout_errors(monkeypatch):
    monkeypatch.setattr("src.database.postgres_backend._driver",lambda:fake_driver(FakeConnection(fail=True)))
    with pytest.raises(QueryBackendError) as raised:
        PostgresQueryBackend("postgresql://unused/db").execute("SELECT 1",ExecutionContext(run_id="timeout",timeout_seconds=0),1)
    assert raised.value.code=="cancelled" and raised.value.retryable


def test_postgres_loader_consumes_logical_batches_and_registers_snapshot(monkeypatch,tmp_path):
    sqlite_result=generate_dataset(tmp_path/"sqlite.db",9,50,200)
    connection=FakeConnection(total_cost=sqlite_result.manifest.stable_summaries["encounter_total_cost"])
    monkeypatch.setattr("src.database.postgres_loader._driver",lambda:fake_driver(connection))
    store=SQLiteManifestStore(tmp_path/"metadata.db")
    result=PostgresLoader("postgresql://unused/db",store,"analytics","postgres:test").generate(9,50,200)
    assert result.completed and result.snapshot.active and result.snapshot.backend_name=="postgres"
    assert result.manifest.dataset_id==sqlite_result.manifest.dataset_id and result.manifest.manifest_id==sqlite_result.manifest.manifest_id
    assert result.snapshot.snapshot_id!=sqlite_result.snapshot.snapshot_id
    assert result.row_counts["patients"]==50 and result.row_counts["encounters"]==200
    assert connection.committed and store.get_active_snapshot("postgres","postgres:test").snapshot_id==result.snapshot.snapshot_id


def test_postgres_loader_rolls_back_unsupported_logical_entity(monkeypatch,tmp_path):
    connection=FakeConnection()
    monkeypatch.setattr("src.database.postgres_loader._driver",lambda:fake_driver(connection))
    loader=PostgresLoader("postgresql://unused/db",SQLiteManifestStore(tmp_path/"metadata.db"))
    manifest=generate_dataset(tmp_path/"sqlite.db",3,2,3).manifest
    with pytest.raises(ValueError,match="Unsupported logical entity"):
        loader.load_batches([LogicalRecordBatch(entity="unknown",records=())],manifest)
    assert connection.rolled_back
