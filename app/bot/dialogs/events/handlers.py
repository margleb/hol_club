import logging
from datetime import datetime

import aiohttp
from aiogram.types import CallbackQuery, Message, User
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.kbd import Button, Select
from fluentogram import TranslatorRunner

from app.bot.enums.roles import UserRole
from app.bot.states.events import EventsSG
from app.infrastructure.database.database.db import DB
from config.config import settings
from app.bot.dialogs.events.constants import (
    ADDRESS_QUERY_MIN,
    AGE_MAX_LEN,
    EVENT_DESC_MAX,
    EVENT_DESC_MIN,
    EVENT_NAME_MAX,
    EVENT_NAME_MIN,
    PRICE_MAX_LEN,
)
from app.bot.dialogs.events.utils import CAPTION_LIMIT, MESSAGE_LIMIT, build_event_text

logger = logging.getLogger(__name__)

GEOCODER_URL = "https://nominatim.openstreetmap.org/search"
GEOCODER_LIMIT = 5
GEOCODER_TIMEOUT = 7
GEOCODER_USER_AGENT = "hol_club_bot"


def _get_events_channel() -> str | None:
    return settings.get("events_channel")


async def _fetch_address_suggestions(
    query: str,
    locale: str | None,
) -> list[str]:
    params = {
        "q": query,
        "format": "json",
        "limit": GEOCODER_LIMIT,
    }
    if locale:
        params["accept-language"] = locale

    headers = {"User-Agent": GEOCODER_USER_AGENT}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                GEOCODER_URL,
                params=params,
                headers=headers,
                timeout=GEOCODER_TIMEOUT,
            ) as response:
                if response.status != 200:
                    return []
                data = await response.json()
    except Exception as exc:
        logger.warning("Geocoder request failed: %s", exc)
        return []

    if not isinstance(data, list):
        return []

    suggestions = []
    for item in data:
        display_name = item.get("display_name")
        if display_name:
            suggestions.append(display_name)
    return suggestions


def _is_edit_mode(dialog_manager: DialogManager) -> bool:
    return bool(dialog_manager.dialog_data.get("edit_mode"))


async def _return_to_preview(dialog_manager: DialogManager) -> None:
    dialog_manager.dialog_data.pop("edit_mode", None)
    await dialog_manager.switch_to(EventsSG.preview)


async def ensure_partner_access(_, dialog_manager: DialogManager) -> None:
    user: User | None = dialog_manager.middleware_data.get("event_from_user")
    db: DB | None = dialog_manager.middleware_data.get("db")
    i18n: TranslatorRunner | None = dialog_manager.middleware_data.get("i18n")

    dialog_manager.dialog_data.clear()

    if not user or not db or not i18n:
        return

    user_record = await db.users.get_user_record(user_id=user.id)
    if not user_record or user_record.role not in {UserRole.PARTNER, UserRole.ADMIN}:
        await dialog_manager.event.bot.send_message(
            user.id,
            i18n.partner.event.forbidden(),
        )
        if isinstance(dialog_manager.event, CallbackQuery):
            await dialog_manager.event.answer()
        await dialog_manager.done()


async def on_event_name_input(
    message: Message,
    widget=None,
    dialog_manager: DialogManager,
    i18n: TranslatorRunner,
) -> None:
    name = (message.text or "").strip()
    if not (EVENT_NAME_MIN <= len(name) <= EVENT_NAME_MAX):
        await message.answer(
            i18n.partner.event.name.invalid(min=EVENT_NAME_MIN, max=EVENT_NAME_MAX)
        )
        return

    dialog_manager.dialog_data["name"] = name
    if _is_edit_mode(dialog_manager):
        await _return_to_preview(dialog_manager)
        return
    await dialog_manager.switch_to(EventsSG.image)


async def on_event_photo_input(
    message: Message,
    widget=None,
    dialog_manager: DialogManager,
) -> None:
    if not message.photo:
        return
    dialog_manager.dialog_data["photo_file_id"] = message.photo[-1].file_id
    if _is_edit_mode(dialog_manager):
        await _return_to_preview(dialog_manager)
        return
    await dialog_manager.switch_to(EventsSG.datetime)


async def skip_event_photo(
    callback: CallbackQuery,
    button: Button,
    dialog_manager: DialogManager,
) -> None:
    dialog_manager.dialog_data["photo_file_id"] = None
    if _is_edit_mode(dialog_manager):
        await _return_to_preview(dialog_manager)
        return
    await dialog_manager.switch_to(EventsSG.datetime)


