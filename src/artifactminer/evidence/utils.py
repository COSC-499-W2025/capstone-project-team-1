"""Shared utilities for evidence extraction."""

from __future__ import annotations

from datetime import date, datetime


def coerce_date(value: object) -> date | None:
    """Coerce a date/datetime to a plain date, or return None."""
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return None
