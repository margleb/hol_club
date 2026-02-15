import asyncio
import logging

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from fluentogram import TranslatorHub, TranslatorRunner
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.infrastructure.database.database.db import DB
from app.services.telegram.delivery_status import apply_delivery_error_status

logger = logging.getLogger(__name__)

PROFILE_NUDGE_CONTINUE_CALLBACK = "profile_nudge_continue"


def _build_nudge_keyboard(i18n: TranslatorRunner) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=i18n.profile.nudge.button(),
                    callback_data=PROFILE_NUDGE_CONTINUE_CALLBACK,
                )
            ]
        ]
    )


def _build_nudge_text(i18n: TranslatorRunner, attempt: int) -> str:
    if attempt <= 1:
        return i18n.profile.nudge.first.text()
    return i18n.profile.nudge.reminder.text()


async def start_profile_nudges_poller(
    *,
    bot,
    db_sessionmaker: async_sessionmaker,
    translator_hub: TranslatorHub,
    poll_interval_seconds: int = 600,
    first_delay_minutes: int = 15,
    remind_delay_hours: int = 24,
    max_attempts: int = 2,
    batch_size: int = 200,
) -> None:
    i18n: TranslatorRunner = translator_hub.get_translator_by_locale("ru")
    try:
        while True:
            await _poll_once(
                bot=bot,
                db_sessionmaker=db_sessionmaker,
                i18n=i18n,
                first_delay_minutes=first_delay_minutes,
                remind_delay_hours=remind_delay_hours,
                max_attempts=max_attempts,
                batch_size=batch_size,
            )
            await asyncio.sleep(poll_interval_seconds)
    except asyncio.CancelledError:
        logger.info("Profile nudges poller cancelled")
        raise
    except Exception as exc:
        logger.exception("Profile nudges poller crashed: %s", exc)


async def _poll_once(
    *,
    bot,
    db_sessionmaker: async_sessionmaker,
    i18n: TranslatorRunner,
    first_delay_minutes: int,
    remind_delay_hours: int,
    max_attempts: int,
    batch_size: int,
) -> None:
    keyboard = _build_nudge_keyboard(i18n)
    async with db_sessionmaker() as session:
        db = DB(session)
        try:
            await db.profile_nudges.mark_completed_for_filled_profiles()
            due_users = await db.profile_nudges.list_due_users(
                first_delay_minutes=first_delay_minutes,
                remind_delay_hours=remind_delay_hours,
                max_attempts=max_attempts,
                limit=batch_size,
            )
            for user_id, attempt in due_users:
                try:
                    await bot.send_message(
                        user_id,
                        text=_build_nudge_text(i18n, attempt),
                        reply_markup=keyboard,
                    )
                    await db.profile_nudges.mark_sent(user_id=user_id)
                except Exception as exc:
                    await apply_delivery_error_status(
                        db=db,
                        user_id=user_id,
                        error=exc,
                    )
                    logger.warning(
                        "Failed to send profile nudge to user_id=%s: %s",
                        user_id,
                        exc,
                    )
            await session.commit()
        except Exception as exc:
            await session.rollback()
            logger.exception("Profile nudges DB error: %s", exc)
