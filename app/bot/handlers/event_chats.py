import os

from aiogram import Router
from aiogram.fsm.context import FSMContext
from urllib.parse import unquote

from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from fluentogram import TranslatorRunner

from app.bot.dialogs.registration.getters import AGE_GROUPS
from app.bot.dialogs.events.utils import build_event_text
from app.bot.enums.event_registrations import EventRegistrationStatus
from app.bot.enums.roles import UserRole
from app.infrastructure.database.database.db import DB
from app.bot.states.attendance import AttendanceSG
from config.config import settings

event_chats_router = Router()

EVENT_JOIN_CHAT_CALLBACK = "event_join_chat"
EVENT_JOIN_CHAT_GENDER_CALLBACK = "event_join_chat_gender"
EVENT_JOIN_CHAT_AGE_CALLBACK = "event_join_chat_age"
EVENT_JOIN_CHAT_INTENT_CALLBACK = "event_join_chat_intent"
EVENT_REGISTER_PAY_CALLBACK = "event_register_pay"
EVENT_REGISTER_CONFIRM_CALLBACK = "event_register_confirm"
EVENT_PREPAY_CONFIRM_CALLBACK = "event_prepay_confirm"
EVENT_ATTEND_CONFIRM_CALLBACK = "event_attend_confirm"
EVENT_CHAT_START_PREFIX = "event_chat_"
INTENT_OPTIONS = ("hot", "warm", "cold")


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


def build_intent_keyboard(
    i18n: TranslatorRunner,
    event_id: int,
    *,
    announce: bool = False,
) -> InlineKeyboardMarkup:
    suffix = ":announce" if announce else ""
    rows = [
        [
            InlineKeyboardButton(
                text=i18n.account.intent.hot(),
                callback_data=(
                    f"{EVENT_JOIN_CHAT_INTENT_CALLBACK}:{event_id}:hot{suffix}"
                ),
            )
        ],
        [
            InlineKeyboardButton(
                text=i18n.account.intent.warm(),
                callback_data=(
                    f"{EVENT_JOIN_CHAT_INTENT_CALLBACK}:{event_id}:warm{suffix}"
                ),
            )
        ],
        [
            InlineKeyboardButton(
                text=i18n.account.intent.cold(),
                callback_data=(
                    f"{EVENT_JOIN_CHAT_INTENT_CALLBACK}:{event_id}:cold{suffix}"
                ),
            )
        ],
    ]
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
    event_id: int | None = None,
) -> None:
    keyboard = _build_chat_link_keyboard(
        i18n=i18n,
        topic_link=topic_link,
        event_id=event_id,
    )
    text = "\n\n".join(
        [
            i18n.partner.event.join.chat.text(),
            i18n.partner.event.join.chat.hint(),
        ]
    )
    await message.answer(text, reply_markup=keyboard)


def _build_chat_link_keyboard(
    *,
    i18n: TranslatorRunner,
    topic_link: str,
    event_id: int | None = None,
) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text=i18n.partner.event.join.chat.button(),
                url=topic_link,
            )
        ]
    ]
    if event_id is not None:
        rows.append(
            [
                InlineKeyboardButton(
                    text=i18n.partner.event.attend.confirm.button(),
                    callback_data=f"{EVENT_ATTEND_CONFIRM_CALLBACK}:{event_id}",
                )
            ]
        )
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def _send_chat_link_notification(
    *,
    bot,
    i18n: TranslatorRunner,
    user_id: int,
    topic_link: str,
    event_id: int | None = None,
) -> None:
    keyboard = _build_chat_link_keyboard(
        i18n=i18n,
        topic_link=topic_link,
        event_id=event_id,
    )
    text = "\n\n".join(
        [
            i18n.partner.event.join.chat.text(),
            i18n.partner.event.join.chat.hint(),
        ]
    )
    await bot.send_message(user_id, text, reply_markup=keyboard)


async def send_event_topic_link_to_user(
    *,
    bot,
    i18n: TranslatorRunner,
    event,
    user_id: int,
    gender: str | None,
) -> None:
    topic_link = _get_event_topic_link(event, gender)
    if not topic_link:
        return
    await _send_chat_link_notification(
        bot=bot,
        i18n=i18n,
        user_id=user_id,
        topic_link=topic_link,
        event_id=event.id,
    )


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


