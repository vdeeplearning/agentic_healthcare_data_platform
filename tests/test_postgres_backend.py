from pathlib import Path

import pytest

from src.config import Settings
from src.database.factory import create_query_backend
from src.database.postgres_backend import PostgresQueryBackend,_normalize


def test_postgres_driver_dependency_error_is_actionable(monkeypatch):
    import builtins
    from src.database.postgres_backend import _driver

    real_import=builtins.__import__
    def missing_psycopg(name,*args,**kwargs):
        if name=="psycopg": raise ImportError("not installed")
        return real_import(name,*args,**kwargs)
    monkeypatch.setattr(builtins,"__import__",missing_psycopg)
    with pytest.raises(RuntimeError,match=r"psycopg\[binary\]"):
        _driver()


def test_postgres_driver_and_normalization_are_available():
    import decimal
    import psycopg
    assert psycopg.__version__.startswith("3.")
    assert _normalize(decimal.Decimal("1.25"))==1.25


def test_backend_factory_defaults_to_sqlite_and_requires_postgres_dsn(tmp_path):
    sqlite_settings=Settings(_env_file=None,db_path=tmp_path/"demo.db",database_backend="sqlite")
    assert create_query_backend(sqlite_settings).name=="sqlite"
    with pytest.raises(ValueError,match="POSTGRES_DSN"):
        create_query_backend(Settings(_env_file=None,database_backend="postgres",postgres_dsn=None))
    postgres=create_query_backend(Settings(_env_file=None,database_backend="postgres",postgres_dsn="postgresql://example.invalid/db"))
    assert isinstance(postgres,PostgresQueryBackend) and postgres.name=="postgres"


def test_database_backend_environment_alias(monkeypatch):
    monkeypatch.setenv("DATABASE_BACKEND","postgres"); monkeypatch.setenv("POSTGRES_DSN","postgresql://example.invalid/db")
    settings=Settings(_env_file=None)
    assert settings.database_backend=="postgres" and settings.postgres_dsn.endswith("/db")


def test_postgres_ddl_is_logically_complete():
    ddl=(Path(__file__).parents[1]/"sql"/"postgres"/"schema.sql").read_text()
    for relation in ("patients","hospitals","providers","encounters","diagnoses","encounter_diagnoses","procedures","encounter_procedures","lab_results","readmissions","quality_measures","encounter_facts","hospital_readmission_summary"):
        assert relation in ddl
    assert "REFERENCES" in ddl and "CHECK" in ddl and "CREATE INDEX" in ddl
