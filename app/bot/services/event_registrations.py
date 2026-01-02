import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from aiogram import Bot
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    User,
)
from fluentogram import TranslatorHub, TranslatorRunner
from redis.asyncio import Redis

from app.bot.dialogs.events.handlers import EVENT_GOING_CALLBACK
from app.bot.enums.roles import UserRole
from app.infrastructure.database.database.db import DB
from app.infrastructure.database.models.events import EventsModel
from app.infrastructure.database.models.users import UsersModel

# Настройка логгера для текущего модуля
logger = logging.getLogger(__name__)

# Константы для callback-данных и тегов
EVENT_PAID_CALLBACK = "event_paid"  # Callback для оплаты мероприятия
EVENT_REGISTER_CALLBACK = "event_register"  # Callback для регистрации на мероприятие
EVENT_MESSAGE_CALLBACK = "event_message"  # Callback для сообщений от партнера
PAID_EVENT_TAG = "event_id="  # Тег для извлечения ID мероприятия из текста
PAID_RECEIPT_TTL_SECONDS = 7 * 24 * 3600  # Время жизни квитанции в кэше (7 дней)
PARTNER_MESSAGE_TTL_SECONDS = 24 * 3600  # Время жизни сообщения партнера в кэше (1 день)
MAX_MESSAGE_LENGTH = 4096  # Максимальная длина текстового сообщения в Telegram


def _format_user_label(user: User) -> str:
    """
    Форматирует метку пользователя для отображения.

    Использует username если он есть, иначе полное имя пользователя.

    Args:
        user: Объект пользователя Telegram

    Returns:
        Строковая метка пользователя
    """
    if user.username:
        return f"@{user.username}"
    return user.full_name


async def _ensure_user_record(db: DB, user: User) -> UsersModel:
    """
    Гарантирует существование записи пользователя в базе данных.

    Если пользователь не найден, создает новую запись с ролью USER.

    Args:
        db: Объект базы данных
        user: Объект пользователя Telegram

    Returns:
        Модель пользователя из базы данных
    """
    user_record = await db.users.get_user_record(user_id=user.id)
    if user_record is not None:
        if user_record.username != user.username:
            await db.users.update_username(
                user_id=user.id,
                username=user.username,
            )
        return user_record

    # Создаем нового пользователя
    await db.users.add(
        user_id=user.id,
        username=user.username,
        language=user.language_code,  # Язык пользователя из Telegram
        role=UserRole.USER,  # Роль по умолчанию
    )
    return await db.users.get_user_record(user_id=user.id)


def _get_user_i18n(
        translator_hub: TranslatorHub,
        user_record: UsersModel | None,
        fallback: TranslatorRunner,
) -> TranslatorRunner:
    """
    Получает переводчик для конкретного пользователя.

    Args:
        translator_hub: Хаб переводчиков для разных языков
        user_record: Запись пользователя из базы данных (может быть None)
        fallback: Переводчик по умолчанию

    Returns:
        Переводчик для языка пользователя или fallback
    """
    if user_record and user_record.language:
        return translator_hub.get_translator_by_locale(user_record.language)
    return fallback


async def _build_partner_label(bot: Bot, partner_user_id: int) -> str:
    """
    Формирует метку партнера для отображения.

    Пытается получить username партнера через API Telegram.
    Если не удается, использует ID пользователя.

    Args:
        bot: Экземпляр бота
        partner_user_id: ID пользователя-партнера

    Returns:
        Строковая метка партнера
    """
    partner_label = f"id:{partner_user_id}"  # Fallback метка
    try:
        partner_chat = await bot.get_chat(partner_user_id)
        if partner_chat.username:
            partner_label = f"@{partner_chat.username}"
        else:
            partner_label = partner_chat.full_name
    except Exception:
        # Если не удалось получить данные, возвращаем fallback метку
        return partner_label
    return partner_label


async def _build_user_label(bot: Bot, user_id: int) -> str:
    """
    Формирует метку пользователя для отображения.

    Args:
        bot: Экземпляр бота
        user_id: ID пользователя

    Returns:
        Строковая метка пользователя
    """
    user_label = f"id:{user_id}"
    try:
        user_chat = await bot.get_chat(user_id)
        if user_chat.username:
            user_label = f"@{user_chat.username}"
        else:
            user_label = user_chat.full_name
    except Exception:
        return user_label
    return user_label


