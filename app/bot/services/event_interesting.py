from logging import Logger
from urllib.parse import unquote

from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from fluentogram import TranslatorRunner

from app.bot.dialogs.events.utils import build_event_text
from app.bot.enums.roles import UserRole
from app.bot.services.event_registrations import EVENT_REGISTER_CALLBACK
from app.infrastructure.database.database.db import DB
from app.infrastructure.database.models.events import EventsModel


def _build_outer_start_keyboard(
        *,
        i18n: TranslatorRunner,
        event_id: int,
        post_url: str | None = None,
) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру для внешнего пользователя (не участника сообщества).

    Args:
        i18n: Переводчик для локализации текста кнопки
        event_id: ID мероприятия для callback_data
        post_url: Ссылка на пост в канале, если доступна

    Returns:
        InlineKeyboardMarkup с кнопкой регистрации на мероприятие
    """
    keyboard_rows = [
        [
            InlineKeyboardButton(
                text=i18n.partner.event.register.button(),
                callback_data=f"{EVENT_REGISTER_CALLBACK}:{event_id}",
            )
        ]
    ]
    if post_url:
        keyboard_rows.append(
            [
                InlineKeyboardButton(
                    text=i18n.partner.event.view.post.button(),
                    url=post_url,
                )
            ]
        )
    return InlineKeyboardMarkup(inline_keyboard=keyboard_rows)


def _build_channel_post_link(
        channel_id: int | None,
        message_id: int | None,
        channel_username: str | None = None,
) -> str | None:
    if not channel_id or not message_id:
        return None
    if channel_username:
        channel_username = channel_username.lstrip("@")
        if channel_username:
            return f"https://t.me/{channel_username}/{message_id}"
    chat_id_str = str(channel_id)
    if chat_id_str.startswith("-100"):
        channel_id_str = chat_id_str[4:]
    else:
        channel_id_str = str(abs(channel_id))
    return f"https://t.me/c/{channel_id_str}/{message_id}"


def _build_event_payload(event: EventsModel) -> dict:
    """
    Формирует словарь с основными данными мероприятия для текстового представления.

    Args:
        event: Модель мероприятия из базы данных

    Returns:
        Словарь с ключевыми полями мероприятия
    """
    return {
        "name": event.name,
        "datetime": event.event_datetime,
        "address": event.address,
        "description": event.description,
        "is_paid": event.is_paid,
        "price": event.price,
        "age_group": event.age_group,
    }


def _parse_outer_start_payload(payload: str | None) -> tuple[int, str, str, str] | None:
    """
    Парсит payload из внешней ссылки для отслеживания источников трафика.

    Формат ожидаемого payload: "start=<event_id>_<placement_date>_<channel_username>_<price>"
    Пример: "start=123_2024-12-01_@channel_100"

    Args:
        payload: Строка payload из команды /start

    Returns:
        Кортеж (event_id, placement_date, channel_username, price) или None при ошибке парсинга
    """
    if not payload:
        return None

    # Декодируем URL-encoded строку и убираем пробелы
    payload = unquote(payload.strip())
    if not payload:
        return None

    # Убираем префикс "start=" если он есть
    if payload.startswith("start="):
        payload = payload.split("=", 1)[1]

    payload = payload.strip()
    if not payload:
        return None

    # Разделяем на части: последний элемент - цена, остальное - остальные параметры
    left, sep, price = payload.rpartition("_")
    if not sep or not price:
        return None

    # Разделяем оставшуюся часть на event_id, дату размещения и username канала
    parts = left.split("_", 2)
    if len(parts) != 3:
        return None

    event_id_raw, placement_date, channel_username = parts
    if not placement_date or not channel_username:
        return None

    # Преобразуем event_id в число
    try:
        event_id = int(event_id_raw)
    except ValueError:
        return None

    # Убираем @ из username канала если есть
    channel_username = channel_username.lstrip("@")
    if not channel_username:
        return None

    return event_id, placement_date, channel_username, price


def _extract_start_payload(text: str | None) -> str | None:
    """
    Извлекает payload из текста команды /start.

    Обрабатывает два формата:
    1. "/start payload" - когда payload передается как аргумент команды
    2. "/start?payload" - когда payload передается как query параметр (из инлайн-кнопок)

    Args:
        text: Полный текст команды /start

    Returns:
        Извлеченный payload или None если payload не найден
    """
    if not text:
        return None

    text = text.strip()

    # Формат: "/start payload" (через пробел)
    if " " in text:
        _, payload = text.split(maxsplit=1)
        return payload.strip() or None

    # Формат: "/start?payload" (как query параметр)
    if "?" in text:
        _, payload = text.split("?", 1)
        return payload.strip() or None

    return None


async def maybe_interesting_outer_start(
        *,
        db: DB,
        user_id: int,
        username: str | None,
        user_role: UserRole,
        message_text: str | None,
) -> tuple[bool, EventsModel] | None:
    """
    Обрабатывает команду /start от внешнего пользователя с payload мероприятия.

    Функция выполняет:
    1. Извлечение и парсинг payload
    2. Проверку роли пользователя (должен быть USER)
    3. Поиск мероприятия по ID
    4. Создание записи о заинтересованности
    5. Запись источника трафика для аналитики

    Args:
        db: Объект базы данных
        user_id: ID пользователя
        username: Username пользователя
        user_role: Роль пользователя в системе
        message_text: Текст сообщения с командой /start

    Returns:
        Кортеж (created, event) где:
        - created: True если запись создана, False если уже существовала
        - event: Модель найденного мероприятия
        Или None если пользователь не подходит или payload некорректен
    """
    # Только обычные пользователи могут переходить по внешним ссылкам
    if user_role != UserRole.USER:
        return None

    # Извлекаем и парсим payload
    payload = _parse_outer_start_payload(_extract_start_payload(message_text))
    if not payload:
        return None

    event_id, placement_date, channel_username, placement_price = payload

    # Получаем мероприятие из базы данных
    event = await db.events.get_event_by_id(event_id=event_id)
    if event is None:
        return None

    # Создаем запись о заинтересованности пользователя
    created = await db.event_registrations.create_interesting(
        event_id=event_id,
        user_id=user_id,
        username=username,
        source="outer",  # Источник - внешняя ссылка
        is_registered=False,  # Пока только заинтересованность, не регистрация
    )

    # Если запись создана успешно, сохраняем информацию об источнике трафика
    if created:
        # Сохраняем детали источника (для аналитики и рекламных кампаний)
        await db.event_registrations.store_interest_source(
            event_id=event_id,
            user_id=user_id,
            placement_date=placement_date,
            channel_username=channel_username,
            placement_price=placement_price,
        )

        # Обновляем статистику показов/заинтересованностей
        await db.adv_stats.increment_interesting(
            event_id=event_id,
            placement_date=placement_date,
            channel_username=channel_username,
            placement_price=placement_price,
        )

    return created, event


async def show_event_to_outer_user(
        bot: Bot,
        user_id: int,
        event: EventsModel,
        i18n: TranslatorRunner,
        logger: Logger,
) -> None:
    """
    Отправляет информацию о мероприятии внешнему пользователю.

    Пытается использовать следующие подходы в порядке приоритета:
    1. Копирование сообщения из канала (если есть channel_id и channel_message_id)
    2. Отправка с фото (если есть photo_file_id)
    3. Отправка текстового сообщения (fallback)

    Args:
        bot: Экземпляр бота для отправки сообщений
        user_id: ID пользователя-получателя
        event: Модель мероприятия
        i18n: Переводчик для локализации текста
        logger: Логгер для записи ошибок
    """
    # Создаем клавиатуру с кнопкой регистрации
    channel_username = None
    if event.channel_id:
        try:
            chat = await bot.get_chat(event.channel_id)
            channel_username = getattr(chat, "username", None)
        except Exception as exc:
            logger.warning(
                "Failed to get channel info for event %s: %s",
                event.id,
                exc,
            )
    post_url = _build_channel_post_link(
        event.channel_id,
        event.channel_message_id,
        channel_username=channel_username,
    )
    outer_keyboard = _build_outer_start_keyboard(
        i18n=i18n,
        event_id=event.id,
        post_url=post_url,
    )

    # Пытаемся скопировать оригинальное сообщение из канала
    if event.channel_id and event.channel_message_id:
        try:
            await bot.copy_message(
                chat_id=user_id,
                from_chat_id=event.channel_id,
                message_id=event.channel_message_id,
                reply_markup=outer_keyboard,  # Добавляем свою клавиатуру с кнопкой регистрации
            )
            return  # Успешно скопировали, выходим из функции
        except Exception as exc:
            # Логируем ошибку, но продолжаем попытки отправить через другие методы
            logger.warning(
                "Failed to copy event announcement to user %s: %s",
                user_id,
                exc,
            )

    # Формируем текст мероприятия
    event_text = build_event_text(_build_event_payload(event), i18n)

    try:
        # Пытаемся отправить с фото если оно есть
        if event.photo_file_id:
            await bot.send_photo(
                user_id,
                photo=event.photo_file_id,
                caption=event_text,
                reply_markup=outer_keyboard,
            )
        else:
            # Fallback: отправляем просто текстовое сообщение
            await bot.send_message(
                user_id,
                text=event_text,
                reply_markup=outer_keyboard,
            )
    except Exception as exc:
        # Логируем критическую ошибку - не удалось отправить вообще никакое сообщение
        logger.warning(
            "Failed to send event announcement to user %s: %s",
            user_id,
            exc,
        )
