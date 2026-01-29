import logging
from typing import Awaitable, Callable

from aiogram import Bot
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    User,
)
from fluentogram import TranslatorHub, TranslatorRunner

from app.bot.enums.partner_requests import PartnerRequestStatus
from app.bot.enums.roles import UserRole
from app.infrastructure.database.database.db import DB
from app.infrastructure.database.models.users import UsersModel

# Настройка логгера для текущего модуля
logger = logging.getLogger(__name__)

# Константы для callback-данных запросов на партнерство
PARTNER_REQUEST_CALLBACK = "partner_request"  # Callback для запроса партнерства
PARTNER_DECISION_CALLBACK = "partner_decision"  # Callback для решения по запросу партнерства

# Тип для функции ответа (используется для callback.answer и message.answer)
AnswerFunc = Callable[[str], Awaitable[None]]


def _build_partner_request_keyboard(i18n: TranslatorRunner) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру с кнопкой запроса партнерства.

    Используется, когда пользователь хочет подать заявку на партнерство.

    Args:
        i18n: Переводчик для локализации текста кнопки

    Returns:
        InlineKeyboardMarkup с одной кнопкой запроса партнерства
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=i18n.partner.request.button(),
                    callback_data=PARTNER_REQUEST_CALLBACK,
                )
            ]
        ]
    )


def _build_partner_decision_keyboard(
        i18n: TranslatorRunner,
        user_id: int,
) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру для принятия решения по запросу партнерства.

    Используется в простых уведомлениях для администраторов.

    Args:
        i18n: Переводчик для локализации текста кнопок
        user_id: ID пользователя, который подал заявку

    Returns:
        InlineKeyboardMarkup с кнопками "Одобрить" и "Отклонить"
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=i18n.partner.request.approve.button(),
                    callback_data=f"{PARTNER_DECISION_CALLBACK}:approve:{user_id}",
                ),
                InlineKeyboardButton(
                    text=i18n.partner.request.reject.button(),
                    callback_data=f"{PARTNER_DECISION_CALLBACK}:reject:{user_id}",
                ),
            ]
        ]
    )


def _build_partner_admin_notification_keyboard(
        i18n: TranslatorRunner,
        user_id: int,
) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру для уведомления администраторов о новом запросе партнерства.

    Args:
        i18n: Переводчик для локализации текста кнопок
        user_id: ID пользователя, который подал заявку

    Returns:
        InlineKeyboardMarkup с кнопками "Одобрить" и "Отклонить"
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=i18n.partner.request.approve.button(),
                    callback_data=f"{PARTNER_DECISION_CALLBACK}:approve:{user_id}",
                ),
                InlineKeyboardButton(
                    text=i18n.partner.request.reject.button(),
                    callback_data=f"{PARTNER_DECISION_CALLBACK}:reject:{user_id}",
                ),
            ],
        ]
    )


def _build_partner_request_list_item_keyboard(
        i18n: TranslatorRunner,
        user_id: int,
) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру для элемента списка запросов партнерства.

    Используется в списке заявок, который администратор может запросить командой.

    Args:
        i18n: Переводчик для локализации текста кнопок
        user_id: ID пользователя, который подал заявку

    Returns:
        InlineKeyboardMarkup с кнопками "Одобрить", "Отклонить" и "Связаться"
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=i18n.partner.request.approve.button(),
                    callback_data=f"{PARTNER_DECISION_CALLBACK}:approve:{user_id}",
                ),
                InlineKeyboardButton(
                    text=i18n.partner.request.reject.button(),
                    callback_data=f"{PARTNER_DECISION_CALLBACK}:reject:{user_id}",
                ),
            ],
            [
                InlineKeyboardButton(
                    text=i18n.partner.request.contact.button(),
                    url=f"tg://user?id={user_id}",  # Ссылка для связи с пользователем
                )
            ],
        ]
    )


def _format_partner_username(user: User) -> str:
    """
    Форматирует имя пользователя для отображения в уведомлениях.

    Использует username если он есть, иначе полное имя пользователя.

    Args:
        user: Объект пользователя Telegram

    Returns:
        Строковое представление пользователя
    """
    if user.username:
        return f"@{user.username}"
    return user.full_name