async def on_event_datetime_input(
    message: Message,
    widget=None,
    dialog_manager: DialogManager,
    i18n: TranslatorRunner,
) -> None:
    value = (message.text or "").strip()
    try:
        datetime.strptime(value, "%d.%m.%Y %H:%M")
    except ValueError:
        await message.answer(i18n.partner.event.datetime.invalid())
        return

    dialog_manager.dialog_data["datetime"] = value
    if _is_edit_mode(dialog_manager):
        await _return_to_preview(dialog_manager)
        return
    await dialog_manager.switch_to(EventsSG.address_query)


async def on_event_address_input(
    message: Message,
    widget=None,
    dialog_manager: DialogManager,
    i18n: TranslatorRunner,
) -> None:
    query = (message.text or "").strip()
    if len(query) < ADDRESS_QUERY_MIN:
        await message.answer(i18n.partner.event.address.short(min=ADDRESS_QUERY_MIN))
        return

    suggestions = await _fetch_address_suggestions(
        query, message.from_user.language_code
    )
    if not suggestions:
        await message.answer(i18n.partner.event.address.empty())
        return

    dialog_manager.dialog_data["address_suggestions"] = suggestions
    await dialog_manager.switch_to(EventsSG.address_select)


async def on_event_address_selected(
    callback: CallbackQuery,
    widget: Select,
    dialog_manager: DialogManager,
    item_id: str,
    i18n: TranslatorRunner,
) -> None:
    suggestions = dialog_manager.dialog_data.get("address_suggestions") or []
    try:
        address = suggestions[int(item_id)]
    except (ValueError, IndexError):
        await callback.answer(i18n.partner.event.address.invalid())
        return

    dialog_manager.dialog_data["address"] = address
    dialog_manager.dialog_data.pop("address_suggestions", None)

    if _is_edit_mode(dialog_manager):
        await _return_to_preview(dialog_manager)
        return
    await dialog_manager.switch_to(EventsSG.description)


async def back_to_address_query(
    callback: CallbackQuery,
    button: Button,
    dialog_manager: DialogManager,
) -> None:
    await dialog_manager.switch_to(EventsSG.address_query)


async def on_event_description_input(
    message: Message,
    widget=None,
    dialog_manager: DialogManager,
    i18n: TranslatorRunner,
) -> None:
    description = (message.text or "").strip()
    if not (EVENT_DESC_MIN <= len(description) <= EVENT_DESC_MAX):
        await message.answer(
            i18n.partner.event.description.invalid(
                min=EVENT_DESC_MIN, max=EVENT_DESC_MAX
            )
        )
        return

    dialog_manager.dialog_data["description"] = description
    if _is_edit_mode(dialog_manager):
        await _return_to_preview(dialog_manager)
        return
    await dialog_manager.switch_to(EventsSG.participation)


async def on_event_participation_selected(
    callback: CallbackQuery,
    widget: Select,
    dialog_manager: DialogManager,
    item_id: str,
) -> None:
    is_paid = item_id == "paid"
    dialog_manager.dialog_data["is_paid"] = is_paid

    if not is_paid:
        dialog_manager.dialog_data["price"] = None
        if _is_edit_mode(dialog_manager):
            await _return_to_preview(dialog_manager)
            return
        await dialog_manager.switch_to(EventsSG.age_group)
        return

    await dialog_manager.switch_to(EventsSG.price)


async def on_event_price_input(
    message: Message,
    widget=None,
    dialog_manager: DialogManager,
    i18n: TranslatorRunner,
) -> None:
    price = (message.text or "").strip()
    if not price or len(price) > PRICE_MAX_LEN:
        await message.answer(i18n.partner.event.price.invalid(max=PRICE_MAX_LEN))
        return

    dialog_manager.dialog_data["price"] = price
    if _is_edit_mode(dialog_manager):
        await _return_to_preview(dialog_manager)
        return
    await dialog_manager.switch_to(EventsSG.age_group)


async def on_event_age_input(
    message: Message,
    widget=None,
    dialog_manager: DialogManager,
    i18n: TranslatorRunner,
) -> None:
    age_group = (message.text or "").strip()
    if not age_group or len(age_group) > AGE_MAX_LEN:
        await message.answer(i18n.partner.event.age.invalid(max=AGE_MAX_LEN))
        return

    dialog_manager.dialog_data["age_group"] = age_group
    if _is_edit_mode(dialog_manager):
        await _return_to_preview(dialog_manager)
        return
    await dialog_manager.switch_to(EventsSG.notify)


async def skip_event_age(
    callback: CallbackQuery,
    button: Button,
    dialog_manager: DialogManager,
) -> None:
    dialog_manager.dialog_data["age_group"] = None
    if _is_edit_mode(dialog_manager):
        await _return_to_preview(dialog_manager)
        return
    await dialog_manager.switch_to(EventsSG.notify)


