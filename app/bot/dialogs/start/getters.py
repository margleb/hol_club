from aiogram.types import ContentType, User
from aiogram_dialog import DialogManager
from aiogram_dialog.api.entities import MediaAttachment, MediaId
from fluentogram import TranslatorRunner

from app.bot.dialogs.events.utils import build_event_text
from app.bot.enums.event_registrations import EventRegistrationStatus
from app.bot.enums.roles import UserRole
from app.infrastructure.database.database.db import DB

EVENTS_PAGE_SIZE = 5


def _build_channel_post_link(channel_id: int | None, message_id: int | None) -> str | None:
    if not channel_id or not message_id:
        return None
    chat_id_str = str(channel_id)
    if chat_id_str.startswith("-100"):
        channel_id_str = chat_id_str[4:]
    else:
        channel_id_str = str(abs(channel_id))
    return f"https://t.me/c/{channel_id_str}/{message_id}"


async def get_hello(
    dialog_manager: DialogManager,
    i18n: TranslatorRunner,
    event_from_user: User,
    db: DB,
    **kwargs,
) -> dict[str, str]:
    username = event_from_user.full_name or event_from_user.username or i18n.stranger()
    user_record = await db.users.get_user_record(user_id=event_from_user.id)
    is_partner = bool(
        user_record and user_record.role in {UserRole.PARTNER, UserRole.ADMIN}
    )
    is_admin = bool(user_record and user_record.role == UserRole.ADMIN)
    return {
        "hello": i18n.start.hello(username=username),
        "create_event_button": i18n.partner.event.create.button(),
        "can_create_event": is_partner,
        "my_account_button": i18n.account.button(),
        "partner_events_list_button": i18n.partner.events.list.button(),
        "can_view_partner_events": is_partner,
        "partner_requests_button": i18n.partner.request.list.button(),
        "can_manage_partner_requests": is_admin,
        "back_button": i18n.back.button(),
    }


