from datetime import datetime

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


def _build_topic_link(
    *,
    chat_id: int | None,
    thread_id: int | None,
    message_id: int | None,
    chat_username: str | None,
) -> str | None:
    if not thread_id or not message_id:
        return None
    if chat_username:
        username = chat_username.lstrip("@")
        if username:
            return f"https://t.me/{username}/{message_id}?thread={thread_id}"
    if not chat_id:
        return None
    chat_id_str = str(chat_id)
    if chat_id_str.startswith("-100"):
        chat_id_str = chat_id_str[4:]
    else:
        chat_id_str = str(abs(chat_id))
    return f"https://t.me/c/{chat_id_str}/{message_id}?thread={thread_id}"


def _is_event_past(event_datetime: str | None) -> bool:
    if not event_datetime:
        return False
    try:
        return datetime.strptime(event_datetime, "%Y.%m.%d %H:%M") < datetime.now()
    except ValueError:
        return False


async def get_hello(
    dialog_manager: DialogManager,
    i18n: TranslatorRunner,
    event_from_user: User,
    db: DB,
    **kwargs,
) -> dict[str, str | bool]:
    username = event_from_user.full_name or event_from_user.username or i18n.stranger()
    user_record = await db.users.get_user_record(user_id=event_from_user.id)

    is_admin = bool(user_record and user_record.role == UserRole.ADMIN)
    is_user = bool(user_record and user_record.role == UserRole.USER)

    return {
        "hello": i18n.start.hello(username=username),
        "create_event_button": i18n.partner.event.create.button(),
        "can_create_event": is_admin,
        "user_events_list_button": i18n.start.events.list.button(),
        "can_view_user_events": is_user,
        "admin_pending_button": i18n.start.admin.registrations.button(),
        "can_manage_pending_registrations": is_admin,
        "back_button": i18n.back.button(),
    }


async def get_user_events(
    dialog_manager: DialogManager,
    i18n: TranslatorRunner,
    event_from_user: User,
    db: DB,
    **kwargs,
) -> dict[str, str | list[tuple[str, str]] | bool]:
    statuses = [
        EventRegistrationStatus.CONFIRMED,
        EventRegistrationStatus.ATTENDED_CONFIRMED,
    ]
    all_events = await db.event_registrations.list_user_events(
        user_id=event_from_user.id,
        statuses=statuses,
    )
    total_events = len(all_events)
    total_pages = max(1, (total_events + EVENTS_PAGE_SIZE - 1) // EVENTS_PAGE_SIZE)
    current_page = int(dialog_manager.dialog_data.get("user_events_page", 0))
    current_page = max(0, min(current_page, total_pages - 1))
    dialog_manager.dialog_data["user_events_page"] = current_page
    start = current_page * EVENTS_PAGE_SIZE
    end = start + EVENTS_PAGE_SIZE
    page_items = all_events[start:end]

    event_items: list[tuple[str, str]] = []
    for event_id, name, event_datetime, _status, _is_paid in page_items:
        tags: list[str] = []
        if _is_event_past(event_datetime):
            tags.append(i18n.start.event.past.tag())
        tags_text = f" {' '.join(tags)}" if tags else ""
        label = i18n.start.events.item(
            name=name,
            datetime=event_datetime,
            tags=tags_text,
        )
        event_items.append((label, str(event_id)))

    return {
        "user_events_title": i18n.start.events.title(),
        "user_events_empty": i18n.start.events.empty(),
        "user_event_items": event_items,
        "has_user_events": bool(event_items),
        "show_user_events_empty": total_events == 0,
        "show_user_events_page": total_pages > 1,
        "user_events_page_text": i18n.start.events.page(
            current=current_page + 1, total=total_pages
        ),
        "user_events_prev_button": i18n.start.events.prev.button(),
        "user_events_next_button": i18n.start.events.next.button(),
        "has_user_prev_page": current_page > 0,
        "has_user_next_page": current_page < total_pages - 1,
        "back_button": i18n.back.button(),
    }


async def get_user_event_details(
    dialog_manager: DialogManager,
    i18n: TranslatorRunner,
    event_from_user: User,
    db: DB,
    **kwargs,
) -> dict[str, object]:
    _ = event_from_user
    event_id = dialog_manager.dialog_data.get("selected_user_event_id")
    if not event_id:
        return {
            "event_details_text": i18n.start.event.details.missing(),
            "back_button": i18n.back.button(),
            "has_post_url": False,
            "view_chat_button": i18n.partner.event.view.chat.button(),
            "event_chat_url": "",
            "has_chat_url": False,
        }

    event = await db.events.get_event_by_id(event_id=event_id)
    if event is None:
        return {
            "event_details_text": i18n.start.event.details.missing(),
            "back_button": i18n.back.button(),
            "has_post_url": False,
            "view_chat_button": i18n.partner.event.view.chat.button(),
            "event_chat_url": "",
            "has_chat_url": False,
        }

    post_url = _build_channel_post_link(event.channel_id, event.channel_message_id)
    event_chat_url = event.private_chat_invite_link or ""
    if not event_chat_url:
        event_chat_url = _build_topic_link(
            chat_id=event.male_chat_id,
            thread_id=event.male_thread_id,
            message_id=event.male_message_id,
            chat_username=event.male_chat_username,
        ) or _build_topic_link(
            chat_id=event.female_chat_id,
            thread_id=event.female_thread_id,
            message_id=event.female_message_id,
            chat_username=event.female_chat_username,
        ) or ""

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

    tags: list[str] = []
    if _is_event_past(event.event_datetime):
        tags.append(i18n.start.event.past.tag())
    if tags:
        event_text = "\n\n".join([event_text, " ".join(tags)])

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
        "event_post_url": post_url or "",
        "has_post_url": bool(post_url),
        "view_chat_button": i18n.partner.event.view.chat.button(),
        "event_chat_url": event_chat_url,
        "has_chat_url": bool(event_chat_url),
    }


