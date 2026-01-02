import asyncio
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from sqlalchemy import text

from app.infrastructure.database.connect_to_pg import get_pg_pool
from config.config import settings

logger = logging.getLogger(__name__)


async def main() -> int:
    engine, session_maker = await get_pg_pool(
        db_name=settings.postgres.db,
        host=settings.postgres.host,
        port=settings.postgres.port,
        user=settings.postgres_user,
        password=settings.postgres_password,
    )

    async with session_maker() as session:
        result = await session.execute(
            text(
                """
                UPDATE event_interesting ei
                SET username = u.username
                FROM users u
                WHERE ei.user_id = u.user_id
                  AND ei.username IS NULL
                  AND u.username IS NOT NULL
                """
            )
        )
        await session.commit()

    await engine.dispose()

    updated = int(result.rowcount or 0)
    print("Event interesting updated: %d" % updated)
    return 0


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.getLevelName(settings.logs.level_name),
        format=settings.logs.format,
    )
    sys.exit(asyncio.run(main()))
