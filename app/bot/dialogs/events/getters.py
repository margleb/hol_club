from aiogram.types import ContentType, User
from aiogram_dialog import DialogManager
from aiogram_dialog.api.entities import MediaAttachment, MediaId
from fluentogram import TranslatorRunner

from app.bot.dialogs.events.constants import EVENT_AGE_GROUPS, EVENT_AGE_GROUP_ALL
from app.bot.enums.roles import UserRole
from app.infrastructure.database.database.db import DB
from config.config import settings
from app.bot.dialogs.events.utils import build_event_text


async def get_event_name(
    dialog_manager: DialogManager,
    i18n: TranslatorRunner,
    **kwargs,
) -> dict[str, str]:
    return {
        "prompt": i18n.partner.event.name.prompt(
            min=settings.events.event_name_min,
            max=settings.events.event_name_max,
        ),
        "back_button": i18n.back.button(),
    }


async def get_event_image(
    dialog_manager: DialogManager,
    i18n: TranslatorRunner,
    **kwargs,
) -> dict[str, str]:
    return {
        "prompt": i18n.partner.event.image.prompt(),
        "skip_button": i18n.partner.event.skip.button(),
        "back_button": i18n.back.button(),
    }


async def get_event_datetime(
    dialog_manager: DialogManager,
    i18n: TranslatorRunner,
    **kwargs,
) -> dict[str, str]:
    return {
        "prompt": i18n.partner.event.datetime.prompt(),
        "back_button": i18n.back.button(),
    }


async def get_event_address_query(
    dialog_manager: DialogManager,
    i18n: TranslatorRunner,
    **kwargs,
) -> dict[str, str]:
    return {
        "prompt": i18n.partner.event.address.prompt(),
        "back_button": i18n.back.button(),
    }


async def get_event_address_select(
    dialog_manager: DialogManager,
    i18n: TranslatorRunner,
    **kwargs,
) -> dict[str, list[tuple[str, str]] | str]:
    suggestions = dialog_manager.dialog_data.get("address_suggestions") or []
    choices = []
    for index, item in enumerate(suggestions):
        if isinstance(item, dict):
            label = item.get("display_name")
        else:
            label = str(item)
        if label:
            choices.append((label, str(index)))
    return {
        "prompt": i18n.partner.event.address.select.prompt(),
        "address_choices": choices,
        "back_button": i18n.back.button(),
    }


async def get_event_description(
    dialog_manager: DialogManager,
    i18n: TranslatorRunner,
    **kwargs,
) -> dict[str, str]:
    return {
        "prompt": i18n.partner.event.description.prompt(
            min=settings.events.event_desc_min,
            max=settings.events.event_desc_max,
        ),
        "back_button": i18n.back.button(),
    }


async def get_event_price(
    dialog_manager: DialogManager,
    i18n: TranslatorRunner,
    event_from_user: User,
    db: DB,
    **kwargs,
) -> dict[str, str]:
    commission_percent = 0
    partner_record = await db.users.get_user_record(user_id=event_from_user.id)
    if partner_record and partner_record.role == UserRole.PARTNER:
        commission_percent = int(partner_record.commission_percent or 0)

    return {
        "prompt": i18n.partner.event.price.prompt(
            max=settings.events.price_max,
            commission_percent=commission_percent,
        ),
        "back_button": i18n.back.button(),
    }


async def get_event_ticket_url(
    dialog_manager: DialogManager,
    i18n: TranslatorRunner,
    **kwargs,
) -> dict[str, str]:
    return {
        "prompt": i18n.partner.event.ticket.link.prompt(),
        "skip_button": i18n.partner.event.skip.button(),
        "back_button": i18n.back.button(),
    }


async def get_event_age_group(
    dialog_manager: DialogManager,
    i18n: TranslatorRunner,
    **kwargs,
) -> dict[str, list[tuple[str, str]] | str]:
    age_choices: list[tuple[str, str]] = []
    for age_group in EVENT_AGE_GROUPS:
        if age_group == EVENT_AGE_GROUP_ALL:
            age_choices.append((i18n.partner.event.age.everyone(), age_group))
            continue
        age_choices.append(
            (i18n.general.registration.age.group(range=age_group), age_group)
        )
    return {
        "prompt": i18n.partner.event.age.prompt(),
        "age_choices": age_choices,
        "back_button": i18n.back.button(),
    }


async def get_event_preview(
    dialog_manager: DialogManager,
    i18n: TranslatorRunner,
    event_from_user: User,
    db: DB,
    **kwargs,
) -> dict[str, str | bool]:
    has_photo = bool(dialog_manager.dialog_data.get("photo_file_id"))
    preview_text = build_event_text(
        dialog_manager.dialog_data,
        i18n,
    )

    lines = []
    lines.append(preview_text)
    ticket_url = (dialog_manager.dialog_data.get("ticket_url") or "").strip()
    if ticket_url:
        lines.append(i18n.partner.event.ticket.link.preview(url=ticket_url))

    user_record = await db.users.get_user_record(user_id=event_from_user.id)
    is_admin = bool(user_record and user_record.role == UserRole.ADMIN)

    return {
        "preview": "\n".join(lines).strip(),
        "preview_media": (
            MediaAttachment(
                type=ContentType.PHOTO,
                file_id=MediaId(dialog_manager.dialog_data["photo_file_id"]),
            )
            if has_photo
            else None
        ),
        "publish_button": i18n.partner.event.publish.button(),
        "edit_name_button": i18n.partner.event.edit.name.button(),
        "edit_image_button": i18n.partner.event.edit.image.button(),
        "edit_datetime_button": i18n.partner.event.edit.datetime.button(),
        "edit_address_button": i18n.partner.event.edit.address.button(),
        "edit_description_button": i18n.partner.event.edit.description.button(),
        "edit_price_button": i18n.partner.event.edit.price.button(),
        "edit_ticket_button": i18n.partner.event.edit.ticket.link.button(),
        "edit_age_button": i18n.partner.event.edit.age.button(),
        "is_paid": bool(dialog_manager.dialog_data.get("is_paid")),
        "can_edit_ticket": is_admin,
        "back_button": i18n.back.button(),
    }
