import html

from aiogram.types import CallbackQuery, Message
from aiogram_dialog import DialogManager, StartMode
from aiogram_dialog.widgets.kbd import Button, Select
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.enums import ParseMode
from fluentogram import TranslatorRunner

from app.bot.enums.partner_requests import PartnerRequestStatus
from app.bot.enums.roles import UserRole
from app.bot.enums.event_registrations import EventRegistrationStatus
from app.bot.handlers.event_chats import (
    EVENT_MESSAGE_USER_CALLBACK,
    EVENT_REPLY_ADMIN_CALLBACK,
    approve_event_registration_payment,
)
from app.bot.states.account import AccountSG
from app.bot.states.start import StartSG
from app.infrastructure.database.database.db import DB


async def show_partner_requests_list(
    callback: CallbackQuery,
    widget: Button,
    dialog_manager: DialogManager,
) -> None:
    db: DB = dialog_manager.middleware_data.get("db")
    i18n: TranslatorRunner = dialog_manager.middleware_data.get("i18n")
    admin_record = await db.users.get_user_record(user_id=callback.from_user.id)
    if admin_record is None or admin_record.role != UserRole.ADMIN:
        await callback.answer(text=i18n.partner.approve.forbidden())
        return

    dialog_manager.dialog_data.pop("selected_partner_request_user_id", None)
    await callback.answer()
    await dialog_manager.switch_to(StartSG.admin_partner_requests_list)


async def show_admin_partner_commissions(
    callback: CallbackQuery,
    widget: Button,
    dialog_manager: DialogManager,
) -> None:
    db: DB = dialog_manager.middleware_data.get("db")
    i18n: TranslatorRunner = dialog_manager.middleware_data.get("i18n")
    admin_record = await db.users.get_user_record(user_id=callback.from_user.id)
    if admin_record is None or admin_record.role != UserRole.ADMIN:
        await callback.answer(text=i18n.partner.approve.forbidden())
        return

    dialog_manager.dialog_data.pop("selected_partner_commission_user_id", None)
    await callback.answer()
    await dialog_manager.switch_to(StartSG.admin_partner_commissions_list)


async def show_admin_partner_commission_edit(
    callback: CallbackQuery,
    widget: Select,
    dialog_manager: DialogManager,
    item_id: str,
) -> None:
    db: DB = dialog_manager.middleware_data.get("db")
    i18n: TranslatorRunner = dialog_manager.middleware_data.get("i18n")
    admin_record = await db.users.get_user_record(user_id=callback.from_user.id)
    if admin_record is None or admin_record.role != UserRole.ADMIN:
        await callback.answer(text=i18n.partner.approve.forbidden())
        return

    try:
        partner_user_id = int(item_id)
    except ValueError:
        await callback.answer()
        return
    dialog_manager.dialog_data["selected_partner_commission_user_id"] = partner_user_id
    await callback.answer()
    await dialog_manager.switch_to(StartSG.admin_partner_commission_edit)


async def back_to_admin_partner_commissions(
    callback: CallbackQuery,
    widget: Button,
    dialog_manager: DialogManager,
) -> None:
    await callback.answer()
    await dialog_manager.switch_to(StartSG.admin_partner_commissions_list)


