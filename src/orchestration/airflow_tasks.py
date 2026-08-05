"""Thin Airflow callables. They coordinate runner stages and contain no transformations."""
from __future__ import annotations

import logging
from pathlib import Path

from src.config import Settings
from src.lake.models import LakeLayer
from src.orchestration.runner import PipelineOrchestrator


LOGGER=logging.getLogger(__name__)


def _conf(context)->dict:
    values=dict(context.get("params") or {}); dag_run=context.get("dag_run")
    if dag_run and getattr(dag_run,"conf",None): values.update(dag_run.conf)
    return values


def _runner(context)->PipelineOrchestrator:
    values=_conf(context); root=Path(values.get("lake_root","data/lake")); serving=Path(values.get("serving_path","data/generated/airflow-serving.db"))
    return PipelineOrchestrator(Settings(_env_file=None,lake_root=root,airflow_serving_path=serving),root,serving)


def _run_id(context)->str:
    identifier=context["ti"].xcom_pull(task_ids="start_run")
    if not identifier: raise RuntimeError("The orchestration run ID is unavailable from start_run.")
    return identifier


def start_run(**context):
    values=_conf(context); dag_run=context["dag_run"]; run=_runner(context).begin(dag_run.run_id,values.get("engine","python"),values.get("profile","test"),int(values.get("seed",17)),values.get("serving_backend","sqlite"),context["dag"].dag_id)
    return run.orchestration_run_id


def generate_source(**context):
    values=_conf(context); return _runner(context).generate_source(_run_id(context),bool(values.get("malformed",False)),values.get("parent_batch_id")).source_batch_id


def source_batch_ready(**context): return _runner(context).source_ready(_run_id(context))
def publish_raw(**context): return _runner(context).publish_raw(_run_id(context)).layer_snapshot_ids["raw"]
def transform_bronze(**context): return _runner(context).transform(_run_id(context),LakeLayer.bronze).layer_snapshot_ids["bronze"]
def quality_gate_bronze(**context): return _runner(context).quality_gate(_run_id(context),LakeLayer.bronze).quality_gate_results["bronze"]
def transform_silver(**context): return _runner(context).transform(_run_id(context),LakeLayer.silver).layer_snapshot_ids["silver"]
def quality_gate_silver(**context): return _runner(context).quality_gate(_run_id(context),LakeLayer.silver).quality_gate_results["silver"]
def transform_gold(**context): return _runner(context).transform(_run_id(context),LakeLayer.gold).layer_snapshot_ids["gold"]
def quality_gate_gold(**context): return _runner(context).quality_gate(_run_id(context),LakeLayer.gold).quality_gate_results["gold"]
def publish_serving(**context): return _runner(context).publish_serving(_run_id(context)).serving_snapshot_id
def verify_serving(**context): return _runner(context).verify(_run_id(context)).model_dump(mode="json")
def mark_success(**context): return _runner(context).complete(_run_id(context)).model_dump(mode="json")


def task_retry_callback(context):
    try: _runner(context).record_retry(_run_id(context),context["task_instance"].task_id,int(context["task_instance"].try_number))
    except Exception: LOGGER.exception("Could not persist retry metadata.")


def task_failure_callback(context):
    try: _runner(context).fail(_run_id(context),context["task_instance"].task_id,str(context.get("exception","task failed")),int(context["task_instance"].try_number))
    except Exception: LOGGER.exception("Could not persist failure metadata.")


def task_success_callback(context): LOGGER.info("Airflow task succeeded: %s",context["task_instance"].task_id)
