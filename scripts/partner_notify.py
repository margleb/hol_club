import asyncio
import logging
import sys

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from app.bot.handlers.partner_requests import _build_partner_request_keyboard
from app.bot.i18n.translator_hub import create_translator_hub
from config.config import settings

logger = logging.getLogger(__name__)


async def main() -> int:
    channel = settings.get("events_channel")
    translator_hub = create_translator_hub()
    i18n = translator_hub.get_translator_by_locale(settings.i18n.default_locale)

    if not channel:
        print(i18n.partner.request.channel.missing())
        return 1

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode(settings.bot.parse_mode)),
    )
    try:
        await bot.send_message(
            chat_id=channel,
            text=i18n.partner.request.channel.text(),
            reply_markup=_build_partner_request_keyboard(i18n),
        )
        print(i18n.partner.request.channel.posted())
    except Exception as exc:
        logger.warning("Failed to post partner request message: %s", exc)
        print(i18n.partner.request.channel.failed())
        return 1
    finally:
        await bot.session.close()

    return 0


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.getLevelName(settings.logs.level_name),
        format=settings.logs.format,
    )
    sys.exit(asyncio.run(main()))
