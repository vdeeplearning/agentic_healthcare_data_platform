import pytest

from src.database.backend import SQLiteQueryBackend
from tests.backend_contract import QueryBackendContract


@pytest.fixture
def backend(db_path):
    return SQLiteQueryBackend(db_path)


@pytest.fixture
def catalog(backend):
    return backend.discover_catalog()


@pytest.fixture
def timeout_sql():
    return "WITH RECURSIVE x(n) AS (SELECT 1 UNION ALL SELECT n+1 FROM x WHERE n<100000000) SELECT SUM(n) FROM x"


class TestSQLiteQueryBackendContract(QueryBackendContract):
    """The permanent SQLite fixture runs the suite future backends must share."""