async def _handle_attendance_confirmation(
    *,
    message: Message,
    i18n: TranslatorRunner,
    db: DB,
    event_id: int,
    user_id: int,
    state: FSMContext,
) -> None:
    event = await db.events.get_event_by_id(event_id=event_id)
    if event is None:
        await message.answer(i18n.partner.event.attend.confirm.missing())
        return
    registration = await db.event_registrations.get_by_user_event(
        event_id=event_id,
        user_id=user_id,
    )
    if registration is None or registration.status not in {
        EventRegistrationStatus.CONFIRMED,
        EventRegistrationStatus.ATTENDED_CONFIRMED,
    }:
        await message.answer(i18n.partner.event.attend.confirm.forbidden())
        return
    await state.set_state(AttendanceSG.waiting_code)
    await state.update_data(event_id=event_id)
    await message.answer(i18n.partner.event.attend.confirm.prompt())


def _get_card_number() -> str:
    env_card = os.getenv("CARD_NUMBER")
    card_number = env_card or getattr(settings.payments, "card_number", "")
    return (card_number or "").strip()


def _calc_prepay_amount(event) -> int | None:
    if event is None:
        return None
    if event.is_paid:
        if not event.price:
            return None
        try:
            price = int(str(event.price).replace(" ", ""))
        except ValueError:
            return None
        percent = event.prepay_percent or 0
        return max(0, int(round(price * percent / 100)))
    return event.prepay_fixed_free


def _bump_intent(current: str | None) -> str:
    order = ("cold", "warm", "hot")
    if current in order:
        return order[min(order.index(current) + 1, len(order) - 1)]
    return "warm"


async def _send_prepay_message(
    *,
    message: Message,
    i18n: TranslatorRunner,
    event,
) -> None:
    amount = _calc_prepay_amount(event)
    card_number = _get_card_number()
    refund_note = (
        i18n.partner.event.prepay.free.refund()
        if not event.is_paid
        else ""
    )
    text = i18n.partner.event.prepay.text(
        amount=amount if amount is not None else "-",
        card_number=card_number or "-",
        refund_note=refund_note,
    )
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=i18n.partner.event.prepay.paid.button(),
                    callback_data=f"{EVENT_REGISTER_PAY_CALLBACK}:{event.id}",
                )
            ]
        ]
    )
    await message.answer(text, reply_markup=keyboard)


