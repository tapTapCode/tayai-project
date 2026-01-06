from logging.config import fileConfig
import asyncio
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# Import models and Base for autogenerate support
import sys
import os
from pathlib import Path

# Add the backend directory to the path so we can import app
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

# Load environment variables and fix potential issues BEFORE importing anything
from dotenv import load_dotenv
load_dotenv(backend_dir.parent / ".env")

# Fix BACKEND_CORS_ORIGINS if it's empty or invalid
cors_origins = os.getenv("BACKEND_CORS_ORIGINS", "")
if not cors_origins or cors_origins.strip() == "":
    os.environ["BACKEND_CORS_ORIGINS"] = '["http://localhost:3000","http://localhost:3001"]'
elif not cors_origins.strip().startswith("["):
    # If it's not JSON, convert it to JSON array
    os.environ["BACKEND_CORS_ORIGINS"] = f'["{cors_origins}"]'

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Get database URL from environment or use default
database_url = os.getenv(
    "DATABASE_URL",
    "postgresql://tayai_user:tayai_password@localhost:5432/tayai_db"
)
# Convert to async URL
database_url = database_url.replace("postgresql://", "postgresql+asyncpg://")
config.set_main_option("sqlalchemy.url", database_url)

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# For migrations that are already written (not autogenerate), we don't need metadata
# The migration file defines the schema explicitly
target_metadata = None


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    # Convert async URL to sync for offline mode
    url = config.get_main_option("sqlalchemy.url").replace("+asyncpg", "")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in 'online' mode with async engine."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

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
