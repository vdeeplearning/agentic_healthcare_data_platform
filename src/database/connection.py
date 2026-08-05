"""SQLite connection helpers."""
from __future__ import annotations
import sqlite3
from pathlib import Path


def connect_writable(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.execute("PRAGMA foreign_keys=ON")
    return connection


def connect_read_only(path: Path) -> sqlite3.Connection:
    """Open a URI-mode, query-only SQLite connection."""
    connection = sqlite3.connect(f"file:{path.resolve().as_posix()}?mode=ro", uri=True, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA query_only=ON")
    connection.execute("PRAGMA foreign_keys=ON")
    return connection


def schema_catalog(path: Path) -> dict[str, set[str]]:
    """Compatibility wrapper for callers expecting the original mapping."""
    from src.database.backend import SQLiteQueryBackend

    return SQLiteQueryBackend(path).discover_catalog().column_names()

