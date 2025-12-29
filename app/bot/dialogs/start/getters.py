from datetime import datetime

from aiogram.types import ContentType, User
from aiogram_dialog import DialogManager
from aiogram_dialog.api.entities import MediaAttachment, MediaId
from fluentogram import TranslatorRunner

from app.bot.dialogs.events.utils import build_event_text
from app.bot.enums.roles import UserRole
from app.infrastructure.database.database.db import DB

EVENTS_PAGE_SIZE = 5


def _build_event_tags(
    *,
    i18n: TranslatorRunner,
    is_paid: bool,
    is_past: bool,
) -> str:
    tags = []
    if is_paid:
        tags.append(i18n.start.event.paid.tag())
    if is_past:
        tags.append(i18n.start.event.past.tag())
    if not tags:
        return ""
    return f" {' '.join(tags)}"


def _is_event_past(event_datetime: str) -> bool:
    try:
        event_dt = datetime.strptime(event_datetime, "%Y.%m.%d %H:%M")
    except ValueError:
        return False
    return event_dt < datetime.now()


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
    can_view_events = bool(user_record and user_record.role == UserRole.USER)
    all_events = []
    if can_view_events:
        all_events = await db.event_registrations.get_user_event_list(
            user_id=event_from_user.id
        )

    total_events = len(all_events)
    total_pages = max(1, (total_events + EVENTS_PAGE_SIZE - 1) // EVENTS_PAGE_SIZE)
    current_page = int(dialog_manager.dialog_data.get("events_page", 0))
    current_page = max(0, min(current_page, total_pages - 1))
    dialog_manager.dialog_data["events_page"] = current_page
    start = current_page * EVENTS_PAGE_SIZE
    end = start + EVENTS_PAGE_SIZE
    page_items = all_events[start:end]

    event_items = []
    for item in page_items:
        tags = _build_event_tags(
            i18n=i18n,
            is_paid=item.is_paid,
            is_past=_is_event_past(item.event_datetime),
        )
        label = i18n.start.events.item(
            name=item.name,
            datetime=item.event_datetime,
            tags=tags,
        )
        event_items.append((label, str(item.event_id)))

    return {
        "hello": i18n.start.hello(username=username),
        "create_event_button": i18n.partner.event.create.button(),
        "can_create_event": is_partner,
        "partner_requests_button": i18n.partner.request.list.button(),
        "can_manage_partner_requests": is_admin,
        "can_view_events": can_view_events,
        "events_list_button": i18n.start.events.list.button(),
        "subscriptions_title": i18n.start.events.title(),
        "subscriptions_empty": i18n.start.events.empty(),
        "event_items": event_items,
        "has_events": bool(event_items),
        "show_empty_events": can_view_events and total_events == 0,
        "show_events_page": can_view_events and total_pages > 1,
        "events_page_text": i18n.start.events.page(
            current=current_page + 1, total=total_pages
        ),
        "events_prev_button": i18n.start.events.prev.button(),
        "events_next_button": i18n.start.events.next.button(),
        "has_prev_page": current_page > 0,
        "has_next_page": current_page < total_pages - 1,
        "back_button": i18n.back.button(),
    }


async def get_event_details(
    dialog_manager: DialogManager,
    i18n: TranslatorRunner,
    event_from_user: User,
    db: DB,
    **kwargs,
) -> dict[str, str]:
    event_id = dialog_manager.dialog_data.get("selected_event_id")
    if not event_id:
        return {
            "event_details_text": i18n.start.event.details.missing(),
            "back_button": i18n.back.button(),
            "can_mark_paid": False,
            "has_post_url": False,
        }

    registration = await db.event_registrations.get_registration(
        event_id=event_id,
        user_id=event_from_user.id,
    )
    event = await db.events.get_event_by_id(event_id=event_id)
    if registration is None or event is None:
        return {
            "event_details_text": i18n.start.event.details.missing(),
            "back_button": i18n.back.button(),
            "can_mark_paid": False,
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
        "mark_paid_button": i18n.partner.event.going.paid.button(),
        "view_post_button": i18n.partner.event.view.post.button(),
        "can_mark_paid": not registration.is_paid,
        "event_post_url": _build_channel_post_link(
            event.channel_id, event.channel_message_id
        )
        or "",
        "has_post_url": bool(
            event.channel_id and event.channel_message_id
        ),
    }
