"""Engine-neutral metadata and execution contracts."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ColumnMetadata(BaseModel):
    name: str
    data_type: str = ""
    nullable: bool = True
    primary_key: bool = False


class RelationMetadata(BaseModel):
    name: str
    kind: str
    columns: list[ColumnMetadata]


class CatalogRelationship(BaseModel):
    left: str
    right: str


class BackendCapabilities(BaseModel):
    read_only: bool = True
    query_plan: bool = True
    native_timeout: bool = False
    cooperative_timeout: bool = False
    result_limit: bool = True


class CatalogMetadata(BaseModel):
    relations: list[RelationMetadata]
    relationships: list[CatalogRelationship] = Field(default_factory=list)
    prohibited_objects: list[str] = Field(default_factory=list)
    sql_dialect: str
    capabilities: BackendCapabilities
    schema_version: str = "1.0"

    def column_names(self) -> dict[str, set[str]]:
        return {relation.name: {column.name for column in relation.columns} for relation in self.relations}


class ExecutionContext(BaseModel):
    run_id: str
    correlation_id: str | None = None
    timeout_seconds: float = 5.0
    deadline: datetime | None = None
    actor_id: str | None = None
    tenant_id: str | None = None
    dataset_id: str | None = None
    snapshot_id: str | None = None


class QueryExecutionResult(BaseModel):
    columns: list[str]
    rows: list[dict[str, Any]]
    execution_time_ms: float
    query_plan: list[dict[str, Any]] = Field(default_factory=list)
    truncated: bool = False
    backend_name: str
    provenance: dict[str, Any] = Field(default_factory=dict)
