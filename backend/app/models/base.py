"""SQLAlchemy declarative base and shared utilities."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import DeclarativeBase


def utcnow() -> datetime:
    # Return naive UTC datetime — columns are TIMESTAMP WITHOUT TIME ZONE.
    # asyncpg rejects timezone-aware datetimes for such columns.
    return datetime.now(UTC).replace(tzinfo=None)


class Base(DeclarativeBase):
    pass


# Re-export for convenience
__all__ = ["Base", "utcnow"]
