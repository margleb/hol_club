import asyncio
import logging

from sqlalchemy.ext.asyncio import async_sessionmaker

from app.infrastructure.database.database.db import DB
from app.services.telegram.private_event_chats import EventPrivateChatService
from app.utils.datetime import now_utc

logger = logging.getLogger(__name__)
DEFAULT_EVENT_CHAT_CLEANUP_INTERVAL_SECONDS = 300


def _get_event_chat_id(event) -> int | None:
    if getattr(event, "male_chat_id", None):
        return event.male_chat_id
    if getattr(event, "female_chat_id", None):
        return event.female_chat_id
    return None


async def cleanup_due_event_chats_once(
    *,
    session_maker: async_sessionmaker,
    event_private_chat_service: EventPrivateChatService | None,
    batch_size: int = 20,
) -> None:
    if event_private_chat_service is None or not event_private_chat_service.connected:
        return

    async with session_maker() as session:
        db = DB(session)
        due_events = await db.events.list_private_chats_due_for_deletion(
            delete_before=now_utc(),
            limit=batch_size,
        )
        for event in due_events:
            chat_id = _get_event_chat_id(event)
            if chat_id is None:
                await db.events.mark_private_chat_deleted(event_id=event.id)
                continue

            deleted = await event_private_chat_service.delete_event_chat(chat_id=chat_id)
            if not deleted:
                logger.warning(
                    "Deferred deletion of private chat failed for event_id=%s chat_id=%s",
                    event.id,
                    chat_id,
                )
                continue

            await db.events.mark_private_chat_deleted(event_id=event.id)

        await session.commit()


async def run_event_chat_cleanup_loop(
    *,
    session_maker: async_sessionmaker,
    event_private_chat_service: EventPrivateChatService | None,
    interval_seconds: int = DEFAULT_EVENT_CHAT_CLEANUP_INTERVAL_SECONDS,
) -> None:
    while True:
        try:
            await cleanup_due_event_chats_once(
                session_maker=session_maker,
                event_private_chat_service=event_private_chat_service,
            )
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Event chat cleanup loop failed")

        await asyncio.sleep(interval_seconds)
