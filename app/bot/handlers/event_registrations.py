from aiogram import Bot, Router
from aiogram.types import CallbackQuery, Message
from fluentogram import TranslatorHub, TranslatorRunner
from redis.asyncio import Redis

from app.bot.dialogs.events.handlers import EVENT_GOING_CALLBACK
from app.bot.services.event_registrations import (
    EVENT_MESSAGE_CALLBACK,
    EVENT_PAID_CALLBACK,
    EVENT_REGISTER_CALLBACK,
    handle_event_going,
    handle_event_paid,
    handle_event_register,
    handle_partner_message_reply,
    handle_partner_message_request,
    handle_paid_receipt,
)
from app.infrastructure.database.database.db import DB

event_registrations_router = Router()


@event_registrations_router.callback_query(
    lambda callback: callback.data and callback.data.startswith(EVENT_GOING_CALLBACK)
)
async def process_event_going(
    callback: CallbackQuery,
    i18n: TranslatorRunner,
    db: DB,
    bot: Bot,
) -> None:
    await handle_event_going(
        callback=callback,
        i18n=i18n,
        db=db,
        bot=bot,
    )


@event_registrations_router.callback_query(
    lambda callback: callback.data and callback.data.startswith(EVENT_REGISTER_CALLBACK)
)
async def process_event_register(
    callback: CallbackQuery,
    i18n: TranslatorRunner,
    db: DB,
    bot: Bot,
) -> None:
    await handle_event_register(
        callback=callback,
        i18n=i18n,
        db=db,
        bot=bot,
    )


@event_registrations_router.callback_query(
    lambda callback: callback.data and callback.data.startswith(EVENT_PAID_CALLBACK)
)
async def process_event_paid(
    callback: CallbackQuery,
    i18n: TranslatorRunner,
    db: DB,
    bot: Bot,
    _cache_pool: Redis | None = None,
) -> None:
    await handle_event_paid(
        callback=callback,
        i18n=i18n,
        db=db,
        bot=bot,
        _cache_pool=_cache_pool,
    )


@event_registrations_router.callback_query(
    lambda callback: callback.data and callback.data.startswith(EVENT_MESSAGE_CALLBACK)
)
async def process_partner_message_request(
    callback: CallbackQuery,
    i18n: TranslatorRunner,
    db: DB,
    bot: Bot,
    _cache_pool: Redis | None = None,
) -> None:
    await handle_partner_message_request(
        callback=callback,
        i18n=i18n,
        db=db,
        bot=bot,
        _cache_pool=_cache_pool,
    )


@event_registrations_router.message(
    lambda message: message.reply_to_message
    and (message.photo or message.document)
)
async def process_paid_receipt(
    message: Message,
    i18n: TranslatorRunner,
    db: DB,
    bot: Bot,
    _cache_pool: Redis | None = None,
) -> None:
    await handle_paid_receipt(
        message=message,
        i18n=i18n,
        db=db,
        bot=bot,
        _cache_pool=_cache_pool,
    )


@event_registrations_router.message(
    lambda message: message.reply_to_message and message.text
)
async def process_partner_message_reply(
    message: Message,
    i18n: TranslatorRunner,
    db: DB,
    bot: Bot,
    translator_hub: TranslatorHub,
    _cache_pool: Redis | None = None,
) -> None:
    await handle_partner_message_reply(
        message=message,
        i18n=i18n,
        db=db,
        bot=bot,
        translator_hub=translator_hub,
        _cache_pool=_cache_pool,
    )

