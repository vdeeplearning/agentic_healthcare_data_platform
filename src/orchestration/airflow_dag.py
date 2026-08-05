"""Lazy Airflow DAG factory; importing project modules never starts Airflow."""
from __future__ import annotations

from datetime import datetime,timedelta,timezone

from src.config import Settings
from src.orchestration import airflow_tasks


TASK_SEQUENCE=("start_run","generate_source","wait_for_source_batch","publish_raw","transform_bronze","quality_gate_bronze","transform_silver","quality_gate_silver","transform_gold","quality_gate_gold","publish_serving","verify_serving","mark_success")


def _airflow_types():
    try:
        from airflow import DAG
        from airflow.operators.python import PythonOperator
        from airflow.sensors.python import PythonSensor
    except ImportError:
        try:
            from airflow.sdk import DAG
            from airflow.providers.standard.operators.python import PythonOperator
            from airflow.providers.standard.sensors.python import PythonSensor
        except ImportError as exc: raise RuntimeError("Airflow DAG support requires the optional `airflow` dependency group.") from exc
    return DAG,PythonOperator,PythonSensor


def build_dag(settings:Settings|None=None):
    settings=settings or Settings(); DAG,PythonOperator,PythonSensor=_airflow_types(); callbacks={"on_failure_callback":airflow_tasks.task_failure_callback,"on_retry_callback":airflow_tasks.task_retry_callback,"on_success_callback":airflow_tasks.task_success_callback}
    default_args={"owner":"clinical-data-platform","depends_on_past":False,"retries":settings.airflow_retries,"retry_delay":timedelta(seconds=settings.airflow_retry_delay_seconds),**callbacks}
    dag=DAG(dag_id=settings.airflow_dag_id,description="Orchestrate registered clinical lake transformations and serving publication.",schedule=settings.airflow_schedule,start_date=datetime(2026,1,1,tzinfo=timezone.utc),catchup=False,max_active_runs=1,default_args=default_args,params={"engine":"python","profile":"test","seed":17,"serving_backend":"sqlite","lake_root":str(settings.lake_root),"serving_path":str(settings.airflow_serving_path),"malformed":False,"parent_batch_id":None},tags=["healthcare","lake","governed","synthetic"])
    with dag:
        tasks={
            "start_run":PythonOperator(task_id="start_run",python_callable=airflow_tasks.start_run),
            "generate_source":PythonOperator(task_id="generate_source",python_callable=airflow_tasks.generate_source),
            "wait_for_source_batch":PythonSensor(task_id="wait_for_source_batch",python_callable=airflow_tasks.source_batch_ready,poke_interval=2,timeout=60,mode="poke"),
            "publish_raw":PythonOperator(task_id="publish_raw",python_callable=airflow_tasks.publish_raw),
            "transform_bronze":PythonOperator(task_id="transform_bronze",python_callable=airflow_tasks.transform_bronze),
            "quality_gate_bronze":PythonOperator(task_id="quality_gate_bronze",python_callable=airflow_tasks.quality_gate_bronze),
            "transform_silver":PythonOperator(task_id="transform_silver",python_callable=airflow_tasks.transform_silver),
            "quality_gate_silver":PythonOperator(task_id="quality_gate_silver",python_callable=airflow_tasks.quality_gate_silver),
            "transform_gold":PythonOperator(task_id="transform_gold",python_callable=airflow_tasks.transform_gold),
            "quality_gate_gold":PythonOperator(task_id="quality_gate_gold",python_callable=airflow_tasks.quality_gate_gold),
            "publish_serving":PythonOperator(task_id="publish_serving",python_callable=airflow_tasks.publish_serving),
            "verify_serving":PythonOperator(task_id="verify_serving",python_callable=airflow_tasks.verify_serving),
            "mark_success":PythonOperator(task_id="mark_success",python_callable=airflow_tasks.mark_success),
        }
        for upstream,downstream in zip(TASK_SEQUENCE,TASK_SEQUENCE[1:]): tasks[upstream]>>tasks[downstream]
    return dag