async def on_event_notify_selected(
    callback: CallbackQuery,
    widget: Select,
    dialog_manager: DialogManager,
    item_id: str,
) -> None:
    dialog_manager.dialog_data["notify_users"] = item_id == "yes"
    await _return_to_preview(dialog_manager)


async def edit_event_name(
    callback: CallbackQuery,
    button: Button,
    dialog_manager: DialogManager,
) -> None:
    dialog_manager.dialog_data["edit_mode"] = True
    await dialog_manager.switch_to(EventsSG.name)


async def edit_event_image(
    callback: CallbackQuery,
    button: Button,
    dialog_manager: DialogManager,
) -> None:
    dialog_manager.dialog_data["edit_mode"] = True
    await dialog_manager.switch_to(EventsSG.image)


async def edit_event_datetime(
    callback: CallbackQuery,
    button: Button,
    dialog_manager: DialogManager,
) -> None:
    dialog_manager.dialog_data["edit_mode"] = True
    await dialog_manager.switch_to(EventsSG.datetime)


async def edit_event_address(
    callback: CallbackQuery,
    button: Button,
    dialog_manager: DialogManager,
) -> None:
    dialog_manager.dialog_data["edit_mode"] = True
    await dialog_manager.switch_to(EventsSG.address_query)


async def edit_event_description(
    callback: CallbackQuery,
    button: Button,
    dialog_manager: DialogManager,
) -> None:
    dialog_manager.dialog_data["edit_mode"] = True
    await dialog_manager.switch_to(EventsSG.description)


async def edit_event_participation(
    callback: CallbackQuery,
    button: Button,
    dialog_manager: DialogManager,
) -> None:
    dialog_manager.dialog_data["edit_mode"] = True
    await dialog_manager.switch_to(EventsSG.participation)


async def edit_event_price(
    callback: CallbackQuery,
    button: Button,
    dialog_manager: DialogManager,
) -> None:
    dialog_manager.dialog_data["edit_mode"] = True
    await dialog_manager.switch_to(EventsSG.price)


async def edit_event_age(
    callback: CallbackQuery,
    button: Button,
    dialog_manager: DialogManager,
) -> None:
    dialog_manager.dialog_data["edit_mode"] = True
    await dialog_manager.switch_to(EventsSG.age_group)


async def edit_event_notify(
    callback: CallbackQuery,
    button: Button,
    dialog_manager: DialogManager,
) -> None:
    dialog_manager.dialog_data["edit_mode"] = True
    await dialog_manager.switch_to(EventsSG.notify)


async def _notify_users(
    *,
    db: DB,
    bot,
    i18n: TranslatorRunner,
    channel: str,
    event_name: str,
) -> int:
    user_ids = await db.users.get_active_user_ids()
    if not user_ids:
        return 0

    text = i18n.partner.event.notify.users(channel=channel, name=event_name)
    sent = 0
    for user_id in user_ids:
        try:
            await bot.send_message(user_id, text=text)
            sent += 1
        except Exception as exc:
            logger.info("Failed to notify user %s: %s", user_id, exc)
    return sent


async def publish_event(
    callback: CallbackQuery,
    button: Button,
    dialog_manager: DialogManager,
) -> None:
    i18n: TranslatorRunner = dialog_manager.middleware_data.get("i18n")
    db: DB | None = dialog_manager.middleware_data.get("db")
    channel = _get_events_channel()

    if not channel:
        await callback.answer(i18n.partner.event.channel.missing(), show_alert=True)
        return

    data = dialog_manager.dialog_data
    photo_id = data.get("photo_file_id")
    max_length = CAPTION_LIMIT if photo_id else MESSAGE_LIMIT
    text, _ = build_event_text(data, i18n, max_length=max_length)

    try:
        if photo_id:
            await callback.bot.send_photo(channel, photo=photo_id, caption=text)
        else:
            await callback.bot.send_message(channel, text=text)
    except Exception as exc:
        logger.warning("Failed to publish event: %s", exc)
        await callback.answer(i18n.partner.event.publish.failed(), show_alert=True)
        return

    message_text = i18n.partner.event.publish.success()
    if data.get("notify_users") and db:
        sent = await _notify_users(
            db=db,
            bot=callback.bot,
            i18n=i18n,
            channel=channel,
            event_name=data.get("name") or "",
        )
        message_text = f"{message_text}\n{i18n.partner.event.notify.sent(count=sent)}"

    await callback.message.answer(message_text)
    await dialog_manager.done()
