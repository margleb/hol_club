from aiogram.types import CallbackQuery, Message
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.kbd import Button, Select
from fluentogram import TranslatorRunner

from app.bot.dialogs.start.event_dialogs import (
    DIALOG_EVENT_ID_KEY,
    DIALOG_PARTICIPANT_USER_ID_KEY,
    build_dialog_notification_text,
    build_event_dialog_keyboard,
    get_dialog_context_for_user,
    get_organizer_dialog_context,
    get_participant_dialog_context,
    sync_dialog_selection,
    format_user_label,
)
from app.bot.enums.event_registrations import EventRegistrationStatus
from app.bot.enums.roles import UserRole
from app.bot.handlers.event_chats import approve_event_registration_payment
from app.bot.states.start import StartSG
from app.infrastructure.database.database.db import DB
from app.services.telegram.delivery_status import apply_delivery_error_status
from app.services.telegram.private_event_chats import EventPrivateChatService


async def back_to_admin_events_list(
    callback: CallbackQuery,
    widget: Button,
    dialog_manager: DialogManager,
) -> None:
    await callback.answer()
    await dialog_manager.switch_to(StartSG.admin_events_list)


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


async def show_admin_events_list(
    callback: CallbackQuery,
    widget: Button,
    dialog_manager: DialogManager,
) -> None:
    dialog_manager.dialog_data.pop("selected_admin_event_id", None)
    await callback.answer()
    await dialog_manager.switch_to(StartSG.admin_events_list)


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


async def show_user_event_dialog(
    callback: CallbackQuery,
    widget: Button,
    dialog_manager: DialogManager,
) -> None:
    db: DB = dialog_manager.middleware_data.get("db")
    i18n: TranslatorRunner = dialog_manager.middleware_data.get("i18n")
    event_id = dialog_manager.dialog_data.get("selected_user_event_id")
    user = callback.from_user
    if not isinstance(event_id, int):
        await callback.answer(i18n.partner.event.dialog.inaccessible())
        return

    context = await get_participant_dialog_context(
        db=db,
        participant_user_id=user.id,
        event_id=event_id,
    )
    if context is None:
        await callback.answer(i18n.partner.event.dialog.inaccessible())
        return

    dialog_manager.dialog_data[DIALOG_EVENT_ID_KEY] = event_id
    dialog_manager.dialog_data[DIALOG_PARTICIPANT_USER_ID_KEY] = user.id
    await callback.answer()
    await dialog_manager.switch_to(StartSG.user_event_dialog)


async def back_from_user_event_dialog(
    callback: CallbackQuery,
    widget: Button,
    dialog_manager: DialogManager,
) -> None:
    event_id, _ = sync_dialog_selection(
        dialog_manager,
        event_id=dialog_manager.dialog_data.get(DIALOG_EVENT_ID_KEY),
        participant_user_id=dialog_manager.dialog_data.get(
            DIALOG_PARTICIPANT_USER_ID_KEY
        ),
    )
    if isinstance(event_id, int):
        dialog_manager.dialog_data["selected_user_event_id"] = event_id
    await callback.answer()
    await dialog_manager.switch_to(StartSG.user_event_details)


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


async def show_admin_event_details(
    callback: CallbackQuery,
    widget: Select,
    dialog_manager: DialogManager,
    item_id: str,
) -> None:
    try:
        dialog_manager.dialog_data["selected_admin_event_id"] = int(item_id)
    except ValueError:
        await callback.answer()
        return
    await callback.answer()
    await dialog_manager.switch_to(StartSG.admin_event_details)


async def show_admin_event_registrations(
    callback: CallbackQuery,
    widget: Button,
    dialog_manager: DialogManager,
) -> None:
    event_id = dialog_manager.dialog_data.get("selected_admin_event_id")
    if not isinstance(event_id, int):
        await callback.answer()
        return
    await callback.answer()
    await dialog_manager.switch_to(StartSG.admin_event_registrations_list)


async def show_admin_event_confirmed_registrations(
    callback: CallbackQuery,
    widget: Button,
    dialog_manager: DialogManager,
) -> None:
    event_id = dialog_manager.dialog_data.get("selected_admin_event_id")
    if not isinstance(event_id, int):
        await callback.answer()
        return
    dialog_manager.dialog_data["selected_confirmed_event_id"] = event_id
    await callback.answer()
    await dialog_manager.switch_to(
        StartSG.admin_event_confirmed_registrations_list
    )


async def back_to_admin_event_details(
    callback: CallbackQuery,
    widget: Button,
    dialog_manager: DialogManager,
) -> None:
    await callback.answer()
    await dialog_manager.switch_to(StartSG.admin_event_details)


