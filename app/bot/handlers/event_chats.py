from aiogram import Router
from urllib.parse import unquote

from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from fluentogram import TranslatorRunner

from app.bot.dialogs.general_registration.getters import AGE_GROUPS
from app.bot.dialogs.events.utils import build_event_text
from app.bot.enums.roles import UserRole
from app.infrastructure.database.database.db import DB

event_chats_router = Router()

EVENT_JOIN_CHAT_CALLBACK = "event_join_chat"
EVENT_JOIN_CHAT_GENDER_CALLBACK = "event_join_chat_gender"
EVENT_JOIN_CHAT_AGE_CALLBACK = "event_join_chat_age"
EVENT_CHAT_START_PREFIX = "event_chat_"


def _parse_callback_parts(
    data: str | None,
    prefix: str,
    expected_parts: int,
) -> list[str] | None:
    if not data or not data.startswith(prefix):
        return None
    parts = data.split(":")
    if len(parts) not in {expected_parts, expected_parts + 1}:
        return None
    return parts


def build_gender_keyboard(
    i18n: TranslatorRunner,
    event_id: int,
    *,
    announce: bool = False,
) -> InlineKeyboardMarkup:
    suffix = ":announce" if announce else ""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=i18n.general.registration.gender.male(),
                    callback_data=(
                        f"{EVENT_JOIN_CHAT_GENDER_CALLBACK}:{event_id}:male{suffix}"
                    ),
                )
            ],
            [
                InlineKeyboardButton(
                    text=i18n.general.registration.gender.female(),
                    callback_data=(
                        f"{EVENT_JOIN_CHAT_GENDER_CALLBACK}:{event_id}:female{suffix}"
                    ),
                )
            ],
        ]
    )


def build_age_keyboard(
    i18n: TranslatorRunner,
    event_id: int,
    *,
    announce: bool = False,
) -> InlineKeyboardMarkup:
    suffix = ":announce" if announce else ""
    rows = []
    for age_group in AGE_GROUPS:
        rows.append(
            [
                InlineKeyboardButton(
                    text=i18n.general.registration.age.group(range=age_group),
                    callback_data=(
                        f"{EVENT_JOIN_CHAT_AGE_CALLBACK}:{event_id}:{age_group}{suffix}"
                    ),
                )
            ]
        )
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def _ensure_user_record(
    *,
    db: DB,
    user_id: int,
    username: str | None,
    language: str | None,
) -> None:
    record = await db.users.get_user_record(user_id=user_id)
    if record is None:
        await db.users.add(
            user_id=user_id,
            username=username,
            language=language or "en",
            role=UserRole.USER,
        )


async def _send_chat_link_message(
    *,
    message: Message,
    i18n: TranslatorRunner,
    topic_link: str,
) -> None:
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=i18n.partner.event.join.chat.button(),
                    url=topic_link,
                )
            ]
        ]
    )
    text = "\n\n".join(
        [
            i18n.partner.event.join.chat.text(),
            i18n.partner.event.join.chat.hint(),
        ]
    )
    await message.answer(text, reply_markup=keyboard)


def parse_event_chat_start_payload(message_text: str | None) -> int | None:
    if not message_text:
        return None
    text = message_text.strip()
    payload = None
    if " " in text:
        _, payload = text.split(maxsplit=1)
    elif "?" in text:
        _, payload = text.split("?", 1)
    if not payload:
        return None
    payload = unquote(payload.strip())
    if payload.startswith("start="):
        payload = payload.split("=", 1)[1]
    if not payload.startswith(EVENT_CHAT_START_PREFIX):
        return None
    raw_event_id = payload[len(EVENT_CHAT_START_PREFIX):]
    if not raw_event_id.isdigit():
        return None
    return int(raw_event_id)