async def on_admin_partner_commission_input(
    message: Message,
    widget: object,
    dialog_manager: DialogManager,
    data: str,
) -> None:
    db: DB = dialog_manager.middleware_data.get("db")
    i18n: TranslatorRunner = dialog_manager.middleware_data.get("i18n")
    if not message.from_user:
        return

    admin_record = await db.users.get_user_record(user_id=message.from_user.id)
    if admin_record is None or admin_record.role != UserRole.ADMIN:
        await message.answer(i18n.partner.approve.forbidden())
        return

    partner_user_id = dialog_manager.dialog_data.get("selected_partner_commission_user_id")
    if not isinstance(partner_user_id, int):
        await message.answer(i18n.start.admin.partner.commission.edit.invalid())
        await dialog_manager.switch_to(StartSG.admin_partner_commissions_list)
        return

    value = (data or "").strip()
    if not value.isdigit():
        await message.answer(i18n.start.admin.partner.commission.invalid())
        return
    commission_percent = int(value)
    if commission_percent < 0 or commission_percent > 100:
        await message.answer(i18n.start.admin.partner.commission.invalid())
        return

    partner = await db.users.get_user_record(user_id=partner_user_id)
    if partner is None or partner.role != UserRole.PARTNER:
        await message.answer(i18n.start.admin.partner.commission.edit.invalid())
        await dialog_manager.switch_to(StartSG.admin_partner_commissions_list)
        return

    await db.users.update_partner_commission_percent(
        user_id=partner_user_id,
        commission_percent=commission_percent,
    )
    await message.answer(
        i18n.start.admin.partner.commission.updated(percent=commission_percent)
    )
    await dialog_manager.switch_to(StartSG.admin_partner_commissions_list)


async def show_admin_partner_request_details(
    callback: CallbackQuery,
    widget: Select,
    dialog_manager: DialogManager,
    item_id: str,
) -> None:
    try:
        target_user_id = int(item_id)
    except ValueError:
        await callback.answer()
        return
    dialog_manager.dialog_data["selected_partner_request_user_id"] = target_user_id
    await callback.answer()
    await dialog_manager.switch_to(StartSG.admin_partner_request_details)


async def back_to_admin_partner_requests(
    callback: CallbackQuery,
    widget: Button,
    dialog_manager: DialogManager,
) -> None:
    await callback.answer()
    await dialog_manager.switch_to(StartSG.admin_partner_requests_list)


async def _process_admin_partner_request_decision(
    *,
    callback: CallbackQuery,
    dialog_manager: DialogManager,
    action: str,
) -> None:
    db: DB = dialog_manager.middleware_data.get("db")
    i18n: TranslatorRunner = dialog_manager.middleware_data.get("i18n")
    bot = dialog_manager.middleware_data.get("bot")
    admin_record = await db.users.get_user_record(user_id=callback.from_user.id)
    if admin_record is None or admin_record.role != UserRole.ADMIN:
        await callback.answer(i18n.partner.approve.forbidden())
        return

    target_user_id = dialog_manager.dialog_data.get("selected_partner_request_user_id")
    if not isinstance(target_user_id, int):
        await callback.answer(i18n.partner.request.invalid())
        return

    request = await db.partner_requests.get_request(user_id=target_user_id)
    if request is None:
        await callback.answer(i18n.partner.approve.missing())
        await dialog_manager.switch_to(StartSG.admin_partner_requests_list)
        return

    if action == "approve":
        if request.status == PartnerRequestStatus.APPROVED:
            await callback.answer(i18n.partner.approve.already())
            return
        if request.status == PartnerRequestStatus.REJECTED:
            await callback.answer(i18n.partner.request.already.rejected())
            return

        await db.partner_requests.set_approved(
            user_id=target_user_id,
            approved_by=callback.from_user.id,
        )
        await db.users.update_role(user_id=target_user_id, role=UserRole.PARTNER)
        if bot:
            try:
                await bot.send_message(target_user_id, i18n.partner.request.approved())
            except Exception:
                pass
        await callback.answer(i18n.partner.decision.approved())
    else:
        if request.status == PartnerRequestStatus.REJECTED:
            await callback.answer(i18n.partner.request.already.rejected())
            return
        if request.status == PartnerRequestStatus.APPROVED:
            await callback.answer(i18n.partner.approve.already())
            return

        await db.partner_requests.set_rejected(
            user_id=target_user_id,
            rejected_by=callback.from_user.id,
        )
        if bot:
            try:
                await bot.send_message(target_user_id, i18n.partner.request.rejected())
            except Exception:
                pass
        await callback.answer(i18n.partner.decision.rejected())

    dialog_manager.dialog_data.pop("selected_partner_request_user_id", None)
    await dialog_manager.switch_to(StartSG.admin_partner_requests_list)


