"""Alembic env.py — async SQLAlchemy + model auto-discovery."""
import asyncio
import sys
from pathlib import Path

# Ensure the backend package root is on sys.path so app.* imports work
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from logging.config import fileConfig  # noqa: E402

from alembic import context  # noqa: E402
from sqlalchemy.ext.asyncio import create_async_engine  # noqa: E402

from app.config import get_settings  # noqa: E402
from app.models import Base  # noqa: E402  # registers all ORM models

# ---------------------------------------------------------------------------
# Alembic config object
# ---------------------------------------------------------------------------
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_url() -> str:
    return get_settings().database_url


def do_run_migrations(connection) -> None:  # type: ignore[type-arg]
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


# ---------------------------------------------------------------------------
# Offline mode (generates SQL without a live DB connection)
# ---------------------------------------------------------------------------

def run_migrations_offline() -> None:
    context.configure(
        url=_get_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


# ---------------------------------------------------------------------------
# Online mode (async engine)
# ---------------------------------------------------------------------------

async def run_migrations_online() -> None:
    engine = create_async_engine(_get_url(), poolclass=None)  # type: ignore[arg-type]
    async with engine.connect() as conn:
        await conn.run_sync(do_run_migrations)
    await engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