def _build_channel_post_link(
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


def build_topic_message_link(
    chat_id: int | None,
    thread_id: int | None,
    message_id: int | None,
    chat_username: str | None = None,
) -> str | None:
    if not thread_id or not message_id:
        return None
    if chat_username:
        username = chat_username.lstrip("@")
        if username:
            return (
                f"https://t.me/{username}/{message_id}?thread={thread_id}"
            )
    if not chat_id:
        return None
    chat_id_str = str(chat_id)
    if chat_id_str.startswith("-100"):
        chat_id_str = chat_id_str[4:]
    else:
        chat_id_str = str(abs(chat_id))
    return f"https://t.me/c/{chat_id_str}/{message_id}?thread={thread_id}"


def _get_event_topic_link(event, gender: str | None) -> str | None:
    if gender == "female":
        return build_topic_message_link(
            event.female_chat_id,
            event.female_thread_id,
            event.female_message_id,
            event.female_chat_username,
        )
    if gender == "male":
        return build_topic_message_link(
            event.male_chat_id,
            event.male_thread_id,
            event.male_message_id,
            event.male_chat_username,
        )
    return None


async def _send_event_announcement(
    *,
    message: Message,
    i18n: TranslatorRunner,
    event,
    topic_link: str,
) -> None:
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
    keyboard_rows = []
    if post_url:
        keyboard_rows.append(
            [
                InlineKeyboardButton(
                    text=i18n.partner.event.view.post.button(),
                    url=post_url,
                )
            ]
        )
    keyboard_rows.append(
        [
            InlineKeyboardButton(
                text=i18n.partner.event.join.chat.button(),
                url=topic_link,
            )
        ]
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_rows)
    if event.photo_file_id:
        await message.answer_photo(
            event.photo_file_id,
            caption=event_text,
            reply_markup=keyboard,
        )
    else:
        await message.answer(event_text, reply_markup=keyboard)


async def handle_event_chat_start(
    *,
    message: Message,
    i18n: TranslatorRunner,
    db: DB,
    event_id: int,
) -> None:
    user = message.from_user
    if not user:
        return

    await _ensure_user_record(
        db=db,
        user_id=user.id,
        username=user.username,
        language=user.language_code,
    )
    event = await db.events.get_event_by_id(event_id=event_id)
    if event is None:
        await message.answer(i18n.partner.event.join.chat.missing())
        return

    user_record = await db.users.get_user_record(user_id=user.id)
    gender = user_record.gender if user_record else None
    age_group = user_record.age_group if user_record else None

    if not gender:
        await message.answer(
            i18n.general.registration.gender.prompt(),
            reply_markup=build_gender_keyboard(i18n, event_id),
        )
        return
    if not age_group:
        await message.answer(
            i18n.general.registration.age.prompt(),
            reply_markup=build_age_keyboard(i18n, event_id),
        )
        return

    topic_link = _get_event_topic_link(event, gender)
    if not topic_link:
        await message.answer(i18n.partner.event.join.chat.missing())
        return
    await _send_chat_link_message(
        message=message,
        i18n=i18n,
        topic_link=topic_link,
    )


@event_chats_router.callback_query(
    lambda callback: callback.data
    and callback.data.startswith(f"{EVENT_JOIN_CHAT_CALLBACK}:")
)
async def process_event_join_chat(
    callback: CallbackQuery,
    i18n: TranslatorRunner,
    db: DB,
) -> None:
    parts = _parse_callback_parts(callback.data, EVENT_JOIN_CHAT_CALLBACK, 2)
    if not parts:
        await callback.answer(i18n.partner.event.join.chat.missing())
        return
    try:
        event_id = int(parts[1])
    except ValueError:
        await callback.answer(i18n.partner.event.join.chat.missing())
        return

    user = callback.from_user
    if not user:
        return

    await _ensure_user_record(
        db=db,
        user_id=user.id,
        username=user.username,
        language=user.language_code,
    )

    event = await db.events.get_event_by_id(event_id=event_id)
    if event is None:
        await callback.answer(i18n.partner.event.join.chat.missing())
        return

    user_record = await db.users.get_user_record(user_id=user.id)
    gender = user_record.gender if user_record else None
    age_group = user_record.age_group if user_record else None

    if not gender:
        if callback.message:
            await callback.message.answer(
                i18n.general.registration.gender.prompt(),
                reply_markup=build_gender_keyboard(i18n, event_id),
            )
        await callback.answer()
        return

    if not age_group:
        if callback.message:
            await callback.message.answer(
                i18n.general.registration.age.prompt(),
                reply_markup=build_age_keyboard(i18n, event_id),
            )
        await callback.answer()
        return

    topic_link = _get_event_topic_link(event, gender)
    if not topic_link:
        await callback.answer(i18n.partner.event.join.chat.missing())
        return

    if callback.message:
        await _send_chat_link_message(
            message=callback.message,
            i18n=i18n,
            topic_link=topic_link,
        )
    await callback.answer()


@event_chats_router.callback_query(
    lambda callback: callback.data
    and callback.data.startswith(f"{EVENT_JOIN_CHAT_GENDER_CALLBACK}:")
)
async def process_event_join_chat_gender(
    callback: CallbackQuery,
    i18n: TranslatorRunner,
    db: DB,
) -> None:
    parts = _parse_callback_parts(callback.data, EVENT_JOIN_CHAT_GENDER_CALLBACK, 3)
    if not parts:
        await callback.answer(i18n.partner.event.join.chat.missing())
        return
    try:
        event_id = int(parts[1])
    except ValueError:
        await callback.answer(i18n.partner.event.join.chat.missing())
        return
    gender = parts[2]
    announce = len(parts) == 4 and parts[3] == "announce"
    if gender not in {"male", "female"}:
        await callback.answer(i18n.partner.event.join.chat.missing())
        return

    user = callback.from_user
    if not user:
        return

    await _ensure_user_record(
        db=db,
        user_id=user.id,
        username=user.username,
        language=user.language_code,
    )
    user_record = await db.users.get_user_record(user_id=user.id)
    age_group = user_record.age_group if user_record else None

    await db.users.update_profile(
        user_id=user.id,
        gender=gender,
        age_group=age_group,
    )

    if not age_group:
        if callback.message:
            await callback.message.answer(
                i18n.general.registration.age.prompt(),
                reply_markup=build_age_keyboard(i18n, event_id, announce=announce),
            )
        await callback.answer()
        return

    event = await db.events.get_event_by_id(event_id=event_id)
    if event is None:
        await callback.answer(i18n.partner.event.join.chat.missing())
        return

    topic_link = _get_event_topic_link(event, gender)
    if not topic_link:
        await callback.answer(i18n.partner.event.join.chat.missing())
        return

    if announce and callback.message:
        await _send_event_announcement(
            message=callback.message,
            i18n=i18n,
            event=event,
            topic_link=topic_link,
        )
    elif callback.message:
        await _send_chat_link_message(
            message=callback.message,
            i18n=i18n,
            topic_link=topic_link,
        )
    await callback.answer()


@event_chats_router.callback_query(
    lambda callback: callback.data
    and callback.data.startswith(f"{EVENT_JOIN_CHAT_AGE_CALLBACK}:")
)
async def process_event_join_chat_age(
    callback: CallbackQuery,
    i18n: TranslatorRunner,
    db: DB,
) -> None:
    parts = _parse_callback_parts(callback.data, EVENT_JOIN_CHAT_AGE_CALLBACK, 3)
    if not parts:
        await callback.answer(i18n.partner.event.join.chat.missing())
        return
    try:
        event_id = int(parts[1])
    except ValueError:
        await callback.answer(i18n.partner.event.join.chat.missing())
        return
    age_group = parts[2]
    announce = len(parts) == 4 and parts[3] == "announce"
    if age_group not in AGE_GROUPS:
        await callback.answer(i18n.partner.event.join.chat.missing())
        return

    user = callback.from_user
    if not user:
        return

    await _ensure_user_record(
        db=db,
        user_id=user.id,
        username=user.username,
        language=user.language_code,
    )
    user_record = await db.users.get_user_record(user_id=user.id)
    gender = user_record.gender if user_record else None

    await db.users.update_profile(
        user_id=user.id,
        gender=gender,
        age_group=age_group,
    )

    if not gender:
        if callback.message:
            await callback.message.answer(
                i18n.general.registration.gender.prompt(),
                reply_markup=build_gender_keyboard(i18n, event_id, announce=announce),
            )
        await callback.answer()
        return

    event = await db.events.get_event_by_id(event_id=event_id)
    if event is None:
        await callback.answer(i18n.partner.event.join.chat.missing())
        return

    topic_link = _get_event_topic_link(event, gender)
    if not topic_link:
        await callback.answer(i18n.partner.event.join.chat.missing())
        return

    if announce and callback.message:
        await _send_event_announcement(
            message=callback.message,
            i18n=i18n,
            event=event,
            topic_link=topic_link,
        )
    elif callback.message:
        await _send_chat_link_message(
            message=callback.message,
            i18n=i18n,
            topic_link=topic_link,
        )
    await callback.answer()
