from aiogram.types import ContentType, User
from aiogram_dialog import DialogManager
from aiogram_dialog.api.entities import MediaAttachment, MediaId
from fluentogram import TranslatorRunner

from app.bot.dialogs.events.utils import build_event_text
from app.bot.enums.event_registrations import EventRegistrationStatus
from app.bot.enums.roles import UserRole
from app.bot.handlers.event_chats import ensure_event_private_chat
from app.infrastructure.database.database.db import DB
from app.services.telegram.private_event_chats import EventPrivateChatService
from app.utils.datetime import format_event_datetime, is_event_past, now_utc

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


def _can_show_event_chat_link(event) -> bool:
    if getattr(event, "private_chat_deleted_at", None) is not None:
        return False
    delete_at = getattr(event, "private_chat_delete_at", None)
    if delete_at is not None and delete_at <= now_utc():
        return False
    return True


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
        "admin_events_button": i18n.start.admin.events.button(),
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
    for event_id, name, event_datetime, _status in page_items:
        tags: list[str] = []
        if is_event_past(event_datetime):
            tags.append(i18n.start.event.past.tag())
        tags_text = f" {' '.join(tags)}" if tags else ""
        label = i18n.start.events.item(
            name=name,
            datetime=format_event_datetime(event_datetime),
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


async def get_admin_events(
    dialog_manager: DialogManager,
    i18n: TranslatorRunner,
    event_from_user: User,
    db: DB,
    **kwargs,
) -> dict[str, object]:
    admin_record = await db.users.get_user_record(user_id=event_from_user.id)
    if not admin_record or admin_record.role != UserRole.ADMIN:
        return {
            "title": i18n.start.admin.events.title(),
            "empty_text": i18n.start.admin.events.empty(),
            "items": [],
            "has_items": False,
            "back_button": i18n.back.button(),
        }

    events = await db.events.list_by_organizer_upcoming(
        organizer_user_id=event_from_user.id,
    )
    items: list[tuple[str, str]] = []
    for event in events:
        label = i18n.start.admin.events.item(
            name=event.name,
            datetime=format_event_datetime(event.event_datetime),
        )
        items.append((label, str(event.id)))

    return {
        "title": i18n.start.admin.events.title(),
        "empty_text": i18n.start.admin.events.empty(),
        "items": items,
        "has_items": bool(items),
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
    event_private_chat_service: EventPrivateChatService | None = (
        dialog_manager.middleware_data.get("event_private_chat_service")
    )
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
    if _can_show_event_chat_link(event) and not event.private_chat_invite_link:
        event_with_chat = await ensure_event_private_chat(
            db=db,
            event_id=event.id,
            event_private_chat_service=event_private_chat_service,
        )
        if event_with_chat is not None:
            event = event_with_chat

    event_chat_url = ""
    if _can_show_event_chat_link(event):
        event_chat_url = event.private_chat_invite_link or ""

    event_text = build_event_text(
        {
            "name": event.name,
            "datetime": event.event_datetime,
            "address": event.address,
            "description": event.description,
            "price": event.price,
            "age_group": event.age_group,
        },
        i18n,
    )

    tags: list[str] = []
    if is_event_past(event.event_datetime):
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


async def get_admin_event_details(
    dialog_manager: DialogManager,
    i18n: TranslatorRunner,
    event_from_user: User,
    db: DB,
    **kwargs,
) -> dict[str, object]:
    admin_record = await db.users.get_user_record(user_id=event_from_user.id)
    if not admin_record or admin_record.role != UserRole.ADMIN:
        return {
            "event_details_text": i18n.partner.event.text.template(
                name=i18n.partner.event.view.post.button(),
                datetime="",
                address="",
                participation="",
                description_block="",
                age_block="",
            ),
            "event_media": None,
            "back_button": i18n.back.button(),
            "view_post_button": i18n.partner.event.view.post.button(),
            "event_post_url": "",
            "has_post_url": False,
            "view_chat_button": i18n.partner.event.view.chat.button(),
            "event_chat_url": "",
            "has_chat_url": False,
            "registrations_button": i18n.partner.event.registrations.pending.button(),
        }

    event_id = dialog_manager.dialog_data.get("selected_admin_event_id")
    if not isinstance(event_id, int):
        return {
            "event_details_text": i18n.start.event.details.missing(),
            "event_media": None,
            "back_button": i18n.back.button(),
            "view_post_button": i18n.partner.event.view.post.button(),
            "event_post_url": "",
            "has_post_url": False,
            "view_chat_button": i18n.partner.event.view.chat.button(),
            "event_chat_url": "",
            "has_chat_url": False,
            "registrations_button": i18n.partner.event.registrations.pending.button(),
        }

    event = await db.events.get_event_by_id(event_id=event_id)
    if event is None:
        return {
            "event_details_text": i18n.start.event.details.missing(),
            "event_media": None,
            "back_button": i18n.back.button(),
            "view_post_button": i18n.partner.event.view.post.button(),
            "event_post_url": "",
            "has_post_url": False,
            "view_chat_button": i18n.partner.event.view.chat.button(),
            "event_chat_url": "",
            "has_chat_url": False,
            "registrations_button": i18n.partner.event.registrations.pending.button(),
        }

    event_text = build_event_text(
        {
            "name": event.name,
            "datetime": event.event_datetime,
            "address": event.address,
            "description": event.description,
            "price": event.price,
            "age_group": event.age_group,
        },
        i18n,
    )

    post_url = _build_channel_post_link(event.channel_id, event.channel_message_id)
    chat_url = event.private_chat_invite_link or ""
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
        "event_chat_url": chat_url,
        "has_chat_url": bool(chat_url),
        "registrations_button": i18n.partner.event.registrations.pending.button(),
    }


async def get_admin_event_registrations(
    dialog_manager: DialogManager,
    i18n: TranslatorRunner,
    event_from_user: User,
    db: DB,
    **kwargs,
) -> dict[str, object]:
    admin_record = await db.users.get_user_record(user_id=event_from_user.id)
    if not admin_record or admin_record.role != UserRole.ADMIN:
        return {
            "title": i18n.start.admin.registrations.pending.title(),
            "empty_text": i18n.start.admin.registrations.pending.empty(),
            "items": [],
            "has_items": False,
            "back_button": i18n.back.button(),
        }

    event_id = dialog_manager.dialog_data.get("selected_admin_event_id")
    if not isinstance(event_id, int):
        return {
            "title": i18n.start.admin.registrations.pending.title(),
            "empty_text": i18n.start.admin.registrations.pending.empty(),
            "items": [],
            "has_items": False,
            "back_button": i18n.back.button(),
        }

    event = await db.events.get_event_by_id(event_id=event_id)
    rows = []
    if event is not None:
        rows = await db.event_registrations.list_by_event_and_status(
            event_id=event_id,
            status=EventRegistrationStatus.PAID_CONFIRM_PENDING,
        )
    items: list[tuple[str, str]] = []
    for user_id, username, status, amount in rows:
        user_label = f"@{username}" if username else f"id:{user_id}"
        amount_label = amount if amount is not None else "-"
        label = i18n.start.admin.registrations.pending.item(
            username=user_label,
            event_name=event.name if event else "-",
            amount=amount_label,
        )
        items.append((label, f"{event_id}:{user_id}"))

    return {
        "title": i18n.start.admin.registrations.pending.title(),
        "empty_text": i18n.start.admin.registrations.pending.empty(),
        "items": items,
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
