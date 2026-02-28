import logging
import os

from aiogram import Router
from aiogram.fsm.context import FSMContext
from urllib.parse import unquote, urlparse

from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from fluentogram import TranslatorRunner

from app.bot.dialogs.events.utils import build_event_text
from app.bot.enums.event_registrations import EventRegistrationStatus
from app.bot.enums.roles import UserRole
from app.infrastructure.database.database.db import DB
from app.bot.states.admin_contact import AdminContactSG
from app.services.telegram.delivery_status import apply_delivery_error_status
from app.services.telegram.private_event_chats import EventPrivateChatService
from config.config import settings

event_chats_router = Router()
logger = logging.getLogger(__name__)

EVENT_JOIN_CHAT_CALLBACK = "event_join_chat"
EVENT_REGISTER_PAY_CALLBACK = "event_register_pay"
EVENT_REGISTER_CONFIRM_CALLBACK = "event_register_confirm"
EVENT_PREPAY_CONFIRM_CALLBACK = "event_prepay_confirm"
EVENT_CHAT_START_PREFIX = "event_chat_"
PAYMENT_PROOF_EVENT_ID_KEY = "payment_proof_event_id"
PAYMENT_PROOF_TYPE_PHOTO = "photo"
PAYMENT_PROOF_TYPE_DOCUMENT = "document"
PAYMENT_RECEIPTS_VAULT_CHANNEL_ENV = "PAYMENT_RECEIPTS_VAULT_CHANNEL"


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


def _extract_payment_proof(message: Message) -> tuple[str, str] | None:
    if message.photo:
        return message.photo[-1].file_id, PAYMENT_PROOF_TYPE_PHOTO
    if message.document:
        return message.document.file_id, PAYMENT_PROOF_TYPE_DOCUMENT
    return None


def _normalize_telegram_chat_target(raw_target: object) -> int | str | None:
    if isinstance(raw_target, int):
        return raw_target
    if raw_target is None:
        return None
    target = str(raw_target).strip()
    if not target:
        return None

    if target.startswith(("https://", "http://")):
        parsed = urlparse(target)
        if parsed.netloc not in {"t.me", "www.t.me"}:
            return None
        target = (parsed.path or "").strip("/")
        if not target:
            return None

    if target.startswith("t.me/"):
        target = target[5:].strip("/")
        if not target:
            return None

    if target.startswith("+"):
        return None

    if target.lstrip("-").isdigit():
        return int(target)

    if not target.startswith("@"):
        target = f"@{target}"
    return target