async def show_admin_event_registration_details(
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


async def show_admin_confirmed_registration_details(
    callback: CallbackQuery,
    widget: Select,
    dialog_manager: DialogManager,
    item_id: str,
) -> None:
    try:
        event_raw, user_raw = item_id.split(":", 1)
        dialog_manager.dialog_data["selected_confirmed_event_id"] = int(event_raw)
        dialog_manager.dialog_data["selected_confirmed_registration_user_id"] = (
            int(user_raw)
        )
    except (ValueError, AttributeError):
        await callback.answer()
        return
    await callback.answer()
    await dialog_manager.switch_to(
        StartSG.admin_registration_confirmed_details
    )


async def back_to_admin_registration_pending_list(
    callback: CallbackQuery,
    widget: Button,
    dialog_manager: DialogManager,
) -> None:
    await callback.answer()
    await dialog_manager.switch_to(StartSG.admin_event_registrations_list)


async def back_to_admin_registration_confirmed_list(
    callback: CallbackQuery,
    widget: Button,
    dialog_manager: DialogManager,
) -> None:
    await callback.answer()
    await dialog_manager.switch_to(
        StartSG.admin_event_confirmed_registrations_list
    )


async def show_admin_pending_registration_dialog(
    callback: CallbackQuery,
    widget: Button,
    dialog_manager: DialogManager,
) -> None:
    db: DB = dialog_manager.middleware_data.get("db")
    i18n: TranslatorRunner = dialog_manager.middleware_data.get("i18n")
    event_id = dialog_manager.dialog_data.get("selected_pending_event_id")
    participant_user_id = dialog_manager.dialog_data.get("selected_registration_user_id")
    if not isinstance(event_id, int) or not isinstance(participant_user_id, int):
        await callback.answer(i18n.partner.event.dialog.inaccessible())
        return

    context = await get_organizer_dialog_context(
        db=db,
        organizer_user_id=callback.from_user.id,
        event_id=event_id,
        participant_user_id=participant_user_id,
    )
    if context is None:
        await callback.answer(i18n.partner.event.dialog.inaccessible())
        return

    dialog_manager.dialog_data[DIALOG_EVENT_ID_KEY] = event_id
    dialog_manager.dialog_data[DIALOG_PARTICIPANT_USER_ID_KEY] = participant_user_id
    await callback.answer()
    await dialog_manager.switch_to(StartSG.admin_event_dialog)


async def show_admin_confirmed_registration_dialog(
    callback: CallbackQuery,
    widget: Button,
    dialog_manager: DialogManager,
) -> None:
    db: DB = dialog_manager.middleware_data.get("db")
    i18n: TranslatorRunner = dialog_manager.middleware_data.get("i18n")
    event_id = dialog_manager.dialog_data.get("selected_confirmed_event_id")
    participant_user_id = dialog_manager.dialog_data.get(
        "selected_confirmed_registration_user_id"
    )
    if not isinstance(event_id, int) or not isinstance(participant_user_id, int):
        await callback.answer(i18n.partner.event.dialog.inaccessible())
        return

    context = await get_organizer_dialog_context(
        db=db,
        organizer_user_id=callback.from_user.id,
        event_id=event_id,
        participant_user_id=participant_user_id,
    )
    if context is None:
        await callback.answer(i18n.partner.event.dialog.inaccessible())
        return

    dialog_manager.dialog_data[DIALOG_EVENT_ID_KEY] = event_id
    dialog_manager.dialog_data[DIALOG_PARTICIPANT_USER_ID_KEY] = participant_user_id
    await callback.answer()
    await dialog_manager.switch_to(StartSG.admin_event_dialog)


async def back_from_admin_event_dialog(
    callback: CallbackQuery,
    widget: Button,
    dialog_manager: DialogManager,
) -> None:
    db: DB = dialog_manager.middleware_data.get("db")
    event_id, participant_user_id = sync_dialog_selection(
        dialog_manager,
        event_id=dialog_manager.dialog_data.get(DIALOG_EVENT_ID_KEY),
        participant_user_id=dialog_manager.dialog_data.get(
            DIALOG_PARTICIPANT_USER_ID_KEY
        ),
    )
    if not isinstance(event_id, int) or not isinstance(participant_user_id, int):
        await callback.answer()
        await dialog_manager.switch_to(StartSG.admin_events_list)
        return

    registration = await db.event_registrations.get_by_user_event(
        event_id=event_id,
        user_id=participant_user_id,
    )
    await callback.answer()
    if registration and registration.status == EventRegistrationStatus.PAID_CONFIRM_PENDING:
        dialog_manager.dialog_data["selected_pending_event_id"] = event_id
        dialog_manager.dialog_data["selected_registration_user_id"] = participant_user_id
        await dialog_manager.switch_to(StartSG.admin_registration_pending_details)
        return

    if registration and registration.status in {
        EventRegistrationStatus.CONFIRMED,
        EventRegistrationStatus.ATTENDED_CONFIRMED,
    }:
        dialog_manager.dialog_data["selected_confirmed_event_id"] = event_id
        dialog_manager.dialog_data["selected_confirmed_registration_user_id"] = (
            participant_user_id
        )
        await dialog_manager.switch_to(StartSG.admin_registration_confirmed_details)
        return

    await dialog_manager.switch_to(StartSG.admin_events_list)


async def approve_pending_registration(
    callback: CallbackQuery,
    widget: Button,
    dialog_manager: DialogManager,
) -> None:
    db: DB = dialog_manager.middleware_data.get("db")
    i18n: TranslatorRunner = dialog_manager.middleware_data.get("i18n")
    bot = callback.bot
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
    await dialog_manager.switch_to(StartSG.admin_event_registrations_list)


async def decline_pending_registration(
    callback: CallbackQuery,
    widget: Button,
    dialog_manager: DialogManager,
) -> None:
    db: DB = dialog_manager.middleware_data.get("db")
    i18n: TranslatorRunner = dialog_manager.middleware_data.get("i18n")
    bot = callback.bot

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
    await dialog_manager.switch_to(StartSG.admin_event_registrations_list)


async def on_user_event_dialog_message(
    message: Message,
    widget: MessageInput,
    dialog_manager: DialogManager,
) -> None:
    await _send_event_dialog_message(
        message=message,
        dialog_manager=dialog_manager,
    )


async def on_admin_event_dialog_message(
    message: Message,
    widget: MessageInput,
    dialog_manager: DialogManager,
) -> None:
    await _send_event_dialog_message(
        message=message,
        dialog_manager=dialog_manager,
    )


async def _send_event_dialog_message(
    *,
    message: Message,
    dialog_manager: DialogManager,
) -> None:
    db: DB = dialog_manager.middleware_data.get("db")
    i18n: TranslatorRunner = dialog_manager.middleware_data.get("i18n")
    user = message.from_user
    if user is None:
        return

    event_id, participant_user_id = sync_dialog_selection(
        dialog_manager,
        event_id=dialog_manager.dialog_data.get(DIALOG_EVENT_ID_KEY),
        participant_user_id=dialog_manager.dialog_data.get(
            DIALOG_PARTICIPANT_USER_ID_KEY
        )
        or user.id,
    )
    if not isinstance(event_id, int) or not isinstance(participant_user_id, int):
        await message.answer(i18n.partner.event.dialog.inaccessible())
        return

    sent = await relay_event_dialog_message(
        message=message,
        db=db,
        i18n=i18n,
        event_id=event_id,
        participant_user_id=participant_user_id,
    )
    if not sent:
        return
    await message.answer(i18n.partner.event.dialog.sent())


async def relay_event_dialog_message(
    *,
    message: Message,
    db: DB,
    i18n: TranslatorRunner,
    event_id: int,
    participant_user_id: int,
) -> bool:
    user = message.from_user
    if user is None:
        return False

    text = (message.text or "").strip()
    if message.text is None:
        await message.answer(i18n.partner.event.dialog.text.only())
        return False
    if not text:
        await message.answer(i18n.partner.event.dialog.validation.empty())
        return False

    context, sender_is_organizer = await get_dialog_context_for_user(
        db=db,
        current_user_id=user.id,
        event_id=event_id,
        participant_user_id=participant_user_id,
    )
    if context is None:
        await message.answer(i18n.partner.event.dialog.inaccessible())
        return False

    recipient_user_id = (
        participant_user_id if sender_is_organizer else context.organizer_user_id
    )
    sender_record = (
        context.organizer_record if sender_is_organizer else context.participant_record
    )
    sender_label = format_user_label(
        user_id=user.id,
        username=sender_record.username if sender_record else user.username,
    )
    notification_text = build_dialog_notification_text(
        i18n=i18n,
        text=text,
        event_name=context.event.name,
        sender_label=sender_label,
        sender_is_organizer=sender_is_organizer,
    )
    reply_markup = build_event_dialog_keyboard(
        i18n=i18n,
        event_id=event_id,
        participant_user_id=participant_user_id,
    )
    try:
        await message.bot.send_message(
            chat_id=recipient_user_id,
            text=notification_text,
            reply_markup=reply_markup,
        )
    except Exception as exc:
        await apply_delivery_error_status(
            db=db,
            user_id=recipient_user_id,
            error=exc,
        )
        await message.answer(i18n.partner.event.dialog.send.failed())
        return False
    return True
