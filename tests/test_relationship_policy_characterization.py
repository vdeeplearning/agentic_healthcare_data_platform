from src.database.backend import APPROVED_RELATIONSHIPS, SQLiteQueryBackend
from src.safety.sql_validator import validate_sql


FUTURE_NEWLY_REJECTED = [
    "SELECT COUNT(*) FROM hospitals h JOIN patients p ON h.hospital_id=p.patient_id",
    "SELECT COUNT(*) FROM providers p JOIN patients x ON p.provider_id=x.patient_id",
]


def test_relationship_metadata_is_characterized(db_path):
    catalog = SQLiteQueryBackend(db_path).discover_catalog()
    pairs = {(relationship.left, relationship.right) for relationship in catalog.relationships}
    assert pairs == set(APPROVED_RELATIONSHIPS)


def test_current_validator_allows_non_cartesian_unregistered_relationships(db_path):
    catalog = SQLiteQueryBackend(db_path).discover_catalog()
    assert all(validate_sql(sql, catalog=catalog).valid for sql in FUTURE_NEWLY_REJECTED)


def test_current_validator_still_rejects_cartesian_join(db_path):
    catalog = SQLiteQueryBackend(db_path).discover_catalog()
    assert not validate_sql("SELECT * FROM hospitals h JOIN patients p", catalog=catalog).valid
