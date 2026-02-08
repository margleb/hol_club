import logging
import os
import html

from aiogram import Router
from aiogram.fsm.context import FSMContext
from urllib.parse import unquote

from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from aiogram.enums import ParseMode
from fluentogram import TranslatorRunner

from app.bot.dialogs.registration.getters import AGE_GROUPS
from app.bot.dialogs.events.utils import build_event_text
from app.bot.enums.event_registrations import EventRegistrationStatus
from app.bot.enums.roles import UserRole
from app.infrastructure.database.database.db import DB
from app.bot.states.admin_contact import AdminContactSG
from config.config import settings

event_chats_router = Router()
logger = logging.getLogger(__name__)

EVENT_JOIN_CHAT_CALLBACK = "event_join_chat"
EVENT_JOIN_CHAT_GENDER_CALLBACK = "event_join_chat_gender"
EVENT_JOIN_CHAT_AGE_CALLBACK = "event_join_chat_age"
EVENT_REGISTER_PAY_CALLBACK = "event_register_pay"
EVENT_REGISTER_CONFIRM_CALLBACK = "event_register_confirm"
EVENT_PREPAY_CONFIRM_CALLBACK = "event_prepay_confirm"
EVENT_MESSAGE_USER_CALLBACK = "event_message_user"
EVENT_REPLY_ADMIN_CALLBACK = "event_reply_admin"
EVENT_CONTACT_PARTNER_CALLBACK = "event_contact_partner"
EVENT_MESSAGE_DONE_BACK_CALLBACK = "event_message_done_back"
EVENT_CHAT_START_PREFIX = "event_chat_"


def _format_username(
    *,
    username: str | None,
    fallback_name: str | None = None,
    user_id: int | None = None,
) -> str:
    if username:
        return f"@{username}"
    if fallback_name:
        return fallback_name
    if user_id is not None:
        return f"id:{user_id}"
    return "-"


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


def _build_done_back_keyboard(i18n: TranslatorRunner) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=i18n.back.button(),
                    callback_data=EVENT_MESSAGE_DONE_BACK_CALLBACK,
                )
            ]
        ]
    )


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
) -> None:
    record = await db.users.get_user_record(user_id=user_id)
    if record is None:
        await db.users.add(
            user_id=user_id,
            username=username,
            role=UserRole.USER,
        )


