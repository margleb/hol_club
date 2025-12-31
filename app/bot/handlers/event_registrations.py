import logging
import re
from datetime import datetime, timezone
from pathlib import Path

from aiogram import Bot, Router
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    User,
)
from fluentogram import TranslatorRunner
from redis.asyncio import Redis

from app.bot.dialogs.events.handlers import EVENT_GOING_CALLBACK
from app.bot.enums.roles import UserRole
from app.infrastructure.database.database.db import DB
from app.infrastructure.database.models.users import UsersModel

logger = logging.getLogger(__name__)

event_registrations_router = Router()


EVENT_PAID_CALLBACK = "event_paid"
EVENT_REGISTER_CALLBACK = "event_register"
PAID_EVENT_TAG = "event_id="
PAID_RECEIPT_TTL_SECONDS = 7 * 24 * 3600


def _format_user_label(user: User) -> str:
    if user.username:
        return f"@{user.username}"
    return user.full_name


async def _ensure_user_record(db: DB, user: User) -> UsersModel:
    user_record = await db.users.get_user_record(user_id=user.id)
    if user_record is not None:
        return user_record

    await db.users.add(
        user_id=user.id,
        language=user.language_code,
        role=UserRole.USER,
    )
    return await db.users.get_user_record(user_id=user.id)


async def _build_partner_label(bot: Bot, partner_user_id: int) -> str:
    partner_label = f"id:{partner_user_id}"
    try:
        partner_chat = await bot.get_chat(partner_user_id)
        if partner_chat.username:
            partner_label = f"@{partner_chat.username}"
        else:
            partner_label = partner_chat.full_name
    except Exception:
        return partner_label
    return partner_label


def _parse_event_id(data: str | None) -> int | None:
    if not data:
        return None
    if data == EVENT_GOING_CALLBACK:
        return None
    prefix = f"{EVENT_GOING_CALLBACK}:"
    if not data.startswith(prefix):
        return None
    parts = data.split(":")
    if len(parts) != 2:
        return None
    try:
        return int(parts[1])
    except ValueError:
        return None


def _parse_register_event_id(data: str | None) -> int | None:
    if not data:
        return None
    prefix = f"{EVENT_REGISTER_CALLBACK}:"
    if not data.startswith(prefix):
        return None
    parts = data.split(":")
    if len(parts) != 2:
        return None
    try:
        return int(parts[1])
    except ValueError:
        return None


def _parse_paid_event_id(data: str | None) -> int | None:
    if not data:
        return None
    prefix = f"{EVENT_PAID_CALLBACK}:"
    if not data.startswith(prefix):
        return None
    parts = data.split(":")
    if len(parts) != 2:
        return None
    try:
        return int(parts[1])
    except ValueError:
        return None


def _extract_event_id_from_text(text: str | None) -> int | None:
    if not text:
        return None
    match = re.search(rf"{PAID_EVENT_TAG}(\d+)", text)
    if not match:
        return None
    return int(match.group(1))


def _build_paid_receipt_key(chat_id: int, message_id: int) -> str:
    return f"paid_receipt:{chat_id}:{message_id}"


def _build_paid_receipt_payload(event_id: int, user_id: int) -> str:
    return f"{event_id}:{user_id}"


def _parse_paid_receipt_payload(payload: bytes | str) -> tuple[int, int] | None:
    if isinstance(payload, bytes):
        payload = payload.decode("utf-8", errors="ignore")
    parts = payload.split(":")
    if len(parts) != 2:
        return None
    try:
        return int(parts[0]), int(parts[1])
    except ValueError:
        return None


def _build_contact_keyboard(
    *,
    i18n: TranslatorRunner,
    user_id: int,
    button_text: str,
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=button_text,
                    url=f"tg://user?id={user_id}",
                )
            ]
        ]
    )


def _build_thanks_keyboard(
    *,
    i18n: TranslatorRunner,
    partner_user_id: int,
    event_id: int,
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=i18n.partner.event.going.contact.partner.button(),
                    url=f"tg://user?id={partner_user_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text=i18n.partner.event.going.paid.button(),
                    callback_data=f"{EVENT_PAID_CALLBACK}:{event_id}",
                )
            ],
        ]
    )


