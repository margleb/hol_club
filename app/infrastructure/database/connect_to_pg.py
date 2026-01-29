import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine

logger = logging.getLogger(__name__)


async def get_pg_pool(
    db_name: str,
    host: str,
    port: int,
    user: str,
    password: str,
) -> tuple[AsyncEngine, async_sessionmaker]:

    try:
        database_url = f'postgresql+psycopg://{user}:{password}@{host}:{port}/{db_name}'
        engine = create_async_engine(
            database_url,
            pool_size=1,
            max_overflow=2,
            pool_pre_ping=True,
        )

        async_session_maker = async_sessionmaker(engine, expire_on_commit=False)

        async with engine.connect() as connection:
            result = await connection.execute(text("SELECT version();"))
            db_version = result.scalar_one()
            logger.info("Connected to %s", db_version)

        return engine, async_session_maker
    except Exception as e:
        logger.exception('Something went wrong while connecting to the database with exception: %s', e)
        raise
