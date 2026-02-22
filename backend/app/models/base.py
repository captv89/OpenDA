"""SQLAlchemy declarative base and shared utilities."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime
from sqlalchemy.orm import DeclarativeBase, mapped_column, MappedColumn


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


# Re-export for convenience
__all__ = ["Base", "utcnow"]
