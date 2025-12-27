import logging

from aiogram import Bot, Router
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, User
from fluentogram import TranslatorRunner

from app.bot.dialogs.events.handlers import EVENT_GOING_CALLBACK
from app.bot.enums.roles import UserRole
from app.infrastructure.database.database.db import DB
from app.infrastructure.database.models.users import UsersModel

logger = logging.getLogger(__name__)

event_registrations_router = Router()


EVENT_PAID_CALLBACK = "event_paid"


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
    )
    if not created:
        await callback.answer(i18n.partner.event.going.already())
        return

    partner_text = i18n.partner.event.going.notify.partner(
        username=_format_user_label(user),
        user_id=user.id,
        event_name=event.name,
    )
    partner_keyboard = _build_contact_keyboard(
        i18n=i18n,
        user_id=user.id,
        button_text=i18n.partner.event.going.contact.user.button(),
    )
    try:
        await bot.send_message(
            event.partner_user_id,
            text=partner_text,
            reply_markup=partner_keyboard,
        )
    except Exception as exc:
        logger.warning("Failed to notify partner %s: %s", event.partner_user_id, exc)

    partner_label = f"id:{event.partner_user_id}"
    try:
        partner_chat = await bot.get_chat(event.partner_user_id)
        if partner_chat.username:
            partner_label = f"@{partner_chat.username}"
        else:
            partner_label = partner_chat.full_name
    except Exception as exc:
        logger.warning("Failed to resolve partner %s: %s", event.partner_user_id, exc)

    thanks_text = i18n.partner.event.going.thanks(
        event_name=event.name,
        partner_username=partner_label,
    )
    thanks_keyboard = _build_thanks_keyboard(
        i18n=i18n,
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
) -> None:
    await callback.answer()

