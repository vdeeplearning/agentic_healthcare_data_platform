"""Atomic repository-local orchestration metadata; not Airflow's metadata DB."""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from src.orchestration.models import OrchestrationRun


class FilesystemOrchestrationStore:
    def __init__(self,lake_root:Path):
        self.root=(Path(lake_root).resolve()/"orchestration"); self.root.mkdir(parents=True,exist_ok=True)

    def _path(self,run_id:str)->Path:
        if not run_id.replace("-","").isalnum(): raise ValueError("Unsafe orchestration run identifier.")
        return self.root/f"{run_id}.json"

    def save(self,run:OrchestrationRun)->OrchestrationRun:
        payload=json.dumps(run.model_dump(mode="json"),sort_keys=True,separators=(",",":")).encode(); path=self._path(run.orchestration_run_id)
        fd,temporary=tempfile.mkstemp(prefix="run-",suffix=".tmp",dir=self.root)
        try:
            with os.fdopen(fd,"wb") as handle: handle.write(payload); handle.flush(); os.fsync(handle.fileno())
            os.replace(temporary,path)
        finally:
            if os.path.exists(temporary): os.unlink(temporary)
        return run

    def get(self,run_id:str)->OrchestrationRun|None:
        path=self._path(run_id); return OrchestrationRun.model_validate_json(path.read_text(encoding="utf-8")) if path.exists() else None

    def list(self,limit:int=100)->list[OrchestrationRun]:
        paths=sorted(self.root.glob("*.json"),key=lambda path:path.stat().st_mtime,reverse=True)[:min(limit,1000)]
        return [OrchestrationRun.model_validate_json(path.read_text(encoding="utf-8")) for path in paths]