def build_partner_registration_notification(
    *,
    i18n: TranslatorRunner,
    user: User,
    event_name: str,
) -> tuple[str, InlineKeyboardMarkup]:
    text = i18n.partner.event.going.notify.partner(
        username=_format_user_label(user),
        user_id=user.id,
        event_name=event_name,
    )
    keyboard = _build_contact_keyboard(
        i18n=i18n,
        user_id=user.id,
        button_text=i18n.partner.event.going.contact.user.button(),
    )
    return text, keyboard


def build_thanks_message(
    *,
    i18n: TranslatorRunner,
    event_name: str,
    partner_username: str,
    partner_user_id: int,
    event_id: int,
) -> tuple[str, InlineKeyboardMarkup]:
    text = i18n.partner.event.going.thanks(
        event_name=event_name,
        partner_username=partner_username,
    )
    keyboard = _build_thanks_keyboard(
        i18n=i18n,
        partner_user_id=partner_user_id,
        event_id=event_id,
    )
    return text, keyboard


@event_registrations_router.callback_query(
    lambda callback: callback.data and callback.data.startswith(EVENT_GOING_CALLBACK)
)
async def process_event_going(
    callback: CallbackQuery,
    i18n: TranslatorRunner,
    db: DB,
    bot: Bot,
) -> None:
    user = callback.from_user
    if not user:
        return

    user_record = await _ensure_user_record(db, user)
    if not user_record or user_record.role != UserRole.USER:
        await callback.answer(i18n.partner.event.going.forbidden())
        return

    event = None
    event_id = _parse_event_id(callback.data)
    if event_id is not None:
        event = await db.events.get_event_by_id(event_id=event_id)

    if event is None and callback.message:
        event = await db.events.get_event_by_channel_message(
            channel_id=callback.message.chat.id,
            message_id=callback.message.message_id,
        )

    if event is None:
        await callback.answer(i18n.partner.event.going.missing())
        return

    source = "bot"
    if callback.message:
        if event.channel_id and callback.message.chat.id == event.channel_id:
            source = "channel"
        elif callback.message.chat.type in {"channel", "supergroup"}:
            source = "channel"

    created = await db.event_registrations.create_registration(
        event_id=event.id,
        user_id=user.id,
        source=source,
        is_registered=True,
    )
    registered_now = created
    if not created:
        registered_now = await db.event_registrations.mark_registered(
            event_id=event.id,
            user_id=user.id,
        )
        if not registered_now:
            await callback.answer(i18n.partner.event.going.already())
            return
    if registered_now:
        source_info = await db.event_registrations.get_interest_source(
            event_id=event.id,
            user_id=user.id,
        )
        if source_info is not None:
            await db.adv_stats.increment_registered(
                event_id=event.id,
                placement_date=source_info.placement_date,
                channel_username=source_info.channel_username,
                placement_price=source_info.placement_price,
            )

    if registered_now:
        partner_text, partner_keyboard = build_partner_registration_notification(
            i18n=i18n,
            user=user,
            event_name=event.name,
        )
        try:
            await bot.send_message(
                event.partner_user_id,
                text=partner_text,
                reply_markup=partner_keyboard,
            )
        except Exception as exc:
            logger.warning(
                "Failed to notify partner %s: %s",
                event.partner_user_id,
                exc,
            )

    partner_label = f"id:{event.partner_user_id}"
    try:
        partner_chat = await bot.get_chat(event.partner_user_id)
        if partner_chat.username:
            partner_label = f"@{partner_chat.username}"
        else:
            partner_label = partner_chat.full_name
    except Exception as exc:
        logger.warning("Failed to resolve partner %s: %s", event.partner_user_id, exc)

    thanks_text, thanks_keyboard = build_thanks_message(
        i18n=i18n,
        event_name=event.name,
        partner_username=partner_label,
        partner_user_id=event.partner_user_id,
        event_id=event.id,
    )
    try:
        await bot.send_message(
            user.id,
            text=thanks_text,
            reply_markup=thanks_keyboard,
        )
    except Exception as exc:
        logger.warning("Failed to notify user %s: %s", user.id, exc)

    await callback.answer(i18n.partner.event.going.done())


