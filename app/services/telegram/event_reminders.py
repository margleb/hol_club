import asyncio
import html
import logging
from datetime import timedelta

from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from fluentogram import TranslatorHub
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.infrastructure.database.database.db import DB
from app.services.telegram.delivery_status import apply_delivery_error_status
from app.utils.datetime import format_event_datetime, now_utc

logger = logging.getLogger(__name__)

DEFAULT_EVENT_REMINDER_INTERVAL_SECONDS = 300
DEFAULT_EVENT_REMINDER_BATCH_SIZE = 50
EVENT_REMINDER_LEAD_TIME = timedelta(days=1)


def _build_channel_post_link(
    channel_id: int | None,
    message_id: int | None,
) -> str | None:
    if not channel_id or not message_id:
        return None

    chat_id_str = str(channel_id)
    if chat_id_str.startswith("-100"):
        channel_id_str = chat_id_str[4:]
    else:
        channel_id_str = str(abs(channel_id))
    return f"https://t.me/c/{channel_id_str}/{message_id}"


def _can_show_event_chat_link(event) -> bool:
    if getattr(event, "private_chat_deleted_at", None) is not None:
        return False

    delete_at = getattr(event, "private_chat_delete_at", None)
    if delete_at is not None and delete_at <= now_utc():
        return False

    return True


def _build_reminder_keyboard(
    *,
    i18n,
    post_url: str | None,
    chat_url: str | None,
) -> InlineKeyboardMarkup | None:
    rows = []

    if post_url:
        rows.append(
            [
                InlineKeyboardButton(
                    text=i18n.partner.event.view.post.button(),
                    url=post_url,
                )
            ]
        )

    if chat_url:
        rows.append(
            [
                InlineKeyboardButton(
                    text=i18n.partner.event.join.chat.link.button(),
                    url=chat_url,
                )
            ]
        )

    if not rows:
        return None

    return InlineKeyboardMarkup(inline_keyboard=rows)


async def send_due_event_reminders_once(
    *,
    bot: Bot,
    session_maker: async_sessionmaker,
    translator_hub: TranslatorHub,
    batch_size: int = DEFAULT_EVENT_REMINDER_BATCH_SIZE,
) -> None:
    current_time = now_utc()
    remind_before = current_time + EVENT_REMINDER_LEAD_TIME
    i18n = translator_hub.get_translator_by_locale("ru")

    async with session_maker() as session:
        db = DB(session)
        due_reminders = await db.event_registrations.list_due_for_reminder(
            now=current_time,
            remind_before=remind_before,
            limit=batch_size,
        )

        for user_id, event in due_reminders:
            post_url = _build_channel_post_link(
                getattr(event, "channel_id", None),
                getattr(event, "channel_message_id", None),
            )
            chat_url = (
                getattr(event, "private_chat_invite_link", None)
                if _can_show_event_chat_link(event)
                else None
            )
            keyboard = _build_reminder_keyboard(
                i18n=i18n,
                post_url=post_url,
                chat_url=chat_url,
            )
            text = i18n.partner.event.reminder.text(
                event_name=html.escape(event.name or ""),
                datetime=html.escape(format_event_datetime(event.event_datetime)),
                address=html.escape(event.address or ""),
            )

            try:
                await bot.send_message(
                    chat_id=user_id,
                    text=text,
                    reply_markup=keyboard,
                )
                await db.event_registrations.mark_reminder_sent_if_pending(
                    event_id=event.id,
                    user_id=user_id,
                )
            except Exception as exc:
                await apply_delivery_error_status(
                    db=db,
                    user_id=user_id,
                    error=exc,
                )
                logger.warning(
                    "Failed to send event reminder to user %s for event %s: %s",
                    user_id,
                    event.id,
                    exc,
                )

        await session.commit()


async def run_event_reminders_loop(
    *,
    bot: Bot,
    session_maker: async_sessionmaker,
    translator_hub: TranslatorHub,
    interval_seconds: int = DEFAULT_EVENT_REMINDER_INTERVAL_SECONDS,
) -> None:
    while True:
        try:
            await send_due_event_reminders_once(
                bot=bot,
                session_maker=session_maker,
                translator_hub=translator_hub,
            )
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Event reminders loop failed")

        await asyncio.sleep(interval_seconds)
