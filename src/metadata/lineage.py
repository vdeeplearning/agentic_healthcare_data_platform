"""Resolve deterministic run provenance back through snapshots and manifests."""
from __future__ import annotations

import json
from typing import Any

from src.audit.repository import AuditStore
from src.metadata.repository import ManifestStore


class LineageResolver:
    def __init__(self, audit_store: AuditStore, manifest_store: ManifestStore):
        self.audit_store=audit_store; self.manifest_store=manifest_store

    def resolve_run(self, run_id: str) -> dict[str, Any] | None:
        run=self.audit_store.get(run_id)
        if not run: return None
        raw=run.get("provenance_json")
        provenance=json.loads(raw) if isinstance(raw,str) and raw else (raw or {})
        snapshot_id=provenance.get("snapshot_id")
        lineage=self.manifest_store.resolve_lineage(snapshot_id) if snapshot_id else None
        return {"run":run,"provenance":provenance,"snapshot":lineage["snapshot"] if lineage else None,"manifest":lineage["manifest"] if lineage else None}
