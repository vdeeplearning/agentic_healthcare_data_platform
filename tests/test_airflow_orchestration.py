from __future__ import annotations

import importlib.util
from types import SimpleNamespace

import pytest

from src.audit.repository import SQLiteAuditStore
from src.config import Settings
from src.lake.engines import LocalPythonTransformationEngine
from src.lake.models import LakeLayer
from src.metadata.lineage import LineageResolver
from src.metadata.repository import SQLiteManifestStore,metadata_path_for
from src.orchestration import airflow_tasks
from src.orchestration.airflow_dag import TASK_SEQUENCE,build_dag
from src.orchestration.models import OrchestrationRun
from src.orchestration.runner import PipelineOrchestrator,QualityGateFailed,orchestration_identity
from src.orchestration.store import FilesystemOrchestrationStore


@pytest.fixture
def orchestrator(tmp_path):
    settings=Settings(_env_file=None,lake_root=tmp_path/"lake",airflow_serving_path=tmp_path/"serving.db")
    return PipelineOrchestrator(settings,tmp_path/"lake",tmp_path/"serving.db")


def test_python_orchestration_runs_complete_dependency_contract(orchestrator):
    summary=orchestrator.run_full("manual__2026-08-05",engine="python",profile="test",seed=17)
    run=summary.run
    assert run.status=="completed" and summary.patient_count==300
    assert set(run.layer_snapshot_ids)=={"raw","bronze","silver","gold"}
    assert all(run.quality_gate_results[layer]["passed"] for layer in ("bronze","silver","gold"))
    assert run.serving_snapshot_id and run.verification_analysis_run_id and run.execution_time_ms>=0
    assert run.notification_events==["run_started","run_succeeded"]


def test_airflow_identity_and_manual_retry_are_idempotent(orchestrator):
    first=orchestrator.begin("scheduled__2026-08-05",profile="test"); again=orchestrator.begin("scheduled__2026-08-05",profile="demo")
    assert first==again and first.orchestration_run_id==orchestration_identity(first.dag_id,first.airflow_run_id)
    retried=orchestrator.record_retry(first.orchestration_run_id,"transform_bronze",2)
    assert retried.retry_count==2 and retried.notification_events[-1]=="retry:transform_bronze:2"


def test_failed_quality_gate_preserves_previous_snapshots_and_serving(orchestrator):
    good=orchestrator.run_full("manual__good",seed=17); bronze_before=orchestrator.lake.get_active_snapshot(LakeLayer.bronze); serving_before=good.run.serving_snapshot_id
    with pytest.raises(QualityGateFailed): orchestrator.run_full("manual__malformed",seed=18,malformed=True)
    failed=orchestrator.runs.get(orchestration_identity(orchestrator.settings.airflow_dag_id,"manual__malformed"))
    assert failed.status=="failed" and failed.failure_stage=="transform_bronze"
    assert orchestrator.lake.get_active_snapshot(LakeLayer.bronze).snapshot_id==bronze_before.snapshot_id
    assert failed.serving_snapshot_id is None and good.run.serving_snapshot_id==serving_before


def test_gate_refuses_missing_or_inactive_candidate(orchestrator):
    run=orchestrator.begin("manual__gate")
    with pytest.raises(QualityGateFailed): orchestrator.quality_gate(run.orchestration_run_id,LakeLayer.gold)
    assert orchestrator.get(run.orchestration_run_id).failure_stage=="quality_gate_gold"


def test_spark_engine_selection_is_configuration_driven(monkeypatch,orchestrator):
    selected=[]
    def factory(settings,store): selected.append(settings.lake_transform_engine); return LocalPythonTransformationEngine()
    monkeypatch.setattr("src.orchestration.runner.create_transformation_engine",factory)
    summary=orchestrator.run_full("manual__spark-config",engine="spark")
    assert summary.run.engine=="spark" and selected==["spark","spark","spark"]


def test_analysis_lineage_includes_airflow_run_between_serving_and_source(orchestrator):
    summary=orchestrator.run_full("manual__lineage")
    resolver=LineageResolver(SQLiteAuditStore(orchestrator.serving_path),SQLiteManifestStore(metadata_path_for(orchestrator.serving_path)),orchestrator.lake,orchestrator.runs)
    lineage=resolver.resolve_run(summary.run.verification_analysis_run_id)
    assert lineage["orchestration_run"]["airflow_run_id"]=="manual__lineage"
    assert lineage["orchestration_run"]["source_batch_id"]==lineage["lake_lineage"][-1]["metadata"]["source_batch_id"]
    assert [item["layer"] for item in lineage["lake_lineage"]]==["gold","silver","bronze","raw"]


