"""Audit persistence."""
from __future__ import annotations
import json, sqlite3
from datetime import datetime,timezone
from pathlib import Path
from typing import Any

from typing import Protocol, runtime_checkable


@runtime_checkable
class AuditStore(Protocol):
    def write(self, record: dict[str, Any]) -> None: ...
    def get(self, run_id: str) -> dict[str, Any] | None: ...
    def list(self, limit: int = 50) -> list[dict[str, Any]]: ...


class SQLiteAuditStore:
    """SQLite audit adapter preserving the existing row representation."""

    def __init__(self, path: Path):
        self.path = Path(path)

    @staticmethod
    def _ensure_provenance_column(connection: sqlite3.Connection) -> None:
        columns={row[1] for row in connection.execute("PRAGMA table_info(audit_runs)")}
        if columns and "provenance_json" not in columns:
            connection.execute("ALTER TABLE audit_runs ADD COLUMN provenance_json TEXT")

    def write(self, record: dict[str, Any]) -> None:
        values=(record["run_id"],record.get("question",""),record.get("normalized_question",""),record.get("model_name","deterministic-demo"),"1.0",json.dumps(record.get("plan")),record.get("sql"),record.get("validation_status","unknown"),record.get("execution_status","unknown"),record.get("row_count",0),record.get("execution_time_ms"),json.dumps(record.get("statistical_tools")),json.dumps(record.get("warnings",[])),record.get("final_answer"),datetime.now(timezone.utc).isoformat(),json.dumps(record.get("provenance")) if record.get("provenance") else None)
        connection=sqlite3.connect(self.path)
        try:
            connection.execute("PRAGMA foreign_keys=ON")
            self._ensure_provenance_column(connection)
            # A retried workflow must not create or overwrite a second audit event.
            connection.execute("""INSERT OR IGNORE INTO audit_runs (
                run_id,user_question,normalized_question,model_name,schema_version,
                analysis_plan_json,generated_sql,validation_status,execution_status,
                result_row_count,execution_time_ms,statistical_tools_json,warnings_json,
                final_answer,created_at,provenance_json
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",values)
            connection.commit()
        finally:
            connection.close()

    def get(self, run_id: str) -> dict[str, Any] | None:
        connection=sqlite3.connect(self.path); connection.row_factory=sqlite3.Row
        try:
            self._ensure_provenance_column(connection)
            connection.commit()
            row=connection.execute("SELECT * FROM audit_runs WHERE run_id=?",(run_id,)).fetchone()
        finally: connection.close()
        return dict(row) if row else None

    def list(self, limit: int = 50) -> list[dict[str, Any]]:
        connection=sqlite3.connect(self.path); connection.row_factory=sqlite3.Row
        try:
            self._ensure_provenance_column(connection)
            connection.commit()
            rows=connection.execute("SELECT * FROM audit_runs ORDER BY created_at DESC LIMIT ?",(min(limit,100),)).fetchall()
        finally: connection.close()
        return [dict(row) for row in rows]

def write_audit(path:Path,record:dict[str,Any])->None:
    SQLiteAuditStore(path).write(record)
def get_run(path:Path,run_id:str)->dict[str,Any]|None:
    return SQLiteAuditStore(path).get(run_id)
def list_runs(path:Path,limit:int=50)->list[dict[str,Any]]:
    return SQLiteAuditStore(path).list(limit)

