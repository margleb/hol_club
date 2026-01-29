import hashlib
import logging
import re
import secrets
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

from app.bot.enums.roles import UserRole
from app.bot.handlers.event_chats import (
    EVENT_CHAT_START_PREFIX,
    EVENT_JOIN_CHAT_CALLBACK,
    build_topic_message_link,
)
from app.bot.states.events import EventsSG
from app.infrastructure.database.database.db import DB
from config.config import settings
from app.bot.dialogs.events.utils import build_event_text, build_event_topic_name
from app.services.geocoders.geocoder import fetch_address_suggestions

logger = logging.getLogger(__name__)
_AGE_GROUP_RE = re.compile(r"^\s*(\d{1,2}\+|\d{1,2}\s*-\s*\d{1,2})\s*$")


def _is_valid_age_group(value: str) -> bool:
    match = _AGE_GROUP_RE.match(value)
    if not match:
        return False
    if "-" in value:
        parts = re.split(r"\s*-\s*", value.strip())
        try:
            start, end = (int(part) for part in parts)
        except ValueError:
            return False
        return start < end
    return True


def _get_events_channel() -> str | None:
    return settings.get("events_channel")


def _get_events_male_chat() -> str | None:
    return getattr(settings.chat_links, "male_chat_url", None)


def _get_events_female_chat() -> str | None:
    return getattr(settings.chat_links, "female_chat_url", None)


def _normalize_chat_target(chat_url: str | None) -> str | None:
    if not chat_url:
        return None
    value = chat_url.strip()
    if not value:
        return None
    if value.startswith("@"):
        return value
    if value.lstrip("-").isdigit():
        return value
    prefix = "https://t.me/"
    if value.startswith(prefix):
        slug = value[len(prefix):].split("?", 1)[0].strip("/")
        if slug.startswith("+") or slug.startswith("c/") or not slug:
            return None
        return f"@{slug}"
    return value


def _generate_attendance_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


async def _create_event_topic_message(
    *,
    bot,
    chat: str,
    topic_name: str,
    text: str,
    photo_id: str | None,
):
    topic = await bot.create_forum_topic(chat, name=topic_name)
    if photo_id:
        message = await bot.send_photo(
            chat,
            photo=photo_id,
            caption=text,
            message_thread_id=topic.message_thread_id,
        )
    else:
        message = await bot.send_message(
            chat,
            text=text,
            message_thread_id=topic.message_thread_id,
        )
    return topic, message


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
    price = (data or "").strip()
    normalized_price = price.replace(" ", "")
    if (
        not normalized_price
        or not normalized_price.isdigit()
        or int(normalized_price) > settings.events.price_max
    ):
        await message.answer(
            i18n.partner.event.price.invalid(
                max=settings.events.price_max,
            )
        )
        return

    dialog_manager.dialog_data["price"] = price
    dialog_manager.dialog_data["is_paid"] = True
    if _is_edit_mode(dialog_manager):
        await _return_to_preview(dialog_manager)
        return
    await dialog_manager.switch_to(EventsSG.age_group)


async def skip_event_price(
    callback: CallbackQuery,
    button: Button,
    dialog_manager: DialogManager,
) -> None:
    dialog_manager.dialog_data["price"] = None
    dialog_manager.dialog_data["is_paid"] = False
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
    if not age_group:
        await message.answer(
            i18n.partner.event.age.invalid()
        )
        return
    if not _is_valid_age_group(age_group):
        await message.answer(
            i18n.partner.event.age.invalid()
        )
        return

    dialog_manager.dialog_data["age_group"] = age_group
    if _is_edit_mode(dialog_manager):
        await _return_to_preview(dialog_manager)
        return
    await dialog_manager.switch_to(EventsSG.preview)


