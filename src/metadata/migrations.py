"""Transactional SQLite migrations for platform lineage metadata only."""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


class MetadataMigrationError(RuntimeError): pass
class UnsupportedMetadataVersion(MetadataMigrationError): pass


@dataclass(frozen=True)
class Migration:
    version: int
    statements: tuple[str, ...]


METADATA_MIGRATIONS = (
    Migration(1, (
        """CREATE TABLE dataset_manifests (
            manifest_id TEXT PRIMARY KEY, dataset_id TEXT NOT NULL UNIQUE,
            manifest_schema_version TEXT NOT NULL, payload_json TEXT NOT NULL,
            registered_at TEXT NOT NULL
        )""",
        "CREATE INDEX idx_manifests_dataset ON dataset_manifests(dataset_id)",
    )),
    Migration(2, (
        """CREATE TABLE dataset_snapshots (
            snapshot_id TEXT PRIMARY KEY, dataset_id TEXT NOT NULL,
            manifest_id TEXT NOT NULL REFERENCES dataset_manifests(manifest_id),
            backend_name TEXT NOT NULL, storage_identity TEXT NOT NULL,
            loader_name TEXT NOT NULL, loader_version TEXT NOT NULL,
            schema_version TEXT NOT NULL, snapshot_schema_version TEXT NOT NULL,
            load_status TEXT NOT NULL, active INTEGER NOT NULL DEFAULT 0 CHECK(active IN (0,1)),
            replaces_snapshot_id TEXT REFERENCES dataset_snapshots(snapshot_id),
            payload_json TEXT NOT NULL, registered_at TEXT NOT NULL
        )""",
        "CREATE INDEX idx_snapshots_dataset ON dataset_snapshots(dataset_id, snapshot_id)",
        "CREATE INDEX idx_snapshots_active ON dataset_snapshots(backend_name, storage_identity, active)",
        "CREATE UNIQUE INDEX idx_one_active_snapshot ON dataset_snapshots(backend_name, storage_identity) WHERE active=1",
    )),
)


def apply_metadata_migrations(path: Path, migrations: tuple[Migration, ...] = METADATA_MIGRATIONS) -> int:
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, isolation_level=None)
    try:
        connection.execute("BEGIN IMMEDIATE")
        connection.execute("CREATE TABLE IF NOT EXISTS platform_metadata_migrations (version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)")
        connection.commit()
        applied = {row[0] for row in connection.execute("SELECT version FROM platform_metadata_migrations")}
        supported = {migration.version for migration in migrations}
        if any(version not in supported for version in applied):
            raise UnsupportedMetadataVersion(f"Metadata database contains unsupported migration versions: {sorted(applied-supported)}")
        for migration in sorted(migrations, key=lambda item: item.version):
            if migration.version in applied: continue
            try:
                connection.execute("BEGIN IMMEDIATE")
                for statement in migration.statements: connection.execute(statement)
                connection.execute("INSERT INTO platform_metadata_migrations VALUES (?,?)", (migration.version, datetime.now(timezone.utc).isoformat()))
                connection.commit()
            except Exception as exc:
                connection.rollback()
                raise MetadataMigrationError(f"Metadata migration {migration.version} failed: {exc}") from exc
        return max(supported, default=0)
    finally:
        connection.close()
