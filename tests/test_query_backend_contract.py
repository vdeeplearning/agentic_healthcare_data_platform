import pytest

from src.database.backend import SQLiteQueryBackend
from tests.backend_contract import QueryBackendContract


@pytest.fixture
def backend(db_path):
    return SQLiteQueryBackend(db_path)


@pytest.fixture
def catalog(backend):
    return backend.discover_catalog()


class TestSQLiteQueryBackendContract(QueryBackendContract):
    """The permanent SQLite fixture runs the suite future backends must share."""

