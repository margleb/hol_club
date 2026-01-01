from aiogram import Bot, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from fluentogram import TranslatorHub, TranslatorRunner

from app.bot.services.partner_requests import (
    PARTNER_DECISION_CALLBACK,
    PARTNER_REQUEST_CALLBACK,
    handle_partner_decision_callback,
    process_partner_request,
)
from app.infrastructure.database.database.db import DB

partner_requests_router = Router()

@partner_requests_router.message(Command("partner_request"))
async def process_partner_request_command(
    message: Message,
    i18n: TranslatorRunner,
    db: DB,
    bot: Bot,
) -> None:
    """Команда для отправки заявки напрямую в боте."""
    await process_partner_request(
        user=message.from_user,
        i18n=i18n,
        db=db,
        bot=bot,
        answer=message.answer,
    )


@partner_requests_router.callback_query(
    lambda callback: callback.data == PARTNER_REQUEST_CALLBACK
)
async def process_partner_request_callback(
    callback: CallbackQuery,
    i18n: TranslatorRunner,
    db: DB,
    bot: Bot,
) -> None:
    """Обработка клика по кнопке заявки в канале."""
    await process_partner_request(
        user=callback.from_user,
        i18n=i18n,
        db=db,
        bot=bot,
        answer=callback.answer,
    )


@partner_requests_router.callback_query(
    lambda callback: callback.data and callback.data.startswith(
        f"{PARTNER_DECISION_CALLBACK}:"
    )
)
async def process_partner_decision_callback(
    callback: CallbackQuery,
    i18n: TranslatorRunner,
    db: DB,
    bot: Bot,
    translator_hub: TranslatorHub,
) -> None:
    await handle_partner_decision_callback(
        callback=callback,
        i18n=i18n,
        db=db,
        bot=bot,
        translator_hub=translator_hub,
    )
