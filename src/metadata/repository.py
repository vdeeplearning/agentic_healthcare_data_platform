"""Durable manifest and materialized-snapshot persistence boundary."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from src.database.lifecycle import (
    DatasetManifest, DatasetSnapshot,
    VersionCompatibilityPolicy, manifest_identity,
)
from src.metadata.migrations import apply_metadata_migrations


class MetadataConflictError(ValueError): pass


def metadata_path_for(analytics_path: Path) -> Path:
    path = Path(analytics_path)
    return path.with_name(path.name + ".metadata.db")


def resolve_active_snapshot(analytics_path: Path) -> DatasetSnapshot | None:
    """Legacy-safe lookup: absent or unreadable metadata never changes query authority."""
    metadata_path=metadata_path_for(analytics_path)
    if not metadata_path.exists(): return None
    try: return SQLiteManifestStore(metadata_path).get_active_snapshot("sqlite",Path(analytics_path).name)
    except (sqlite3.Error, ValueError, RuntimeError): return None


def _json(value: Any) -> str:
    if hasattr(value, "model_dump"): value = value.model_dump(mode="json")
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def _manifest_stable(manifest: DatasetManifest) -> dict[str, Any]:
    value = manifest.model_dump(mode="json")
    for key in ("generation_timestamp", "load_timestamp", "loader_backend", "load_complete", "validation_summary"):
        value.pop(key, None)
    return value


def _snapshot_stable(snapshot: DatasetSnapshot) -> dict[str, Any]:
    value = snapshot.model_dump(mode="json")
    for key in ("load_timestamp", "load_status", "active", "replaces_snapshot_id"):
        value.pop(key, None)
    return value


@runtime_checkable
class ManifestStore(Protocol):
    def register_manifest(self, manifest: DatasetManifest) -> DatasetManifest: ...
    def get_manifest(self, identifier: str) -> DatasetManifest | None: ...
    def list_manifests(self, limit: int = 100) -> list[DatasetManifest]: ...
    def register_snapshot(self, snapshot: DatasetSnapshot) -> DatasetSnapshot: ...
    def get_snapshot(self, snapshot_id: str) -> DatasetSnapshot | None: ...
    def get_active_snapshot(self, backend_name: str | None = None, storage_identity: str | None = None) -> DatasetSnapshot | None: ...
    def list_snapshots(self, limit: int = 100) -> list[DatasetSnapshot]: ...
    def resolve_lineage(self, snapshot_id: str) -> dict[str, Any] | None: ...


class SQLiteManifestStore:
    """SQLite sidecar repository; never participates in analytical authorization."""

    def __init__(self, path: Path):
        self.path = Path(path)
        apply_metadata_migrations(self.path)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        return connection

    def _fetchone(self, sql: str, parameters=()):
        connection=self._connect()
        try: return connection.execute(sql,parameters).fetchone()
        finally: connection.close()

    def _fetchall(self, sql: str, parameters=()):
        connection=self._connect()
        try: return connection.execute(sql,parameters).fetchall()
        finally: connection.close()

    def register_manifest(self, manifest: DatasetManifest) -> DatasetManifest:
        decision = VersionCompatibilityPolicy().check(generator_version=manifest.generator_version, logical_schema_version=manifest.schema_version, loader_version="1.0.0",manifest_schema_version=manifest.manifest_schema_version)
        if not decision.compatible: raise MetadataConflictError(decision.reason)
        manifest_id = manifest.manifest_id or manifest_identity(manifest)
        candidate = manifest.model_copy(update={"manifest_id": manifest_id})
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute("SELECT payload_json FROM dataset_manifests WHERE manifest_id=? OR dataset_id=?", (manifest_id, candidate.dataset_id)).fetchone()
            if row:
                existing = DatasetManifest.model_validate_json(row[0])
                if _manifest_stable(existing) != _manifest_stable(candidate):
                    raise MetadataConflictError(f"Manifest identifier conflicts with existing content: {manifest_id}")
                connection.rollback(); return existing
            connection.execute("INSERT INTO dataset_manifests VALUES (?,?,?,?,?)", (manifest_id,candidate.dataset_id,candidate.manifest_schema_version,_json(candidate),datetime.now(timezone.utc).isoformat()))
            connection.commit(); return candidate
        except Exception:
            connection.rollback(); raise
        finally: connection.close()

    def get_manifest(self, identifier: str) -> DatasetManifest | None:
        row=self._fetchone("SELECT payload_json FROM dataset_manifests WHERE manifest_id=? OR dataset_id=?",(identifier,identifier))
        return DatasetManifest.model_validate_json(row[0]) if row else None

    def list_manifests(self, limit: int = 100) -> list[DatasetManifest]:
        rows=self._fetchall("SELECT payload_json FROM dataset_manifests ORDER BY dataset_id,manifest_id LIMIT ?",(min(limit,1000),))
        return [DatasetManifest.model_validate_json(row[0]) for row in rows]

    def register_snapshot(self, snapshot: DatasetSnapshot) -> DatasetSnapshot:
        candidate=snapshot.model_copy(update={"active":False})
        connection=self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            manifest_row=connection.execute("SELECT payload_json FROM dataset_manifests WHERE manifest_id=? AND dataset_id=?",(candidate.manifest_id,candidate.dataset_id)).fetchone()
            if not manifest_row: raise MetadataConflictError("Snapshot references an unknown or mismatched manifest.")
            manifest=DatasetManifest.model_validate_json(manifest_row[0])
            decision=VersionCompatibilityPolicy().check(generator_version=manifest.generator_version,logical_schema_version=candidate.schema_version,loader_version=candidate.loader_version,manifest_schema_version=manifest.manifest_schema_version,snapshot_schema_version=candidate.snapshot_schema_version)
            if not decision.compatible: raise MetadataConflictError(decision.reason)
            row=connection.execute("SELECT payload_json FROM dataset_snapshots WHERE snapshot_id=?",(candidate.snapshot_id,)).fetchone()
            if row:
                existing=DatasetSnapshot.model_validate_json(row[0])
                if _snapshot_stable(existing)!=_snapshot_stable(candidate):
                    raise MetadataConflictError(f"Snapshot identifier conflicts with existing content: {candidate.snapshot_id}")
                connection.rollback(); return existing
            connection.execute("INSERT INTO dataset_snapshots VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",(candidate.snapshot_id,candidate.dataset_id,candidate.manifest_id,candidate.backend_name,candidate.storage_identity,candidate.loader_name,candidate.loader_version,candidate.schema_version,candidate.snapshot_schema_version,candidate.load_status,0,candidate.replaces_snapshot_id,_json(candidate),datetime.now(timezone.utc).isoformat()))
            connection.commit(); return candidate
        except Exception:
            connection.rollback(); raise
        finally: connection.close()

    def activate_snapshot(self, snapshot_id: str) -> DatasetSnapshot:
        connection=self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            row=connection.execute("SELECT * FROM dataset_snapshots WHERE snapshot_id=?",(snapshot_id,)).fetchone()
            if not row: raise KeyError(f"Unknown snapshot: {snapshot_id}")
            snapshot=DatasetSnapshot.model_validate_json(row["payload_json"])
            if snapshot.load_status not in {"validated","completed","active"} or any(snapshot.validation_summary.values()):
                raise ValueError("Only successfully validated snapshots can become active.")
            previous=connection.execute("SELECT snapshot_id FROM dataset_snapshots WHERE backend_name=? AND storage_identity=? AND active=1",(snapshot.backend_name,snapshot.storage_identity)).fetchone()
            previous_id=previous[0] if previous and previous[0]!=snapshot_id else snapshot.replaces_snapshot_id
            prior_rows=connection.execute("SELECT snapshot_id,payload_json FROM dataset_snapshots WHERE backend_name=? AND storage_identity=? AND active=1",(snapshot.backend_name,snapshot.storage_identity)).fetchall()
            for prior in prior_rows:
                prior_snapshot=DatasetSnapshot.model_validate_json(prior["payload_json"]).model_copy(update={"active":False,"load_status":"superseded"})
                connection.execute("UPDATE dataset_snapshots SET active=0,load_status='superseded',payload_json=? WHERE snapshot_id=?",(_json(prior_snapshot),prior["snapshot_id"]))
            active=snapshot.model_copy(update={"active":True,"load_status":"active","replaces_snapshot_id":previous_id})
            connection.execute("UPDATE dataset_snapshots SET active=1,load_status='active',replaces_snapshot_id=?,payload_json=? WHERE snapshot_id=?",(previous_id,_json(active),snapshot_id))
            connection.commit(); return active
        except Exception:
            connection.rollback(); raise
        finally: connection.close()

    def get_snapshot(self, snapshot_id: str) -> DatasetSnapshot | None:
        row=self._fetchone("SELECT payload_json FROM dataset_snapshots WHERE snapshot_id=?",(snapshot_id,))
        return DatasetSnapshot.model_validate_json(row[0]) if row else None

    def get_active_snapshot(self, backend_name: str | None = None, storage_identity: str | None = None) -> DatasetSnapshot | None:
        conditions=["active=1"]; values=[]
        if backend_name is not None: conditions.append("backend_name=?"); values.append(backend_name)
        if storage_identity is not None: conditions.append("storage_identity=?"); values.append(storage_identity)
        row=self._fetchone(f"SELECT payload_json FROM dataset_snapshots WHERE {' AND '.join(conditions)} ORDER BY snapshot_id LIMIT 1",values)
        return DatasetSnapshot.model_validate_json(row[0]) if row else None

    def list_snapshots(self, limit: int = 100) -> list[DatasetSnapshot]:
        rows=self._fetchall("SELECT payload_json FROM dataset_snapshots ORDER BY dataset_id,snapshot_id LIMIT ?",(min(limit,1000),))
        return [DatasetSnapshot.model_validate_json(row[0]) for row in rows]

    def resolve_lineage(self, snapshot_id: str) -> dict[str, Any] | None:
        snapshot=self.get_snapshot(snapshot_id)
        if not snapshot: return None
        manifest=self.get_manifest(snapshot.manifest_id)
        return {"snapshot":snapshot.model_dump(mode="json"),"manifest":manifest.model_dump(mode="json") if manifest else None}
