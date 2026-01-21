"""Helper utility functions."""
import hashlib
from typing import List, Any
from datetime import datetime


def hash_password(password: str) -> str:
    """Hash a password using SHA-256."""
    return hashlib.sha256(password.encode()).hexdigest()


def format_timestamp(dt: datetime) -> str:
    """Format datetime to ISO string."""
    return dt.isoformat()


def paginate(items: List[Any], page: int = 1, per_page: int = 10) -> List[Any]:
    """Paginate a list of items."""
    start = (page - 1) * per_page
    end = start + per_page
    return items[start:end]


def validate_email(email: str) -> bool:
    """Basic email validation."""
    return "@" in email and "." in email.split("@")[-1]
