"""Filesystem implementation of the narrow lake persistence contract."""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path, PurePosixPath
from typing import Protocol, runtime_checkable

from src.lake.models import DataObject, LakeLayer, LayerManifest, LineageEdge, PublishedSnapshot, SourceBatch


class LakeConflictError(ValueError): pass


@runtime_checkable
class LakeStore(Protocol):
    def write_object(self, layer: LakeLayer, entity: str, object_id: str, payload: bytes, row_count: int) -> DataObject: ...
    def read_object(self, data_object: DataObject) -> bytes: ...
    def list_objects(self, layer: LakeLayer) -> list[DataObject]: ...
    def object_exists(self, data_object: DataObject) -> bool: ...
    def register_layer_manifest(self, manifest: LayerManifest) -> LayerManifest: ...
    def get_layer_manifest(self, manifest_id: str) -> LayerManifest | None: ...
    def list_layer_manifests(self, layer: LakeLayer | None = None) -> list[LayerManifest]: ...
    def publish_snapshot(self, snapshot: PublishedSnapshot) -> PublishedSnapshot: ...
    def resolve_parent_lineage(self, snapshot_id: str) -> list[PublishedSnapshot]: ...
    def validate_checksum(self, data_object: DataObject) -> bool: ...


class LocalFilesystemLakeStore:
    """Atomic, path-safe local store. Raw object identifiers are immutable."""

    def __init__(self, root: Path):
        self.root=Path(root).resolve()
        for directory in ("objects","manifests","snapshots","batches","edges","staging"):
            (self.root/directory).mkdir(parents=True,exist_ok=True)

    @staticmethod
    def checksum(payload: bytes) -> str: return hashlib.sha256(payload).hexdigest()

    def _safe(self, *parts: str) -> Path:
        for part in parts:
            value=PurePosixPath(str(part).replace("\\","/"))
            if value.is_absolute() or ".." in value.parts: raise ValueError("Unsafe lake path component.")
        path=self.root.joinpath(*parts).resolve()
        if path != self.root and self.root not in path.parents: raise ValueError("Lake path escapes configured root.")
        return path

    @staticmethod
    def _canonical(model) -> bytes:
        return json.dumps(model.model_dump(mode="json"),sort_keys=True,separators=(",",":"),default=str).encode()

    def _atomic(self,path:Path,payload:bytes,immutable:bool=False)->None:
        path.parent.mkdir(parents=True,exist_ok=True)
        if path.exists():
            if path.read_bytes()!=payload: raise LakeConflictError(f"Identifier conflicts with existing content: {path.stem}")
            return
        fd,temp=tempfile.mkstemp(prefix="candidate-",dir=self.root/"staging")
        try:
            with os.fdopen(fd,"wb") as handle: handle.write(payload); handle.flush(); os.fsync(handle.fileno())
            if immutable:
                try: os.link(temp,path)
                except FileExistsError:
                    if path.read_bytes()!=payload: raise LakeConflictError("Raw objects are immutable.")
                else: os.unlink(temp)
            else: os.replace(temp,path)
        finally:
            if os.path.exists(temp): os.unlink(temp)

    def _replace_atomic(self,path:Path,payload:bytes)->None:
        path.parent.mkdir(parents=True,exist_ok=True)
        fd,temp=tempfile.mkstemp(prefix="candidate-",dir=self.root/"staging")
        try:
            with os.fdopen(fd,"wb") as handle: handle.write(payload); handle.flush(); os.fsync(handle.fileno())
            os.replace(temp,path)
        finally:
            if os.path.exists(temp): os.unlink(temp)

    def write_object(self,layer:LakeLayer,entity:str,object_id:str,payload:bytes,row_count:int)->DataObject:
        if not entity.replace("_","").isalnum() or not object_id.replace("-","").isalnum(): raise ValueError("Unsafe object identity.")
        relative=f"objects/{layer.value}/{entity}/{object_id}.jsonl"
        path=self._safe(*relative.split("/")); self._atomic(path,payload,immutable=layer==LakeLayer.raw)
        return DataObject(object_id=object_id,layer=layer,entity=entity,relative_path=relative,checksum=self.checksum(payload),row_count=row_count,size_bytes=len(payload))

    def read_object(self,data_object:DataObject)->bytes: return self._safe(*data_object.relative_path.split("/")).read_bytes()
    def object_exists(self,data_object:DataObject)->bool: return self._safe(*data_object.relative_path.split("/")).exists()
    def validate_checksum(self,data_object:DataObject)->bool: return self.object_exists(data_object) and self.checksum(self.read_object(data_object))==data_object.checksum

    def _records(self,directory:str,model)->list:
        return [model.model_validate_json(path.read_text(encoding="utf-8")) for path in sorted(self._safe(directory).glob("*.json"))]

    def list_objects(self,layer:LakeLayer)->list[DataObject]:
        objects=[]
        for path in sorted(self._safe("objects",layer.value).rglob("*.jsonl")):
            payload=path.read_bytes(); relative=path.relative_to(self.root).as_posix()
            objects.append(DataObject(object_id=path.stem,layer=layer,entity=path.parent.name,relative_path=relative,checksum=self.checksum(payload),row_count=len(payload.splitlines()),size_bytes=len(payload)))
        return objects

    def _register(self,directory:str,identifier:str,model):
        self._atomic(self._safe(directory,f"{identifier}.json"),self._canonical(model)); return model

    def register_source_batch(self,batch:SourceBatch)->SourceBatch:
        existing=self.get_source_batch(batch.batch_id)
        if existing:
            left=existing.model_dump(mode="json",exclude={"created_at"}); right=batch.model_dump(mode="json",exclude={"created_at"})
            if left!=right: raise LakeConflictError(f"Identifier conflicts with existing content: {batch.batch_id}")
            return existing
        return self._register("batches",batch.batch_id,batch)
    def get_source_batch(self,batch_id:str)->SourceBatch|None:
        path=self._safe("batches",f"{batch_id}.json"); return SourceBatch.model_validate_json(path.read_text()) if path.exists() else None
    def register_layer_manifest(self,manifest:LayerManifest)->LayerManifest:
        existing=self.get_layer_manifest(manifest.manifest_id)
        if existing:
            left=existing.model_dump(mode="json",exclude={"created_at"}); right=manifest.model_dump(mode="json",exclude={"created_at"})
            if left!=right: raise LakeConflictError(f"Identifier conflicts with existing content: {manifest.manifest_id}")
            return existing
        return self._register("manifests",manifest.manifest_id,manifest)
    def get_layer_manifest(self,manifest_id:str)->LayerManifest|None:
        path=self._safe("manifests",f"{manifest_id}.json"); return LayerManifest.model_validate_json(path.read_text()) if path.exists() else None
    def list_layer_manifests(self,layer:LakeLayer|None=None)->list[LayerManifest]:
        values=self._records("manifests",LayerManifest); return [item for item in values if layer is None or item.layer==layer]
    def register_edge(self,edge:LineageEdge)->LineageEdge:
        identifier=hashlib.sha256(self._canonical(edge)).hexdigest()[:24]; return self._register("edges",identifier,edge)

    def publish_snapshot(self,snapshot:PublishedSnapshot)->PublishedSnapshot:
        if snapshot.status not in {"validated","active"}: raise ValueError("Only validated candidates may publish.")
        manifest=self.get_layer_manifest(snapshot.layer_manifest_id)
        if not manifest or not manifest.validation.passed: raise ValueError("Snapshot requires a validated registered manifest.")
        existing=self.get_snapshot(snapshot.snapshot_id)
        if existing:
            stable=lambda value:value.model_dump(mode="json",exclude={"published_at","active","status","replaces_snapshot_id"})
            if stable(existing)!=stable(snapshot): raise LakeConflictError(f"Identifier conflicts with existing content: {snapshot.snapshot_id}")
            snapshot=snapshot.model_copy(update={"published_at":existing.published_at})
        active_path=self._safe("snapshots",f"active-{snapshot.layer.value}.json")
        previous=PublishedSnapshot.model_validate_json(active_path.read_text()) if active_path.exists() else None
        published=snapshot.model_copy(update={"active":True,"status":"active","replaces_snapshot_id":previous.snapshot_id if previous and previous.snapshot_id!=snapshot.snapshot_id else snapshot.replaces_snapshot_id})
        if existing: self._replace_atomic(self._safe("snapshots",f"{snapshot.snapshot_id}.json"),self._canonical(published))
        else: self._register("snapshots",snapshot.snapshot_id,published)
        self._replace_atomic(active_path,self._canonical(published))
        if previous and previous.snapshot_id!=snapshot.snapshot_id:
            superseded=previous.model_copy(update={"active":False,"status":"superseded"})
            self._replace_atomic(self._safe("snapshots",f"{previous.snapshot_id}.json"),self._canonical(superseded))
        return published

    def get_snapshot(self,snapshot_id:str)->PublishedSnapshot|None:
        path=self._safe("snapshots",f"{snapshot_id}.json"); return PublishedSnapshot.model_validate_json(path.read_text()) if path.exists() else None
    def get_active_snapshot(self,layer:LakeLayer)->PublishedSnapshot|None:
        path=self._safe("snapshots",f"active-{layer.value}.json"); return PublishedSnapshot.model_validate_json(path.read_text()) if path.exists() else None
    def resolve_parent_lineage(self,snapshot_id:str)->list[PublishedSnapshot]:
        result=[]; pending=[snapshot_id]; seen=set()
        while pending:
            current=pending.pop(0)
            if current in seen: continue
            seen.add(current); snapshot=self.get_snapshot(current)
            if snapshot: result.append(snapshot); pending.extend(snapshot.parent_snapshot_ids)
        return result