@event_registrations_router.callback_query(
    lambda callback: callback.data and callback.data.startswith(EVENT_REGISTER_CALLBACK)
)
async def process_event_register(
    callback: CallbackQuery,
    i18n: TranslatorRunner,
    db: DB,
    bot: Bot,
) -> None:
    user = callback.from_user
    if not user:
        return

    user_record = await _ensure_user_record(db, user)
    if not user_record or user_record.role != UserRole.USER:
        await callback.answer(i18n.partner.event.going.forbidden())
        return

    event_id = _parse_register_event_id(callback.data)
    if event_id is None:
        await callback.answer(i18n.partner.event.going.missing())
        return

    event = await db.events.get_event_by_id(event_id=event_id)
    if event is None:
        await callback.answer(i18n.partner.event.going.missing())
        return

    registered = await db.event_registrations.mark_registered(
        event_id=event.id,
        user_id=user.id,
    )
    if not registered:
        existing = await db.event_registrations.get_registration(
            event_id=event.id,
            user_id=user.id,
        )
        if existing is not None:
            await callback.answer(i18n.partner.event.going.already())
            return
        await callback.answer(i18n.partner.event.going.missing())
        return

    source_info = await db.event_registrations.get_interest_source(
        event_id=event.id,
        user_id=user.id,
    )
    if source_info is not None:
        await db.adv_stats.increment_registered(
            event_id=event.id,
            placement_date=source_info.placement_date,
            channel_username=source_info.channel_username,
            placement_price=source_info.placement_price,
        )

    partner_text, partner_keyboard = build_partner_registration_notification(
        i18n=i18n,
        user=user,
        event_name=event.name,
    )
    try:
        await bot.send_message(
            event.partner_user_id,
            text=partner_text,
            reply_markup=partner_keyboard,
        )
    except Exception as exc:
        logger.warning(
            "Failed to notify partner %s: %s",
            event.partner_user_id,
            exc,
        )

    partner_label = await _build_partner_label(bot, event.partner_user_id)
    thanks_text, thanks_keyboard = build_thanks_message(
        i18n=i18n,
        event_name=event.name,
        partner_username=partner_label,
        partner_user_id=event.partner_user_id,
        event_id=event.id,
    )
    try:
        await bot.send_message(
            user.id,
            text=thanks_text,
            reply_markup=thanks_keyboard,
        )
    except Exception as exc:
        logger.warning("Failed to notify user %s: %s", user.id, exc)
    await callback.answer(i18n.partner.event.going.done())


@event_registrations_router.callback_query(
    lambda callback: callback.data and callback.data.startswith(EVENT_PAID_CALLBACK)
)
async def process_event_paid(
    callback: CallbackQuery,
    i18n: TranslatorRunner,
    db: DB,
    bot: Bot,
    _cache_pool: Redis | None = None,
) -> None:
    user = callback.from_user
    if not user:
        return

    user_record = await _ensure_user_record(db, user)
    if not user_record or user_record.role != UserRole.USER:
        await callback.answer(i18n.partner.event.going.forbidden())
        return

    event_id = _parse_paid_event_id(callback.data)
    if event_id is None:
        await callback.answer(i18n.partner.event.paid.missing())
        return

    event = await db.events.get_event_by_id(event_id=event_id)
    if event is None:
        await callback.answer(i18n.partner.event.paid.missing())
        return

    registration = await db.event_registrations.get_registration(
        event_id=event_id,
        user_id=user.id,
    )
    if registration is None:
        await callback.answer(i18n.partner.event.paid.not_registered())
        return
    if registration.is_paid:
        await callback.answer(i18n.partner.event.paid.already())
        return

    updated = await db.event_registrations.mark_paid(
        event_id=event_id,
        user_id=user.id,
    )
    if not updated:
        await callback.answer(i18n.partner.event.paid.already())
        return

    source_info = await db.event_registrations.get_interest_source(
        event_id=event_id,
        user_id=user.id,
    )
    if source_info is not None:
        await db.adv_stats.increment_paid(
            event_id=event_id,
            placement_date=source_info.placement_date,
            channel_username=source_info.channel_username,
            placement_price=source_info.placement_price,
        )

    partner_text = i18n.partner.event.paid.notify.partner(
        username=_format_user_label(user),
        user_id=user.id,
        event_name=event.name,
        event_id=event.id,
    )
    partner_keyboard = _build_contact_keyboard(
        i18n=i18n,
        user_id=user.id,
        button_text=i18n.partner.event.going.contact.user.button(),
    )
    try:
        sent = await bot.send_message(
            event.partner_user_id,
            text=partner_text,
            reply_markup=partner_keyboard,
        )
        if _cache_pool:
            key = _build_paid_receipt_key(sent.chat.id, sent.message_id)
            payload = _build_paid_receipt_payload(event.id, user.id)
            await _cache_pool.set(key, payload, ex=PAID_RECEIPT_TTL_SECONDS)
    except Exception as exc:
        logger.warning("Failed to notify partner %s: %s", event.partner_user_id, exc)

    await callback.answer(i18n.partner.event.paid.done())


