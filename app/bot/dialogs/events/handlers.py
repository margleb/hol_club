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

GEOCODER_URL = settings.get("geocoder_url")
GEOCODER_LIMIT = int(settings.get("geocoder_limit") or 5)
GEOCODER_TIMEOUT = float(settings.get("geocoder_timeout") or 7)
GEOCODER_USER_AGENT = settings.get("geocoder_user_agent") or "hol_club_bot"
GEOCODER_REGIONS = settings.get("geocoder_regions") or {}
GEOCODER_BOUNDED = settings.get("geocoder_bounded")


def _get_events_channel() -> str | None:
    return settings.get("events_channel")


def _normalize_viewbox(viewbox: object) -> str | None:
    if isinstance(viewbox, (list, tuple)):
        return ",".join(str(value) for value in viewbox)
    if viewbox is None:
        return None
    viewbox = str(viewbox).strip()
    return viewbox or None


def _build_suggestion(item: dict) -> dict[str, str | bool] | None:
    display_name = item.get("display_name")
    if not display_name:
        return None

    address = item.get("address")
    has_house_number = bool(
        isinstance(address, dict) and address.get("house_number")
    )
    return {
        "display_name": display_name,
        "has_house_number": has_house_number,
    }


def _add_suggestion(
    item: dict,
    suggestions: list[dict[str, str | bool]],
    index_by_name: dict[str, int],
) -> None:
    suggestion = _build_suggestion(item)
    if not suggestion:
        return

    display_name = suggestion["display_name"]
    existing_index = index_by_name.get(display_name)
    if existing_index is None:
        suggestions.append(suggestion)
        index_by_name[display_name] = len(suggestions) - 1
        return

    if suggestion["has_house_number"] and not suggestions[existing_index][
        "has_house_number"
    ]:
        suggestions[existing_index]["has_house_number"] = True


def _get_geocoder_viewboxes() -> list[str]:
    if not GEOCODER_REGIONS:
        return []

    region_map = GEOCODER_REGIONS
    if isinstance(region_map, dict):
        candidates = region_map.values()
    elif isinstance(region_map, (list, tuple)):
        candidates = region_map
    else:
        candidates = [region_map]

    viewboxes = []
    for candidate in candidates:
        viewbox = _normalize_viewbox(candidate)
        if viewbox:
            viewboxes.append(viewbox)

    if not viewboxes:
        logger.warning("Geocoder regions are configured but no valid viewboxes found")
    return viewboxes


async def _request_geocoder(
    session: aiohttp.ClientSession,
    params: dict,
    headers: dict[str, str],
) -> list[dict]:
    try:
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
    return data


async def _fetch_address_suggestions(
    query: str,
    locale: str | None,
) -> list[dict[str, str | bool]]:
    if not GEOCODER_URL:
        logger.warning("Geocoder URL is not set")
        return []

    params = {
        "q": query,
        "format": "json",
        "limit": GEOCODER_LIMIT,
        "addressdetails": 1,
    }
    if locale:
        params["accept-language"] = locale

    headers = {"User-Agent": GEOCODER_USER_AGENT}

    suggestions: list[dict[str, str | bool]] = []
    index_by_name: dict[str, int] = {}
    viewboxes = _get_geocoder_viewboxes()
    async with aiohttp.ClientSession() as session:
        if viewboxes:
            for viewbox in viewboxes:
                regional_params = dict(params)
                regional_params["viewbox"] = viewbox
                if GEOCODER_BOUNDED:
                    regional_params["bounded"] = 1
                data = await _request_geocoder(session, regional_params, headers)
                for item in data:
                    _add_suggestion(item, suggestions, index_by_name)
                    if len(suggestions) >= GEOCODER_LIMIT:
                        return suggestions
        else:
            data = await _request_geocoder(session, params, headers)
            for item in data:
                _add_suggestion(item, suggestions, index_by_name)
                if len(suggestions) >= GEOCODER_LIMIT:
                    return suggestions

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
    widget,
    dialog_manager: DialogManager,
    data: str,
) -> None:
    i18n: TranslatorRunner = dialog_manager.middleware_data.get("i18n")
    name = (data or "").strip()
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
    widget,
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
    widget,
    dialog_manager: DialogManager,
    data: str,
) -> None:
    i18n: TranslatorRunner = dialog_manager.middleware_data.get("i18n")
    value = (data or "").strip()
    try:
        event_datetime = datetime.strptime(value, "%Y.%m.%d %H:%M")
    except ValueError:
        await message.answer(i18n.partner.event.datetime.invalid())
        return

    if event_datetime <= datetime.now():
        await message.answer(i18n.partner.event.datetime.past())
        return

    dialog_manager.dialog_data["datetime"] = value
    if _is_edit_mode(dialog_manager):
        await _return_to_preview(dialog_manager)
        return
    await dialog_manager.switch_to(EventsSG.address_query)


async def on_event_address_input(
    message: Message,
    widget,
    dialog_manager: DialogManager,
    data: str,
) -> None:
    i18n: TranslatorRunner = dialog_manager.middleware_data.get("i18n")
    query = (data or "").strip()
    if len(query) < ADDRESS_QUERY_MIN:
        await message.answer(i18n.partner.event.address.short(min=ADDRESS_QUERY_MIN))
        return
    if not any(char.isdigit() for char in query):
        await message.answer(i18n.partner.event.address.house.missing())
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
) -> None:
    i18n: TranslatorRunner = dialog_manager.middleware_data.get("i18n")
    suggestions = dialog_manager.dialog_data.get("address_suggestions") or []
    try:
        selected = suggestions[int(item_id)]
    except (ValueError, IndexError):
        await callback.answer(i18n.partner.event.address.invalid())
        return

    if isinstance(selected, dict):
        address = selected.get("display_name")
        has_house_number = bool(selected.get("has_house_number"))
    else:
        address = str(selected)
        has_house_number = True

    if not address:
        await callback.answer(i18n.partner.event.address.invalid())
        return

    if not has_house_number:
        await callback.answer(
            i18n.partner.event.address.house.missing(),
            show_alert=True,
        )
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
    widget,
    dialog_manager: DialogManager,
    data: str,
) -> None:
    i18n: TranslatorRunner = dialog_manager.middleware_data.get("i18n")
    description = (data or "").strip()
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
    widget,
    dialog_manager: DialogManager,
    data: str,
) -> None:
    i18n: TranslatorRunner = dialog_manager.middleware_data.get("i18n")
    price = (data or "").strip()
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
    widget,
    dialog_manager: DialogManager,
    data: str,
) -> None:
    i18n: TranslatorRunner = dialog_manager.middleware_data.get("i18n")
    age_group = (data or "").strip()
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
