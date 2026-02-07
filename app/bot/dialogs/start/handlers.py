from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager, StartMode
from aiogram_dialog.widgets.kbd import Button, Select
from fluentogram import TranslatorRunner

from app.bot.enums.roles import UserRole
from app.bot.enums.event_registrations import EventRegistrationStatus
from app.bot.handlers.event_chats import send_event_topic_link_to_user
from app.bot.services.partner_requests import send_partner_requests_list
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


async def start_user_attend_confirm(
    callback: CallbackQuery,
    widget: Button,
    dialog_manager: DialogManager,
) -> None:
    await callback.answer()
    await dialog_manager.switch_to(StartSG.user_event_attend_code)


async def on_user_event_attend_code(
    message,
    widget,
    dialog_manager: DialogManager,
    data: str,
) -> None:
    db: DB = dialog_manager.middleware_data.get("db")
    i18n: TranslatorRunner = dialog_manager.middleware_data.get("i18n")
    event_id = dialog_manager.dialog_data.get("selected_user_event_id")
    if not event_id:
        await message.answer(i18n.partner.event.attend.confirm.missing())
        return
    event = await db.events.get_event_by_id(event_id=event_id)
    if event is None or not event.attendance_code:
        await message.answer(i18n.partner.event.attend.confirm.missing())
        return
    user = message.from_user
    if not user:
        return
    reg = await db.event_registrations.get_by_user_event(
        event_id=event_id,
        user_id=user.id,
    )
    if reg is None or reg.status not in {
        EventRegistrationStatus.CONFIRMED,
        EventRegistrationStatus.ATTENDED_CONFIRMED,
    }:
        await message.answer(i18n.partner.event.attend.confirm.forbidden())
        return
    if reg.status == EventRegistrationStatus.ATTENDED_CONFIRMED:
        await message.answer(i18n.partner.event.attend.confirm.already())
        return
    code = (data or "").strip()
    normalized_code = "".join(ch for ch in code if ch.isdigit())
    expected_code = "".join(ch for ch in (event.attendance_code or "") if ch.isdigit())
    if normalized_code != expected_code:
        alt_event_id = await db.event_registrations.find_user_event_by_attendance_code(
            user_id=user.id,
            attendance_code=normalized_code,
            statuses=[
                EventRegistrationStatus.CONFIRMED,
                EventRegistrationStatus.ATTENDED_CONFIRMED,
            ],
        )
        if not alt_event_id:
            await message.answer(i18n.partner.event.attend.confirm.invalid())
            return
        event_id = alt_event_id
        dialog_manager.dialog_data["selected_user_event_id"] = event_id
        event = await db.events.get_event_by_id(event_id=event_id)
        if event is None or not event.attendance_code:
            await message.answer(i18n.partner.event.attend.confirm.invalid())
            return
        reg = await db.event_registrations.get_by_user_event(
            event_id=event_id,
            user_id=user.id,
        )
        if reg is None or reg.status not in {
            EventRegistrationStatus.CONFIRMED,
            EventRegistrationStatus.ATTENDED_CONFIRMED,
        }:
            await message.answer(i18n.partner.event.attend.confirm.forbidden())
            return
        if reg.status == EventRegistrationStatus.ATTENDED_CONFIRMED:
            await message.answer(i18n.partner.event.attend.confirm.already())
            return

    await db.event_registrations.mark_attended_confirmed(
        event_id=event_id,
        user_id=user.id,
    )

    user_record = await db.users.get_user_record(user_id=user.id)
    if user_record:
        await db.users.update_profile(
            user_id=user.id,
            gender=user_record.gender,
            age_group=user_record.age_group,
            intent="hot",
        )

    username = f"@{user.username}" if user.username else user.full_name
    await message.answer(i18n.partner.event.attend.confirm.ok())
    bot = dialog_manager.middleware_data.get("bot")
    if bot:
        try:
            await bot.send_message(
                event.partner_user_id,
                i18n.partner.event.attend.confirm.notify(
                    username=username,
                    event_name=event.name,
                ),
            )
        except Exception:
            pass
    await dialog_manager.switch_to(StartSG.user_event_details)


async def show_partner_pending_registrations(
    callback: CallbackQuery,
    widget: Button,
    dialog_manager: DialogManager,
) -> None:
    await callback.answer()
    await dialog_manager.switch_to(StartSG.partner_event_pending_list)


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
    dialog_manager.dialog_data["selected_registration_user_id"] = int(item_id)
    await callback.answer()
    await dialog_manager.switch_to(StartSG.partner_event_pending_details)


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
    await db.event_registrations.mark_paid_confirmed(
        event_id=event_id,
        user_id=user_id,
    )
    user_record = await db.users.get_user_record(user_id=user_id)
    if user_record:
        await db.users.update_profile(
            user_id=user_id,
            gender=user_record.gender,
            age_group=user_record.age_group,
            intent="warm",
        )
    if bot:
        await bot.send_message(
            user_id,
            i18n.partner.event.prepay.approved(),
        )
        event = await db.events.get_event_by_id(event_id=event_id)
        if event and user_record:
            await send_event_topic_link_to_user(
                bot=bot,
                i18n=i18n,
                event=event,
                user_id=user_id,
                gender=user_record.gender,
            )
    await callback.answer(i18n.partner.event.prepay.approved.partner())
    await dialog_manager.switch_to(StartSG.partner_event_pending_list)


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
    await dialog_manager.switch_to(StartSG.partner_event_pending_list)


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
