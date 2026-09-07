import asyncio
import os
from logging.config import fileConfig

from sqlalchemy.engine import Connection

import app.persistence.models  # noqa: F401 Ensure all models are registered
from alembic import context
from app.config.settings import get_settings
from app.persistence.database import Base, get_engine

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Determine database URL from config, env, or app settings
cfg_url = config.get_main_option("sqlalchemy.url")
db_url = (
    cfg_url
    if cfg_url and not cfg_url.startswith("driver://")
    else (
        os.environ.get("TOKI_DATABASE_URL")
        or os.environ.get("DATABASE_URL")
        or get_settings().database_url
    )
)

# Normalize sqlite URLs for async
if db_url.startswith("sqlite:///"):
    db_url = db_url.replace("sqlite:///", "sqlite+aiosqlite:///")
elif db_url == "sqlite:///:memory:":
    db_url = "sqlite+aiosqlite:///:memory:"

config.set_main_option("sqlalchemy.url", db_url)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        render_as_batch=connection.dialect.name == "sqlite",
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations using the application's async engine."""
    connectable = get_engine(db_url)

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
