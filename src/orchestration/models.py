"""Bounded metadata emitted by local and Airflow-orchestrated pipeline runs."""
from __future__ import annotations

from datetime import datetime,timezone
from typing import Any,Literal

from pydantic import BaseModel,Field


class OrchestrationRun(BaseModel):
    orchestration_run_id:str
    dag_id:str
    airflow_run_id:str
    status:Literal["running","failed","completed"]="running"
    engine:Literal["python","spark"]="python"
    serving_backend:Literal["sqlite","postgres"]="sqlite"
    profile:str="test"
    seed:int=17
    started_at:datetime=Field(default_factory=lambda:datetime.now(timezone.utc))
    finished_at:datetime|None=None
    execution_time_ms:float|None=None
    current_stage:str="initialized"
    dataset_id:str|None=None
    source_batch_id:str|None=None
    layer_snapshot_ids:dict[str,str]=Field(default_factory=dict)
    layer_manifest_ids:dict[str,str]=Field(default_factory=dict)
    transformation_run_ids:dict[str,str]=Field(default_factory=dict)
    quality_gate_results:dict[str,dict[str,Any]]=Field(default_factory=dict)
    warnings:list[str]=Field(default_factory=list)
    serving_snapshot_id:str|None=None
    serving_manifest_id:str|None=None
    verification_analysis_run_id:str|None=None
    parent_lineage:list[str]=Field(default_factory=list)
    failure_stage:str|None=None
    failure_message:str|None=None
    retry_count:int=0
    notification_events:list[str]=Field(default_factory=list)


class OrchestrationSummary(BaseModel):
    run:OrchestrationRun
    patient_count:int|None=None
