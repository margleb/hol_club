from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.kbd import Button, Select
from fluentogram import TranslatorRunner

from app.bot.enums.roles import UserRole
from app.bot.services.partner_requests import send_partner_requests_list
from app.bot.states.start import StartSG
from app.infrastructure.database.database.db import DB


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


async def show_partner_event_details(
    callback: CallbackQuery,
    widget: Select,
    dialog_manager: DialogManager,
    item_id: str,
) -> None:
    dialog_manager.dialog_data["selected_partner_event_id"] = int(item_id)
    await callback.answer()
    await dialog_manager.switch_to(StartSG.partner_event_details)


async def show_partner_events_list(
    callback: CallbackQuery,
    widget: Button,
    dialog_manager: DialogManager,
) -> None:
    await callback.answer()
    await dialog_manager.switch_to(StartSG.partner_events_list)


async def back_to_start(
    callback: CallbackQuery,
    widget: Button,
    dialog_manager: DialogManager,
) -> None:
    await callback.answer()
    await dialog_manager.switch_to(StartSG.start)


async def back_to_partner_events_list(
    callback: CallbackQuery,
    widget: Button,
    dialog_manager: DialogManager,
) -> None:
    await callback.answer()
    await dialog_manager.switch_to(StartSG.partner_events_list)


async def back_to_partner_event_details(
    callback: CallbackQuery,
    widget: Button,
    dialog_manager: DialogManager,
) -> None:
    await callback.answer()
    await dialog_manager.switch_to(StartSG.partner_event_details)


async def show_prev_partner_events_page(
    callback: CallbackQuery,
    widget: Button,
    dialog_manager: DialogManager,
) -> None:
    current_page = int(dialog_manager.dialog_data.get("partner_events_page", 0))
    dialog_manager.dialog_data["partner_events_page"] = max(0, current_page - 1)
    await callback.answer()
    await dialog_manager.switch_to(StartSG.partner_events_list)


async def show_next_partner_events_page(
    callback: CallbackQuery,
    widget: Button,
    dialog_manager: DialogManager,
) -> None:
    current_page = int(dialog_manager.dialog_data.get("partner_events_page", 0))
    dialog_manager.dialog_data["partner_events_page"] = current_page + 1
    await callback.answer()
    await dialog_manager.switch_to(StartSG.partner_events_list)
