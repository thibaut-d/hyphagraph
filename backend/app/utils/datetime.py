"""Datetime helpers for database-safe UTC timestamps."""

from __future__ import annotations

from datetime import datetime, timezone


def utc_now_naive() -> datetime:
    """Return the current UTC time without tzinfo for naive DB timestamp columns."""
    return datetime.now(timezone.utc).replace(tzinfo=None)
