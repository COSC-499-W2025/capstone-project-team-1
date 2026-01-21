"""Mock database connection utilities."""
from typing import Any, Dict

_mock_db: Dict[str, Any] = {
    "users": {
        1: {"id": 1, "username": "alice", "email": "alice@example.com"},
        2: {"id": 2, "username": "bob", "email": "bob@example.com"},
    },
    "items": [],
}


def get_db_connection() -> Dict[str, Any]:
    """Return mock database connection."""
    return _mock_db


def insert_record(table: str, record: Dict[str, Any]) -> bool:
    """Insert a record into the mock database."""
    if table not in _mock_db:
        _mock_db[table] = []
    _mock_db[table].append(record)
    return True


def close_connection() -> None:
    """Close the mock database connection."""
    pass
