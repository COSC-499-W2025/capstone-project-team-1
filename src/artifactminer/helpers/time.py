from __future__ import annotations

from datetime import datetime, timezone


def utcnow() -> datetime:
    """Return a naive UTC datetime (compatible with existing DB columns)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)

