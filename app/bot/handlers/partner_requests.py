"""Партнерские заявки: кнопка в канале, решение админом, уведомления."""

import logging
from typing import Awaitable, Callable

from aiogram import Bot, Router
from aiogram.filters import Command
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    User,
)
from fluentogram import TranslatorHub, TranslatorRunner

from config.config import settings
from app.bot.enums.partner_requests import PartnerRequestStatus
from app.bot.enums.roles import UserRole
from app.infrastructure.database.database.db import DB
from app.infrastructure.database.models.users import UsersModel

logger = logging.getLogger(__name__)

partner_requests_router = Router()

PARTNER_REQUEST_CALLBACK = "partner_request"
PARTNER_DECISION_CALLBACK = "partner_decision"

AnswerFunc = Callable[[str], Awaitable[None]]


def _get_partner_channel() -> str | None:
    """Берет канал партнерских заявок из настроек (ENV через Dynaconf)."""
    partner_cfg = settings.get("partner")
    if not partner_cfg:
        return None
    if isinstance(partner_cfg, dict):
        return partner_cfg.get("channel") or None
    return getattr(partner_cfg, "channel", None)


def _build_partner_request_keyboard(i18n: TranslatorRunner) -> InlineKeyboardMarkup:
    """Кнопка для пользователя в канале, чтобы отправить заявку."""
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
    """Кнопки для админа: принять/отклонить заявку пользователя."""
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


def _format_partner_username(user: User) -> str:
    """Показываем @username, иначе имя пользователя."""
    if user.username:
        return f"@{user.username}"
    return user.full_name


def _get_user_i18n(
    translator_hub: TranslatorHub,
    user_record: UsersModel | None,
    fallback: TranslatorRunner,
) -> TranslatorRunner:
    """Возвращает переводчик на основе языка пользователя."""
    if user_record and user_record.language:
        return translator_hub.get_translator_by_locale(user_record.language)
    return fallback


