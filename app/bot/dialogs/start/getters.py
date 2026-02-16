from datetime import datetime

from aiogram.types import ContentType, User
from aiogram_dialog import DialogManager
from aiogram_dialog.api.entities import MediaAttachment, MediaId
from fluentogram import TranslatorRunner

from app.bot.enums.partner_requests import PartnerRequestStatus
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
) -> dict[str, str]:
    username = event_from_user.full_name or event_from_user.username or i18n.stranger()
    user_record = await db.users.get_user_record(user_id=event_from_user.id)
    can_create_event = bool(
        user_record and user_record.role in {UserRole.PARTNER, UserRole.ADMIN}
    )
    can_view_partner_events = bool(
        user_record and user_record.role == UserRole.PARTNER
    )
    is_admin = bool(user_record and user_record.role == UserRole.ADMIN)
    is_user = bool(user_record and user_record.role == UserRole.USER)
    return {
        "hello": i18n.start.hello(username=username),
        "create_event_button": i18n.partner.event.create.button(),
        "can_create_event": can_create_event,
        "my_account_button": i18n.account.button(),
        "user_events_list_button": i18n.start.events.list.button(),
        "can_view_user_events": is_user,
        "partner_events_list_button": i18n.partner.events.list.button(),
        "can_view_partner_events": can_view_partner_events,
        "admin_partners_button": i18n.start.admin.partners.button(),
        "can_manage_partners": is_admin,
        "partner_requests_button": i18n.partner.request.list.button(),
        "can_manage_partner_requests": is_admin,
        "back_button": i18n.back.button(),
    }


async def get_admin_partner_commissions(
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
            "title": i18n.start.admin.partner.commissions.title(),
            "items": [],
            "empty_text": i18n.start.admin.partner.commissions.empty(),
            "has_items": False,
            "back_button": i18n.back.button(),
        }

    partners = await db.users.list_partners_with_commission()
    items: list[tuple[str, str]] = []
    for partner_user_id, partner_username, commission_percent in partners:
        partner_label = (
            f"@{partner_username}" if partner_username else f"id:{partner_user_id}"
        )
        label = i18n.start.admin.partner.commissions.item(
            username=partner_label,
            percent=commission_percent,
        )
        items.append((label, str(partner_user_id)))

    return {
        "title": i18n.start.admin.partner.commissions.title(),
        "items": items,
        "empty_text": i18n.start.admin.partner.commissions.empty(),
        "has_items": bool(items),
        "back_button": i18n.back.button(),
    }