def _parse_event_id(data: str | None) -> int | None:
    """
    Парсит ID мероприятия из callback данных формата "event_going:<event_id>".

    Args:
        data: Callback данные

    Returns:
        ID мероприятия или None если данные некорректны
    """
    if not data:
        return None

    # Проверяем, что это именно callback "going", а не что-то другое
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
    """
    Парсит ID мероприятия из callback данных формата "event_register:<event_id>".

    Args:
        data: Callback данные

    Returns:
        ID мероприятия или None если данные некорректны
    """
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


def _parse_partner_message_data(data: str | None) -> tuple[int, int] | None:
    """
    Парсит callback данные для отправки сообщения пользователю.

    Формат: "event_message:<event_id>:<user_id>"

    Args:
        data: Callback данные

    Returns:
        Кортеж (event_id, user_id) или None если данные некорректны
    """
    if not data:
        return None

    prefix = f"{EVENT_MESSAGE_CALLBACK}:"
    if not data.startswith(prefix):
        return None

    parts = data.split(":")
    if len(parts) != 3:
        return None

    try:
        return int(parts[1]), int(parts[2])
    except ValueError:
        return None


def _parse_paid_event_id(data: str | None) -> int | None:
    """
    Парсит ID мероприятия из callback данных формата "event_paid:<event_id>".

    Args:
        data: Callback данные

    Returns:
        ID мероприятия или None если данные некорректны
    """
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
    """
    Извлекает ID мероприятия из текста по шаблону "event_id=<number>".

    Используется для парсинга квитанций об оплате.

    Args:
        text: Текст сообщения

    Returns:
        ID мероприятия или None если не найден
    """
    if not text:
        return None

    match = re.search(rf"{PAID_EVENT_TAG}(\d+)", text)
    if not match:
        return None

    return int(match.group(1))


def _build_paid_receipt_key(chat_id: int, message_id: int) -> str:
    """
    Создает ключ для хранения квитанции об оплате в Redis.

    Формат: "paid_receipt:<chat_id>:<message_id>"

    Args:
        chat_id: ID чата
        message_id: ID сообщения

    Returns:
        Строковый ключ для Redis
    """
    return f"paid_receipt:{chat_id}:{message_id}"


def _build_paid_receipt_payload(event_id: int, user_id: int) -> str:
    """
    Создает payload для хранения в кэше квитанции.

    Формат: "<event_id>:<user_id>"

    Args:
        event_id: ID мероприятия
        user_id: ID пользователя

    Returns:
        Строковый payload
    """
    return f"{event_id}:{user_id}"


def _build_partner_message_key(chat_id: int, message_id: int) -> str:
    """
    Создает ключ для хранения сообщения партнера в Redis.

    Формат: "partner_message:<chat_id>:<message_id>"

    Args:
        chat_id: ID чата
        message_id: ID сообщения

    Returns:
        Строковый ключ для Redis
    """
    return f"partner_message:{chat_id}:{message_id}"


def _build_partner_message_payload(event_id: int, user_id: int) -> str:
    """
    Создает payload для хранения сообщения партнера в кэше.

    Формат: "<event_id>:<user_id>"

    Args:
        event_id: ID мероприятия
        user_id: ID пользователя

    Returns:
        Строковый payload
    """
    return f"{event_id}:{user_id}"


def _parse_partner_message_payload(
        payload: bytes | str,
) -> tuple[int, int] | None:
    """
    Парсит payload сообщения партнера из кэша.

    Args:
        payload: Данные из Redis (байты или строка)

    Returns:
        Кортеж (event_id, user_id) или None если парсинг не удался
    """
    if isinstance(payload, bytes):
        payload = payload.decode("utf-8", errors="ignore")

    parts = payload.split(":")
    if len(parts) != 2:
        return None

    try:
        return int(parts[0]), int(parts[1])
    except ValueError:
        return None