async def approve_admin_partner_request(
    callback: CallbackQuery,
    widget: Button,
    dialog_manager: DialogManager,
) -> None:
    await _process_admin_partner_request_decision(
        callback=callback,
        dialog_manager=dialog_manager,
        action="approve",
    )


async def reject_admin_partner_request(
    callback: CallbackQuery,
    widget: Button,
    dialog_manager: DialogManager,
) -> None:
    await _process_admin_partner_request_decision(
        callback=callback,
        dialog_manager=dialog_manager,
        action="reject",
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
    dialog_manager.dialog_data["selected_user_event_id"] = int(item_id)
    await callback.answer()
    await dialog_manager.switch_to(StartSG.user_event_details)


async def start_user_message_partner(
    callback: CallbackQuery,
    widget: Button,
    dialog_manager: DialogManager,
) -> None:
    db: DB = dialog_manager.middleware_data.get("db")
    i18n: TranslatorRunner = dialog_manager.middleware_data.get("i18n")
    user = callback.from_user
    if not user:
        return
    user_record = await db.users.get_user_record(user_id=user.id)
    if user_record is None or user_record.role != UserRole.USER:
        await callback.answer(i18n.partner.event.prepay.contact.partner.failed())
        return

    event_id = dialog_manager.dialog_data.get("selected_user_event_id")
    if not isinstance(event_id, int):
        await callback.answer(i18n.partner.event.prepay.contact.partner.failed())
        return
    event = await db.events.get_event_by_id(event_id=event_id)
    if event is None or not isinstance(event.partner_user_id, int):
        await callback.answer(i18n.partner.event.prepay.contact.partner.failed())
        return
    reg = await db.event_registrations.get_by_user_event(
        event_id=event_id,
        user_id=user.id,
    )
    if reg is None or reg.status not in {
        EventRegistrationStatus.CONFIRMED,
        EventRegistrationStatus.ATTENDED_CONFIRMED,
    }:
        await callback.answer(i18n.partner.event.prepay.contact.partner.failed())
        return

    dialog_manager.dialog_data["selected_user_event_partner_id"] = event.partner_user_id
    await callback.answer()
    await dialog_manager.switch_to(StartSG.user_event_message_partner)


async def on_user_event_message_partner_input(
    message: Message,
    widget: object,
    dialog_manager: DialogManager,
    data: str,
) -> None:
    db: DB = dialog_manager.middleware_data.get("db")
    i18n: TranslatorRunner = dialog_manager.middleware_data.get("i18n")
    bot = dialog_manager.middleware_data.get("bot") or message.bot
    user = message.from_user
    if not user:
        return
    user_record = await db.users.get_user_record(user_id=user.id)
    if user_record is None or user_record.role != UserRole.USER:
        await message.answer(i18n.partner.event.prepay.contact.partner.failed())
        return

    event_id = dialog_manager.dialog_data.get("selected_user_event_id")
    partner_user_id = dialog_manager.dialog_data.get("selected_user_event_partner_id")
    if not isinstance(event_id, int) or not isinstance(partner_user_id, int):
        await message.answer(i18n.partner.event.prepay.contact.partner.failed())
        await dialog_manager.switch_to(StartSG.user_event_details)
        return
    event = await db.events.get_event_by_id(event_id=event_id)
    reg = await db.event_registrations.get_by_user_event(
        event_id=event_id,
        user_id=user.id,
    )
    if (
        event is None
        or event.partner_user_id != partner_user_id
        or reg is None
        or reg.status
        not in {
            EventRegistrationStatus.CONFIRMED,
            EventRegistrationStatus.ATTENDED_CONFIRMED,
        }
    ):
        await message.answer(i18n.partner.event.prepay.contact.partner.failed())
        await dialog_manager.switch_to(StartSG.user_event_details)
        return

    payload = (data or "").strip()
    if not payload:
        await message.answer(i18n.partner.event.prepay.contact.partner.prompt())
        return

    sender_label = (
        f"@{user.username}" if user.username else user.full_name or f"id:{user.id}"
    )
    quoted_payload = f"<blockquote>{html.escape(payload)}</blockquote>"
    reply_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=i18n.start.admin.registrations.pending.reply.button(),
                    callback_data=f"{EVENT_MESSAGE_USER_CALLBACK}:{user.id}",
                )
            ]
        ]
    )
    try:
        await bot.send_message(
            partner_user_id,
            i18n.start.user.event.message.partner.to.partner(
                username=html.escape(sender_label),
                event_name=html.escape(event.name or "-"),
                text=quoted_payload,
            ),
            reply_markup=reply_keyboard,
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        await message.answer(i18n.partner.event.prepay.contact.partner.failed())
        return

    await dialog_manager.switch_to(StartSG.user_event_message_partner_done)


async def show_partner_confirmed_registrations(
    callback: CallbackQuery,
    widget: Button,
    dialog_manager: DialogManager,
) -> None:
    await callback.answer()
    await dialog_manager.switch_to(StartSG.partner_event_confirmed_list)


async def show_pending_registration_details(
    callback: CallbackQuery,
    widget: Select,
    dialog_manager: DialogManager,
    item_id: str,
) -> None:
    try:
        if ":" in item_id:
            event_raw, user_raw = item_id.split(":", 1)
            dialog_manager.dialog_data["selected_partner_event_id"] = int(event_raw)
            dialog_manager.dialog_data["selected_registration_user_id"] = int(user_raw)
        else:
            dialog_manager.dialog_data["selected_registration_user_id"] = int(item_id)
    except ValueError:
        await callback.answer()
        return
    await callback.answer()
    await dialog_manager.switch_to(StartSG.partner_event_pending_details)


async def show_admin_registration_partners(
    callback: CallbackQuery,
    widget: Button,
    dialog_manager: DialogManager,
) -> None:
    dialog_manager.dialog_data.pop("selected_partner_user_id", None)
    dialog_manager.dialog_data.pop("selected_partner_event_id", None)
    dialog_manager.dialog_data.pop("selected_registration_user_id", None)
    await callback.answer()
    await dialog_manager.switch_to(StartSG.admin_registration_partners_list)


async def show_admin_registration_pending_list(
    callback: CallbackQuery,
    widget: Select,
    dialog_manager: DialogManager,
    item_id: str,
) -> None:
    try:
        partner_user_id = int(item_id)
    except ValueError:
        await callback.answer()
        return
    dialog_manager.dialog_data["selected_partner_user_id"] = partner_user_id
    dialog_manager.dialog_data["pending_source"] = "admin_partner"
    await callback.answer()
    await dialog_manager.switch_to(StartSG.admin_registration_pending_list)


async def back_to_admin_registration_partners(
    callback: CallbackQuery,
    widget: Button,
    dialog_manager: DialogManager,
) -> None:
    await callback.answer()
    await dialog_manager.switch_to(StartSG.admin_registration_partners_list)


async def back_to_pending_registrations_source(
    callback: CallbackQuery,
    widget: Button,
    dialog_manager: DialogManager,
) -> None:
    await callback.answer()
    source = dialog_manager.dialog_data.get("pending_source")
    if source == "admin_partner":
        await dialog_manager.switch_to(StartSG.admin_registration_pending_list)
        return
    await dialog_manager.switch_to(StartSG.admin_registration_partners_list)


async def back_to_registration_message_source(
    callback: CallbackQuery,
    widget: Button,
    dialog_manager: DialogManager,
) -> None:
    await callback.answer()
    source = dialog_manager.dialog_data.get("message_source")
    if source == "partner_confirmed":
        await dialog_manager.switch_to(StartSG.partner_event_confirmed_list)
        return
    await dialog_manager.switch_to(StartSG.partner_event_pending_details)


async def start_message_registration_user(
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
    user_id = dialog_manager.dialog_data.get("selected_registration_user_id")
    if not isinstance(user_id, int):
        await callback.answer(i18n.start.admin.registrations.pending.message.invalid())
        return
    dialog_manager.dialog_data["message_source"] = "pending_details"
    await callback.answer()
    await dialog_manager.switch_to(StartSG.admin_registration_message_user)


async def start_message_confirmed_user(
    callback: CallbackQuery,
    widget: Select,
    dialog_manager: DialogManager,
    item_id: str,
) -> None:
    db: DB = dialog_manager.middleware_data.get("db")
    i18n: TranslatorRunner = dialog_manager.middleware_data.get("i18n")
    user_record = await db.users.get_user_record(user_id=callback.from_user.id)
    if user_record is None or user_record.role != UserRole.PARTNER:
        await callback.answer(i18n.partner.event.prepay.admin.only())
        return

    try:
        target_user_id = int(item_id)
    except ValueError:
        await callback.answer(i18n.start.admin.registrations.pending.message.invalid())
        return

    event_id = dialog_manager.dialog_data.get("selected_partner_event_id")
    if not isinstance(event_id, int):
        await callback.answer(i18n.start.admin.registrations.pending.message.invalid())
        return
    event = await db.events.get_event_by_id(event_id=event_id)
    if event is None or event.partner_user_id != callback.from_user.id:
        await callback.answer(i18n.start.admin.registrations.pending.message.invalid())
        return
    reg = await db.event_registrations.get_by_user_event(
        event_id=event_id,
        user_id=target_user_id,
    )
    if reg is None or reg.status not in {
        EventRegistrationStatus.CONFIRMED,
        EventRegistrationStatus.ATTENDED_CONFIRMED,
    }:
        await callback.answer(i18n.start.admin.registrations.pending.message.invalid())
        return

    dialog_manager.dialog_data["selected_registration_user_id"] = target_user_id
    dialog_manager.dialog_data["message_source"] = "partner_confirmed"
    await callback.answer()
    await dialog_manager.switch_to(StartSG.admin_registration_message_user)


async def on_admin_registration_message_input(
    message: Message,
    widget: object,
    dialog_manager: DialogManager,
    data: str,
) -> None:
    db: DB = dialog_manager.middleware_data.get("db")
    i18n: TranslatorRunner = dialog_manager.middleware_data.get("i18n")
    bot = dialog_manager.middleware_data.get("bot") or message.bot
    user = message.from_user
    if not user:
        return

    sender_record = await db.users.get_user_record(user_id=user.id)
    if sender_record is None or sender_record.role not in {UserRole.ADMIN, UserRole.PARTNER}:
        await message.answer(i18n.partner.event.prepay.admin.only())
        return

    target_user_id = dialog_manager.dialog_data.get("selected_registration_user_id")
    if not isinstance(target_user_id, int):
        await message.answer(i18n.start.admin.registrations.pending.message.invalid())
        source = dialog_manager.dialog_data.get("message_source")
        if source == "partner_confirmed":
            await dialog_manager.switch_to(StartSG.partner_event_confirmed_list)
            return
        await dialog_manager.switch_to(StartSG.partner_event_pending_details)
        return

    if sender_record.role == UserRole.PARTNER:
        event_id = dialog_manager.dialog_data.get("selected_partner_event_id")
        if not isinstance(event_id, int):
            await message.answer(i18n.start.admin.registrations.pending.message.invalid())
            return
        event = await db.events.get_event_by_id(event_id=event_id)
        if event is None or event.partner_user_id != user.id:
            await message.answer(i18n.start.admin.registrations.pending.message.invalid())
            return
        reg = await db.event_registrations.get_by_user_event(
            event_id=event_id,
            user_id=target_user_id,
        )
        if reg is None or reg.status not in {
            EventRegistrationStatus.CONFIRMED,
            EventRegistrationStatus.ATTENDED_CONFIRMED,
        }:
            await message.answer(i18n.start.admin.registrations.pending.message.invalid())
            return

    payload = (data or "").strip()
    if not payload:
        await message.answer(i18n.start.admin.registrations.pending.message.invalid())
        return

    safe_payload = html.escape(payload)
    quoted_payload = f"<blockquote>{safe_payload}</blockquote>"
    admin_label = (
        f"@{user.username}" if user.username else user.full_name or f"id:{user.id}"
    )
    sender_role = i18n.start.admin.registrations.pending.message.sender.admin()
    if sender_record.role == UserRole.PARTNER:
        sender_role = i18n.start.admin.registrations.pending.message.sender.partner()
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=i18n.start.admin.registrations.pending.reply.button(),
                    callback_data=f"{EVENT_REPLY_ADMIN_CALLBACK}:{user.id}",
                )
            ]
        ]
    )
    try:
        await bot.send_message(
            target_user_id,
            i18n.start.admin.registrations.pending.message.to.user(
                sender_role=sender_role,
                sender=html.escape(admin_label),
                text=quoted_payload,
            ),
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        await message.answer(i18n.start.admin.registrations.pending.message.invalid())
        return

    await dialog_manager.switch_to(StartSG.admin_registration_message_done)


async def _switch_after_pending_action(dialog_manager: DialogManager) -> None:
    source = dialog_manager.dialog_data.get("pending_source")
    if source == "admin_partner":
        await dialog_manager.switch_to(StartSG.admin_registration_pending_list)
        return
    await dialog_manager.switch_to(StartSG.admin_registration_partners_list)


async def approve_pending_registration(
    callback: CallbackQuery,
    widget: Button,
    dialog_manager: DialogManager,
) -> None:
    db: DB = dialog_manager.middleware_data.get("db")
    i18n = dialog_manager.middleware_data.get("i18n")
    bot = dialog_manager.middleware_data.get("bot")
    admin_record = await db.users.get_user_record(user_id=callback.from_user.id)
    if admin_record is None or admin_record.role != UserRole.ADMIN:
        await callback.answer(i18n.partner.event.prepay.admin.only())
        return
    event_id = dialog_manager.dialog_data.get("selected_partner_event_id")
    user_id = dialog_manager.dialog_data.get("selected_registration_user_id")
    if not event_id or not user_id:
        await callback.answer()
        return

    approved = await approve_event_registration_payment(
        db=db,
        i18n=i18n,
        bot=bot,
        event_id=event_id,
        user_id=user_id,
    )
    if not approved:
        await callback.answer(i18n.partner.event.prepay.already.processed())
        return
    await callback.answer(i18n.partner.event.prepay.approved.partner())
    await _switch_after_pending_action(dialog_manager)


async def decline_pending_registration(
    callback: CallbackQuery,
    widget: Button,
    dialog_manager: DialogManager,
) -> None:
    db: DB = dialog_manager.middleware_data.get("db")
    i18n = dialog_manager.middleware_data.get("i18n")
    bot = dialog_manager.middleware_data.get("bot")
    admin_record = await db.users.get_user_record(user_id=callback.from_user.id)
    if admin_record is None or admin_record.role != UserRole.ADMIN:
        await callback.answer(i18n.partner.event.prepay.admin.only())
        return
    event_id = dialog_manager.dialog_data.get("selected_partner_event_id")
    user_id = dialog_manager.dialog_data.get("selected_registration_user_id")
    if not event_id or not user_id:
        await callback.answer()
        return
    await db.event_registrations.update_status(
        event_id=event_id,
        user_id=user_id,
        status=EventRegistrationStatus.DECLINED,
    )
    if bot:
        await bot.send_message(
            user_id,
            i18n.partner.event.prepay.declined(),
        )
    await callback.answer(i18n.partner.event.prepay.declined.partner())
    await _switch_after_pending_action(dialog_manager)


async def start_my_account(
    callback: CallbackQuery,
    widget: Button,
    dialog_manager: DialogManager,
) -> None:
    await callback.answer()
    await dialog_manager.start(
        state=AccountSG.summary,
        mode=StartMode.NORMAL,
        data={"edit_profile": True},
    )


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


async def back_to_user_events_list(
    callback: CallbackQuery,
    widget: Button,
    dialog_manager: DialogManager,
) -> None:
    await callback.answer()
    await dialog_manager.switch_to(StartSG.user_events_list)


async def back_to_user_event_details(
    callback: CallbackQuery,
    widget: Button,
    dialog_manager: DialogManager,
) -> None:
    await callback.answer()
    await dialog_manager.switch_to(StartSG.user_event_details)


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