def test_orchestration_store_is_atomic_bounded_and_path_safe(tmp_path):
    store=FilesystemOrchestrationStore(tmp_path/"lake"); run=OrchestrationRun(orchestration_run_id="orchestration-safe",dag_id="dag",airflow_run_id="manual")
    assert store.save(run)==run and store.get(run.orchestration_run_id)==run and store.list(1)==[run]
    with pytest.raises(ValueError,match="Unsafe"): store.get("../outside")
    assert not list(store.root.glob("*.tmp"))


class FakeTask:
    def __init__(self,task_id,python_callable,**kwargs): self.task_id=task_id; self.python_callable=python_callable; self.downstream_task_ids=set(); FakeDag.current.tasks.append(self)
    def __rshift__(self,other): self.downstream_task_ids.add(other.task_id); return other


class FakeDag:
    current=None
    def __init__(self,**kwargs): self.__dict__.update(kwargs); self.tasks=[]
    def __enter__(self): FakeDag.current=self; return self
    def __exit__(self,*args): FakeDag.current=None
    @property
    def task_ids(self): return [task.task_id for task in self.tasks]
    def get_task(self,task_id): return next(task for task in self.tasks if task.task_id==task_id)


def test_dag_validity_order_retries_schedule_and_catchup(monkeypatch,tmp_path):
    monkeypatch.setattr("src.orchestration.airflow_dag._airflow_types",lambda:(FakeDag,FakeTask,FakeTask))
    settings=Settings(_env_file=None,lake_root=tmp_path/"lake",airflow_serving_path=tmp_path/"serving.db",airflow_retries=3,airflow_retry_delay_seconds=7)
    dag=build_dag(settings)
    assert tuple(dag.task_ids)==TASK_SEQUENCE and not dag.catchup and dag.schedule=="@daily" and dag.max_active_runs==1
    assert dag.default_args["retries"]==3 and dag.default_args["retry_delay"].total_seconds()==7
    for upstream,downstream in zip(TASK_SEQUENCE,TASK_SEQUENCE[1:]): assert dag.get_task(upstream).downstream_task_ids=={downstream}


def test_airflow_callables_share_only_identifiers_via_xcom(monkeypatch,tmp_path):
    values={}; ti=SimpleNamespace(xcom_pull=lambda task_ids:values.get(task_ids),task_id="task",try_number=1); dag=SimpleNamespace(dag_id="clinical_lake_pipeline"); dag_run=SimpleNamespace(run_id="manual__tasks",conf={"lake_root":str(tmp_path/"lake"),"serving_path":str(tmp_path/"serving.db"),"engine":"python"}); context={"ti":ti,"task_instance":ti,"dag":dag,"dag_run":dag_run,"params":{}}
    values["start_run"]=airflow_tasks.start_run(**context); batch=airflow_tasks.generate_source(**context)
    assert isinstance(values["start_run"],str) and isinstance(batch,str) and airflow_tasks.source_batch_ready(**context)
    raw=airflow_tasks.publish_raw(**context); bronze=airflow_tasks.transform_bronze(**context); gate=airflow_tasks.quality_gate_bronze(**context)
    assert all(isinstance(value,str) for value in (raw,bronze)) and gate["passed"]


def test_callbacks_log_retry_failure_and_success(monkeypatch,orchestrator):
    run=orchestrator.begin("manual__callback"); ti=SimpleNamespace(xcom_pull=lambda task_ids:run.orchestration_run_id,task_id="transform_bronze",try_number=2); context={"ti":ti,"task_instance":ti,"dag_run":SimpleNamespace(conf={"lake_root":str(orchestrator.lake.root),"serving_path":str(orchestrator.serving_path)}),"params":{},"exception":RuntimeError("boom")}
    airflow_tasks.task_retry_callback(context); airflow_tasks.task_failure_callback(context); airflow_tasks.task_success_callback(context)
    failed=orchestrator.runs.get(run.orchestration_run_id); assert failed.status=="failed" and failed.retry_count==2 and failed.failure_message=="boom"


@pytest.mark.skipif(importlib.util.find_spec("airflow") is None,reason="optional Airflow dependency is not installed")
def test_real_airflow_dag_imports_without_errors():
    dag=build_dag(); assert tuple(task.task_id for task in dag.topological_sort())==TASK_SEQUENCE