async def _maybe_start_registration(
    *,
    message: Message,
    i18n: TranslatorRunner,
    db: DB,
    event,
    user_id: int,
    gender: str | None,
) -> None:
    if event and event.partner_user_id == user_id:
        await message.answer(i18n.partner.event.join.chat.self.forbidden())
        return
    if not gender:
        await message.answer(i18n.partner.event.join.chat.missing())
        return

    registration = await db.event_registrations.get_by_user_event(
        event_id=event.id,
        user_id=user_id,
    )

    if registration and registration.status in {
        EventRegistrationStatus.CONFIRMED,
        EventRegistrationStatus.ATTENDED_CONFIRMED,
    }:
        topic_link = _get_event_topic_link(event, gender)
        if not topic_link:
            await message.answer(i18n.partner.event.join.chat.missing())
            return
        await _send_chat_link_message(
            message=message,
            i18n=i18n,
            topic_link=topic_link,
            event_id=event.id,
        )
        return

    if registration and registration.status == EventRegistrationStatus.PAID_CONFIRM_PENDING:
        await message.answer(i18n.partner.event.prepay.waiting())
        return

    amount = _calc_prepay_amount(event)
    if registration is None:
        await db.event_registrations.create(
            event_id=event.id,
            user_id=user_id,
            status=EventRegistrationStatus.PENDING_PAYMENT,
            amount=amount,
        )
    await _send_prepay_message(message=message, i18n=i18n, event=event)


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
    intent = user_record.intent if user_record else None

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
    if not intent:
        await message.answer(
            i18n.account.intent.prompt(),
            reply_markup=build_intent_keyboard(i18n, event_id),
        )
        return

    await _maybe_start_registration(
        message=message,
        i18n=i18n,
        db=db,
        event=event,
        user_id=user.id,
        gender=gender,
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
    intent = user_record.intent if user_record else None

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
    if not intent:
        if callback.message:
            await callback.message.answer(
                i18n.account.intent.prompt(),
                reply_markup=build_intent_keyboard(i18n, event_id),
            )
        await callback.answer()
        return

    if callback.message:
        await _maybe_start_registration(
            message=callback.message,
            i18n=i18n,
            db=db,
            event=event,
            user_id=user.id,
            gender=gender,
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
    intent = user_record.intent if user_record else None

    await db.users.update_profile(
        user_id=user.id,
        gender=gender,
        age_group=age_group,
        intent=intent,
    )

    if not age_group:
        if callback.message:
            await callback.message.answer(
                i18n.general.registration.age.prompt(),
                reply_markup=build_age_keyboard(i18n, event_id, announce=announce),
            )
        await callback.answer()
        return
    if not intent:
        if callback.message:
            await callback.message.answer(
                i18n.account.intent.prompt(),
                reply_markup=build_intent_keyboard(i18n, event_id, announce=announce),
            )
        await callback.answer()
        return

    event = await db.events.get_event_by_id(event_id=event_id)
    if event is None:
        await callback.answer(i18n.partner.event.join.chat.missing())
        return

    if callback.message:
        await _maybe_start_registration(
            message=callback.message,
            i18n=i18n,
            db=db,
            event=event,
            user_id=user.id,
            gender=gender,
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
    intent = user_record.intent if user_record else None

    await db.users.update_profile(
        user_id=user.id,
        gender=gender,
        age_group=age_group,
        intent=intent,
    )

    if not gender:
        if callback.message:
            await callback.message.answer(
                i18n.general.registration.gender.prompt(),
                reply_markup=build_gender_keyboard(i18n, event_id, announce=announce),
            )
        await callback.answer()
        return
    if not intent:
        if callback.message:
            await callback.message.answer(
                i18n.account.intent.prompt(),
                reply_markup=build_intent_keyboard(i18n, event_id, announce=announce),
            )
        await callback.answer()
        return

    event = await db.events.get_event_by_id(event_id=event_id)
    if event is None:
        await callback.answer(i18n.partner.event.join.chat.missing())
        return

    if callback.message:
        await _maybe_start_registration(
            message=callback.message,
            i18n=i18n,
            db=db,
            event=event,
            user_id=user.id,
            gender=gender,
        )
    await callback.answer()


@event_chats_router.callback_query(
    lambda callback: callback.data
    and callback.data.startswith(f"{EVENT_JOIN_CHAT_INTENT_CALLBACK}:")
)
async def process_event_join_chat_intent(
    callback: CallbackQuery,
    i18n: TranslatorRunner,
    db: DB,
) -> None:
    parts = _parse_callback_parts(callback.data, EVENT_JOIN_CHAT_INTENT_CALLBACK, 3)
    if not parts:
        await callback.answer(i18n.partner.event.join.chat.missing())
        return
    try:
        event_id = int(parts[1])
    except ValueError:
        await callback.answer(i18n.partner.event.join.chat.missing())
        return
    intent = parts[2]
    announce = len(parts) == 4 and parts[3] == "announce"
    if intent not in INTENT_OPTIONS:
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
    age_group = user_record.age_group if user_record else None

    await db.users.update_profile(
        user_id=user.id,
        gender=gender,
        age_group=age_group,
        intent=intent,
    )

    if not gender:
        if callback.message:
            await callback.message.answer(
                i18n.general.registration.gender.prompt(),
                reply_markup=build_gender_keyboard(i18n, event_id, announce=announce),
            )
        await callback.answer()
        return

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

    if callback.message:
        await _maybe_start_registration(
            message=callback.message,
            i18n=i18n,
            db=db,
            event=event,
            user_id=user.id,
            gender=gender,
        )
    await callback.answer()


@event_chats_router.callback_query(
    lambda callback: callback.data
    and callback.data.startswith(f"{EVENT_REGISTER_PAY_CALLBACK}:")
)
async def process_event_register_pay(
    callback: CallbackQuery,
    i18n: TranslatorRunner,
    db: DB,
) -> None:
    parts = _parse_callback_parts(callback.data, EVENT_REGISTER_PAY_CALLBACK, 2)
    if not parts:
        await callback.answer(i18n.partner.event.join.chat.missing())
        return
    try:
        event_id = int(parts[1])
    except ValueError:
        await callback.answer(i18n.partner.event.join.chat.missing())
        return

    if not callback.message:
        await callback.answer()
        return

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=i18n.partner.event.prepay.confirm.yes(),
                    callback_data=f"{EVENT_REGISTER_CONFIRM_CALLBACK}:{event_id}:yes",
                ),
                InlineKeyboardButton(
                    text=i18n.partner.event.prepay.confirm.no(),
                    callback_data=f"{EVENT_REGISTER_CONFIRM_CALLBACK}:{event_id}:no",
                ),
            ]
        ]
    )
    await callback.message.answer(i18n.partner.event.prepay.confirm.prompt(), reply_markup=keyboard)
    await callback.answer()