async def _send_chat_link_message(
    *,
    message: Message,
    i18n: TranslatorRunner,
    topic_link: str,
) -> None:
    keyboard = _build_chat_link_keyboard(
        i18n=i18n,
        topic_link=topic_link,
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
) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text=i18n.partner.event.join.chat.button(),
                url=topic_link,
            )
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def _send_chat_link_notification(
    *,
    bot,
    i18n: TranslatorRunner,
    user_id: int,
    topic_link: str,
) -> None:
    keyboard = _build_chat_link_keyboard(
        i18n=i18n,
        topic_link=topic_link,
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
        if event.prepay_percent is None and event.prepay_fixed_free is not None:
            return max(0, int(event.prepay_fixed_free))
        percent = event.prepay_percent if event.prepay_percent is not None else 100
        return max(0, int(round(price * percent / 100)))
    return event.prepay_fixed_free


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
    user_record = await db.users.get_user_record(user_id=user_id)
    if user_record and user_record.role in {UserRole.PARTNER, UserRole.ADMIN}:
        await message.answer(i18n.partner.event.join.chat.role.forbidden())
        return

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
    if user_record and user_record.temperature != "hot":
        await db.users.update_profile(
            user_id=user_id,
            gender=user_record.gender,
            age_group=user_record.age_group,
            temperature="warm",
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
    )
    user_record = await db.users.get_user_record(user_id=user.id)
    age_group = user_record.age_group if user_record else None
    temperature = user_record.temperature if user_record else "cold"

    await db.users.update_profile(
        user_id=user.id,
        gender=gender,
        age_group=age_group,
        temperature=temperature,
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
    )
    user_record = await db.users.get_user_record(user_id=user.id)
    gender = user_record.gender if user_record else None
    temperature = user_record.temperature if user_record else "cold"

    await db.users.update_profile(
        user_id=user.id,
        gender=gender,
        age_group=age_group,
        temperature=temperature,
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

    event = await db.events.get_event_by_id(event_id=event_id)
    if event is None:
        await callback.answer(i18n.partner.event.join.chat.missing())
        return
    if not callback.bot:
        await callback.answer()
        return

    moved_to_pending = await db.event_registrations.update_status_if_current(
        event_id=event_id,
        user_id=user.id,
        current_status=EventRegistrationStatus.PENDING_PAYMENT,
        new_status=EventRegistrationStatus.PAID_CONFIRM_PENDING,
    )
    if not moved_to_pending:
        registration = await db.event_registrations.get_by_user_event(
            event_id=event_id,
            user_id=user.id,
        )
        if registration and registration.status == EventRegistrationStatus.PAID_CONFIRM_PENDING:
            if callback.message:
                await callback.message.answer(i18n.partner.event.prepay.waiting())
            await callback.answer()
            return
        await callback.answer(i18n.partner.event.prepay.already.processed())
        return

    payer_username = _format_username(
        username=user.username,
        fallback_name=user.full_name,
        user_id=user.id,
    )
    partner_record = await db.users.get_user_record(user_id=event.partner_user_id)
    partner_username = _format_username(
        username=partner_record.username if partner_record else None,
        user_id=event.partner_user_id,
    )
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
            ,
            [
                InlineKeyboardButton(
                    text=i18n.start.admin.registrations.pending.write.button(),
                    callback_data=f"{EVENT_MESSAGE_USER_CALLBACK}:{user.id}",
                )
            ]
        ]
    )
    admin_ids = await db.users.get_admin_user_ids()
    if not admin_ids:
        logger.warning(
            "No admins found for prepay confirmation of event %s",
            event_id,
        )
        reverted = await db.event_registrations.update_status_if_current(
            event_id=event_id,
            user_id=user.id,
            current_status=EventRegistrationStatus.PAID_CONFIRM_PENDING,
            new_status=EventRegistrationStatus.PENDING_PAYMENT,
        )
        if not reverted:
            logger.warning(
                "Failed to revert prepay status to pending_payment for event %s and user %s",
                event_id,
                user.id,
            )
        if callback.message:
            await callback.message.answer(i18n.partner.event.prepay.admin.missing())
        await callback.answer()
        return
    prepay_amount = _calc_prepay_amount(event)
    notify_text = i18n.partner.event.prepay.notify(
        username=payer_username,
        event_name=event.name,
        partner_username=partner_username,
        amount=prepay_amount if prepay_amount is not None else "-",
    )
    successful_notifications = 0
    for recipient_id in admin_ids:
        try:
            await callback.bot.send_message(
                recipient_id,
                notify_text,
                reply_markup=keyboard,
            )
            successful_notifications += 1
        except Exception as exc:
            logger.warning(
                "Failed to notify user %s about payment confirmation for event %s: %s",
                recipient_id,
                event_id,
                exc,
            )
    if not successful_notifications:
        reverted = await db.event_registrations.update_status_if_current(
            event_id=event_id,
            user_id=user.id,
            current_status=EventRegistrationStatus.PAID_CONFIRM_PENDING,
            new_status=EventRegistrationStatus.PENDING_PAYMENT,
        )
        if not reverted:
            logger.warning(
                "Failed to revert prepay status after notification errors for event %s and user %s",
                event_id,
                user.id,
            )
        if callback.message:
            await callback.message.answer(i18n.partner.event.prepay.admin.missing())
        await callback.answer()
        return

    if callback.message:
        status_keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=i18n.partner.event.prepay.contact.button(),
                        url=f"tg://user?id={admin_ids[0]}",
                    )
                ]
            ]
        )
        await callback.message.answer(
            i18n.partner.event.prepay.sent(),
            reply_markup=status_keyboard,
        )
    await callback.answer()


@event_chats_router.callback_query(
    lambda callback: callback.data
    and callback.data.startswith(f"{EVENT_MESSAGE_USER_CALLBACK}:")
)
async def process_event_message_user(
    callback: CallbackQuery,
    i18n: TranslatorRunner,
    db: DB,
    state: FSMContext,
) -> None:
    parts = _parse_callback_parts(callback.data, EVENT_MESSAGE_USER_CALLBACK, 2)
    if not parts:
        await callback.answer(i18n.partner.event.join.chat.missing())
        return
    try:
        target_user_id = int(parts[1])
    except ValueError:
        await callback.answer(i18n.partner.event.join.chat.missing())
        return

    sender = callback.from_user
    if not sender:
        return
    sender_record = await db.users.get_user_record(user_id=sender.id)
    if not sender_record or sender_record.role not in {UserRole.ADMIN, UserRole.PARTNER}:
        await callback.answer(i18n.partner.event.prepay.admin.only())
        return

    target_user = await db.users.get_user_record(user_id=target_user_id)
    username = (
        f"@{target_user.username}"
        if target_user and target_user.username
        else f"id:{target_user_id}"
    )
    await state.set_state(AdminContactSG.waiting_admin_text)
    await state.update_data(message_user_id=target_user_id)
    if callback.message:
        await callback.message.answer(
            i18n.start.admin.registrations.pending.message.prompt(
                username=username,
            )
        )
    await callback.answer()


