import asyncio
import logging

from fluentogram import TranslatorHub, TranslatorRunner
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.bot.enums.event_registrations import EventRegistrationStatus
from app.bot.enums.roles import UserRole
from app.bot.handlers.event_chats import (
    approve_event_ticket_purchase,
    parse_sub1_event_user,
)
from app.infrastructure.database.database.db import DB
from app.services.advcake.client import fetch_orders
from app.services.telegram.private_event_chats import EventPrivateChatService

logger = logging.getLogger(__name__)

APPROVED_STATUS = 2


async def start_advcake_poller(
    *,
    bot,
    db_sessionmaker: async_sessionmaker,
    translator_hub: TranslatorHub,
    api_key: str,
    event_private_chat_service: EventPrivateChatService | None = None,
    poll_interval_seconds: int = 600,
    days: int = 2,
) -> None:
    i18n: TranslatorRunner = translator_hub.get_translator_by_locale("ru")
    try:
        while True:
            await _poll_once(
                bot=bot,
                db_sessionmaker=db_sessionmaker,
                i18n=i18n,
                api_key=api_key,
                event_private_chat_service=event_private_chat_service,
                days=days,
            )
            await asyncio.sleep(poll_interval_seconds)
    except asyncio.CancelledError:
        logger.info("AdvCake poller cancelled")
        raise
    except Exception as exc:
        logger.exception("AdvCake poller crashed: %s", exc)


async def _poll_once(
    *,
    bot,
    db_sessionmaker: async_sessionmaker,
    i18n: TranslatorRunner,
    api_key: str,
    event_private_chat_service: EventPrivateChatService | None,
    days: int,
) -> None:
    orders = await fetch_orders(api_key=api_key, days=days)
    if not orders:
        return

    async with db_sessionmaker() as session:
        db = DB(session)
        try:
            for order in orders:
                if order.status != APPROVED_STATUS:
                    continue
                parsed = parse_sub1_event_user(order.sub1)
                if not parsed:
                    continue
                event_id, user_id = parsed
                user_record = await db.users.get_user_record(user_id=user_id)
                if user_record is None:
                    await db.users.add(
                        user_id=user_id,
                        username=None,
                        role=UserRole.USER,
                    )
                reg = await db.event_registrations.get_by_user_event(
                    event_id=event_id,
                    user_id=user_id,
                )
                if reg is None:
                    await db.event_registrations.create(
                        event_id=event_id,
                        user_id=user_id,
                        status=EventRegistrationStatus.PENDING_PAYMENT,
                        amount=None,
                    )
                await approve_event_ticket_purchase(
                    db=db,
                    i18n=i18n,
                    bot=bot,
                    event_id=event_id,
                    user_id=user_id,
                    event_private_chat_service=event_private_chat_service,
                )
            await session.commit()
        except Exception as exc:
            await session.rollback()
            logger.exception("AdvCake poller DB error: %s", exc)