@event_registrations_router.message(
    lambda message: message.reply_to_message
    and (message.photo or message.document)
)
async def process_paid_receipt(
    message: Message,
    i18n: TranslatorRunner,
    db: DB,
    bot: Bot,
    _cache_pool: Redis | None = None,
) -> None:
    user = message.from_user
    if not user:
        return

    # Проверяет, является ли пользователь партнером или администратором
    user_record = await db.users.get_user_record(user_id=user.id)
    if not user_record or user_record.role not in {UserRole.PARTNER, UserRole.ADMIN}:
        await message.answer(i18n.partner.event.paid.receipt.forbidden())
        return

    # Получаем ID мероприятия
    reply = message.reply_to_message
    event_id = None
    payer_user_id = None
    cache_key = None
    if reply and _cache_pool:
        cache_key = _build_paid_receipt_key(reply.chat.id, reply.message_id)
        cached = await _cache_pool.get(cache_key)
        if cached:
            parsed = _parse_paid_receipt_payload(cached)
            if parsed:
                event_id, payer_user_id = parsed
    if event_id is None or payer_user_id is None:
        await message.answer(i18n.partner.event.paid.receipt.forbidden())
        return

    # Верификация доступа. Отправить чек может только партнер по своему мероприятию
    event = await db.events.get_event_by_id(event_id=event_id)
    if event is None:
        await message.answer(i18n.partner.event.paid.receipt.forbidden())
        return
    if user_record.role == UserRole.PARTNER and event.partner_user_id != user.id:
        await message.answer(i18n.partner.event.paid.receipt.forbidden())
        return

    # Создает уникальное имя файла с timestamp и сохраняет файл
    file_object = message.document or message.photo[-1]
    try:
        file_info = await bot.get_file(file_object.file_id)
        suffix = Path(file_info.file_path).suffix or ".dat"
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d")
        target_dir = Path("upload") / str(event.partner_user_id) / str(event_id)
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / f"receipt_{payer_user_id}_{timestamp}{suffix}"
        await bot.download_file(file_info.file_path, destination=target_path)
    except Exception as exc:
        logger.warning("Failed to save receipt for event %s: %s", event_id, exc)
        await message.answer(i18n.partner.event.paid.receipt.failed())
        return

    updated, is_new_receipt = await db.event_registrations.set_receipt(
        event_id=event_id,
        user_id=payer_user_id,
        receipt=target_path.name,
    )
    if not updated:
        logger.warning(
            "Failed to store receipt for event %s and user %s",
            event_id,
            payer_user_id,
        )
    if updated and is_new_receipt:
        source_info = await db.event_registrations.get_interest_source(
            event_id=event_id,
            user_id=payer_user_id,
        )
        if source_info is not None:
            await db.adv_stats.increment_confirmed(
                event_id=event_id,
                placement_date=source_info.placement_date,
                channel_username=source_info.channel_username,
                placement_price=source_info.placement_price,
            )

    if _cache_pool and cache_key:
        await _cache_pool.delete(cache_key)
    await message.answer(i18n.partner.event.paid.receipt.saved())