def _parse_paid_receipt_payload(payload: bytes | str) -> tuple[int, int] | None:
    """
    Парсит payload квитанции из кэша.

    Args:
        payload: Данные из Redis (байты или строка)

    Returns:
        Кортеж (event_id, user_id) или None если парсинг не удался
    """
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
    """
    Создает клавиатуру с кнопкой для связи с пользователем.

    Args:
        i18n: Переводчик для локализации
        user_id: ID пользователя для ссылки
        button_text: Текст кнопки

    Returns:
        InlineKeyboardMarkup с одной кнопкой
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=button_text,
                    url=f"tg://user?id={user_id}",  # Ссылка на пользователя Telegram
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
    """
    Создает клавиатуру для благодарственного сообщения после регистрации.

    Содержит:
    1. Кнопку для связи с партнером
    2. Кнопку для подтверждения оплаты

    Args:
        i18n: Переводчик для локализации
        partner_user_id: ID партнера
        event_id: ID мероприятия

    Returns:
        InlineKeyboardMarkup с двумя кнопками
    """
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


def _build_partner_registration_keyboard(
        *,
        i18n: TranslatorRunner,
        event_id: int,
        user_id: int,
) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру для уведомления партнера о регистрации.

    Содержит:
    1. Кнопку для связи с пользователем
    2. Кнопку отправки сообщения пользователю через бота
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=i18n.partner.event.going.contact.user.button(),
                    url=f"tg://user?id={user_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text=i18n.partner.event.going.message.user.button(),
                    callback_data=(
                        f"{EVENT_MESSAGE_CALLBACK}:{event_id}:{user_id}"
                    ),
                )
            ],
        ]
    )


def build_partner_registration_notification(
        *,
        i18n: TranslatorRunner,
        user: User,
        event_id: int,
        event_name: str,
) -> tuple[str, InlineKeyboardMarkup]:
    """
    Создает уведомление для партнера о новой регистрации.

    Args:
        i18n: Переводчик для локализации
        user: Пользователь, который зарегистрировался
        event_id: ID мероприятия
        event_name: Название мероприятия

    Returns:
        Кортеж (текст сообщения, клавиатура)
    """
    text = i18n.partner.event.going.notify.partner(
        username=_format_user_label(user),
        user_id=user.id,
        event_name=event_name,
    )
    keyboard = _build_partner_registration_keyboard(
        i18n=i18n,
        event_id=event_id,
        user_id=user.id,
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
    """
    Создает благодарственное сообщение пользователю после регистрации.

    Args:
        i18n: Переводчик для локализации
        event_name: Название мероприятия
        partner_username: Имя/username партнера
        partner_user_id: ID партнера
        event_id: ID мероприятия

    Returns:
        Кортеж (текст сообщения, клавиатура)
    """
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


async def handle_event_going(
        callback: CallbackQuery,
        i18n: TranslatorRunner,
        db: DB,
        bot: Bot,
) -> None:
    """
    Обрабатывает callback "event_going" - регистрацию на мероприятие.

    Основной обработчик для кнопки "Пойду" на мероприятиях.

    Args:
        callback: Callback запрос от пользователя
        i18n: Переводчик для локализации
        db: Объект базы данных
        bot: Экземпляр бота
    """
    user = callback.from_user
    if not user:
        return

    # Проверяем существование пользователя в базе
    user_record = await _ensure_user_record(db, user)
    if not user_record or user_record.role != UserRole.USER:
        await callback.answer(i18n.partner.event.going.forbidden())
        return

    # Пытаемся получить мероприятие из callback данных или из сообщения
    event = None
    event_id = _parse_event_id(callback.data)
    if event_id is not None:
        event = await db.events.get_event_by_id(event_id=event_id)

    # Если не нашли по ID, пытаемся найти по сообщению в канале
    if event is None and callback.message:
        event = await db.events.get_event_by_channel_message(
            channel_id=callback.message.chat.id,
            message_id=callback.message.message_id,
        )

    if event is None:
        await callback.answer(i18n.partner.event.going.missing())
        return

    # Определяем источник регистрации
    source = "bot"
    if callback.message:
        if event.channel_id and callback.message.chat.id == event.channel_id:
            source = "channel"
        elif callback.message.chat.type in {"channel", "supergroup"}:
            source = "channel"

    # Создаем или обновляем регистрацию
    created = await db.event_registrations.create_interesting(
        event_id=event.id,
        user_id=user.id,
        username=user.username,
        source=source,
        is_registered=True,
    )

    registered_now = created
    if not created:
        # Если запись уже существует, помечаем как зарегистрированную
        registered_now = await db.event_registrations.mark_registered(
            event_id=event.id,
            user_id=user.id,
        )
        if not registered_now:
            await callback.answer(i18n.partner.event.going.already())
            return

    # Если регистрация прошла успешно, выполняем дополнительные действия
    if registered_now:
        await _handle_post_registration_actions(
            db=db,
            bot=bot,
            i18n=i18n,
            user=user,
            event=event,
            callback=callback,
        )


async def handle_event_register(
        callback: CallbackQuery,
        i18n: TranslatorRunner,
        db: DB,
        bot: Bot,
) -> None:
    """
    Обрабатывает callback "event_register" - регистрацию из внешних источников.

    Аналогичен handle_event_going, но с более структурированной валидацией.

    Args:
        callback: Callback запрос от пользователя
        i18n: Переводчик для локализации
        db: Объект базы данных
        bot: Экземпляр бота
    """
    user = callback.from_user
    if not user:
        return

    # Валидация пользователя
    validation_result = await _validate_user_for_registration(db, user, i18n)
    if not validation_result.is_valid:
        await callback.answer(validation_result.error_message)
        return

    # Валидация и получение мероприятия
    event_validation = await _validate_and_get_event(callback.data, db, i18n)
    if not event_validation.is_valid:
        await callback.answer(event_validation.error_message)
        return

    event = event_validation.event

    # Регистрация пользователя на мероприятие
    registration_result = await _register_user_for_event(
        db, user.id, event.id, i18n
    )
    if not registration_result.success:
        await callback.answer(registration_result.error_message)
        return

    # Действия после успешной регистрации
    await _handle_post_registration_actions(
        db=db,
        bot=bot,
        i18n=i18n,
        user=user,
        event=event,
        callback=callback
    )


async def _validate_user_for_registration(
        db: DB, user: User, i18n: TranslatorRunner
) -> "ValidationResult":
    """
    Валидирует пользователя для регистрации на мероприятие.

    Проверяет, что пользователь существует и имеет роль USER.

    Args:
        db: Объект базы данных
        user: Пользователь для валидации
        i18n: Переводчик для локализации сообщений об ошибках

    Returns:
        ValidationResult с результатом валидации
    """
    user_record = await _ensure_user_record(db, user)
    if not user_record or user_record.role != UserRole.USER:
        return ValidationResult(
            is_valid=False,
            error_message=i18n.partner.event.going.forbidden()
        )
    return ValidationResult(is_valid=True)


async def _validate_and_get_event(
        callback_data: str, db: DB, i18n: TranslatorRunner
) -> "EventValidationResult":
    """
    Валидирует callback данные и получает мероприятие.

    Args:
        callback_data: Данные callback
        db: Объект базы данных
        i18n: Переводчик для локализации сообщений об ошибках

    Returns:
        EventValidationResult с результатом валидации и мероприятием
    """
    event_id = _parse_register_event_id(callback_data)
    if event_id is None:
        return EventValidationResult(
            is_valid=False,
            error_message=i18n.partner.event.going.missing()
        )

    event = await db.events.get_event_by_id(event_id=event_id)
    if event is None:
        return EventValidationResult(
            is_valid=False,
            error_message=i18n.partner.event.going.missing()
        )

    return EventValidationResult(is_valid=True, event=event)


async def _register_user_for_event(
        db: DB, user_id: int, event_id: int, i18n: TranslatorRunner
) -> "RegistrationResult":
    """
    Регистрирует пользователя на мероприятие.

    Args:
        db: Объект базы данных
        user_id: ID пользователя
        event_id: ID мероприятия
        i18n: Переводчик для локализации сообщений об ошибках

    Returns:
        RegistrationResult с результатом регистрации
    """
    registered = await db.event_registrations.mark_registered(
        event_id=event_id,
        user_id=user_id,
    )

    if not registered:
        # Проверяем причину неудачи
        existing = await db.event_registrations.get_registration(
            event_id=event_id,
            user_id=user_id,
        )
        if existing is not None:
            return RegistrationResult(
                success=False,
                error_message=i18n.partner.event.going.already()
            )
        return RegistrationResult(
            success=False,
            error_message=i18n.partner.event.going.missing()
        )

    return RegistrationResult(success=True)


async def _handle_post_registration_actions(
        db: DB,
        bot: Bot,
        i18n: TranslatorRunner,
        user: User,
        event: EventsModel,
        callback: CallbackQuery
) -> None:
    """
    Выполняет действия после успешной регистрации.

    Включает:
    1. Сбор аналитики
    2. Уведомление партнера
    3. Отправку благодарности пользователю

    Args:
        db: Объект базы данных
        bot: Экземпляр бота
        i18n: Переводчик для локализации
        user: Пользователь, который зарегистрировался
        event: Мероприятие
        callback: Callback запрос
    """
    # Сбор аналитики по источнику трафика
    await _collect_registration_analytics(db, event.id, user.id)

    # Уведомление партнера о новой регистрации
    await _notify_partner_about_registration(
        bot, i18n, user, event
    )

    # Отправка благодарности пользователю
    await _send_thanks_to_user(
        bot, i18n, user, event
    )

    # Подтверждение пользователю
    await callback.answer(i18n.partner.event.going.done())


async def _collect_registration_analytics(
        db: DB, event_id: int, user_id: int
) -> None:
    """
    Собирает аналитику по регистрации для рекламных кампаний.

    Args:
        db: Объект базы данных
        event_id: ID мероприятия
        user_id: ID пользователя
    """
    source_info = await db.event_registrations.get_interest_source(
        event_id=event_id,
        user_id=user_id,
    )

    if source_info is not None:
        await db.adv_stats.increment_registered(
            event_id=event_id,
            placement_date=source_info.placement_date,
            channel_username=source_info.channel_username,
            placement_price=source_info.placement_price,
        )


async def _notify_partner_about_registration(
        bot: Bot, i18n: TranslatorRunner, user: User, event: EventsModel
) -> None:
    """
    Отправляет уведомление партнеру о новой регистрации.

    Args:
        bot: Экземпляр бота
        i18n: Переводчик для локализации
        user: Пользователь, который зарегистрировался
        event: Мероприятие
    """
    partner_text, partner_keyboard = build_partner_registration_notification(
        i18n=i18n,
        user=user,
        event_id=event.id,
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


async def _send_thanks_to_user(
        bot: Bot, i18n: TranslatorRunner, user: User, event: EventsModel
) -> None:
    """
    Отправляет благодарственное сообщение пользователю после регистрации.

    Args:
        bot: Экземпляр бота
        i18n: Переводчик для локализации
        user: Пользователь
        event: Мероприятие
    """
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


@dataclass
class ValidationResult:
    """Результат валидации пользователя."""
    is_valid: bool
    error_message: Optional[str] = None


@dataclass
class EventValidationResult:
    """Результат валидации и получения мероприятия."""
    is_valid: bool
    event: Optional[EventsModel] = None
    error_message: Optional[str] = None


@dataclass
class RegistrationResult:
    """Результат регистрации пользователя на мероприятие."""
    success: bool
    error_message: Optional[str] = None


async def handle_event_paid(
        callback: CallbackQuery,
        i18n: TranslatorRunner,
        db: DB,
        bot: Bot,
        _cache_pool: Redis | None = None,
) -> None:
    """
    Обрабатывает callback "event_paid" - подтверждение оплаты мероприятия.

    Пользователь нажимает кнопку "Оплатил" после регистрации.

    Args:
        callback: Callback запрос от пользователя
        i18n: Переводчик для локализации
        db: Объект базы данных
        bot: Экземпляр бота
        _cache_pool: Пул соединений Redis (опционально)
    """
    user = callback.from_user
    if not user:
        return

    # Валидация пользователя
    user_record = await _ensure_user_record(db, user)
    if not user_record or user_record.role != UserRole.USER:
        await callback.answer(i18n.partner.event.going.forbidden())
        return

    # Парсинг ID мероприятия
    event_id = _parse_paid_event_id(callback.data)
    if event_id is None:
        await callback.answer(i18n.partner.event.paid.missing())
        return

    # Получение мероприятия
    event = await db.events.get_event_by_id(event_id=event_id)
    if event is None:
        await callback.answer(i18n.partner.event.paid.missing())
        return

    # Проверка регистрации пользователя
    registration = await db.event_registrations.get_registration(
        event_id=event_id,
        user_id=user.id,
    )
    if registration is None:
        await callback.answer(i18n.partner.event.paid.not_registered())
        return

    # Проверка, не оплачено ли уже
    if registration.is_paid:
        await callback.answer(i18n.partner.event.paid.already())
        return

    # Отметка как оплаченного
    updated = await db.event_registrations.mark_paid(
        event_id=event_id,
        user_id=user.id,
    )
    if not updated:
        await callback.answer(i18n.partner.event.paid.already())
        return

    # Обновление статистики
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

    # Уведомление партнера
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
        # Сохраняем в кэш информацию о квитанции
        if _cache_pool:
            key = _build_paid_receipt_key(sent.chat.id, sent.message_id)
            payload = _build_paid_receipt_payload(event.id, user.id)
            await _cache_pool.set(key, payload, ex=PAID_RECEIPT_TTL_SECONDS)
    except Exception as exc:
        logger.warning("Failed to notify partner %s: %s", event.partner_user_id, exc)

    await callback.answer(i18n.partner.event.paid.done())


@dataclass
class PartnerMessageContext:
    """Контекст для обработки сообщения партнера пользователю."""
    event_id: int | None = None
    recipient_user_id: int | None = None
    cache_key: str | None = None


async def _resolve_partner_message_context(
        reply: Message | None,
        cache_pool: Redis | None,
) -> PartnerMessageContext:
    """
    Разрешает контекст сообщения партнера из ответного сообщения и кэша.

    Args:
        reply: Сообщение, на которое отвечает партнер
        cache_pool: Пул соединений Redis

    Returns:
        PartnerMessageContext с извлеченными данными
    """
    if not reply or not cache_pool:
        return PartnerMessageContext()

    cache_key = _build_partner_message_key(reply.chat.id, reply.message_id)
    cached = await cache_pool.get(cache_key)
    if not cached:
        return PartnerMessageContext()

    parsed = _parse_partner_message_payload(cached)
    if not parsed:
        return PartnerMessageContext()

    event_id, recipient_user_id = parsed
    return PartnerMessageContext(
        event_id=event_id,
        recipient_user_id=recipient_user_id,
        cache_key=cache_key,
    )


async def handle_partner_message_request(
        callback: CallbackQuery,
        i18n: TranslatorRunner,
        db: DB,
        bot: Bot,
        _cache_pool: Redis | None = None,
) -> None:
    """
    Обрабатывает callback на отправку сообщения пользователю от партнера.

    Партнер получает prompt и отвечает на него сообщением, которое будет
    отправлено пользователю в боте.
    """
    user = callback.from_user
    if not user:
        return

    if not _cache_pool:
        await callback.answer(i18n.partner.event.going.message.failed())
        return

    parsed = _parse_partner_message_data(callback.data)
    if not parsed:
        await callback.answer(i18n.partner.event.going.message.failed())
        return

    event_id, recipient_user_id = parsed

    user_record = await db.users.get_user_record(user_id=user.id)
    if not user_record or user_record.role not in {UserRole.PARTNER, UserRole.ADMIN}:
        await callback.answer(i18n.partner.event.going.message.forbidden())
        return

    event = await db.events.get_event_by_id(event_id=event_id)
    if event is None:
        await callback.answer(i18n.partner.event.going.message.missing())
        return

    if user_record.role == UserRole.PARTNER and event.partner_user_id != user.id:
        await callback.answer(i18n.partner.event.going.message.forbidden())
        return

    registration = await db.event_registrations.get_registration(
        event_id=event_id,
        user_id=recipient_user_id,
    )
    if registration is None:
        await callback.answer(i18n.partner.event.going.message.missing())
        return

    user_label = await _build_user_label(bot, recipient_user_id)
    prompt_text = i18n.partner.event.going.message.prompt(
        user_label=user_label,
        user_id=recipient_user_id,
        event_name=event.name,
    )

    try:
        sent = await bot.send_message(user.id, text=prompt_text)
        key = _build_partner_message_key(sent.chat.id, sent.message_id)
        payload = _build_partner_message_payload(event_id, recipient_user_id)
        await _cache_pool.set(key, payload, ex=PARTNER_MESSAGE_TTL_SECONDS)
    except Exception as exc:
        logger.warning(
            "Failed to prompt partner %s about message to user %s: %s",
            user.id,
            recipient_user_id,
            exc,
        )
        await callback.answer(i18n.partner.event.going.message.failed())
        return

    await callback.answer()


async def handle_partner_message_reply(
        message: Message,
        i18n: TranslatorRunner,
        db: DB,
        bot: Bot,
        translator_hub: TranslatorHub,
        _cache_pool: Redis | None = None,
) -> None:
    """
    Обрабатывает сообщение партнера, отправленное в ответ на prompt.

    Сообщение пересылается пользователю через бота.
    """
    partner_message_context = await _resolve_partner_message_context(
        message.reply_to_message,
        _cache_pool,
    )
    if (
        partner_message_context.event_id is None
        or partner_message_context.recipient_user_id is None
    ):
        return

    user = message.from_user
    if not user:
        return

    user_record = await db.users.get_user_record(user_id=user.id)
    if not user_record or user_record.role not in {UserRole.PARTNER, UserRole.ADMIN}:
        await message.answer(i18n.partner.event.going.message.forbidden())
        return

    event = await db.events.get_event_by_id(
        event_id=partner_message_context.event_id,
    )
    if event is None:
        await message.answer(i18n.partner.event.going.message.missing())
        return

    if user_record.role == UserRole.PARTNER and event.partner_user_id != user.id:
        await message.answer(i18n.partner.event.going.message.forbidden())
        return

    registration = await db.event_registrations.get_registration(
        event_id=partner_message_context.event_id,
        user_id=partner_message_context.recipient_user_id,
    )
    if registration is None:
        await message.answer(i18n.partner.event.going.message.missing())
        return

    partner_label = await _build_partner_label(bot, event.partner_user_id)
    recipient_user = await db.users.get_user_record(
        user_id=partner_message_context.recipient_user_id,
    )
    user_i18n = _get_user_i18n(translator_hub, recipient_user, i18n)
    header_text = user_i18n.partner.event.going.message.user.text(
        event_name=event.name,
        partner_username=partner_label,
    )
    message_text = message.html_text or message.text or ""
    combined_text = f"{header_text}\n\n{message_text}"
    reply_keyboard = _build_contact_keyboard(
        i18n=user_i18n,
        user_id=event.partner_user_id,
        button_text=user_i18n.partner.event.going.message.reply.button(),
    )

    try:
        if len(combined_text) <= MAX_MESSAGE_LENGTH:
            await bot.send_message(
                partner_message_context.recipient_user_id,
                text=combined_text,
                reply_markup=reply_keyboard,
            )
        else:
            await bot.send_message(
                partner_message_context.recipient_user_id,
                text=header_text,
                reply_markup=reply_keyboard,
            )
            await bot.send_message(
                partner_message_context.recipient_user_id,
                text=message_text,
            )
    except Exception as exc:
        logger.warning(
            "Failed to send partner message to user %s: %s",
            partner_message_context.recipient_user_id,
            exc,
        )
        await message.answer(i18n.partner.event.going.message.failed())
        return

    if _cache_pool and partner_message_context.cache_key:
        await _cache_pool.delete(partner_message_context.cache_key)

    await message.answer(i18n.partner.event.going.message.sent())


@dataclass
class ReceiptContext:
    """Контекст для обработки квитанции об оплате."""
    event_id: int | None = None
    payer_user_id: int | None = None
    cache_key: str | None = None


async def _resolve_receipt_context(
        reply: Message | None,
        cache_pool: Redis | None,
) -> ReceiptContext:
    """
    Разрешает контекст квитанции из ответного сообщения и кэша.

    Args:
        reply: Сообщение, на которое отвечают квитанцией
        cache_pool: Пул соединений Redis

    Returns:
        ReceiptContext с извлеченными данными
    """
    if not reply or not cache_pool:
        return ReceiptContext()

    # Пытаемся получить данные из кэша
    cache_key = _build_paid_receipt_key(reply.chat.id, reply.message_id)
    cached = await cache_pool.get(cache_key)
    if not cached:
        return ReceiptContext()

    # Парсим payload
    parsed = _parse_paid_receipt_payload(cached)
    if not parsed:
        return ReceiptContext()

    event_id, payer_user_id = parsed
    return ReceiptContext(
        event_id=event_id,
        payer_user_id=payer_user_id,
        cache_key=cache_key,
    )


async def handle_paid_receipt(
        message: Message,
        i18n: TranslatorRunner,
        db: DB,
        bot: Bot,
        _cache_pool: Redis | None = None,
) -> None:
    """
    Обрабатывает квитанцию об оплате от партнера.

    Партнер отправляет документ или фото в ответ на уведомление об оплате.

    Args:
        message: Сообщение с квитанцией
        i18n: Переводчик для локализации
        db: Объект базы данных
        bot: Экземпляр бота
        _cache_pool: Пул соединений Redis (опционально)
    """
    user = message.from_user
    if not user:
        return

    # Проверка прав пользователя
    user_record = await db.users.get_user_record(user_id=user.id)
    if not user_record or user_record.role not in {UserRole.PARTNER, UserRole.ADMIN}:
        await message.answer(i18n.partner.event.paid.receipt.forbidden())
        return

    # Получение контекста из кэша
    receipt_context = await _resolve_receipt_context(
        message.reply_to_message,
        _cache_pool,
    )
    if receipt_context.event_id is None or receipt_context.payer_user_id is None:
        await message.answer(i18n.partner.event.paid.receipt.forbidden())
        return

    # Проверка мероприятия и прав партнера
    event = await db.events.get_event_by_id(event_id=receipt_context.event_id)
    if event is None:
        await message.answer(i18n.partner.event.paid.receipt.forbidden())
        return
    if user_record.role == UserRole.PARTNER and event.partner_user_id != user.id:
        await message.answer(i18n.partner.event.paid.receipt.forbidden())
        return

    # Сохранение файла квитанции
    file_object = message.document or message.photo[-1]  # Берем документ или самое большое фото
    try:
        file_info = await bot.get_file(file_object.file_id)
        # Формируем имя файла с временной меткой
        suffix = Path(file_info.file_path).suffix or ".dat"
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d")
        target_dir = Path("upload") / str(event.partner_user_id) / str(
            receipt_context.event_id
        )
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = (
                target_dir
                / f"receipt_{receipt_context.payer_user_id}_{timestamp}{suffix}"
        )
        await bot.download_file(file_info.file_path, destination=target_path)
    except Exception as exc:
        logger.warning(
            "Failed to save receipt for event %s: %s",
            receipt_context.event_id,
            exc,
        )
        await message.answer(i18n.partner.event.paid.receipt.failed())
        return

    # Сохранение информации о квитанции в базу
    updated, is_new_receipt = await db.event_registrations.set_receipt(
        event_id=receipt_context.event_id,
        user_id=receipt_context.payer_user_id,
        receipt=target_path.name,  # Сохраняем только имя файла
    )

    if not updated:
        logger.warning(
            "Failed to store receipt for event %s and user %s",
            receipt_context.event_id,
            receipt_context.payer_user_id,
        )

    # Обновление статистики, если это новая квитанция
    if updated and is_new_receipt:
        source_info = await db.event_registrations.get_interest_source(
            event_id=receipt_context.event_id,
            user_id=receipt_context.payer_user_id,
        )
        if source_info is not None:
            await db.adv_stats.increment_confirmed(
                event_id=receipt_context.event_id,
                placement_date=source_info.placement_date,
                channel_username=source_info.channel_username,
                placement_price=source_info.placement_price,
            )

    # Очистка кэша
    if _cache_pool and receipt_context.cache_key:
        await _cache_pool.delete(receipt_context.cache_key)

    await message.answer(i18n.partner.event.paid.receipt.saved())