@event_chats_router.callback_query(
    lambda callback: callback.data
    and callback.data.startswith(f"{EVENT_REGISTER_CONFIRM_CALLBACK}:")
)
async def process_event_register_confirm(
    callback: CallbackQuery,
    i18n: TranslatorRunner,
    db: DB,
) -> None:
    parts = _parse_callback_parts(callback.data, EVENT_REGISTER_CONFIRM_CALLBACK, 3)
    if not parts:
        await callback.answer(i18n.partner.event.join.chat.missing())
        return
    try:
        event_id = int(parts[1])
    except ValueError:
        await callback.answer(i18n.partner.event.join.chat.missing())
        return
    decision = parts[2]
    if decision not in {"yes", "no"}:
        await callback.answer(i18n.partner.event.join.chat.missing())
        return

    user = callback.from_user
    if not user:
        return

    if decision == "no":
        await callback.answer(i18n.partner.event.prepay.cancelled())
        return

    await db.event_registrations.update_status(
        event_id=event_id,
        user_id=user.id,
        status=EventRegistrationStatus.PAID_CONFIRM_PENDING,
    )
    event = await db.events.get_event_by_id(event_id=event_id)
    if event and callback.bot:
        username = f"@{user.username}" if user.username else user.full_name
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=i18n.partner.event.registrations.pending.approve.button(),
                        callback_data=(
                            f"{EVENT_PREPAY_CONFIRM_CALLBACK}:{event_id}:{user.id}:approve"
                        ),
                    ),
                    InlineKeyboardButton(
                        text=i18n.partner.event.registrations.pending.decline.button(),
                        callback_data=(
                            f"{EVENT_PREPAY_CONFIRM_CALLBACK}:{event_id}:{user.id}:decline"
                        ),
                    ),
                ]
            ]
        )
        await callback.bot.send_message(
            event.partner_user_id,
            i18n.partner.event.prepay.notify(
                username=username,
                event_name=event.name,
            ),
            reply_markup=keyboard,
        )
    if callback.message:
        await callback.message.answer(i18n.partner.event.prepay.sent())
    await callback.answer()


@event_chats_router.callback_query(
    lambda callback: callback.data
    and callback.data.startswith(f"{EVENT_PREPAY_CONFIRM_CALLBACK}:")
)
async def process_event_prepay_confirm(
    callback: CallbackQuery,
    i18n: TranslatorRunner,
    db: DB,
) -> None:
    parts = _parse_callback_parts(callback.data, EVENT_PREPAY_CONFIRM_CALLBACK, 4)
    if not parts:
        await callback.answer(i18n.partner.event.join.chat.missing())
        return
    try:
        event_id = int(parts[1])
        user_id = int(parts[2])
    except ValueError:
        await callback.answer(i18n.partner.event.join.chat.missing())
        return
    decision = parts[3]
    if decision not in {"approve", "decline"}:
        await callback.answer(i18n.partner.event.join.chat.missing())
        return

    approver = callback.from_user
    if not approver:
        return

    approver_record = await db.users.get_user_record(user_id=approver.id)
    if not approver_record or approver_record.role not in {UserRole.PARTNER, UserRole.ADMIN}:
        await callback.answer(i18n.partner.event.forbidden())
        return

    event = await db.events.get_event_by_id(event_id=event_id)
    if event is None:
        await callback.answer(i18n.partner.event.join.chat.missing())
        return
    if approver_record.role == UserRole.PARTNER and event.partner_user_id != approver.id:
        await callback.answer(i18n.partner.event.forbidden())
        return

    reg = await db.event_registrations.get_by_user_event(
        event_id=event_id,
        user_id=user_id,
    )
    if reg is None:
        await callback.answer(i18n.partner.event.registrations.pending.details.missing())
        return

    if decision == "approve":
        await db.event_registrations.mark_paid_confirmed(
            event_id=event_id,
            user_id=user_id,
        )
        user_record = await db.users.get_user_record(user_id=user_id)
        if user_record:
            new_intent = _bump_intent(user_record.intent)
            await db.users.update_profile(
                user_id=user_id,
                gender=user_record.gender,
                age_group=user_record.age_group,
                intent=new_intent,
            )
        if callback.bot:
            await callback.bot.send_message(
                user_id,
                i18n.partner.event.prepay.approved(),
            )
            gender = user_record.gender if user_record else None
            await send_event_topic_link_to_user(
                bot=callback.bot,
                i18n=i18n,
                event=event,
                user_id=user_id,
                gender=gender,
            )
        await callback.answer(i18n.partner.event.prepay.approved.partner())
    else:
        await db.event_registrations.update_status(
            event_id=event_id,
            user_id=user_id,
            status=EventRegistrationStatus.DECLINED,
        )
        if callback.bot:
            await callback.bot.send_message(
                user_id,
                i18n.partner.event.prepay.declined(),
            )
        await callback.answer(i18n.partner.event.prepay.declined.partner())

