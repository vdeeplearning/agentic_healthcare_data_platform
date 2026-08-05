"""Psycopg 3 analytical query backend; authorization remains centralized."""
from __future__ import annotations

import datetime as dt
import decimal
import time
from typing import Any

from src.database.backend import APPROVED_RELATIONSHIPS
from src.database.lifecycle import SCHEMA_VERSION
from src.database.models import (
    BackendCapabilities, CatalogMetadata, CatalogRelationship, ColumnMetadata,
    ExecutionContext, QueryBackendError, QueryExecutionResult, RelationMetadata,
)


def _driver():
    try:
        import psycopg
        from psycopg import sql
        from psycopg.rows import dict_row
        return psycopg,sql,dict_row
    except ImportError as exc:
        raise RuntimeError('PostgreSQL support requires `psycopg[binary]>=3.1`.') from exc


def _normalize(value: Any) -> Any:
    if isinstance(value, decimal.Decimal): return float(value)
    if isinstance(value, (dt.date,dt.datetime,dt.time)): return value.isoformat()
    if isinstance(value, memoryview): return bytes(value)
    if isinstance(value, list): return [_normalize(item) for item in value]
    if isinstance(value, dict): return {key:_normalize(item) for key,item in value.items()}
    return value


class PostgresQueryBackend:
    """Execute already-approved queries in read-only PostgreSQL transactions."""

    name="postgres"

    def __init__(self, dsn: str, schema: str = "public", storage_identity: str | None = None):
        if not dsn: raise ValueError("A PostgreSQL DSN is required.")
        self._dsn=dsn; self.schema=schema; self.storage_identity=storage_identity or f"postgres:{schema}"

    def _connect(self):
        psycopg,_,dict_row=_driver()
        return psycopg.connect(self._dsn,row_factory=dict_row,autocommit=False)

    def discover_catalog(self) -> CatalogMetadata:
        _,sql,_=_driver(); connection=self._connect()
        try:
            with connection.transaction():
                connection.execute("SET TRANSACTION READ ONLY")
                objects=connection.execute("""SELECT table_name,table_type FROM information_schema.tables
                    WHERE table_schema=%s AND table_type IN ('BASE TABLE','VIEW') ORDER BY table_name""",(self.schema,)).fetchall()
                primary_keys={(row["table_name"],row["column_name"]) for row in connection.execute("""SELECT kcu.table_name,kcu.column_name
                    FROM information_schema.table_constraints tc JOIN information_schema.key_column_usage kcu
                    ON tc.constraint_name=kcu.constraint_name AND tc.table_schema=kcu.table_schema
                    WHERE tc.table_schema=%s AND tc.constraint_type='PRIMARY KEY'""",(self.schema,)).fetchall()}
                relations=[]
                for obj in objects:
                    name=obj["table_name"]
                    columns=[ColumnMetadata(name=row["column_name"],data_type=row["data_type"].lower(),nullable=row["is_nullable"]=="YES",primary_key=(name,row["column_name"]) in primary_keys) for row in connection.execute("""SELECT column_name,data_type,is_nullable FROM information_schema.columns
                        WHERE table_schema=%s AND table_name=%s ORDER BY ordinal_position""",(self.schema,name)).fetchall()]
                    relations.append(RelationMetadata(name=name,kind="table" if obj["table_type"]=="BASE TABLE" else "view",columns=columns))
        finally: connection.close()
        return CatalogMetadata(relations=relations,relationships=[CatalogRelationship(left=left,right=right) for left,right in APPROVED_RELATIONSHIPS],prohibited_objects=["audit_runs","pg_catalog","information_schema"],sql_dialect="postgres",capabilities=BackendCapabilities(native_timeout=True),schema_version=SCHEMA_VERSION)

    def execute(self, sql_text: str, context: ExecutionContext, max_rows: int) -> QueryExecutionResult:
        psycopg,sql,_=_driver(); started=time.perf_counter(); connection=self._connect()
        try:
            database_name=connection.info.dbname or "analytics"
            with connection.transaction():
                connection.execute("SET TRANSACTION READ ONLY")
                connection.execute("SELECT set_config('statement_timeout',%s,true)",(f"{max(1,int(context.timeout_seconds*1000))}ms",))
                connection.execute(sql.SQL("SET LOCAL search_path TO {} ").format(sql.Identifier(self.schema)))
                plan_value=connection.execute("EXPLAIN (FORMAT JSON) "+sql_text).fetchone()["QUERY PLAN"]
                cursor=connection.execute(sql_text); columns=[item.name for item in cursor.description]
                raw_rows=cursor.fetchmany(max_rows+1); truncated=len(raw_rows)>max_rows
                rows=[{key:_normalize(value) for key,value in row.items()} for row in raw_rows[:max_rows]]
            query_plan=_normalize(plan_value if isinstance(plan_value,list) else [{"plan":plan_value}])
        except psycopg.Error as exc:
            code="cancelled" if getattr(exc,"sqlstate",None)=="57014" else "execution_failed"
            raise QueryBackendError(str(exc),backend_name=self.name,code=code,retryable=code=="cancelled") from exc
        finally: connection.close()
        return QueryExecutionResult(columns=columns,rows=rows,execution_time_ms=(time.perf_counter()-started)*1000,query_plan=query_plan,truncated=truncated,backend_name=self.name,provenance={"database":f"postgresql:{database_name}","read_only":True,"dataset_id":context.dataset_id,"manifest_id":context.manifest_id,"snapshot_id":context.snapshot_id,"fixture_profile":context.fixture_profile,"generator_version":context.generator_version,"schema_version":SCHEMA_VERSION,"backend_schema":self.schema})