async def _ensure_user_record(db: DB, user: User) -> UsersModel:
    """Гарантирует наличие записи пользователя в базе."""
    user_record = await db.users.get_user_record(user_id=user.id)
    if user_record is not None:
        return user_record

    await db.users.add(
        user_id=user.id,
        language=user.language_code,
        role=UserRole.USER,
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
    """Уведомляет всех админов о новой заявке с кнопками решения."""
    admin_ids = await db.users.get_admin_user_ids()
    if not admin_ids:
        return

    text = i18n.partner.request.admin.notify(username=username, user_id=user_id)
    keyboard = _build_partner_decision_keyboard(i18n, user_id)
    for admin_id in admin_ids:
        try:
            await bot.send_message(admin_id, text=text, reply_markup=keyboard)
        except Exception as exc:
            logger.warning(
                "Failed to notify admin %s about partner request: %s",
                admin_id,
                exc,
            )


async def _process_partner_request(
    *,
    user: User,
    i18n: TranslatorRunner,
    db: DB,
    bot: Bot,
    answer: AnswerFunc,
) -> None:
    """Единая логика заявки для команды и callback-кнопки."""
    user_record = await _ensure_user_record(db, user)
    if user_record.role in {UserRole.ADMIN, UserRole.PARTNER}:
        await answer(i18n.partner.request.forbidden())
        return

    # Не дублируем логику между командой и callback.
    request = await db.partner_requests.get_request(user_id=user.id)
    if request is None:
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

    if request.status == PartnerRequestStatus.PENDING:
        await answer(i18n.partner.request.pending())
        return

    if request.status == PartnerRequestStatus.APPROVED:
        if user_record.role != UserRole.PARTNER:
            await db.users.update_role(user_id=user.id, role=UserRole.PARTNER)
        await answer(i18n.partner.request.approved())
        return

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
    """Парсит callback вида partner_decision:action:user_id."""
    parts = data.split(":")
    if len(parts) != 3:
        return None
    if parts[0] != PARTNER_DECISION_CALLBACK:
        return None
    action = parts[1]
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
    """Применяет решение админа и уведомляет пользователя."""
    request = await db.partner_requests.get_request(user_id=target_user_id)
    if request is None:
        await answer(i18n.partner.approve.missing())
        return False

    target_user = await db.users.get_user_record(user_id=target_user_id)
    if target_user is None:
        await answer(i18n.partner.approve.user.missing())
        return False

    user_i18n = _get_user_i18n(translator_hub, target_user, i18n)

    if action == "approve":
        if request.status == PartnerRequestStatus.APPROVED:
            await answer(i18n.partner.approve.already())
            return False
        if request.status == PartnerRequestStatus.REJECTED:
            await answer(i18n.partner.request.already.rejected())
            return False

        await db.partner_requests.set_approved(
            user_id=target_user_id,
            approved_by=admin_id,
        )
        await db.users.update_role(user_id=target_user_id, role=UserRole.PARTNER)
        # Уведомляем пользователя об одобрении.
        try:
            await bot.send_message(target_user_id, user_i18n.partner.request.approved())
        except Exception as exc:
            logger.warning("Failed to notify user %s about approval: %s", target_user_id, exc)
        await answer(i18n.partner.decision.approved())
        return True

    if action == "reject":
        if request.status == PartnerRequestStatus.REJECTED:
            await answer(i18n.partner.request.already.rejected())
            return False
        if request.status == PartnerRequestStatus.APPROVED:
            await answer(i18n.partner.approve.already())
            return False

        await db.partner_requests.set_rejected(
            user_id=target_user_id,
            rejected_by=admin_id,
        )
        # Уведомляем пользователя об отказе.
        try:
            await bot.send_message(target_user_id, user_i18n.partner.request.rejected())
        except Exception as exc:
            logger.warning("Failed to notify user %s about rejection: %s", target_user_id, exc)
        await answer(i18n.partner.decision.rejected())
        return True

    await answer(i18n.partner.request.invalid())
    return False


@partner_requests_router.message(Command("partner_post"))
async def process_partner_post_command(
    message: Message,
    i18n: TranslatorRunner,
    db: DB,
    bot: Bot,
) -> None:
    """Публикация сообщения с кнопкой заявки в канале (только админ)."""
    admin_record = await db.users.get_user_record(user_id=message.from_user.id)
    if admin_record is None or admin_record.role != UserRole.ADMIN:
        await message.answer(text=i18n.partner.approve.forbidden())
        return

    channel = _get_partner_channel()
    if not channel:
        await message.answer(text=i18n.partner.request.channel.missing())
        return

    try:
        await bot.send_message(
            chat_id=channel,
            text=i18n.partner.request.channel.text(),
            reply_markup=_build_partner_request_keyboard(i18n),
        )
    except Exception as exc:
        logger.warning("Failed to post partner request message: %s", exc)
        await message.answer(text=i18n.partner.request.channel.failed())
        return

    await message.answer(text=i18n.partner.request.channel.posted())


@partner_requests_router.message(Command("partner_request"))
async def process_partner_request_command(
    message: Message,
    i18n: TranslatorRunner,
    db: DB,
    bot: Bot,
) -> None:
    """Команда для отправки заявки напрямую в боте."""
    await _process_partner_request(
        user=message.from_user,
        i18n=i18n,
        db=db,
        bot=bot,
        answer=message.answer,
    )


@partner_requests_router.callback_query(
    lambda callback: callback.data == PARTNER_REQUEST_CALLBACK
)
async def process_partner_request_callback(
    callback: CallbackQuery,
    i18n: TranslatorRunner,
    db: DB,
    bot: Bot,
) -> None:
    """Обработка клика по кнопке заявки в канале."""
    await _process_partner_request(
        user=callback.from_user,
        i18n=i18n,
        db=db,
        bot=bot,
        answer=callback.answer,
    )


@partner_requests_router.callback_query(
    lambda callback: callback.data and callback.data.startswith(
        f"{PARTNER_DECISION_CALLBACK}:"
    )
)
async def process_partner_decision_callback(
    callback: CallbackQuery,
    i18n: TranslatorRunner,
    db: DB,
    bot: Bot,
    translator_hub: TranslatorHub,
) -> None:
    """Обработка решения админа по заявке."""
    admin_record = await db.users.get_user_record(user_id=callback.from_user.id)
    if admin_record is None or admin_record.role != UserRole.ADMIN:
        await callback.answer(text=i18n.partner.approve.forbidden())
        return

    if not callback.data:
        await callback.answer(text=i18n.partner.request.invalid())
        return

    parsed = _parse_decision_callback(callback.data)
    if not parsed:
        await callback.answer(text=i18n.partner.request.invalid())
        return

    action, target_user_id = parsed
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
    if decision_done and callback.message:
        # Убираем кнопки после успешного решения.
        try:
            await callback.message.edit_reply_markup(reply_markup=None)
        except Exception as exc:
            logger.warning("Failed to update admin message: %s", exc)


@partner_requests_router.message(Command("partner_approve"))
async def process_partner_approve_command(
    message: Message,
    i18n: TranslatorRunner,
    db: DB,
    bot: Bot,
    translator_hub: TranslatorHub,
) -> None:
    """Резервная команда одобрения по user_id."""
    admin_record = await db.users.get_user_record(user_id=message.from_user.id)
    if admin_record is None or admin_record.role != UserRole.ADMIN:
        await message.answer(text=i18n.partner.approve.forbidden())
        return

    if not message.text:
        await message.answer(text=i18n.partner.approve.usage())
        return

    command_parts = message.text.split(maxsplit=1)
    if len(command_parts) < 2:
        await message.answer(text=i18n.partner.approve.usage())
        return

    try:
        target_user_id = int(command_parts[1])
    except ValueError:
        await message.answer(text=i18n.partner.approve.usage())
        return

    await _decide_partner_request(
        action="approve",
        target_user_id=target_user_id,
        admin_id=message.from_user.id,
        i18n=i18n,
        db=db,
        bot=bot,
        translator_hub=translator_hub,
        answer=message.answer,
    )