async def get_admin_registration_pending(
    dialog_manager: DialogManager,
    i18n: TranslatorRunner,
    event_from_user: User,
    db: DB,
    **kwargs,
) -> dict[str, object]:
    admin_record = await db.users.get_user_record(user_id=event_from_user.id)
    is_admin = bool(admin_record and admin_record.role == UserRole.ADMIN)
    if not is_admin:
        return {
            "title": i18n.start.admin.registrations.pending.title(),
            "items": [],
            "empty_text": i18n.start.admin.registrations.pending.empty(),
            "has_items": False,
            "back_button": i18n.back.button(),
        }

    pending_rows = await db.event_registrations.list_pending_for_admin()
    items: list[tuple[str, str]] = []
    for event_id, user_id, username, event_name, amount in pending_rows:
        user_label = f"@{username}" if username else f"id:{user_id}"
        amount_label = amount if amount is not None else "-"
        label = i18n.start.admin.registrations.pending.item(
            username=user_label,
            event_name=event_name,
            amount=amount_label,
        )
        items.append((label, f"{event_id}:{user_id}"))

    return {
        "title": i18n.start.admin.registrations.pending.title(),
        "items": items,
        "empty_text": i18n.start.admin.registrations.pending.empty(),
        "has_items": bool(items),
        "back_button": i18n.back.button(),
    }


async def get_admin_registration_pending_details(
    dialog_manager: DialogManager,
    i18n: TranslatorRunner,
    event_from_user: User,
    db: DB,
    **kwargs,
) -> dict[str, object]:
    admin_record = await db.users.get_user_record(user_id=event_from_user.id)
    is_admin = bool(admin_record and admin_record.role == UserRole.ADMIN)
    if not is_admin:
        return {
            "details_text": i18n.partner.event.registrations.pending.details.missing(),
            "approve_button": i18n.partner.event.registrations.pending.approve.button(),
            "decline_button": i18n.partner.event.registrations.pending.decline.button(),
            "payment_proof_media": None,
            "has_payment_proof_media": False,
            "back_button": i18n.back.button(),
        }

    event_id = dialog_manager.dialog_data.get("selected_pending_event_id")
    user_id = dialog_manager.dialog_data.get("selected_registration_user_id")
    if not event_id or not user_id:
        return {
            "details_text": i18n.partner.event.registrations.pending.details.missing(),
            "approve_button": i18n.partner.event.registrations.pending.approve.button(),
            "decline_button": i18n.partner.event.registrations.pending.decline.button(),
            "payment_proof_media": None,
            "has_payment_proof_media": False,
            "back_button": i18n.back.button(),
        }

    event = await db.events.get_event_by_id(event_id=event_id)
    reg = await db.event_registrations.get_by_user_event(
        event_id=event_id,
        user_id=user_id,
    )
    if event is None or reg is None:
        return {
            "details_text": i18n.partner.event.registrations.pending.details.missing(),
            "approve_button": i18n.partner.event.registrations.pending.approve.button(),
            "decline_button": i18n.partner.event.registrations.pending.decline.button(),
            "payment_proof_media": None,
            "has_payment_proof_media": False,
            "back_button": i18n.back.button(),
        }

    user = await db.users.get_user_record(user_id=user_id)
    owner = await db.users.get_user_record(user_id=event.organizer_user_id)
    username = f"@{user.username}" if user and user.username else f"id:{user_id}"
    owner_username = (
        f"@{owner.username}" if owner and owner.username else f"id:{event.organizer_user_id}"
    )

    amount = reg.amount if reg.amount is not None else "-"
    details_text = i18n.partner.event.prepay.notify(
        username=username,
        event_name=event.name,
        organizer_username=owner_username,
        amount=amount,
    )

    payment_proof_media = None
    if reg.payment_proof_file_id and reg.payment_proof_type in {"photo", "document"}:
        media_type = (
            ContentType.PHOTO
            if reg.payment_proof_type == "photo"
            else ContentType.DOCUMENT
        )
        payment_proof_media = MediaAttachment(
            type=media_type,
            file_id=MediaId(reg.payment_proof_file_id),
        )

    return {
        "details_text": details_text,
        "approve_button": i18n.partner.event.registrations.pending.approve.button(),
        "decline_button": i18n.partner.event.registrations.pending.decline.button(),
        "payment_proof_media": payment_proof_media,
        "has_payment_proof_media": payment_proof_media is not None,
        "back_button": i18n.back.button(),
    }
