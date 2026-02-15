import asyncio
import os
import sys
from logging.config import fileConfig

from sqlalchemy.ext.asyncio import AsyncConnection, create_async_engine

from alembic import context
from config.config import settings
from app.infrastructure.database.models.base import BaseModel
from app.infrastructure.database.models import (  # noqa: F401
    partner_requests,
    profile_nudges,
    users,
)

# Alembic Config object
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Metadata object for autogenerate support
target_metadata = BaseModel.metadata

# Database URL for SQLAlchemy
url = f"postgresql+psycopg://{settings.postgres_user}:{settings.postgres_password}@{settings.postgres.host}:{settings.postgres.port}/{settings.postgres.db}"
engine = create_async_engine(url)


async def run_migrations():
    async with engine.connect() as connection:
        await connection.run_sync(do_run_migrations)


def do_run_migrations(connection: AsyncConnection):
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        render_as_batch=True,
    )

    with context.begin_transaction():
        context.run_migrations()


if sys.platform.startswith("win") or os.name == "nt":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

asyncio.run(run_migrations())
