import asyncio
import logging
import sys
from datetime import date
from pathlib import Path
from urllib.parse import quote

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy import or_, select

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from app.bot.enums.roles import UserRole
from app.bot.i18n.translator_hub import create_translator_hub
from app.infrastructure.database.connect_to_pg import get_pg_pool
from app.infrastructure.database.models.users import UsersModel
from config.config import settings

logger = logging.getLogger(__name__)


def _build_start_payload() -> str:
    placement_date = date.today().isoformat()
    channel = "hol_club"
    price = "0"
    return f"{placement_date}_{channel}_{price}"


def _build_keyboard(i18n, bot_username: str) -> InlineKeyboardMarkup:
    payload = _build_start_payload()
    url = f"https://t.me/{bot_username}?start={quote(payload)}"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=i18n.general.registration.request.button(),
                    url=url,
                )
            ]
        ]
    )


async def main() -> int:
    translator_hub = create_translator_hub()
    i18n = translator_hub.get_translator_by_locale(settings.i18n.default_locale)
    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode(settings.bot.parse_mode)),
    )

    try:
        me = await bot.get_me()
        bot_username = me.username
    except Exception as exc:
        logger.warning("Failed to fetch bot username: %s", exc)
        await bot.session.close()
        return 1

    if not bot_username:
        print("Bot username is missing.")
        await bot.session.close()
        return 1

    engine, session_maker = await get_pg_pool(
        db_name=settings.postgres.db,
        host=settings.postgres.host,
        port=settings.postgres.port,
        user=settings.postgres_user,
        password=settings.postgres_password,
    )

    sent = 0
    failed = 0

    async with session_maker() as session:
        result = await session.execute(
            select(UsersModel.user_id).where(
                UsersModel.role == UserRole.USER,
                UsersModel.is_alive.is_(True),
                UsersModel.is_blocked.is_(False),
                or_(UsersModel.gender.is_(None), UsersModel.age_group.is_(None)),
            )
        )
        user_ids = [row[0] for row in result.all()]

    if not user_ids:
        print(i18n.general.registration.request.empty())
        await bot.session.close()
        await engine.dispose()
        return 0

    keyboard = _build_keyboard(i18n, bot_username)
    for user_id in user_ids:
        try:
            await bot.send_message(
                chat_id=user_id,
                text=i18n.general.registration.request.text(),
                reply_markup=keyboard,
            )
            sent += 1
        except Exception as exc:
            failed += 1
            logger.warning("Failed to send message to user_id=%s: %s", user_id, exc)

        await asyncio.sleep(0.05)

    await bot.session.close()
    await engine.dispose()

    print("Sent: %d, failed: %d" % (sent, failed))
    return 0


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.getLevelName(settings.logs.level_name),
        format=settings.logs.format,
    )
    sys.exit(asyncio.run(main()))
