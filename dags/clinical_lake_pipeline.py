"""Airflow discovery entry point; business logic lives in registered platform contracts."""
from src.orchestration.airflow_dag import build_dag

dag=build_dag()