def _get_payment_receipts_vault_channel() -> int | str | None:
    configured = os.getenv(PAYMENT_RECEIPTS_VAULT_CHANNEL_ENV)
    if not configured:
        configured = settings.get("payment_receipts_vault_channel")
    return _normalize_telegram_chat_target(configured)


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
    event_name: str | None,
) -> None:
    keyboard = _build_chat_link_keyboard(
        i18n=i18n,
        topic_link=topic_link,
    )
    text = "\n\n".join(
        [
            i18n.partner.event.join.chat.text(event_name=event_name or "-"),
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
                text=i18n.partner.event.join.chat.link.button(),
                url=topic_link,
            )
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def _send_chat_link_notification(
    *,
    bot,
    i18n: TranslatorRunner,
    db: DB | None,
    user_id: int,
    topic_link: str,
    event_name: str | None,
) -> None:
    keyboard = _build_chat_link_keyboard(
        i18n=i18n,
        topic_link=topic_link,
    )
    text = "\n\n".join(
        [
            i18n.partner.event.join.chat.text(event_name=event_name or "-"),
            i18n.partner.event.join.chat.hint(),
        ]
    )
    try:
        await bot.send_message(user_id, text, reply_markup=keyboard)
    except Exception as exc:
        if db is not None:
            await apply_delivery_error_status(
                db=db,
                user_id=user_id,
                error=exc,
            )
        raise


async def send_event_topic_link_to_user(
    *,
    bot,
    i18n: TranslatorRunner,
    db: DB | None = None,
    event,
    user_id: int,
    event_private_chat_service: EventPrivateChatService | None = None,
) -> None:
    current_event = event
    topic_link = _get_event_topic_link(current_event)
    if (
        not topic_link
        and db is not None
        and current_event is not None
        and event_private_chat_service is not None
    ):
        current_event = await ensure_event_private_chat(
            db=db,
            event_id=current_event.id,
            event_private_chat_service=event_private_chat_service,
        )
        topic_link = _get_event_topic_link(current_event) if current_event else None
    if not topic_link:
        return
    await _send_chat_link_notification(
        bot=bot,
        i18n=i18n,
        db=db,
        user_id=user_id,
        topic_link=topic_link,
        event_name=current_event.name if current_event else None,
    )


async def ensure_event_private_chat(
    *,
    db: DB,
    event_id: int,
    event_private_chat_service: EventPrivateChatService | None,
):
    if event_private_chat_service is None or not event_private_chat_service.enabled:
        return await db.events.get_event_by_id(event_id=event_id)

    event = await db.events.get_event_by_id(event_id=event_id, for_update=True)
    if event is None:
        return None
    if (getattr(event, "private_chat_invite_link", None) or "").strip():
        return event

    partner_username: str | None = None
    if isinstance(event.partner_user_id, int):
        partner_record = await db.users.get_user_record(user_id=event.partner_user_id)
        if partner_record:
            partner_username = partner_record.username

    private_chat = await event_private_chat_service.create_event_chat(
        event_id=event.id,
        event_name=event.name,
        partner_user_id=event.partner_user_id,
        partner_username=partner_username,
    )
    if private_chat is None:
        logger.warning(
            "Failed to lazily create private event chat for event %s",
            event_id,
        )
        return event

    await db.events.mark_event_private_chat(
        event_id=event.id,
        chat_id=private_chat.chat_id,
        invite_link=private_chat.invite_link,
    )
    return await db.events.get_event_by_id(event_id=event.id)


async def approve_event_registration_payment(
    *,
    db: DB,
    i18n: TranslatorRunner,
    bot,
    event_id: int,
    user_id: int,
    event_private_chat_service: EventPrivateChatService | None = None,
) -> bool:
    event = await db.events.get_event_by_id(event_id=event_id)
    if event is None:
        return False

    registration = await db.event_registrations.get_by_user_event(
        event_id=event_id,
        user_id=user_id,
    )
    if registration is None or not registration.payment_proof_file_id:
        return False

    approved = await db.event_registrations.mark_paid_confirmed_if_current(
        event_id=event_id,
        user_id=user_id,
        current_status=EventRegistrationStatus.PAID_CONFIRM_PENDING,
    )
    if not approved:
        return False

    if not bot:
        return True

    try:
        await bot.send_message(
            user_id,
            i18n.partner.event.prepay.approved(),
        )
    except Exception as exc:
        await apply_delivery_error_status(
            db=db,
            user_id=user_id,
            error=exc,
        )
        logger.warning(
            "Failed to notify user %s about approved prepay for event %s: %s",
            user_id,
            event_id,
            exc,
        )
    try:
        await send_event_topic_link_to_user(
            bot=bot,
            i18n=i18n,
            db=db,
            event=event,
            user_id=user_id,
            event_private_chat_service=event_private_chat_service,
        )
    except Exception as exc:
        logger.warning(
            "Failed to send event topic link to user %s for event %s: %s",
            user_id,
            event_id,
            exc,
        )

    return True


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


def _get_event_topic_link(event) -> str | None:
    invite_link = getattr(event, "private_chat_invite_link", None)
    if invite_link:
        return invite_link
    male_link = build_topic_message_link(
        event.male_chat_id,
        event.male_thread_id,
        event.male_message_id,
        event.male_chat_username,
    )
    if male_link:
        return male_link
    return build_topic_message_link(
        event.female_chat_id,
        event.female_thread_id,
        event.female_message_id,
        event.female_chat_username,
    )


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


async def _save_payment_proof_to_vault_channel(
    *,
    message: Message,
    event_id: int,
    user_id: int,
    payment_proof_file_id: str,
    payment_proof_type: str,
    caption: str,
) -> None:
    vault_channel = _get_payment_receipts_vault_channel()
    if vault_channel is None:
        return

    try:
        if payment_proof_type == PAYMENT_PROOF_TYPE_PHOTO:
            await message.bot.send_photo(
                chat_id=vault_channel,
                photo=payment_proof_file_id,
                caption=caption,
            )
            return
        if payment_proof_type == PAYMENT_PROOF_TYPE_DOCUMENT:
            await message.bot.send_document(
                chat_id=vault_channel,
                document=payment_proof_file_id,
                caption=caption,
            )
            return
        await message.bot.send_message(chat_id=vault_channel, text=caption)
    except Exception as exc:
        logger.warning(
            "Failed to save payment proof to vault channel. event_id=%s, user_id=%s, "
            "channel=%s, error=%s",
            event_id,
            user_id,
            vault_channel,
            exc,
        )


async def _maybe_start_registration(
    *,
    message: Message,
    i18n: TranslatorRunner,
    db: DB,
    event,
    user_id: int,
    event_private_chat_service: EventPrivateChatService | None = None,
) -> None:
    user_record = await db.users.get_user_record(user_id=user_id)
    if user_record and user_record.role == UserRole.ADMIN:
        await message.answer(i18n.partner.event.join.chat.role.forbidden())
        return

    if event and event.partner_user_id == user_id:
        await message.answer(i18n.partner.event.join.chat.self.forbidden())
        return

    registration = await db.event_registrations.get_by_user_event(
        event_id=event.id,
        user_id=user_id,
    )

    if registration and registration.status in {
        EventRegistrationStatus.CONFIRMED,
        EventRegistrationStatus.ATTENDED_CONFIRMED,
    }:
        event_with_chat = event
        topic_link = _get_event_topic_link(event_with_chat)
        if not topic_link:
            ensured_event = await ensure_event_private_chat(
                db=db,
                event_id=event.id,
                event_private_chat_service=event_private_chat_service,
            )
            if ensured_event is not None:
                event_with_chat = ensured_event
                topic_link = _get_event_topic_link(event_with_chat)
        if not topic_link:
            await message.answer(i18n.partner.event.join.chat.missing())
            return
        await _send_chat_link_message(
            message=message,
            i18n=i18n,
            topic_link=topic_link,
            event_name=event_with_chat.name if event_with_chat else None,
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
    event_private_chat_service: EventPrivateChatService | None = None,
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

    await _maybe_start_registration(
        message=message,
        i18n=i18n,
        db=db,
        event=event,
        user_id=user.id,
        event_private_chat_service=event_private_chat_service,
    )


@event_chats_router.callback_query(
    lambda callback: callback.data
    and callback.data.startswith(f"{EVENT_JOIN_CHAT_CALLBACK}:")
)
async def process_event_join_chat(
    callback: CallbackQuery,
    i18n: TranslatorRunner,
    db: DB,
    event_private_chat_service: EventPrivateChatService | None = None,
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

    if callback.message:
        await _maybe_start_registration(
            message=callback.message,
            i18n=i18n,
            db=db,
            event=event,
            user_id=user.id,
            event_private_chat_service=event_private_chat_service,
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
    state: FSMContext,
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
    registration = await db.event_registrations.get_by_user_event(
        event_id=event_id,
        user_id=user.id,
    )
    if registration is None:
        await callback.answer(i18n.partner.event.join.chat.missing())
        return
    if registration.status == EventRegistrationStatus.PAID_CONFIRM_PENDING:
        if callback.message:
            await callback.message.answer(i18n.partner.event.prepay.waiting())
        await callback.answer()
        return
    if registration.status != EventRegistrationStatus.PENDING_PAYMENT:
        await callback.answer(i18n.partner.event.prepay.already.processed())
        return

    await state.set_state(AdminContactSG.waiting_payment_proof)
    await state.update_data(**{PAYMENT_PROOF_EVENT_ID_KEY: event_id})
    if callback.message:
        await callback.message.answer(i18n.partner.event.prepay.receipt.prompt())
    await callback.answer()


@event_chats_router.message(AdminContactSG.waiting_payment_proof)
async def process_event_payment_proof(
    message: Message,
    i18n: TranslatorRunner,
    db: DB,
    state: FSMContext,
) -> None:
    data = await state.get_data()
    event_id = data.get(PAYMENT_PROOF_EVENT_ID_KEY)
    if not isinstance(event_id, int):
        await state.clear()
        await message.answer(i18n.partner.event.prepay.receipt.invalid())
        return

    user = message.from_user
    if not user:
        await state.clear()
        return

    event = await db.events.get_event_by_id(event_id=event_id)
    if event is None:
        await state.clear()
        await message.answer(i18n.partner.event.join.chat.missing())
        return

    registration = await db.event_registrations.get_by_user_event(
        event_id=event_id,
        user_id=user.id,
    )
    if registration is None:
        await state.clear()
        await message.answer(i18n.partner.event.join.chat.missing())
        return
    if registration.status == EventRegistrationStatus.PAID_CONFIRM_PENDING:
        await state.clear()
        await message.answer(i18n.partner.event.prepay.waiting())
        return
    if registration.status != EventRegistrationStatus.PENDING_PAYMENT:
        await state.clear()
        await message.answer(i18n.partner.event.prepay.already.processed())
        return

    payment_proof = _extract_payment_proof(message)
    if payment_proof is None:
        await message.answer(i18n.partner.event.prepay.receipt.invalid())
        return
    payment_proof_file_id, payment_proof_type = payment_proof

    moved_to_pending = (
        await db.event_registrations.attach_payment_proof_and_move_to_pending_if_current(
            event_id=event_id,
            user_id=user.id,
            payment_proof_file_id=payment_proof_file_id,
            payment_proof_type=payment_proof_type,
        )
    )
    if not moved_to_pending:
        current_registration = await db.event_registrations.get_by_user_event(
            event_id=event_id,
            user_id=user.id,
        )
        await state.clear()
        if (
            current_registration
            and current_registration.status == EventRegistrationStatus.PAID_CONFIRM_PENDING
        ):
            await message.answer(i18n.partner.event.prepay.waiting())
            return
        await message.answer(i18n.partner.event.prepay.already.processed())
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
            ],
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
        await state.clear()
        await message.answer(i18n.partner.event.prepay.admin.missing())
        return
    prepay_amount = _calc_prepay_amount(event)
    notify_text = i18n.partner.event.prepay.notify(
        username=payer_username,
        event_name=event.name,
        partner_username=partner_username,
        amount=prepay_amount if prepay_amount is not None else "-",
    )

    await _save_payment_proof_to_vault_channel(
        message=message,
        event_id=event_id,
        user_id=user.id,
        payment_proof_file_id=payment_proof_file_id,
        payment_proof_type=payment_proof_type,
        caption=notify_text,
    )

    successful_notifications = 0
    for recipient_id in admin_ids:
        try:
            if payment_proof_type == PAYMENT_PROOF_TYPE_PHOTO:
                await message.bot.send_photo(
                    recipient_id,
                    photo=payment_proof_file_id,
                    caption=notify_text,
                    reply_markup=keyboard,
                )
            elif payment_proof_type == PAYMENT_PROOF_TYPE_DOCUMENT:
                await message.bot.send_document(
                    recipient_id,
                    document=payment_proof_file_id,
                    caption=notify_text,
                    reply_markup=keyboard,
                )
            else:
                await message.bot.send_message(
                    recipient_id,
                    notify_text,
                    reply_markup=keyboard,
                )
            successful_notifications += 1
        except Exception as exc:
            await apply_delivery_error_status(
                db=db,
                user_id=recipient_id,
                error=exc,
            )
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
        await state.clear()
        await message.answer(i18n.partner.event.prepay.admin.missing())
        return

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
    await state.clear()
    await message.answer(
        i18n.partner.event.prepay.sent(),
        reply_markup=status_keyboard,
    )

@event_chats_router.callback_query(
    lambda callback: callback.data
    and callback.data.startswith(f"{EVENT_PREPAY_CONFIRM_CALLBACK}:")
)
async def process_event_prepay_confirm(
    callback: CallbackQuery,
    i18n: TranslatorRunner,
    db: DB,
    event_private_chat_service: EventPrivateChatService | None = None,
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
        if not registration.payment_proof_file_id:
            await callback.answer(i18n.partner.event.prepay.receipt.required())
            return
        approved = await approve_event_registration_payment(
            db=db,
            i18n=i18n,
            bot=callback.bot,
            event_id=event_id,
            user_id=user_id,
            event_private_chat_service=event_private_chat_service,
        )
        if not approved:
            await callback.answer(i18n.partner.event.prepay.already.processed())
            return
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
        try:
            await callback.bot.send_message(
                user_id,
                i18n.partner.event.prepay.declined(),
            )
        except Exception as exc:
            await apply_delivery_error_status(
                db=db,
                user_id=user_id,
                error=exc,
            )
    await callback.answer(i18n.partner.event.prepay.declined.partner())
