"""Alembic env.py — synchronous SQLAlchemy engine for migrations.

Alembic is a synchronous tool; we use psycopg2 here for migrations.
The application itself uses asyncpg at runtime — the two coexist fine.
"""

import logging
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from logging.config import fileConfig  # noqa: E402

from sqlalchemy import create_engine, pool  # noqa: E402

from alembic import context  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.models import Base  # noqa: E402

log = logging.getLogger("alembic.env")

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _get_sync_url() -> str:
    """Convert asyncpg URL to psycopg2 URL for Alembic."""
    url = get_settings().database_url
    # postgresql+asyncpg:// -> postgresql+psycopg2://
    return re.sub(r"postgresql\+asyncpg", "postgresql+psycopg2", url)


def run_migrations_offline() -> None:
    context.configure(
        url=_get_sync_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    url = _get_sync_url()
    log.info("Connecting to database for migrations (psycopg2)...")
    connectable = create_engine(url, poolclass=pool.NullPool)
    with connectable.connect() as connection:
        log.info("Running migrations...")
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()
    log.info("Migrations complete.")


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
