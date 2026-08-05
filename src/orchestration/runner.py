"""Stage coordinator invoking existing engines, gates, loaders, analysis, and lineage."""
from __future__ import annotations

import hashlib
import logging
import time
from datetime import datetime,timezone
from pathlib import Path

from src.agent.workflow import Analyst
from src.config import Settings
from src.lake.engines import create_transformation_engine
from src.lake.models import LakeLayer
from src.lake.pipeline import LocalLakePipeline
from src.lake.serving import publish_gold_to_postgres,publish_gold_to_sqlite
from src.lake.store import LocalFilesystemLakeStore
from src.database.factory import create_query_backend
from src.database.sqlite_loader import SQLiteSyntheticDatasetLoader
from src.metadata.repository import SQLiteManifestStore,metadata_path_for
from src.orchestration.models import OrchestrationRun,OrchestrationSummary
from src.orchestration.store import FilesystemOrchestrationStore


LOGGER=logging.getLogger(__name__)


class QualityGateFailed(RuntimeError): pass


def orchestration_identity(dag_id:str,airflow_run_id:str)->str:
    return "orchestration-"+hashlib.sha256(f"{dag_id}:{airflow_run_id}".encode()).hexdigest()[:20]


class PipelineOrchestrator:
    """Coordinates named stages; all transformation and policy logic remains elsewhere."""

    def __init__(self,settings:Settings|None=None,lake_root:Path|None=None,serving_path:Path|None=None):
        self.settings=settings or Settings(); self.lake=LocalFilesystemLakeStore(lake_root or self.settings.lake_root); self.runs=FilesystemOrchestrationStore(self.lake.root); self.serving_path=Path(serving_path or self.settings.airflow_serving_path)

    def begin(self,airflow_run_id:str,engine:str="python",profile:str="test",seed:int=17,serving_backend:str="sqlite",dag_id:str|None=None)->OrchestrationRun:
        identifier=orchestration_identity(dag_id or self.settings.airflow_dag_id,airflow_run_id); existing=self.runs.get(identifier)
        if existing: return existing
        run=OrchestrationRun(orchestration_run_id=identifier,dag_id=dag_id or self.settings.airflow_dag_id,airflow_run_id=airflow_run_id,engine=engine,profile=profile,seed=seed,serving_backend=serving_backend,notification_events=["run_started"])
        LOGGER.info("Orchestration run started: %s",identifier); return self.runs.save(run)

    def _update(self,run:OrchestrationRun,**values)->OrchestrationRun: return self.runs.save(run.model_copy(update=values))
    def get(self,identifier:str)->OrchestrationRun:
        run=self.runs.get(identifier)
        if not run: raise KeyError(f"Unknown orchestration run: {identifier}")
        return run
    def _pipeline(self,run): return LocalLakePipeline(self.lake,run.orchestration_run_id)

    def generate_source(self,identifier:str,malformed:bool=False,parent_batch_id:str|None=None)->OrchestrationRun:
        run=self.get(identifier); batch=self._pipeline(run).generate_source(run.profile,run.seed,"incremental" if parent_batch_id else "initial",parent_batch_id,malformed)
        return self._update(run,current_stage="source_generated",dataset_id=batch.dataset_id,source_batch_id=batch.batch_id)

    def source_ready(self,identifier:str)->bool:
        run=self.get(identifier); return bool(run.source_batch_id and self.lake.get_source_batch(run.source_batch_id))

    def publish_raw(self,identifier:str)->OrchestrationRun:
        run=self.get(identifier); batch=self.lake.get_source_batch(run.source_batch_id or "")
        if not batch: raise RuntimeError("Source batch is not registered.")
        snapshot=self._pipeline(run).publish_raw(batch); snapshots={**run.layer_snapshot_ids,"raw":snapshot.snapshot_id}; manifests={**run.layer_manifest_ids,"raw":snapshot.layer_manifest_id}
        return self._update(run,current_stage="raw_published",layer_snapshot_ids=snapshots,layer_manifest_ids=manifests,parent_lineage=[snapshot.snapshot_id,batch.batch_id])

    def transform(self,identifier:str,layer:LakeLayer)->OrchestrationRun:
        run=self.get(identifier); parent={LakeLayer.bronze:"raw",LakeLayer.silver:"bronze",LakeLayer.gold:"silver"}[layer]; source_id=run.layer_snapshot_ids.get(parent)
        if not source_id: raise RuntimeError(f"Missing {parent} parent snapshot.")
        selected=self.settings.model_copy(update={"lake_transform_engine":run.engine}); engine=create_transformation_engine(selected,self.lake)
        try: result=self._pipeline(run).transform(source_id,layer,engine=engine)
        finally: engine.close()
        transforms={**run.transformation_run_ids,layer.value:result.run_id}; quality={**run.quality_gate_results,layer.value:result.validation.model_dump(mode="json")}; warnings=list(dict.fromkeys(run.warnings+result.validation.warnings))
        if result.status!="completed":
            failed=self._update(run,current_stage=f"{layer.value}_failed",transformation_run_ids=transforms,quality_gate_results=quality,warnings=warnings,failure_stage=f"transform_{layer.value}",failure_message="Layer quality gate failed.")
            raise QualityGateFailed(f"{layer.value} transformation failed for {failed.orchestration_run_id}")
        snapshot=self.lake.get_active_snapshot(layer); snapshots={**run.layer_snapshot_ids,layer.value:snapshot.snapshot_id}; manifests={**run.layer_manifest_ids,layer.value:snapshot.layer_manifest_id}
        return self._update(run,current_stage=f"{layer.value}_transformed",layer_snapshot_ids=snapshots,layer_manifest_ids=manifests,transformation_run_ids=transforms,quality_gate_results=quality,warnings=warnings,parent_lineage=[snapshot.snapshot_id]+run.parent_lineage)

    def quality_gate(self,identifier:str,layer:LakeLayer)->OrchestrationRun:
        run=self.get(identifier); snapshot_id=run.layer_snapshot_ids.get(layer.value); snapshot=self.lake.get_snapshot(snapshot_id) if snapshot_id else None; manifest=self.lake.get_layer_manifest(snapshot.layer_manifest_id) if snapshot else None
        if not snapshot or not snapshot.active or not manifest or not manifest.validation.passed:
            self._update(run,current_stage=f"{layer.value}_gate_failed",failure_stage=f"quality_gate_{layer.value}",failure_message="Candidate is not an active validated snapshot.")
            raise QualityGateFailed(f"{layer.value} quality gate failed")
        return self._update(run,current_stage=f"{layer.value}_gate_passed",quality_gate_results={**run.quality_gate_results,layer.value:manifest.validation.model_dump(mode="json")})

    def publish_serving(self,identifier:str)->OrchestrationRun:
        run=self.get(identifier); gold_id=run.layer_snapshot_ids.get("gold")
        if not gold_id: raise RuntimeError("Validated gold snapshot is required before serving publication.")
        if run.serving_backend=="sqlite": result=publish_gold_to_sqlite(self.lake,gold_id,self.serving_path)
        else:
            if not self.settings.postgres_dsn: raise RuntimeError("PostgreSQL serving publication requires POSTGRES_DSN.")
            metadata=SQLiteManifestStore(self.settings.metadata_path or metadata_path_for(self.serving_path)); result=publish_gold_to_postgres(self.lake,gold_id,self.settings.postgres_dsn,metadata,self.settings.postgres_schema,self.settings.postgres_storage_identity)
        if not result.completed or not result.snapshot or not result.snapshot.active: raise RuntimeError("Serving publication did not activate a validated snapshot.")
        return self._update(run,current_stage="serving_published",serving_snapshot_id=result.snapshot.snapshot_id,serving_manifest_id=result.manifest.manifest_id,parent_lineage=[result.snapshot.snapshot_id]+run.parent_lineage)

    def verify(self,identifier:str)->OrchestrationSummary:
        run=self.get(identifier)
        if run.serving_backend=="sqlite":
            metadata=SQLiteManifestStore(metadata_path_for(self.serving_path)); snapshot=metadata.get_snapshot(run.serving_snapshot_id or ""); analyst=Analyst(self.serving_path,dataset_snapshot=snapshot)
        else:
            metadata=SQLiteManifestStore(self.settings.metadata_path or metadata_path_for(self.serving_path)); snapshot=metadata.get_snapshot(run.serving_snapshot_id or "")
            if not self.serving_path.exists(): SQLiteSyntheticDatasetLoader().create_schema(self.serving_path)
            analyst=Analyst(self.serving_path,query_backend=create_query_backend(self.settings.model_copy(update={"database_backend":"postgres"})),dataset_snapshot=snapshot)
        response=analyst.analyze("How many patients are in the dataset?")
        if response.status!="completed": raise RuntimeError("Serving verification analysis failed.")
        count=int(response.rows[0]["patient_count"]); updated=self._update(run,current_stage="serving_verified",verification_analysis_run_id=response.run_id)
        return OrchestrationSummary(run=updated,patient_count=count)

    def complete(self,identifier:str)->OrchestrationRun:
        run=self.get(identifier); finished=datetime.now(timezone.utc); elapsed=(finished-run.started_at).total_seconds()*1000
        LOGGER.info("Orchestration run completed: %s",identifier); return self._update(run,status="completed",current_stage="completed",finished_at=finished,execution_time_ms=elapsed,notification_events=run.notification_events+["run_succeeded"])

    def fail(self,identifier:str,stage:str,message:str,retry_count:int=0)->OrchestrationRun:
        run=self.get(identifier); finished=datetime.now(timezone.utc); elapsed=(finished-run.started_at).total_seconds()*1000; safe_message=str(message)[:500]
        LOGGER.error("Orchestration run failed at %s: %s",stage,safe_message); return self._update(run,status="failed",current_stage="failed",finished_at=finished,execution_time_ms=elapsed,failure_stage=stage,failure_message=safe_message,retry_count=retry_count,notification_events=run.notification_events+[f"run_failed:{stage}"])

    def record_retry(self,identifier:str,stage:str,retry_count:int)->OrchestrationRun:
        run=self.get(identifier); LOGGER.warning("Retrying orchestration stage %s for %s",stage,identifier)
        return self._update(run,retry_count=max(run.retry_count,retry_count),notification_events=run.notification_events+[f"retry:{stage}:{retry_count}"])

    def run_full(self,airflow_run_id:str,engine:str="python",profile:str="test",seed:int=17,serving_backend:str="sqlite",malformed:bool=False)->OrchestrationSummary:
        run=self.begin(airflow_run_id,engine,profile,seed,serving_backend)
        try:
            run=self.generate_source(run.orchestration_run_id,malformed); run=self.publish_raw(run.orchestration_run_id)
            for layer in (LakeLayer.bronze,LakeLayer.silver,LakeLayer.gold): run=self.transform(run.orchestration_run_id,layer); run=self.quality_gate(run.orchestration_run_id,layer)
            run=self.publish_serving(run.orchestration_run_id); summary=self.verify(run.orchestration_run_id); completed=self.complete(run.orchestration_run_id); return summary.model_copy(update={"run":completed})
        except Exception as exc:
            current=self.get(run.orchestration_run_id)
            if current.status!="failed": self.fail(run.orchestration_run_id,current.failure_stage or current.current_stage,str(exc),current.retry_count)
            raise
