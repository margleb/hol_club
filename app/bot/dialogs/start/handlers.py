import logging

from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.kbd import Button, Select
from fluentogram import TranslatorRunner

from app.bot.enums.roles import UserRole
from app.bot.handlers.event_registrations import (
    PAID_RECEIPT_TTL_SECONDS,
    _build_contact_keyboard,
    _build_paid_receipt_key,
    _build_paid_receipt_payload,
    _format_user_label,
)
from app.bot.handlers.partner_requests import send_partner_requests_list
from app.bot.states.start import StartSG
from app.infrastructure.database.database.db import DB

logger = logging.getLogger(__name__)


async def show_partner_requests_list(
    callback: CallbackQuery,
    widget: Button,
    dialog_manager: DialogManager,
) -> None:
    db: DB = dialog_manager.middleware_data.get("db")
    i18n: TranslatorRunner = dialog_manager.middleware_data.get("i18n")
    bot = dialog_manager.middleware_data.get("bot")

    admin_record = await db.users.get_user_record(user_id=callback.from_user.id)
    if admin_record is None or admin_record.role != UserRole.ADMIN:
        await callback.answer(text=i18n.partner.approve.forbidden())
        return

    await callback.answer()
    await send_partner_requests_list(
        admin_id=callback.from_user.id,
        i18n=i18n,
        db=db,
        bot=bot,
    )


async def show_user_event_details(
    callback: CallbackQuery,
    widget: Select,
    dialog_manager: DialogManager,
    item_id: str,
) -> None:
    dialog_manager.dialog_data["selected_event_id"] = int(item_id)
    await callback.answer()
    await dialog_manager.switch_to(StartSG.event_details)


async def show_user_events_list(
    callback: CallbackQuery,
    widget: Button,
    dialog_manager: DialogManager,
) -> None:
    await callback.answer()
    await dialog_manager.switch_to(StartSG.events_list)


async def back_to_start(
    callback: CallbackQuery,
    widget: Button,
    dialog_manager: DialogManager,
) -> None:
    await callback.answer()
    await dialog_manager.switch_to(StartSG.start)


async def back_to_events_list(
    callback: CallbackQuery,
    widget: Button,
    dialog_manager: DialogManager,
) -> None:
    await callback.answer()
    await dialog_manager.switch_to(StartSG.events_list)


async def mark_user_event_paid(
    callback: CallbackQuery,
    widget: Button,
    dialog_manager: DialogManager,
) -> None:
    db: DB = dialog_manager.middleware_data.get("db")
    i18n: TranslatorRunner = dialog_manager.middleware_data.get("i18n")
    bot = dialog_manager.middleware_data.get("bot")
    cache_pool = dialog_manager.middleware_data.get("_cache_pool")
    user = callback.from_user
    if not user:
        return

    user_record = await db.users.get_user_record(user_id=user.id)
    if not user_record or user_record.role != UserRole.USER:
        await callback.answer(i18n.partner.event.going.forbidden())
        return

    event_id = dialog_manager.dialog_data.get("selected_event_id")
    if not event_id:
        await callback.answer(i18n.partner.event.paid.missing())
        return

    event = await db.events.get_event_by_id(event_id=event_id)
    if event is None:
        await callback.answer(i18n.partner.event.paid.missing())
        return

    registration = await db.event_registrations.get_registration(
        event_id=event_id,
        user_id=user.id,
    )
    if registration is None:
        await callback.answer(i18n.partner.event.paid.not_registered())
        return

    updated = await db.event_registrations.mark_paid(
        event_id=event_id,
        user_id=user.id,
    )
    if updated:
        partner_text = i18n.partner.event.paid.notify.partner(
            username=_format_user_label(user),
            user_id=user.id,
            event_name=event.name,
            event_id=event.id,
        )
        partner_keyboard = _build_contact_keyboard(
            i18n=i18n,
            user_id=user.id,
            button_text=i18n.partner.event.going.contact.user.button(),
        )
        if bot:
            try:
                sent = await bot.send_message(
                    event.partner_user_id,
                    text=partner_text,
                    reply_markup=partner_keyboard,
                )
                if cache_pool:
                    key = _build_paid_receipt_key(sent.chat.id, sent.message_id)
                    payload = _build_paid_receipt_payload(event.id, user.id)
                    await cache_pool.set(
                        key, payload, ex=PAID_RECEIPT_TTL_SECONDS
                    )
            except Exception as exc:
                logger.warning(
                    "Failed to notify partner %s: %s",
                    event.partner_user_id,
                    exc,
                )
        await callback.answer(i18n.partner.event.paid.done())
    else:
        await callback.answer(i18n.partner.event.paid.already())

    await dialog_manager.switch_to(StartSG.event_details)


async def show_prev_events_page(
    callback: CallbackQuery,
    widget: Button,
    dialog_manager: DialogManager,
) -> None:
    current_page = int(dialog_manager.dialog_data.get("events_page", 0))
    dialog_manager.dialog_data["events_page"] = max(0, current_page - 1)
    await callback.answer()
    await dialog_manager.switch_to(StartSG.events_list)


async def show_next_events_page(
    callback: CallbackQuery,
    widget: Button,
    dialog_manager: DialogManager,
) -> None:
    current_page = int(dialog_manager.dialog_data.get("events_page", 0))
    dialog_manager.dialog_data["events_page"] = current_page + 1
    await callback.answer()
    await dialog_manager.switch_to(StartSG.events_list)