async def skip_event_age(
    callback: CallbackQuery,
    button: Button,
    dialog_manager: DialogManager,
) -> None:
    dialog_manager.dialog_data["age_group"] = None
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
            data.get("age_group") or "",
        ]
    )
    fingerprint = hashlib.sha256(fingerprint_source.encode("utf-8")).hexdigest()
    attendance_code = _generate_attendance_code()

    event_id = await db.events.create_event(
        partner_user_id=user.id,
        name=data.get("name") or "",
        event_datetime=data.get("datetime") or "",
        address=data.get("address") or "",
        description=data.get("description") or "",
        is_paid=bool(data.get("is_paid")),
        price=data.get("price"),
        age_group=data.get("age_group"),
        photo_file_id=photo_id,
        fingerprint=fingerprint,
        attendance_code=attendance_code,
    )
    if event_id is None:
        await callback.answer(
            i18n.partner.event.publish.already(),
            show_alert=True,
        )
        return

    male_chat = _normalize_chat_target(_get_events_male_chat())
    female_chat = _normalize_chat_target(_get_events_female_chat())
    if not male_chat or not female_chat:
        await db.events.delete_event(event_id=event_id)
        await callback.answer(i18n.partner.event.publish.failed(), show_alert=True)
        return

    event_name = data.get("name") or ""
    event_datetime = data.get("datetime") or ""
    topic_name = build_event_topic_name(event_datetime, event_name)
    try:
        male_topic, male_message = await _create_event_topic_message(
            bot=callback.bot,
            chat=male_chat,
            topic_name=topic_name,
            text=text,
            photo_id=photo_id,
        )
        female_topic, female_message = await _create_event_topic_message(
            bot=callback.bot,
            chat=female_chat,
            topic_name=topic_name,
            text=text,
            photo_id=photo_id,
        )
    except Exception as exc:
        logger.warning("Failed to publish event topics: %s", exc)
        await db.events.delete_event(event_id=event_id)
        await callback.answer(i18n.partner.event.publish.failed(), show_alert=True)
        return

    male_topic_link = build_topic_message_link(
        male_message.chat.id,
        male_topic.message_thread_id,
        male_message.message_id,
        male_message.chat.username,
    )
    female_topic_link = build_topic_message_link(
        female_message.chat.id,
        female_topic.message_thread_id,
        female_message.message_id,
        female_message.chat.username,
    )
    if not male_topic_link or not female_topic_link:
        await db.events.delete_event(event_id=event_id)
        await callback.answer(i18n.partner.event.publish.failed(), show_alert=True)
        return

    await db.events.mark_event_chat_topics(
        event_id=event_id,
        male_chat_id=male_message.chat.id,
        male_thread_id=male_topic.message_thread_id,
        male_message_id=male_message.message_id,
        male_chat_username=male_message.chat.username,
        female_chat_id=female_message.chat.id,
        female_thread_id=female_topic.message_thread_id,
        female_message_id=female_message.message_id,
        female_chat_username=female_message.chat.username,
    )

    bot_username = None
    try:
        bot_info = await callback.bot.get_me()
        bot_username = getattr(bot_info, "username", None)
    except Exception:
        bot_username = None
    start_link = None
    if bot_username:
        start_link = (
            f"https://t.me/{bot_username}?start={EVENT_CHAT_START_PREFIX}{event_id}"
        )

    join_button = None
    if start_link:
        join_button = InlineKeyboardButton(
            text=i18n.partner.event.join.chat.button(),
            url=start_link,
        )
    else:
        join_button = InlineKeyboardButton(
            text=i18n.partner.event.join.chat.button(),
            callback_data=f"{EVENT_JOIN_CHAT_CALLBACK}:{event_id}",
        )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[join_button]])

    try:
        if photo_id:
            channel_message = await callback.bot.send_photo(
                channel,
                photo=photo_id,
                caption=text,
                reply_markup=keyboard,
            )
        else:
            channel_message = await callback.bot.send_message(
                channel,
                text=text,
                reply_markup=keyboard,
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
