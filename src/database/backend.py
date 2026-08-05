"""Query execution boundary and the SQLite compatibility implementation."""
from __future__ import annotations

import sqlite3
import time
from pathlib import Path
from typing import Protocol, runtime_checkable

from src.database.connection import connect_read_only
from src.database.models import (
    BackendCapabilities,
    CatalogMetadata,
    CatalogRelationship,
    ColumnMetadata,
    ExecutionContext,
    QueryExecutionResult,
    RelationMetadata,
)


APPROVED_RELATIONSHIPS = [
    ("encounters.patient_id", "patients.patient_id"),
    ("encounters.hospital_id", "hospitals.hospital_id"),
    ("encounters.provider_id", "providers.provider_id"),
    ("providers.hospital_id", "hospitals.hospital_id"),
    ("encounter_diagnoses.encounter_id", "encounters.encounter_id"),
    ("encounter_diagnoses.diagnosis_id", "diagnoses.diagnosis_id"),
    ("encounter_procedures.encounter_id", "encounters.encounter_id"),
    ("encounter_procedures.procedure_id", "procedures.procedure_id"),
    ("lab_results.encounter_id", "encounters.encounter_id"),
    ("readmissions.index_encounter_id", "encounters.encounter_id"),
    ("readmissions.readmission_encounter_id", "encounters.encounter_id"),
    ("quality_measures.hospital_id", "hospitals.hospital_id"),
]


@runtime_checkable
class QueryBackend(Protocol):
    name: str

    def discover_catalog(self) -> CatalogMetadata: ...

    def execute(self, sql: str, context: ExecutionContext, max_rows: int) -> QueryExecutionResult: ...


class SQLiteQueryBackend:
    """Read-only SQLite adapter retaining the original execution semantics."""

    name = "sqlite"

    def __init__(self, path: Path):
        self.path = Path(path)

    def discover_catalog(self) -> CatalogMetadata:
        relations: list[RelationMetadata] = []
        with connect_read_only(self.path) as connection:
            objects = connection.execute(
                "SELECT name,type FROM sqlite_schema "
                "WHERE type IN ('table','view') AND name NOT LIKE 'sqlite_%' ORDER BY name"
            ).fetchall()
            for name, kind in objects:
                columns = [
                    ColumnMetadata(
                        name=row[1], data_type=row[2] or "", nullable=not bool(row[3]), primary_key=bool(row[5])
                    )
                    for row in connection.execute(f'PRAGMA table_info("{name}")')
                ]
                relations.append(RelationMetadata(name=name, kind=kind, columns=columns))
        return CatalogMetadata(
            relations=relations,
            relationships=[CatalogRelationship(left=left, right=right) for left, right in APPROVED_RELATIONSHIPS],
            prohibited_objects=["audit_runs", "sqlite_master", "sqlite_schema"],
            sql_dialect="sqlite",
            capabilities=BackendCapabilities(cooperative_timeout=True),
        )

    def execute(self, sql: str, context: ExecutionContext, max_rows: int) -> QueryExecutionResult:
        started = time.perf_counter()
        try:
            with connect_read_only(self.path) as connection:
                deadline = time.monotonic() + context.timeout_seconds
                connection.set_progress_handler(lambda: 1 if time.monotonic() > deadline else 0, 1000)
                query_plan = [dict(row) for row in connection.execute("EXPLAIN QUERY PLAN " + sql).fetchall()]
                cursor = connection.execute(sql)
                columns = [description[0] for description in cursor.description]
                raw_rows = cursor.fetchmany(max_rows + 1)
                truncated = len(raw_rows) > max_rows
                rows = [dict(zip(columns, row)) for row in raw_rows[:max_rows]]
        except sqlite3.Error:
            raise
        return QueryExecutionResult(
            columns=columns,
            rows=rows,
            execution_time_ms=(time.perf_counter() - started) * 1000,
            query_plan=query_plan,
            truncated=truncated,
            backend_name=self.name,
            provenance={
                "database": str(self.path),
                "read_only": True,
                "dataset_id": context.dataset_id,
                "snapshot_id": context.snapshot_id,
            },
        )