def _get_user_i18n(
        translator_hub: TranslatorHub,
        user_record: UsersModel | None,
        fallback: TranslatorRunner,
) -> TranslatorRunner:
    """
    Получает переводчик для конкретного пользователя.

    Использует язык пользователя из базы данных или fallback переводчик.

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


async def _notify_admins(
        *,
        bot: Bot,
        db: DB,
        i18n: TranslatorRunner,
        user_id: int,
        username: str,
) -> None:
    """
    Отправляет уведомление всем администраторам о новом запросе партнерства.

    Args:
        bot: Экземпляр бота для отправки сообщений
        db: Объект базы данных для получения списка администраторов
        i18n: Переводчик для локализации текста уведомления
        user_id: ID пользователя, подавшего заявку
        username: Имя пользователя для отображения в уведомлении
    """
    admin_ids = await db.users.get_admin_user_ids()
    if not admin_ids:
        return  # Нет администраторов для уведомления

    # Формируем текст уведомления и клавиатуру
    text = i18n.partner.request.admin.notify(username=username, user_id=user_id)
    keyboard = _build_partner_admin_notification_keyboard(i18n, user_id)

    # Отправляем уведомление каждому администратору
    for admin_id in admin_ids:
        try:
            await bot.send_message(admin_id, text=text, reply_markup=keyboard)
        except Exception as exc:
            logger.warning(
                "Failed to notify admin %s about partner request: %s",
                admin_id,
                exc,
            )


async def process_partner_request(
        *,
        user: User,
        i18n: TranslatorRunner,
        db: DB,
        bot: Bot,
        answer: AnswerFunc,
) -> None:
    """
    Обрабатывает запрос пользователя на получение статуса партнера.

    Основная логика обработки кнопки "Стать партнером".

    Args:
        user: Пользователь, подающий заявку
        i18n: Переводчик для локализации ответов
        db: Объект базы данных
        bot: Экземпляр бота для уведомлений
        answer: Функция для отправки ответа пользователю
    """
    # Проверяем/создаем запись пользователя
    user_record = await _ensure_user_record(db, user)

    # Проверяем, что пользователь не уже администратор или партнер
    if user_record.role in {UserRole.ADMIN, UserRole.PARTNER}:
        await answer(i18n.partner.request.forbidden())
        return

    # Проверяем существующие запросы пользователя
    request = await db.partner_requests.get_request(user_id=user.id)

    if request is None:
        # Первый запрос пользователя
        await db.partner_requests.create_request(user_id=user.id)
        await _notify_admins(
            bot=bot,
            db=db,
            i18n=i18n,
            user_id=user.id,
            username=_format_partner_username(user),
        )
        await answer(i18n.partner.request.sent())
        return

    # Обработка различных статусов существующего запроса
    if request.status == PartnerRequestStatus.PENDING:
        await answer(i18n.partner.request.pending())
        return

    if request.status == PartnerRequestStatus.APPROVED:
        # Если запрос уже одобрен, но роль не обновлена
        if user_record.role != UserRole.PARTNER:
            await db.users.update_role(user_id=user.id, role=UserRole.PARTNER)
        await answer(i18n.partner.request.approved())
        return

    # Если запрос был отклонен, повторно отправляем его
    await db.partner_requests.set_pending(user_id=user.id)
    await _notify_admins(
        bot=bot,
        db=db,
        i18n=i18n,
        user_id=user.id,
        username=_format_partner_username(user),
    )
    await answer(i18n.partner.request.sent())


def _parse_decision_callback(data: str) -> tuple[str, int] | None:
    """
    Парсит callback данные для принятия решения по запросу партнерства.

    Ожидаемый формат: "partner_decision:<action>:<user_id>"
    Пример: "partner_decision:approve:123456"

    Args:
        data: Callback данные из кнопки

    Returns:
        Кортеж (action, target_user_id) или None при ошибке парсинга
    """
    parts = data.split(":")
    if len(parts) != 3:
        return None
    if parts[0] != PARTNER_DECISION_CALLBACK:
        return None

    action = parts[1]  # "approve" или "reject"
    try:
        target_user_id = int(parts[2])
    except ValueError:
        return None

    return action, target_user_id


async def _decide_partner_request(
        *,
        action: str,
        target_user_id: int,
        admin_id: int,
        i18n: TranslatorRunner,
        db: DB,
        bot: Bot,
        translator_hub: TranslatorHub,
        answer: AnswerFunc,
) -> bool:
    """
    Обрабатывает решение администратора по запросу партнерства.

    Args:
        action: Действие - "approve" (одобрить) или "reject" (отклонить)
        target_user_id: ID пользователя, чья заявка рассматривается
        admin_id: ID администратора, принимающего решение
        i18n: Переводчик для локализации ответов администратору
        db: Объект базы данных
        bot: Экземпляр бота для уведомления пользователя
        translator_hub: Хаб переводчиков для локализации уведомления пользователю
        answer: Функция для отправки ответа администратору

    Returns:
        True если решение успешно обработано, False в противном случае
    """
    # Получаем запрос из базы данных
    request = await db.partner_requests.get_request(user_id=target_user_id)
    if request is None:
        await answer(i18n.partner.approve.missing())
        return False

    # Получаем информацию о пользователе
    target_user = await db.users.get_user_record(user_id=target_user_id)
    if target_user is None:
        await answer(i18n.partner.approve.user.missing())
        return False

    # Получаем переводчик для пользователя (для уведомления на его языке)
    user_i18n = _get_user_i18n(translator_hub, target_user, i18n)

    if action == "approve":
        # Проверяем, что запрос еще не был обработан
        if request.status == PartnerRequestStatus.APPROVED:
            await answer(i18n.partner.approve.already())
            return False
        if request.status == PartnerRequestStatus.REJECTED:
            await answer(i18n.partner.request.already.rejected())
            return False

        # Одобряем запрос
        await db.partner_requests.set_approved(
            user_id=target_user_id,
            approved_by=admin_id,  # Сохраняем ID администратора, который одобрил
        )
        await db.users.update_role(user_id=target_user_id, role=UserRole.PARTNER)

        # Уведомляем пользователя об одобрении
        try:
            await bot.send_message(target_user_id, user_i18n.partner.request.approved())
        except Exception as exc:
            logger.warning(
                "Failed to notify user %s about approval: %s",
                target_user_id,
                exc,
            )

        await answer(i18n.partner.decision.approved())
        return True

    if action == "reject":
        # Проверяем, что запрос еще не был обработан
        if request.status == PartnerRequestStatus.REJECTED:
            await answer(i18n.partner.request.already.rejected())
            return False
        if request.status == PartnerRequestStatus.APPROVED:
            await answer(i18n.partner.approve.already())
            return False

        # Отклоняем запрос
        await db.partner_requests.set_rejected(
            user_id=target_user_id,
            rejected_by=admin_id,  # Сохраняем ID администратора, который отклонил
        )

        # Уведомляем пользователя об отклонении
        try:
            await bot.send_message(target_user_id, user_i18n.partner.request.rejected())
        except Exception as exc:
            logger.warning(
                "Failed to notify user %s about rejection: %s",
                target_user_id,
                exc,
            )

        await answer(i18n.partner.decision.rejected())
        return True

    # Некорректное действие
    await answer(i18n.partner.request.invalid())
    return False


async def send_partner_requests_list(
        *,
        admin_id: int,
        i18n: TranslatorRunner,
        db: DB,
        bot: Bot,
) -> None:
    """
    Отправляет администратору список всех ожидающих запросов на партнерство.

    Вызывается по команде администратора для просмотра всех заявок.

    Args:
        admin_id: ID администратора, запрашивающего список
        i18n: Переводчик для локализации текста
        db: Объект базы данных
        bot: Экземпляр бота для отправки сообщений
    """
    # Получаем список ожидающих запросов
    pending_requests = await db.partner_requests.list_pending_requests()

    if not pending_requests:
        # Если нет ожидающих запросов
        await bot.send_message(admin_id, text=i18n.partner.request.list.empty())
        return

    # Отправляем заголовок с количеством запросов
    await bot.send_message(
        admin_id,
        text=i18n.partner.request.list.header(count=len(pending_requests)),
    )

    # Отправляем каждый запрос отдельным сообщением с клавиатурой
    for request in pending_requests:
        await bot.send_message(
            admin_id,
            text=i18n.partner.request.list.item(user_id=request.user_id),
            reply_markup=_build_partner_request_list_item_keyboard(
                i18n, request.user_id
            ),
        )


async def handle_partner_decision_callback(
        callback: CallbackQuery,
        i18n: TranslatorRunner,
        db: DB,
        bot: Bot,
        translator_hub: TranslatorHub,
) -> None:
    """
    Обрабатывает callback от администратора по решению запроса партнерства.

    Args:
        callback: Callback запрос от администратора
        i18n: Переводчик для локализации ответов
        db: Объект базы данных
        bot: Экземпляр бота для уведомлений
        translator_hub: Хаб переводчиков для локализации уведомлений пользователям
    """
    # Проверяем права администратора
    admin_record = await db.users.get_user_record(user_id=callback.from_user.id)
    if admin_record is None or admin_record.role != UserRole.ADMIN:
        await callback.answer(text=i18n.partner.approve.forbidden())
        return

    # Проверяем наличие callback данных
    if not callback.data:
        await callback.answer(text=i18n.partner.request.invalid())
        return

    # Парсим callback данные
    parsed = _parse_decision_callback(callback.data)
    if not parsed:
        await callback.answer(text=i18n.partner.request.invalid())
        return

    # Извлекаем действие и ID пользователя
    action, target_user_id = parsed

    # Обрабатываем решение
    decision_done = await _decide_partner_request(
        action=action,
        target_user_id=target_user_id,
        admin_id=callback.from_user.id,
        i18n=i18n,
        db=db,
        bot=bot,
        translator_hub=translator_hub,
        answer=callback.answer,
    )

    # Если решение успешно обработано, убираем кнопки из сообщения
    if decision_done and callback.message:
        try:
            await callback.message.edit_reply_markup(reply_markup=None)
        except Exception as exc:
            logger.warning("Failed to update admin message: %s", exc)