@event_chats_router.callback_query(
    lambda callback: callback.data
    and callback.data.startswith(f"{EVENT_ATTEND_CONFIRM_CALLBACK}:")
)
async def process_event_attend_confirm(
    callback: CallbackQuery,
    i18n: TranslatorRunner,
    db: DB,
    state: FSMContext,
) -> None:
    parts = _parse_callback_parts(callback.data, EVENT_ATTEND_CONFIRM_CALLBACK, 2)
    if not parts:
        await callback.answer(i18n.partner.event.attend.confirm.missing())
        return
    try:
        event_id = int(parts[1])
    except ValueError:
        await callback.answer(i18n.partner.event.attend.confirm.missing())
        return

    user = callback.from_user
    if not user:
        return

    if callback.message:
        await _handle_attendance_confirmation(
            message=callback.message,
            i18n=i18n,
            db=db,
            event_id=event_id,
            user_id=user.id,
            state=state,
        )
    await callback.answer()


@event_chats_router.message(AttendanceSG.waiting_code)
async def process_attendance_code(
    message: Message,
    i18n: TranslatorRunner,
    db: DB,
    state: FSMContext,
) -> None:
    data = await state.get_data()
    event_id = data.get("event_id")
    if not isinstance(event_id, int):
        await state.clear()
        await message.answer(i18n.partner.event.attend.confirm.missing())
        return

    event = await db.events.get_event_by_id(event_id=event_id)
    if event is None or not event.attendance_code:
        await state.clear()
        await message.answer(i18n.partner.event.attend.confirm.missing())
        return

    user = message.from_user
    if not user:
        await state.clear()
        return

    reg = await db.event_registrations.get_by_user_event(
        event_id=event_id,
        user_id=user.id,
    )
    if reg is None or reg.status not in {
        EventRegistrationStatus.CONFIRMED,
        EventRegistrationStatus.ATTENDED_CONFIRMED,
    }:
        await state.clear()
        await message.answer(i18n.partner.event.attend.confirm.forbidden())
        return

    if reg.status == EventRegistrationStatus.ATTENDED_CONFIRMED:
        await state.clear()
        await message.answer(i18n.partner.event.attend.confirm.already())
        return

    code = (message.text or "").strip()
    if code != event.attendance_code:
        await message.answer(i18n.partner.event.attend.confirm.invalid())
        return

    await db.event_registrations.mark_attended_confirmed(
        event_id=event_id,
        user_id=user.id,
    )

    user_record = await db.users.get_user_record(user_id=user.id)
    if user_record:
        new_intent = _bump_intent(user_record.intent)
        await db.users.update_profile(
            user_id=user.id,
            gender=user_record.gender,
            age_group=user_record.age_group,
            intent=new_intent,
        )

    username = f"@{user.username}" if user.username else user.full_name
    await message.answer(i18n.partner.event.attend.confirm.ok())
    try:
        await message.bot.send_message(
            event.partner_user_id,
            i18n.partner.event.attend.confirm.notify(
                username=username,
                event_name=event.name,
            ),
        )
    except Exception:
        pass

    await state.clear()
