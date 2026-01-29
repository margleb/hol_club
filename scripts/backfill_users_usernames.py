import asyncio
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from sqlalchemy import select, update

from app.infrastructure.database.connect_to_pg import get_pg_pool
from app.infrastructure.database.models.users import UsersModel
from config.config import settings

logger = logging.getLogger(__name__)


async def main() -> int:
    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode(settings.bot.parse_mode)),
    )
    engine, session_maker = await get_pg_pool(
        db_name=settings.postgres.db,
        host=settings.postgres.host,
        port=settings.postgres.port,
        user=settings.postgres_user,
        password=settings.postgres_password,
    )

    processed = 0
    updated = 0
    batch = 0

    async with session_maker() as session:
        result = await session.execute(
            select(UsersModel.user_id).where(UsersModel.username.is_(None))
        )
        user_ids = [row[0] for row in result.all()]
        if not user_ids:
            print("No users to backfill.")
            await bot.session.close()
            await engine.dispose()
            return 0

        for user_id in user_ids:
            processed += 1
            try:
                chat = await bot.get_chat(user_id)
            except Exception as exc:
                logger.warning("Failed to fetch chat for user_id=%s: %s", user_id, exc)
                continue

            username = getattr(chat, "username", None)
            if not username:
                continue

            stmt = (
                update(UsersModel)
                .where(UsersModel.user_id == user_id)
                .where(UsersModel.username.is_(None))
                .values(username=username)
            )
            update_result = await session.execute(stmt)
            if update_result.rowcount:
                updated += update_result.rowcount

            batch += 1
            if batch >= 100:
                await session.commit()
                batch = 0

        if batch:
            await session.commit()

    await bot.session.close()
    await engine.dispose()

    print("Processed users: %d, users updated: %d" % (processed, updated))
    return 0


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.getLevelName(settings.logs.level_name),
        format=settings.logs.format,
    )
    sys.exit(asyncio.run(main()))
