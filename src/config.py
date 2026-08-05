"""Application configuration."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal
from pydantic import AliasChoices,Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-backed settings; secrets are never serialized to audit logs."""

    model_config = SettingsConfigDict(env_prefix="CLINICAL_SQL_", env_file=".env", extra="ignore",populate_by_name=True)
    db_path: Path = Path("data/generated/clinical.db")
    database_backend: Literal["sqlite","postgres"] = Field(default="sqlite",validation_alias=AliasChoices("DATABASE_BACKEND","CLINICAL_SQL_DATABASE_BACKEND"))
    postgres_dsn: str | None = Field(default=None,validation_alias=AliasChoices("POSTGRES_DSN","DATABASE_URL","CLINICAL_SQL_POSTGRES_DSN"))
    postgres_schema: str = "public"
    postgres_storage_identity: str = "postgres:public"
    metadata_path: Path | None = None
    lake_root: Path = Path("data/lake")
    lake_transform_engine: Literal["python","spark"] = "python"
    spark_master: str = "local[*]"
    spark_shuffle_partitions: int = 4
    spark_log_level: str = "WARN"
    airflow_dag_id: str = "clinical_lake_pipeline"
    airflow_schedule: str = "@daily"
    airflow_retries: int = 2
    airflow_retry_delay_seconds: int = 300
    airflow_serving_path: Path = Path("data/generated/airflow-serving.db")
    demo_mode: bool = True
    seed: int = 42
    query_timeout_seconds: float = 5.0
    max_rows: int = 1000
    max_joins: int = 8
    max_selected_columns: int = 20
    small_cell_threshold: int = 10
    openai_api_key: str | None = None
    openai_model: str = "gpt-5.6-sol"


@lru_cache
def get_settings() -> Settings:
    return Settings()
