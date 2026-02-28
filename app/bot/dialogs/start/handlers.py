from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.kbd import Button, Select
from fluentogram import TranslatorRunner

from app.bot.enums.event_registrations import EventRegistrationStatus
from app.bot.enums.roles import UserRole
from app.bot.handlers.event_chats import approve_event_registration_payment
from app.bot.states.start import StartSG
from app.infrastructure.database.database.db import DB
from app.services.telegram.delivery_status import apply_delivery_error_status
from app.services.telegram.private_event_chats import EventPrivateChatService


async def back_to_start(
    callback: CallbackQuery,
    widget: Button,
    dialog_manager: DialogManager,
) -> None:
    await callback.answer()
    await dialog_manager.switch_to(StartSG.start)


async def show_user_events_list(
    callback: CallbackQuery,
    widget: Button,
    dialog_manager: DialogManager,
) -> None:
    await callback.answer()
    await dialog_manager.switch_to(StartSG.user_events_list)


async def show_user_event_details(
    callback: CallbackQuery,
    widget: Select,
    dialog_manager: DialogManager,
    item_id: str,
) -> None:
    try:
        dialog_manager.dialog_data["selected_user_event_id"] = int(item_id)
    except ValueError:
        await callback.answer()
        return
    await callback.answer()
    await dialog_manager.switch_to(StartSG.user_event_details)


async def back_to_user_events_list(
    callback: CallbackQuery,
    widget: Button,
    dialog_manager: DialogManager,
) -> None:
    await callback.answer()
    await dialog_manager.switch_to(StartSG.user_events_list)


async def show_prev_user_events_page(
    callback: CallbackQuery,
    widget: Button,
    dialog_manager: DialogManager,
) -> None:
    current_page = int(dialog_manager.dialog_data.get("user_events_page", 0))
    dialog_manager.dialog_data["user_events_page"] = max(0, current_page - 1)
    await callback.answer()
    await dialog_manager.switch_to(StartSG.user_events_list)


async def show_next_user_events_page(
    callback: CallbackQuery,
    widget: Button,
    dialog_manager: DialogManager,
) -> None:
    current_page = int(dialog_manager.dialog_data.get("user_events_page", 0))
    dialog_manager.dialog_data["user_events_page"] = current_page + 1
    await callback.answer()
    await dialog_manager.switch_to(StartSG.user_events_list)


async def show_admin_registration_pending_list(
    callback: CallbackQuery,
    widget: Button,
    dialog_manager: DialogManager,
) -> None:
    db: DB = dialog_manager.middleware_data.get("db")
    i18n: TranslatorRunner = dialog_manager.middleware_data.get("i18n")

    admin_record = await db.users.get_user_record(user_id=callback.from_user.id)
    if admin_record is None or admin_record.role != UserRole.ADMIN:
        await callback.answer(i18n.partner.event.prepay.admin.only())
        return

    dialog_manager.dialog_data.pop("selected_pending_event_id", None)
    dialog_manager.dialog_data.pop("selected_registration_user_id", None)
    await callback.answer()
    await dialog_manager.switch_to(StartSG.admin_registration_pending_list)


async def show_pending_registration_details(
    callback: CallbackQuery,
    widget: Select,
    dialog_manager: DialogManager,
    item_id: str,
) -> None:
    try:
        event_raw, user_raw = item_id.split(":", 1)
        dialog_manager.dialog_data["selected_pending_event_id"] = int(event_raw)
        dialog_manager.dialog_data["selected_registration_user_id"] = int(user_raw)
    except (ValueError, AttributeError):
        await callback.answer()
        return

    await callback.answer()
    await dialog_manager.switch_to(StartSG.admin_registration_pending_details)


async def back_to_admin_registration_pending_list(
    callback: CallbackQuery,
    widget: Button,
    dialog_manager: DialogManager,
) -> None:
    await callback.answer()
    await dialog_manager.switch_to(StartSG.admin_registration_pending_list)


async def approve_pending_registration(
    callback: CallbackQuery,
    widget: Button,
    dialog_manager: DialogManager,
) -> None:
    db: DB = dialog_manager.middleware_data.get("db")
    i18n: TranslatorRunner = dialog_manager.middleware_data.get("i18n")
    bot = dialog_manager.middleware_data.get("bot")
    event_private_chat_service: EventPrivateChatService | None = (
        dialog_manager.middleware_data.get("event_private_chat_service")
    )

    admin_record = await db.users.get_user_record(user_id=callback.from_user.id)
    if admin_record is None or admin_record.role != UserRole.ADMIN:
        await callback.answer(i18n.partner.event.prepay.admin.only())
        return

    event_id = dialog_manager.dialog_data.get("selected_pending_event_id")
    user_id = dialog_manager.dialog_data.get("selected_registration_user_id")
    if not isinstance(event_id, int) or not isinstance(user_id, int):
        await callback.answer(i18n.partner.event.registrations.pending.details.missing())
        return

    registration = await db.event_registrations.get_by_user_event(
        event_id=event_id,
        user_id=user_id,
    )
    if registration is None:
        await callback.answer(i18n.partner.event.registrations.pending.details.missing())
        return
    if not registration.payment_proof_file_id:
        await callback.answer(i18n.partner.event.prepay.receipt.required())
        return

    approved = await approve_event_registration_payment(
        db=db,
        i18n=i18n,
        bot=bot,
        event_id=event_id,
        user_id=user_id,
        event_private_chat_service=event_private_chat_service,
    )
    if not approved:
        await callback.answer(i18n.partner.event.prepay.already.processed())
        return

    await callback.answer(i18n.partner.event.prepay.approved.partner())
    await dialog_manager.switch_to(StartSG.admin_registration_pending_list)


async def decline_pending_registration(
    callback: CallbackQuery,
    widget: Button,
    dialog_manager: DialogManager,
) -> None:
    db: DB = dialog_manager.middleware_data.get("db")
    i18n: TranslatorRunner = dialog_manager.middleware_data.get("i18n")
    bot = dialog_manager.middleware_data.get("bot")

    admin_record = await db.users.get_user_record(user_id=callback.from_user.id)
    if admin_record is None or admin_record.role != UserRole.ADMIN:
        await callback.answer(i18n.partner.event.prepay.admin.only())
        return

    event_id = dialog_manager.dialog_data.get("selected_pending_event_id")
    user_id = dialog_manager.dialog_data.get("selected_registration_user_id")
    if not isinstance(event_id, int) or not isinstance(user_id, int):
        await callback.answer(i18n.partner.event.registrations.pending.details.missing())
        return

    declined = await db.event_registrations.update_status_if_current(
        event_id=event_id,
        user_id=user_id,
        current_status=EventRegistrationStatus.PAID_CONFIRM_PENDING,
        new_status=EventRegistrationStatus.DECLINED,
    )
    if not declined:
        await callback.answer(i18n.partner.event.prepay.already.processed())
        return

    if bot:
        try:
            await bot.send_message(user_id, i18n.partner.event.prepay.declined())
        except Exception as exc:
            await apply_delivery_error_status(
                db=db,
                user_id=user_id,
                error=exc,
            )

    await callback.answer(i18n.partner.event.prepay.declined.partner())
    await dialog_manager.switch_to(StartSG.admin_registration_pending_list)