async def get_admin_partner_commission_edit(
    dialog_manager: DialogManager,
    i18n: TranslatorRunner,
    event_from_user: User,
    db: DB,
    **kwargs,
) -> dict[str, object]:
    admin_record = await db.users.get_user_record(user_id=event_from_user.id)
    selected_user_id = dialog_manager.dialog_data.get("selected_partner_commission_user_id")
    is_admin = bool(admin_record and admin_record.role == UserRole.ADMIN)
    if not is_admin or not isinstance(selected_user_id, int):
        return {
            "prompt": i18n.start.admin.partner.commission.edit.invalid(),
            "back_button": i18n.back.button(),
        }

    partner = await db.users.get_user_record(user_id=selected_user_id)
    if partner is None or partner.role != UserRole.PARTNER:
        return {
            "prompt": i18n.start.admin.partner.commission.edit.invalid(),
            "back_button": i18n.back.button(),
        }

    username = f"@{partner.username}" if partner.username else f"id:{partner.user_id}"
    return {
        "prompt": i18n.start.admin.partner.commission.edit.prompt(
            username=username,
            percent=int(partner.commission_percent or 0),
        ),
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
        user_record and user_record.role == UserRole.PARTNER
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

    event_items = []
    for event_id, name, event_datetime, _status, _is_paid in page_items:
        tags = []
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


async def get_admin_registration_partners(
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
            "title": i18n.start.admin.registrations.partners.title(),
            "items": [],
            "empty_text": i18n.start.admin.registrations.partners.empty(),
            "has_items": False,
            "back_button": i18n.back.button(),
        }

    partners = await db.users.list_partners_with_commission()
    pending_partners = await db.event_registrations.list_partners_with_pending_payment()
    pending_map: dict[int, int] = {}
    for partner_user_id, _partner_username, pending_count in pending_partners:
        pending_map[partner_user_id] = pending_count
    items: list[tuple[str, str]] = []
    for partner_user_id, partner_username, commission_percent in partners:
        partner_label = (
            f"@{partner_username}" if partner_username else f"id:{partner_user_id}"
        )
        pending_count = pending_map.get(partner_user_id, 0)
        percent = int(commission_percent or 0)
        label = i18n.start.admin.registrations.partners.item(
            username=partner_label,
            percent=percent,
            pending=pending_count,
        )
        items.append((label, str(partner_user_id)))

    return {
        "title": i18n.start.admin.registrations.partners.title(),
        "items": items,
        "empty_text": i18n.start.admin.registrations.partners.empty(),
        "has_items": bool(items),
        "back_button": i18n.back.button(),
    }


async def get_admin_partner_actions(
    dialog_manager: DialogManager,
    i18n: TranslatorRunner,
    event_from_user: User,
    db: DB,
    **kwargs,
) -> dict[str, object]:
    admin_record = await db.users.get_user_record(user_id=event_from_user.id)
    is_admin = bool(admin_record and admin_record.role == UserRole.ADMIN)
    partner_user_id = dialog_manager.dialog_data.get("selected_partner_user_id")
    if not is_admin or not isinstance(partner_user_id, int):
        return {
            "title": i18n.start.admin.partner.actions.invalid(),
            "show_actions": False,
            "set_commission_button": i18n.start.admin.partner.actions.commission.button(),
            "registrations_button": i18n.start.admin.partner.actions.registrations.button(),
            "back_button": i18n.back.button(),
        }

    partner = await db.users.get_user_record(user_id=partner_user_id)
    partner_label = (
        f"@{partner.username}" if partner and partner.username else f"id:{partner_user_id}"
    )
    return {
        "title": i18n.start.admin.partner.actions.title(username=partner_label),
        "show_actions": True,
        "set_commission_button": i18n.start.admin.partner.actions.commission.button(),
        "registrations_button": i18n.start.admin.partner.actions.registrations.button(),
        "back_button": i18n.back.button(),
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
            "title": i18n.start.admin.registrations.pending.title(partner="-"),
            "items": [],
            "empty_text": i18n.start.admin.registrations.pending.empty(),
            "has_items": False,
            "back_button": i18n.back.button(),
        }

    partner_user_id = dialog_manager.dialog_data.get("selected_partner_user_id")
    if not isinstance(partner_user_id, int):
        return {
            "title": i18n.start.admin.registrations.pending.title(partner="-"),
            "items": [],
            "empty_text": i18n.start.admin.registrations.pending.empty(),
            "has_items": False,
            "back_button": i18n.back.button(),
        }

    partner = await db.users.get_user_record(user_id=partner_user_id)
    partner_label = (
        f"@{partner.username}" if partner and partner.username else f"id:{partner_user_id}"
    )

    pending = await db.event_registrations.list_pending_by_partner(
        partner_user_id=partner_user_id
    )
    items: list[tuple[str, str]] = []
    for event_id, user_id, username, event_name, amount in pending:
        user_label = f"@{username}" if username else f"id:{user_id}"
        amount_label = amount if amount is not None else "-"
        label = i18n.start.admin.registrations.pending.item(
            username=user_label,
            event_name=event_name,
            amount=amount_label,
        )
        items.append((label, f"{event_id}:{user_id}"))

    return {
        "title": i18n.start.admin.registrations.pending.title(partner=partner_label),
        "items": items,
        "empty_text": i18n.start.admin.registrations.pending.empty(),
        "has_items": bool(items),
        "back_button": i18n.back.button(),
    }


async def get_admin_partner_requests(
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
            "title": i18n.start.admin.partner.requests.title(),
            "items": [],
            "empty_text": i18n.start.admin.partner.requests.empty(),
            "has_items": False,
            "back_button": i18n.back.button(),
        }

    requests = await db.partner_requests.list_pending_requests_with_usernames()
    items: list[tuple[str, str]] = []
    for user_id, username in requests:
        user_label = f"@{username}" if username else f"id:{user_id}"
        label = i18n.start.admin.partner.requests.item(
            username=user_label,
            user_id=user_id,
        )
        items.append((label, str(user_id)))

    return {
        "title": i18n.start.admin.partner.requests.title(),
        "items": items,
        "empty_text": i18n.start.admin.partner.requests.empty(),
        "has_items": bool(items),
        "back_button": i18n.back.button(),
    }


async def get_admin_partner_request_details(
    dialog_manager: DialogManager,
    i18n: TranslatorRunner,
    event_from_user: User,
    db: DB,
    **kwargs,
) -> dict[str, object]:
    admin_record = await db.users.get_user_record(user_id=event_from_user.id)
    is_admin = bool(admin_record and admin_record.role == UserRole.ADMIN)
    selected_user_id = dialog_manager.dialog_data.get("selected_partner_request_user_id")
    if not is_admin or not isinstance(selected_user_id, int):
        return {
            "details_text": i18n.partner.request.invalid(),
            "approve_button": i18n.partner.request.approve.button(),
            "reject_button": i18n.partner.request.reject.button(),
            "back_button": i18n.back.button(),
        }

    request = await db.partner_requests.get_request(user_id=selected_user_id)
    if request is None or request.status != PartnerRequestStatus.PENDING:
        return {
            "details_text": i18n.partner.approve.missing(),
            "approve_button": i18n.partner.request.approve.button(),
            "reject_button": i18n.partner.request.reject.button(),
            "back_button": i18n.back.button(),
        }

    target_user = await db.users.get_user_record(user_id=selected_user_id)
    username = (
        f"@{target_user.username}"
        if target_user and target_user.username
        else f"id:{selected_user_id}"
    )
    return {
        "details_text": i18n.start.admin.partner.request.details(
            username=username,
            user_id=selected_user_id,
        ),
        "approve_button": i18n.partner.request.approve.button(),
        "reject_button": i18n.partner.request.reject.button(),
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
        user_record and user_record.role == UserRole.PARTNER
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
    if event.partner_user_id != event_from_user.id:
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
    post_url = _build_channel_post_link(
        event.channel_id, event.channel_message_id
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
        "event_post_url": post_url or "",
        "has_post_url": bool(post_url),
        "confirmed_regs_button": i18n.partner.event.registrations.confirmed.button(),
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
            "can_confirm_payment": False,
            "payment_proof_media": None,
            "has_payment_proof_media": False,
            "show_contact_user_button": False,
            "contact_user_button": "",
            "admin_only_note": i18n.partner.event.prepay.admin.only(),
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
            "can_confirm_payment": False,
            "payment_proof_media": None,
            "has_payment_proof_media": False,
            "show_contact_user_button": False,
            "contact_user_button": "",
            "admin_only_note": i18n.partner.event.prepay.admin.only(),
            "back_button": i18n.back.button(),
        }

    user = await db.users.get_user_record(user_id=user_id)
    viewer = await db.users.get_user_record(user_id=event_from_user.id)
    can_confirm_payment = bool(viewer and viewer.role == UserRole.ADMIN)
    username = f"@{user.username}" if user and user.username else f"id:{user_id}"
    partner_record = await db.users.get_user_record(user_id=event.partner_user_id)
    partner_username = (
        f"@{partner_record.username}"
        if partner_record and partner_record.username
        else f"id:{event.partner_user_id}"
    )
    amount = reg.amount if reg.amount is not None else "-"
    text = i18n.partner.event.prepay.notify(
        username=username,
        event_name=event.name,
        partner_username=partner_username,
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
        "details_text": text,
        "approve_button": i18n.partner.event.registrations.pending.approve.button(),
        "decline_button": i18n.partner.event.registrations.pending.decline.button(),
        "can_confirm_payment": can_confirm_payment,
        "payment_proof_media": payment_proof_media,
        "has_payment_proof_media": payment_proof_media is not None,
        "show_contact_user_button": can_confirm_payment,
        "contact_user_button": i18n.start.admin.registrations.pending.contact.button(),
        "admin_only_note": i18n.partner.event.prepay.admin.only(),
        "back_button": i18n.back.button(),
    }


async def get_admin_registration_message_prompt(
    dialog_manager: DialogManager,
    i18n: TranslatorRunner,
    event_from_user: User,
    db: DB,
    **kwargs,
) -> dict[str, object]:
    sender_record = await db.users.get_user_record(user_id=event_from_user.id)
    selected_user_id = dialog_manager.dialog_data.get("selected_registration_user_id")
    if sender_record is None or not isinstance(selected_user_id, int):
        return {
            "prompt": i18n.start.admin.registrations.pending.message.invalid(),
            "back_button": i18n.back.button(),
        }
    if sender_record.role not in {UserRole.ADMIN, UserRole.PARTNER}:
        return {
            "prompt": i18n.start.admin.registrations.pending.message.invalid(),
            "back_button": i18n.back.button(),
        }

    if sender_record.role == UserRole.PARTNER:
        event_id = dialog_manager.dialog_data.get("selected_partner_event_id")
        if not isinstance(event_id, int):
            return {
                "prompt": i18n.start.admin.registrations.pending.message.invalid(),
                "back_button": i18n.back.button(),
            }
        event = await db.events.get_event_by_id(event_id=event_id)
        if event is None or event.partner_user_id != event_from_user.id:
            return {
                "prompt": i18n.start.admin.registrations.pending.message.invalid(),
                "back_button": i18n.back.button(),
            }
        reg = await db.event_registrations.get_by_user_event(
            event_id=event_id,
            user_id=selected_user_id,
        )
        if reg is None or reg.status not in {
            EventRegistrationStatus.CONFIRMED,
            EventRegistrationStatus.ATTENDED_CONFIRMED,
        }:
            return {
                "prompt": i18n.start.admin.registrations.pending.message.invalid(),
                "back_button": i18n.back.button(),
            }

    user = await db.users.get_user_record(user_id=selected_user_id)
    username = (
        f"@{user.username}"
        if user and user.username
        else f"id:{selected_user_id}"
    )
    return {
        "prompt": i18n.start.admin.registrations.pending.message.prompt(
            username=username,
        ),
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


async def get_user_event_details(
    dialog_manager: DialogManager,
    i18n: TranslatorRunner,
    event_from_user: User,
    db: DB,
    **kwargs,
) -> dict[str, object]:
    event_id = dialog_manager.dialog_data.get("selected_user_event_id")
    if not event_id:
        return {
            "event_details_text": i18n.start.event.details.missing(),
            "back_button": i18n.back.button(),
            "has_post_url": False,
            "view_chat_button": i18n.partner.event.view.chat.button(),
            "event_chat_url": "",
            "has_chat_url": False,
            "contact_partner_button": i18n.partner.event.prepay.contact.partner.button(),
            "show_contact_partner_button": False,
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
            "contact_partner_button": i18n.partner.event.prepay.contact.partner.button(),
            "show_contact_partner_button": False,
        }
    reg = await db.event_registrations.get_by_user_event(
        event_id=event_id,
        user_id=event_from_user.id,
    )
    user_record = await db.users.get_user_record(user_id=event_from_user.id)
    post_url = _build_channel_post_link(
        event.channel_id, event.channel_message_id
    )
    event_chat_url = event.private_chat_invite_link or ""
    if not event_chat_url:
        user_gender = user_record.gender if user_record else None
        if user_gender == "female":
            event_chat_url = _build_topic_link(
                chat_id=event.female_chat_id,
                thread_id=event.female_thread_id,
                message_id=event.female_message_id,
                chat_username=event.female_chat_username,
            ) or ""
        elif user_gender == "male":
            event_chat_url = _build_topic_link(
                chat_id=event.male_chat_id,
                thread_id=event.male_thread_id,
                message_id=event.male_message_id,
                chat_username=event.male_chat_username,
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
    tags = []
    if _is_event_past(event.event_datetime):
        tags.append(i18n.start.event.past.tag())
    if tags:
        event_text = "\n\n".join([event_text, " ".join(tags)])
    can_contact_partner = bool(
        reg
        and reg.status in {
            EventRegistrationStatus.CONFIRMED,
            EventRegistrationStatus.ATTENDED_CONFIRMED,
        }
        and isinstance(event.partner_user_id, int)
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
        "event_post_url": post_url or "",
        "has_post_url": bool(post_url),
        "view_chat_button": i18n.partner.event.view.chat.button(),
        "event_chat_url": event_chat_url,
        "has_chat_url": bool(event_chat_url),
        "contact_partner_button": i18n.partner.event.prepay.contact.partner.button(),
        "show_contact_partner_button": can_contact_partner,
    }


async def get_user_event_message_partner_prompt(
    dialog_manager: DialogManager,
    i18n: TranslatorRunner,
    **kwargs,
) -> dict[str, str]:
    return {
        "prompt": i18n.partner.event.prepay.contact.partner.prompt(),
        "back_button": i18n.back.button(),
    }


async def get_user_event_message_partner_done_prompt(
    dialog_manager: DialogManager,
    i18n: TranslatorRunner,
    **kwargs,
) -> dict[str, str]:
    return {
        "prompt": i18n.partner.event.prepay.contact.partner.sent(),
        "back_button": i18n.back.button(),
    }


async def get_admin_registration_message_done_prompt(
    dialog_manager: DialogManager,
    i18n: TranslatorRunner,
    **kwargs,
) -> dict[str, str]:
    return {
        "prompt": i18n.start.admin.registrations.pending.message.sent(),
        "back_button": i18n.back.button(),
    }
