import hashlib
import logging
from datetime import datetime

from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    User,
)
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.kbd import Button, Select
from fluentogram import TranslatorRunner

from app.bot.dialogs.events.constants import EVENT_AGE_GROUP_ALL, EVENT_AGE_GROUPS
from app.bot.enums.roles import UserRole
from app.bot.states.events import EventsSG
from app.infrastructure.database.database.db import DB
from config.config import settings
from app.bot.dialogs.events.utils import build_event_text
from app.services.geocoders.geocoder import fetch_address_suggestions

logger = logging.getLogger(__name__)
EVENT_JOIN_CHAT_CALLBACK = "event_join_chat"
EVENT_CHAT_START_PREFIX = "event_chat_"


def _get_events_channel() -> str | None:
    return settings.get("events_channel")


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
    if not user_record or user_record.role != UserRole.PARTNER:
        await dialog_manager.event.bot.send_message(
            user.id,
            i18n.partner.event.forbidden(),
        )
        if isinstance(dialog_manager.event, CallbackQuery):
            await dialog_manager.event.answer()
        await dialog_manager.done()
        return



async def on_event_name_input(
    message: Message,
    widget,
    dialog_manager: DialogManager,
    data: str,
) -> None:
    i18n: TranslatorRunner = dialog_manager.middleware_data.get("i18n")
    name = (data or "").strip()
    if not (
        settings.events.event_name_min
        <= len(name)
        <= settings.events.event_name_max
    ):
        await message.answer(
            i18n.partner.event.name.invalid(
                min=settings.events.event_name_min,
                max=settings.events.event_name_max,
            )
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
    if not any(char.isdigit() for char in query):
        await message.answer(i18n.partner.event.address.house.missing())
        return

    suggestions = await fetch_address_suggestions(
        query,
        message.from_user.language_code,
        settings,
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


async def back_from_event_name(
    callback: CallbackQuery,
    button: Button,
    dialog_manager: DialogManager,
) -> None:
    if _is_edit_mode(dialog_manager):
        await _return_to_preview(dialog_manager)
        return
    await dialog_manager.done()


async def back_from_event_image(
    callback: CallbackQuery,
    button: Button,
    dialog_manager: DialogManager,
) -> None:
    if _is_edit_mode(dialog_manager):
        await _return_to_preview(dialog_manager)
        return
    await dialog_manager.switch_to(EventsSG.name)


async def back_from_event_datetime(
    callback: CallbackQuery,
    button: Button,
    dialog_manager: DialogManager,
) -> None:
    if _is_edit_mode(dialog_manager):
        await _return_to_preview(dialog_manager)
        return
    await dialog_manager.switch_to(EventsSG.image)


async def back_from_event_address_query(
    callback: CallbackQuery,
    button: Button,
    dialog_manager: DialogManager,
) -> None:
    if _is_edit_mode(dialog_manager):
        await _return_to_preview(dialog_manager)
        return
    await dialog_manager.switch_to(EventsSG.datetime)


async def back_from_event_description(
    callback: CallbackQuery,
    button: Button,
    dialog_manager: DialogManager,
) -> None:
    if _is_edit_mode(dialog_manager):
        await _return_to_preview(dialog_manager)
        return
    await dialog_manager.switch_to(EventsSG.address_query)


async def back_from_event_price(
    callback: CallbackQuery,
    button: Button,
    dialog_manager: DialogManager,
) -> None:
    if _is_edit_mode(dialog_manager):
        await _return_to_preview(dialog_manager)
        return
    await dialog_manager.switch_to(EventsSG.description)


async def back_from_event_age_group(
    callback: CallbackQuery,
    button: Button,
    dialog_manager: DialogManager,
) -> None:
    if _is_edit_mode(dialog_manager):
        await _return_to_preview(dialog_manager)
        return
    await dialog_manager.switch_to(EventsSG.price)




async def back_from_event_preview(
    callback: CallbackQuery,
    button: Button,
    dialog_manager: DialogManager,
) -> None:
    await dialog_manager.switch_to(EventsSG.age_group)


async def on_event_description_input(
    message: Message,
    widget,
    dialog_manager: DialogManager,
    data: str,
) -> None:
    i18n: TranslatorRunner = dialog_manager.middleware_data.get("i18n")
    description = (data or "").strip()
    if not (
        settings.events.event_desc_min
        <= len(description)
        <= settings.events.event_desc_max
    ):
        await message.answer(
            i18n.partner.event.description.invalid(
                min=settings.events.event_desc_min,
                max=settings.events.event_desc_max,
            )
        )
        return

    dialog_manager.dialog_data["description"] = description
    if _is_edit_mode(dialog_manager):
        await _return_to_preview(dialog_manager)
        return
    await dialog_manager.switch_to(EventsSG.price)


async def on_event_price_input(
    message: Message,
    widget,
    dialog_manager: DialogManager,
    data: str,
) -> None:
    i18n: TranslatorRunner = dialog_manager.middleware_data.get("i18n")
    db: DB | None = dialog_manager.middleware_data.get("db")
    price = (data or "").strip()
    normalized_price = price.replace(" ", "")
    if not normalized_price or not normalized_price.isdigit():
        await message.answer(
            i18n.partner.event.price.invalid(
                max=settings.events.price_max,
            )
        )
        return

    base_price = int(normalized_price)
    if (
        base_price > settings.events.price_max
    ):
        await message.answer(
            i18n.partner.event.price.invalid(
                max=settings.events.price_max,
            )
        )
        return

    commission_percent = 0
    if db and message.from_user:
        partner_record = await db.users.get_user_record(user_id=message.from_user.id)
        if partner_record and partner_record.role == UserRole.PARTNER:
            commission_percent = int(partner_record.commission_percent or 0)

    commission_amount = max(0, int(round(base_price * commission_percent / 100)))
    final_price = base_price + commission_amount

    dialog_manager.dialog_data["price"] = str(final_price)
    dialog_manager.dialog_data["is_paid"] = True
    dialog_manager.dialog_data["prepay_percent"] = None
    dialog_manager.dialog_data["prepay_fixed_free"] = commission_amount
    if _is_edit_mode(dialog_manager):
        await _return_to_preview(dialog_manager)
        return
    await dialog_manager.switch_to(EventsSG.age_group)

async def on_event_age_selected(
    callback: CallbackQuery,
    widget: Select,
    dialog_manager: DialogManager,
    item_id: str,
) -> None:
    i18n: TranslatorRunner = dialog_manager.middleware_data.get("i18n")
    if item_id not in EVENT_AGE_GROUPS:
        await callback.answer(i18n.partner.event.age.invalid(), show_alert=True)
        return

    dialog_manager.dialog_data["age_group"] = item_id
    await callback.answer()
    if _is_edit_mode(dialog_manager):
        await _return_to_preview(dialog_manager)
        return
    await dialog_manager.switch_to(EventsSG.preview)

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


def _build_channel_post_link(chat, message_id: int) -> str | None:
    username = getattr(chat, "username", None)
    if username:
        return f"https://t.me/{username}/{message_id}"
    chat_id = getattr(chat, "id", None)
    if isinstance(chat_id, int):
        chat_id_str = str(chat_id)
        if chat_id_str.startswith("-100"):
            channel_id = chat_id_str[4:]
        else:
            channel_id = str(abs(chat_id))
        return f"https://t.me/c/{channel_id}/{message_id}"
    return None


def _build_channel_post_link_by_id(
    channel_id: int | None,
    message_id: int | None,
) -> str | None:
    if not channel_id or not message_id:
        return None
    chat_id_str = str(channel_id)
    if chat_id_str.startswith("-100"):
        channel_id_str = chat_id_str[4:]
    else:
        channel_id_str = str(abs(channel_id))
    return f"https://t.me/c/{channel_id_str}/{message_id}"


async def _build_event_join_start_link(
    *,
    bot,
    event_id: int | None,
) -> str | None:
    if not event_id:
        return None
    try:
        me = await bot.get_me()
    except Exception as exc:
        logger.warning("Failed to get bot username for event registration link: %s", exc)
        return None
    username = getattr(me, "username", None)
    if not username:
        return None
    return f"https://t.me/{username}?start={EVENT_CHAT_START_PREFIX}{event_id}"


async def _send_event_announcement_to_user(
    *,
    bot,
    i18n: TranslatorRunner,
    user_id: int,
    event_payload: dict[str, object],
) -> None:
    event_text = build_event_text(
        {
            "name": event_payload.get("name"),
            "datetime": event_payload.get("event_datetime"),
            "address": event_payload.get("address"),
            "description": event_payload.get("description"),
            "is_paid": event_payload.get("is_paid"),
            "price": event_payload.get("price"),
            "age_group": event_payload.get("age_group"),
        },
        i18n,
    )
    post_url = _build_channel_post_link_by_id(
        event_payload.get("channel_id"),
        event_payload.get("channel_message_id"),
    )
    event_id = event_payload.get("id")
    keyboard_rows = []
    if isinstance(event_id, int):
        keyboard_rows.append(
            [
                InlineKeyboardButton(
                    text=i18n.partner.event.join.chat.button(),
                    callback_data=f"{EVENT_JOIN_CHAT_CALLBACK}:{event_id}",
                )
            ]
        )
    if post_url:
        keyboard_rows.append(
            [
                InlineKeyboardButton(
                    text=i18n.partner.event.view.post.button(),
                    url=post_url,
                )
            ]
        )
    keyboard = (
        InlineKeyboardMarkup(inline_keyboard=keyboard_rows)
        if keyboard_rows
        else None
    )
    photo_id = event_payload.get("photo_file_id")
    if photo_id:
        await bot.send_photo(
            user_id,
            photo=photo_id,
            caption=event_text,
            reply_markup=keyboard,
        )
    else:
        await bot.send_message(
            user_id,
            text=event_text,
            reply_markup=keyboard,
        )


async def _broadcast_event_announcement(
    *,
    bot,
    i18n: TranslatorRunner,
    db: DB,
    event_payload: dict[str, object],
) -> None:
    target_age_group = str(event_payload.get("age_group") or "").strip()
    send_to_all = not target_age_group or target_age_group == EVENT_AGE_GROUP_ALL
    user_profiles = await db.users.get_active_user_profiles_by_role(role=UserRole.USER)
    for user_id, _gender, user_age_group in user_profiles:
        if not send_to_all and user_age_group != target_age_group:
            continue
        try:
            await _send_event_announcement_to_user(
                bot=bot,
                i18n=i18n,
                user_id=user_id,
                event_payload=event_payload,
            )
        except Exception as exc:
            logger.warning(
                "Failed to send event announcement to user_id=%s: %s",
                user_id,
                exc,
            )


async def publish_event(
    callback: CallbackQuery,
    button: Button,
    dialog_manager: DialogManager,
) -> None:
    i18n: TranslatorRunner = dialog_manager.middleware_data.get("i18n")
    db: DB | None = dialog_manager.middleware_data.get("db")
    user: User | None = dialog_manager.middleware_data.get("event_from_user")
    channel = _get_events_channel()

    if not channel:
        await callback.answer(i18n.partner.event.channel.missing(), show_alert=True)
        return

    if not db or not user:
        await callback.answer(i18n.partner.event.publish.failed(), show_alert=True)
        return

    data = dialog_manager.dialog_data
    photo_id = data.get("photo_file_id")
    text = build_event_text(data, i18n)

    fingerprint_source = "\n".join(
        [
            str(user.id),
            data.get("name") or "",
            data.get("datetime") or "",
            data.get("address") or "",
            data.get("description") or "",
            "1" if data.get("is_paid") else "0",
            data.get("price") or "",
            str(data.get("prepay_percent") or ""),
            str(data.get("prepay_fixed_free") or ""),
            data.get("age_group") or "",
        ]
    )
    fingerprint = hashlib.sha256(fingerprint_source.encode("utf-8")).hexdigest()
    event_id = await db.events.create_event(
        partner_user_id=user.id,
        name=data.get("name") or "",
        event_datetime=data.get("datetime") or "",
        address=data.get("address") or "",
        description=data.get("description") or "",
        is_paid=bool(data.get("is_paid")),
        price=data.get("price"),
        prepay_percent=data.get("prepay_percent"),
        prepay_fixed_free=data.get("prepay_fixed_free"),
        age_group=data.get("age_group"),
        photo_file_id=photo_id,
        fingerprint=fingerprint,
    )
    if event_id is None:
        await callback.answer(
            i18n.partner.event.publish.already(),
            show_alert=True,
        )
        return

    join_url = await _build_event_join_start_link(
        bot=callback.bot,
        event_id=event_id,
    )
    channel_keyboard = None
    if join_url:
        channel_keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=i18n.partner.event.join.chat.button(),
                        url=join_url,
                    )
                ]
            ]
        )

    try:
        if photo_id:
            channel_message = await callback.bot.send_photo(
                channel,
                photo=photo_id,
                caption=text,
                reply_markup=channel_keyboard,
            )
        else:
            channel_message = await callback.bot.send_message(
                channel,
                text=text,
                reply_markup=channel_keyboard,
            )
    except Exception as exc:
        logger.warning("Failed to publish event: %s", exc)
        await db.events.delete_event(event_id=event_id)
        await callback.answer(i18n.partner.event.publish.failed(), show_alert=True)
        return

    await db.events.mark_event_published(
        event_id=event_id,
        channel_id=channel_message.chat.id,
        channel_message_id=channel_message.message_id,
    )

    event_payload = {
        "id": event_id,
        "name": data.get("name") or "",
        "event_datetime": data.get("datetime") or "",
        "address": data.get("address") or "",
        "description": data.get("description") or "",
        "is_paid": bool(data.get("is_paid")),
        "price": data.get("price"),
        "age_group": data.get("age_group"),
        "photo_file_id": photo_id,
        "channel_id": channel_message.chat.id,
        "channel_message_id": channel_message.message_id,
    }
    await _broadcast_event_announcement(
        bot=callback.bot,
        i18n=i18n,
        db=db,
        event_payload=event_payload,
    )

    post_link = _build_channel_post_link(
        channel_message.chat,
        channel_message.message_id,
    )
    message_text = i18n.partner.event.publish.success()
    partner_keyboard = None
    if post_link:
        partner_keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=i18n.partner.event.view.post.button(),
                        url=post_link,
                    )
                ]
            ]
        )

    await callback.message.answer(message_text, reply_markup=partner_keyboard)
    await dialog_manager.done()
