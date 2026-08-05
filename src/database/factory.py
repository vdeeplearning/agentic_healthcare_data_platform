"""Configuration-driven analytical backend construction."""
from __future__ import annotations

from src.config import Settings
from src.database.backend import QueryBackend,SQLiteQueryBackend


def create_query_backend(settings: Settings) -> QueryBackend:
    if settings.database_backend=="sqlite": return SQLiteQueryBackend(settings.db_path)
    if not settings.postgres_dsn: raise ValueError("POSTGRES_DSN is required when DATABASE_BACKEND=postgres.")
    from src.database.postgres_backend import PostgresQueryBackend
    return PostgresQueryBackend(settings.postgres_dsn,settings.postgres_schema,settings.postgres_storage_identity)
