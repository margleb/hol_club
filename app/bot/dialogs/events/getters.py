from aiogram_dialog import DialogManager
from fluentogram import TranslatorRunner

from app.bot.dialogs.events.constants import (
    ADDRESS_QUERY_MIN,
    AGE_MAX_LEN,
    EVENT_DESC_MAX,
    EVENT_DESC_MIN,
    EVENT_NAME_MAX,
    EVENT_NAME_MIN,
    PRICE_MAX_LEN,
)
from app.bot.dialogs.events.utils import CAPTION_LIMIT, build_event_text


async def get_event_name(
    dialog_manager: DialogManager,
    i18n: TranslatorRunner,
    **kwargs,
) -> dict[str, str]:
    return {
        "prompt": i18n.partner.event.name.prompt(
            min=EVENT_NAME_MIN, max=EVENT_NAME_MAX
        ),
    }


async def get_event_image(
    dialog_manager: DialogManager,
    i18n: TranslatorRunner,
    **kwargs,
) -> dict[str, str]:
    return {
        "prompt": i18n.partner.event.image.prompt(),
        "skip_button": i18n.partner.event.skip.button(),
    }


async def get_event_datetime(
    dialog_manager: DialogManager,
    i18n: TranslatorRunner,
    **kwargs,
) -> dict[str, str]:
    return {
        "prompt": i18n.partner.event.datetime.prompt(),
    }


async def get_event_address_query(
    dialog_manager: DialogManager,
    i18n: TranslatorRunner,
    **kwargs,
) -> dict[str, str]:
    return {
        "prompt": i18n.partner.event.address.prompt(min=ADDRESS_QUERY_MIN),
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
            min=EVENT_DESC_MIN, max=EVENT_DESC_MAX
        ),
    }


async def get_event_participation(
    dialog_manager: DialogManager,
    i18n: TranslatorRunner,
    **kwargs,
) -> dict[str, list[tuple[str, str]] | str]:
    choices = [
        (i18n.partner.event.participation.free(), "free"),
        (i18n.partner.event.participation.paid(), "paid"),
    ]
    return {
        "prompt": i18n.partner.event.participation.prompt(),
        "participation_choices": choices,
    }


async def get_event_price(
    dialog_manager: DialogManager,
    i18n: TranslatorRunner,
    **kwargs,
) -> dict[str, str]:
    return {
        "prompt": i18n.partner.event.price.prompt(max=PRICE_MAX_LEN),
    }


async def get_event_age_group(
    dialog_manager: DialogManager,
    i18n: TranslatorRunner,
    **kwargs,
) -> dict[str, str]:
    return {
        "prompt": i18n.partner.event.age.prompt(max=AGE_MAX_LEN),
        "skip_button": i18n.partner.event.skip.button(),
    }


async def get_event_notify(
    dialog_manager: DialogManager,
    i18n: TranslatorRunner,
    **kwargs,
) -> dict[str, list[tuple[str, str]] | str]:
    choices = [
        (i18n.partner.event.notify.yes(), "yes"),
        (i18n.partner.event.notify.no(), "no"),
    ]
    return {
        "prompt": i18n.partner.event.notify.prompt(),
        "notify_choices": choices,
    }


async def get_event_preview(
    dialog_manager: DialogManager,
    i18n: TranslatorRunner,
    **kwargs,
) -> dict[str, str | bool]:
    has_photo = bool(dialog_manager.dialog_data.get("photo_file_id"))
    max_length = CAPTION_LIMIT if has_photo else None
    preview_text, trimmed = build_event_text(
        dialog_manager.dialog_data,
        i18n,
        max_length=max_length,
    )

    lines = [i18n.partner.event.preview.title()]
    if has_photo:
        lines.append(i18n.partner.event.preview.photo.attached())
    if trimmed:
        lines.append(i18n.partner.event.preview.trimmed())
    lines.append("")
    lines.append(preview_text)

    return {
        "preview": "\n".join(lines).strip(),
        "publish_button": i18n.partner.event.publish.button(),
        "edit_name_button": i18n.partner.event.edit.name.button(),
        "edit_image_button": i18n.partner.event.edit.image.button(),
        "edit_datetime_button": i18n.partner.event.edit.datetime.button(),
        "edit_address_button": i18n.partner.event.edit.address.button(),
        "edit_description_button": i18n.partner.event.edit.description.button(),
        "edit_participation_button": i18n.partner.event.edit.participation.button(),
        "edit_price_button": i18n.partner.event.edit.price.button(),
        "edit_age_button": i18n.partner.event.edit.age.button(),
        "edit_notify_button": i18n.partner.event.edit.notify.button(),
        "is_paid": bool(dialog_manager.dialog_data.get("is_paid")),
    }
