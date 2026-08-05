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

    def write(self, record: dict[str, Any]) -> None:
        values=(record["run_id"],record.get("question",""),record.get("normalized_question",""),record.get("model_name","deterministic-demo"),"1.0",json.dumps(record.get("plan")),record.get("sql"),record.get("validation_status","unknown"),record.get("execution_status","unknown"),record.get("row_count",0),record.get("execution_time_ms"),json.dumps(record.get("statistical_tools")),json.dumps(record.get("warnings",[])),record.get("final_answer"),datetime.now(timezone.utc).isoformat())
        connection=sqlite3.connect(self.path)
        try:
            connection.execute("PRAGMA foreign_keys=ON")
            # A retried workflow must not create or overwrite a second audit event.
            connection.execute("INSERT OR IGNORE INTO audit_runs VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",values)
            connection.commit()
        finally:
            connection.close()

    def get(self, run_id: str) -> dict[str, Any] | None:
        connection=sqlite3.connect(self.path); connection.row_factory=sqlite3.Row
        try: row=connection.execute("SELECT * FROM audit_runs WHERE run_id=?",(run_id,)).fetchone()
        finally: connection.close()
        return dict(row) if row else None

    def list(self, limit: int = 50) -> list[dict[str, Any]]:
        connection=sqlite3.connect(self.path); connection.row_factory=sqlite3.Row
        try: rows=connection.execute("SELECT * FROM audit_runs ORDER BY created_at DESC LIMIT ?",(min(limit,100),)).fetchall()
        finally: connection.close()
        return [dict(row) for row in rows]

def write_audit(path:Path,record:dict[str,Any])->None:
    SQLiteAuditStore(path).write(record)
def get_run(path:Path,run_id:str)->dict[str,Any]|None:
    return SQLiteAuditStore(path).get(run_id)
def list_runs(path:Path,limit:int=50)->list[dict[str,Any]]:
    return SQLiteAuditStore(path).list(limit)