@event_chats_router.message(AdminContactSG.waiting_admin_text)
async def process_event_message_user_text(
    message: Message,
    i18n: TranslatorRunner,
    state: FSMContext,
) -> None:
    data = await state.get_data()
    target_user_id = data.get("message_user_id")
    payload = (message.text or "").strip()
    if not payload:
        await message.answer(i18n.start.admin.registrations.pending.message.invalid())
        return
    if not isinstance(target_user_id, int):
        await state.clear()
        await message.answer(i18n.start.admin.registrations.pending.message.invalid())
        return

    sender = message.from_user
    if not sender:
        await state.clear()
        await message.answer(i18n.start.admin.registrations.pending.message.invalid())
        return
    admin_label = _format_username(
        username=sender.username,
        fallback_name=sender.full_name,
        user_id=sender.id,
    )
    quoted_payload = f"<blockquote>{html.escape(payload)}</blockquote>"
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=i18n.start.admin.registrations.pending.reply.button(),
                    callback_data=f"{EVENT_REPLY_ADMIN_CALLBACK}:{sender.id}",
                )
            ]
        ]
    )
    try:
        await message.bot.send_message(
            target_user_id,
            i18n.start.admin.registrations.pending.message.to.user(
                admin=html.escape(admin_label),
                text=quoted_payload,
            ),
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        await state.clear()
        await message.answer(i18n.start.admin.registrations.pending.message.invalid())
        return

    await state.clear()
    await message.answer(
        i18n.start.admin.registrations.pending.message.sent(),
        reply_markup=_build_done_back_keyboard(i18n),
    )


@event_chats_router.callback_query(
    lambda callback: callback.data
    and callback.data.startswith(f"{EVENT_REPLY_ADMIN_CALLBACK}:")
)
async def process_event_reply_admin(
    callback: CallbackQuery,
    i18n: TranslatorRunner,
    db: DB,
    state: FSMContext,
) -> None:
    parts = _parse_callback_parts(callback.data, EVENT_REPLY_ADMIN_CALLBACK, 2)
    if not parts:
        await callback.answer(i18n.partner.event.join.chat.missing())
        return
    try:
        target_user_id = int(parts[1])
    except ValueError:
        await callback.answer(i18n.partner.event.join.chat.missing())
        return

    target_user_record = await db.users.get_user_record(user_id=target_user_id)
    target_role = target_user_record.role if target_user_record else UserRole.ADMIN
    prompt = (
        i18n.partner.event.prepay.contact.partner.prompt()
        if target_role == UserRole.PARTNER
        else i18n.start.admin.registrations.pending.reply.prompt()
    )

    await state.set_state(AdminContactSG.waiting_reply_text)
    await state.update_data(
        reply_admin_user_id=target_user_id,
        reply_target_role=target_role.value,
    )
    if callback.message:
        await callback.message.answer(prompt)
    await callback.answer()


@event_chats_router.message(AdminContactSG.waiting_reply_text)
async def process_event_reply_admin_text(
    message: Message,
    i18n: TranslatorRunner,
    state: FSMContext,
) -> None:
    data = await state.get_data()
    admin_user_id = data.get("reply_admin_user_id")
    reply_target_role = data.get("reply_target_role")
    is_partner_target = reply_target_role == UserRole.PARTNER.value
    prompt_text = (
        i18n.partner.event.prepay.contact.partner.prompt()
        if is_partner_target
        else i18n.start.admin.registrations.pending.reply.prompt()
    )
    failed_text = (
        i18n.partner.event.prepay.contact.partner.failed()
        if is_partner_target
        else i18n.start.admin.registrations.pending.reply.failed()
    )
    sent_text = (
        i18n.partner.event.prepay.contact.partner.sent()
        if is_partner_target
        else i18n.start.admin.registrations.pending.reply.sent()
    )
    payload = (message.text or "").strip()
    if not payload:
        await message.answer(prompt_text)
        return
    if not isinstance(admin_user_id, int):
        await state.clear()
        await message.answer(failed_text)
        return

    sender = message.from_user
    if not sender:
        await state.clear()
        await message.answer(failed_text)
        return
    sender_label = _format_username(
        username=sender.username,
        fallback_name=sender.full_name,
        user_id=sender.id,
    )
    quoted_payload = f"<blockquote>{html.escape(payload)}</blockquote>"
    reply_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=i18n.start.admin.registrations.pending.reply.back.button(),
                    callback_data=f"{EVENT_MESSAGE_USER_CALLBACK}:{sender.id}",
                )
            ]
        ]
    )
    try:
        await message.bot.send_message(
            admin_user_id,
            i18n.start.admin.registrations.pending.reply.admin.received(
                username=html.escape(sender_label),
                text=quoted_payload,
            ),
            reply_markup=reply_keyboard,
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        await state.clear()
        await message.answer(failed_text)
        return

    await state.clear()
    await message.answer(
        sent_text,
        reply_markup=_build_done_back_keyboard(i18n),
    )


@event_chats_router.callback_query(
    lambda callback: callback.data == EVENT_MESSAGE_DONE_BACK_CALLBACK
)
async def process_event_message_done_back(callback: CallbackQuery) -> None:
    if callback.message:
        try:
            await callback.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass
    await callback.answer()


@event_chats_router.callback_query(
    lambda callback: callback.data
    and callback.data.startswith(f"{EVENT_CONTACT_PARTNER_CALLBACK}:")
)
async def process_event_contact_partner(
    callback: CallbackQuery,
    i18n: TranslatorRunner,
    state: FSMContext,
) -> None:
    parts = _parse_callback_parts(callback.data, EVENT_CONTACT_PARTNER_CALLBACK, 2)
    if not parts:
        await callback.answer(i18n.partner.event.join.chat.missing())
        return
    try:
        partner_user_id = int(parts[1])
    except ValueError:
        await callback.answer(i18n.partner.event.join.chat.missing())
        return

    await state.set_state(AdminContactSG.waiting_reply_text)
    await state.update_data(
        reply_admin_user_id=partner_user_id,
        reply_target_role=UserRole.PARTNER.value,
    )
    if callback.message:
        await callback.message.answer(i18n.partner.event.prepay.contact.partner.prompt())
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
    if not approver_record or approver_record.role != UserRole.ADMIN:
        await callback.answer(i18n.partner.event.prepay.admin.only())
        return

    event = await db.events.get_event_by_id(event_id=event_id)
    if event is None:
        await callback.answer(i18n.partner.event.join.chat.missing())
        return

    registration = await db.event_registrations.get_by_user_event(
        event_id=event_id,
        user_id=user_id,
    )
    if registration is None:
        await callback.answer(i18n.partner.event.registrations.pending.details.missing())
        return

    if decision == "approve":
        approved = await db.event_registrations.mark_paid_confirmed_if_current(
            event_id=event_id,
            user_id=user_id,
            current_status=EventRegistrationStatus.PAID_CONFIRM_PENDING,
        )
        if not approved:
            await callback.answer(i18n.partner.event.prepay.already.processed())
            return
        user_record = await db.users.get_user_record(user_id=user_id)
        if user_record:
            await db.users.update_profile(
                user_id=user_id,
                gender=user_record.gender,
                age_group=user_record.age_group,
                temperature="hot",
            )
        if callback.bot:
            partner_contact_keyboard = None
            if isinstance(event.partner_user_id, int):
                partner_contact_keyboard = InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            InlineKeyboardButton(
                                text=i18n.partner.event.prepay.contact.partner.button(),
                                callback_data=f"{EVENT_CONTACT_PARTNER_CALLBACK}:{event.partner_user_id}",
                            )
                        ]
                    ]
                )
            await callback.bot.send_message(
                user_id,
                i18n.partner.event.prepay.approved(),
                reply_markup=partner_contact_keyboard,
            )
            gender = user_record.gender if user_record else None
            await send_event_topic_link_to_user(
                bot=callback.bot,
                i18n=i18n,
                event=event,
                user_id=user_id,
                gender=gender,
            )
            payer_username = _format_username(
                username=user_record.username if user_record else None,
                user_id=user_id,
            )
            partner_reply_keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text=i18n.start.admin.registrations.pending.contact.button(),
                            callback_data=f"{EVENT_MESSAGE_USER_CALLBACK}:{user_id}",
                        )
                    ]
                ]
            )
            if isinstance(event.partner_user_id, int):
                try:
                    await callback.bot.send_message(
                        event.partner_user_id,
                        i18n.partner.event.prepay.approved.partner.notify(
                            username=payer_username,
                            event_name=event.name,
                        ),
                        reply_markup=partner_reply_keyboard,
                    )
                except Exception as exc:
                    logger.warning(
                        "Failed to notify partner %s about approved payment for event %s: %s",
                        event.partner_user_id,
                        event_id,
                        exc,
                    )
            else:
                logger.warning(
                    "Skipped partner notification for event %s: missing partner_user_id",
                    event_id,
                )
        await callback.answer(i18n.partner.event.prepay.approved.partner())
        return

    declined = await db.event_registrations.update_status_if_current(
        event_id=event_id,
        user_id=user_id,
        current_status=EventRegistrationStatus.PAID_CONFIRM_PENDING,
        new_status=EventRegistrationStatus.DECLINED,
    )
    if not declined:
        await callback.answer(i18n.partner.event.prepay.already.processed())
        return
    if callback.bot:
        await callback.bot.send_message(
            user_id,
            i18n.partner.event.prepay.declined(),
        )
    await callback.answer(i18n.partner.event.prepay.declined.partner())
