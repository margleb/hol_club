from aiogram import Router
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from fluentogram import TranslatorRunner

from app.bot.dialogs.general_registration.getters import AGE_GROUPS
from app.bot.enums.roles import UserRole
from app.infrastructure.database.database.db import DB

event_chats_router = Router()

EVENT_JOIN_CHAT_CALLBACK = "event_join_chat"
EVENT_JOIN_CHAT_GENDER_CALLBACK = "event_join_chat_gender"
EVENT_JOIN_CHAT_AGE_CALLBACK = "event_join_chat_age"


def _parse_callback_parts(
    data: str | None,
    prefix: str,
    expected_parts: int,
) -> list[str] | None:
    if not data or not data.startswith(prefix):
        return None
    parts = data.split(":")
    if len(parts) != expected_parts:
        return None
    return parts


def _build_gender_keyboard(
    i18n: TranslatorRunner,
    event_id: int,
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=i18n.general.registration.gender.male(),
                    callback_data=f"{EVENT_JOIN_CHAT_GENDER_CALLBACK}:{event_id}:male",
                )
            ],
            [
                InlineKeyboardButton(
                    text=i18n.general.registration.gender.female(),
                    callback_data=f"{EVENT_JOIN_CHAT_GENDER_CALLBACK}:{event_id}:female",
                )
            ],
        ]
    )


def _build_age_keyboard(
    i18n: TranslatorRunner,
    event_id: int,
) -> InlineKeyboardMarkup:
    rows = []
    for age_group in AGE_GROUPS:
        rows.append(
            [
                InlineKeyboardButton(
                    text=i18n.general.registration.age.group(range=age_group),
                    callback_data=f"{EVENT_JOIN_CHAT_AGE_CALLBACK}:{event_id}:{age_group}",
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


async def _send_chat_link(
    *,
    callback: CallbackQuery,
    i18n: TranslatorRunner,
    chat_url: str,
) -> None:
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=i18n.partner.event.join.chat.button(),
                    url=chat_url,
                )
            ]
        ]
    )
    if callback.message:
        await callback.message.answer(
            i18n.partner.event.join.chat.text(),
            reply_markup=keyboard,
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
                reply_markup=_build_gender_keyboard(i18n, event_id),
            )
        await callback.answer()
        return

    if not age_group:
        if callback.message:
            await callback.message.answer(
                i18n.general.registration.age.prompt(),
                reply_markup=_build_age_keyboard(i18n, event_id),
            )
        await callback.answer()
        return

    chat_url = event.female_chat_url if gender == "female" else event.male_chat_url
    if not chat_url:
        await callback.answer(i18n.partner.event.join.chat.missing())
        return

    await _send_chat_link(callback=callback, i18n=i18n, chat_url=chat_url)
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
                reply_markup=_build_age_keyboard(i18n, event_id),
            )
        await callback.answer()
        return

    event = await db.events.get_event_by_id(event_id=event_id)
    if event is None:
        await callback.answer(i18n.partner.event.join.chat.missing())
        return

    chat_url = event.female_chat_url if gender == "female" else event.male_chat_url
    if not chat_url:
        await callback.answer(i18n.partner.event.join.chat.missing())
        return

    await _send_chat_link(callback=callback, i18n=i18n, chat_url=chat_url)
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
                reply_markup=_build_gender_keyboard(i18n, event_id),
            )
        await callback.answer()
        return

    event = await db.events.get_event_by_id(event_id=event_id)
    if event is None:
        await callback.answer(i18n.partner.event.join.chat.missing())
        return

    chat_url = event.female_chat_url if gender == "female" else event.male_chat_url
    if not chat_url:
        await callback.answer(i18n.partner.event.join.chat.missing())
        return

    await _send_chat_link(callback=callback, i18n=i18n, chat_url=chat_url)
    await callback.answer()