async def get_partner_events(
    dialog_manager: DialogManager,
    i18n: TranslatorRunner,
    event_from_user: User,
    db: DB,
    **kwargs,
) -> dict[str, str | list[tuple[str, str]] | bool]:
    user_record = await db.users.get_user_record(user_id=event_from_user.id)
    is_partner = bool(
        user_record and user_record.role in {UserRole.PARTNER, UserRole.ADMIN}
    )
    all_events = []
    if is_partner:
        all_events = await db.events.get_partner_event_list(
            partner_user_id=event_from_user.id
        )
    total_events = len(all_events)
    total_pages = max(1, (total_events + EVENTS_PAGE_SIZE - 1) // EVENTS_PAGE_SIZE)
    current_page = int(dialog_manager.dialog_data.get("partner_events_page", 0))
    current_page = max(0, min(current_page, total_pages - 1))
    dialog_manager.dialog_data["partner_events_page"] = current_page
    start = current_page * EVENTS_PAGE_SIZE
    end = start + EVENTS_PAGE_SIZE
    page_items = all_events[start:end]

    event_items = []
    for item in page_items:
        label = i18n.partner.events.item(
            name=item.name,
            datetime=item.event_datetime,
        )
        event_items.append((label, str(item.event_id)))

    return {
        "partner_events_title": i18n.partner.events.title(),
        "partner_events_empty": i18n.partner.events.empty(),
        "partner_event_items": event_items,
        "has_partner_events": bool(event_items),
        "show_partner_events_empty": is_partner and total_events == 0,
        "show_partner_events_page": is_partner and total_pages > 1,
        "partner_events_page_text": i18n.partner.events.page(
            current=current_page + 1, total=total_pages
        ),
        "partner_events_prev_button": i18n.partner.events.prev.button(),
        "partner_events_next_button": i18n.partner.events.next.button(),
        "has_partner_prev_page": current_page > 0,
        "has_partner_next_page": current_page < total_pages - 1,
        "back_button": i18n.back.button(),
    }


async def get_partner_event_details(
    dialog_manager: DialogManager,
    i18n: TranslatorRunner,
    event_from_user: User,
    db: DB,
    **kwargs,
) -> dict[str, str | bool | MediaAttachment | None]:
    event_id = dialog_manager.dialog_data.get("selected_partner_event_id")
    if not event_id:
        return {
            "event_details_text": i18n.start.event.details.missing(),
            "back_button": i18n.back.button(),
            "has_post_url": False,
        }

    user_record = await db.users.get_user_record(user_id=event_from_user.id)
    is_partner = bool(
        user_record and user_record.role in {UserRole.PARTNER, UserRole.ADMIN}
    )
    if not is_partner:
        return {
            "event_details_text": i18n.partner.event.forbidden(),
            "back_button": i18n.back.button(),
            "has_post_url": False,
        }

    event = await db.events.get_event_by_id(event_id=event_id)
    if event is None:
        return {
            "event_details_text": i18n.start.event.details.missing(),
            "back_button": i18n.back.button(),
            "has_post_url": False,
        }
    if user_record.role == UserRole.PARTNER and event.partner_user_id != event_from_user.id:
        return {
            "event_details_text": i18n.partner.event.forbidden(),
            "back_button": i18n.back.button(),
            "has_post_url": False,
        }

    event_text = build_event_text(
        {
            "name": event.name,
            "datetime": event.event_datetime,
            "address": event.address,
            "description": event.description,
            "is_paid": event.is_paid,
            "price": event.price,
            "age_group": event.age_group,
        },
        i18n,
    )
    if event.attendance_code:
        event_text = "\n\n".join(
            [
                event_text,
                i18n.partner.event.attendance.code(value=event.attendance_code),
            ]
        )

    return {
        "event_details_text": event_text,
        "event_media": (
            MediaAttachment(
                type=ContentType.PHOTO,
                file_id=MediaId(event.photo_file_id),
            )
            if event.photo_file_id
            else None
        ),
        "back_button": i18n.back.button(),
        "view_post_button": i18n.partner.event.view.post.button(),
        "event_post_url": _build_channel_post_link(
            event.channel_id, event.channel_message_id
        )
        or "",
        "has_post_url": bool(event.channel_id and event.channel_message_id),
        "pending_regs_button": i18n.partner.event.registrations.pending.button(),
        "confirmed_regs_button": i18n.partner.event.registrations.confirmed.button(),
    }


async def get_partner_pending_registrations(
    dialog_manager: DialogManager,
    i18n: TranslatorRunner,
    event_from_user: User,
    db: DB,
    **kwargs,
) -> dict[str, object]:
    event_id = dialog_manager.dialog_data.get("selected_partner_event_id")
    if not event_id:
        return {
            "title": i18n.partner.event.registrations.pending.title(),
            "items": [],
            "empty_text": i18n.partner.event.registrations.pending.empty(),
            "has_items": False,
            "back_button": i18n.back.button(),
        }

    items = await db.event_registrations.list_by_event_and_status(
        event_id=event_id,
        status=EventRegistrationStatus.PAID_CONFIRM_PENDING,
    )
    formatted = []
    for user_id, username, status, amount in items:
        label = i18n.partner.event.registrations.pending.item(
            user_id=user_id,
            username=f"@{username}" if username else f"id:{user_id}",
            amount=amount if amount is not None else "-",
        )
        formatted.append((label, str(user_id)))

    return {
        "title": i18n.partner.event.registrations.pending.title(),
        "items": formatted,
        "empty_text": i18n.partner.event.registrations.pending.empty(),
        "has_items": bool(formatted),
        "back_button": i18n.back.button(),
    }


async def get_partner_pending_registration_details(
    dialog_manager: DialogManager,
    i18n: TranslatorRunner,
    event_from_user: User,
    db: DB,
    **kwargs,
) -> dict[str, object]:
    event_id = dialog_manager.dialog_data.get("selected_partner_event_id")
    user_id = dialog_manager.dialog_data.get("selected_registration_user_id")
    if not event_id or not user_id:
        return {
            "details_text": i18n.partner.event.registrations.pending.details.missing(),
            "approve_button": i18n.partner.event.registrations.pending.approve.button(),
            "decline_button": i18n.partner.event.registrations.pending.decline.button(),
            "back_button": i18n.back.button(),
        }

    reg = await db.event_registrations.get_by_user_event(
        event_id=event_id,
        user_id=user_id,
    )
    user = await db.users.get_user_record(user_id=user_id)
    username = f"@{user.username}" if user and user.username else f"id:{user_id}"
    amount = reg.amount if reg else "-"
    text = i18n.partner.event.registrations.pending.details.text(
        username=username,
        amount=amount,
    )
    return {
        "details_text": text,
        "approve_button": i18n.partner.event.registrations.pending.approve.button(),
        "decline_button": i18n.partner.event.registrations.pending.decline.button(),
        "back_button": i18n.back.button(),
    }


async def get_partner_confirmed_registrations(
    dialog_manager: DialogManager,
    i18n: TranslatorRunner,
    event_from_user: User,
    db: DB,
    **kwargs,
) -> dict[str, object]:
    event_id = dialog_manager.dialog_data.get("selected_partner_event_id")
    if not event_id:
        return {
            "title": i18n.partner.event.registrations.confirmed.title(),
            "items": [],
            "empty_text": i18n.partner.event.registrations.confirmed.empty(),
            "has_items": False,
            "back_button": i18n.back.button(),
        }

    items = await db.event_registrations.list_by_event_and_status(
        event_id=event_id,
        status=EventRegistrationStatus.CONFIRMED,
    )
    formatted = []
    for user_id, username, status, amount in items:
        label = i18n.partner.event.registrations.confirmed.item(
            user_id=user_id,
            username=f"@{username}" if username else f"id:{user_id}",
        )
        formatted.append((label, str(user_id)))

    return {
        "title": i18n.partner.event.registrations.confirmed.title(),
        "items": formatted,
        "empty_text": i18n.partner.event.registrations.confirmed.empty(),
        "has_items": bool(formatted),
        "back_button": i18n.back.button(),
    }
