import logging

from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, Message
from aiogram_dialog import DialogManager, StartMode
from fluentogram import TranslatorRunner

from app.bot.enums.roles import UserRole
from app.bot.handlers.event_chats import (
    handle_event_chat_start,
    handle_event_buy_start,
    parse_event_chat_start_payload,
    parse_event_buy_start_payload,
)
from app.bot.services.registration import parse_general_start_payload
from app.bot.states.account import AccountSG
from app.bot.states.registration import GeneralRegistrationSG
from app.bot.states.start import StartSG
from app.infrastructure.database.database.db import DB
from app.infrastructure.database.models.users import UsersModel
from app.services.profile_nudges.poller import PROFILE_NUDGE_CONTINUE_CALLBACK

logger = logging.getLogger(__name__)

commands_router = Router()


@commands_router.message(CommandStart())
async def process_start_command(
    message: Message,
    dialog_manager: DialogManager,
    i18n: TranslatorRunner,
    db: DB,
) -> None:
    if not message.from_user:
        return

    # 1. Инициализация/получение пользователя
    user_record: UsersModel | None = await db.users.get_user_record(
        user_id=message.from_user.id
    )
    if user_record is None:
        await db.users.add(
            user_id=message.from_user.id,
            username=message.from_user.username,
            role=UserRole.USER
        )
        user_role = UserRole.USER
    else:
        if user_record.username != message.from_user.username:
            await db.users.update_username(
                user_id=message.from_user.id,
                username=message.from_user.username,
            )
        user_role = user_record.role

    # 2. Попытка обработки event chat ссылки
    event_chat_id = parse_event_chat_start_payload(message.text)
    if event_chat_id is not None:
        await handle_event_chat_start(
            message=message,
            i18n=i18n,
            db=db,
            event_id=event_chat_id,
        )
        return

    # 2.1 Попытка обработки event buy ссылки
    event_buy_id = parse_event_buy_start_payload(message.text)
    if event_buy_id is not None:
        await handle_event_buy_start(
            message=message,
            i18n=i18n,
            db=db,
            event_id=event_buy_id,
        )
        return

    # 3. Попытка обработки рекламной ссылки
    general_payload = parse_general_start_payload(message.text)
    if general_payload and user_role == UserRole.USER:
        placement_date, channel_username, placement_price = general_payload
        await db.adv_stats.register_general(
            user_id=message.from_user.id,
            placement_date=placement_date,
            channel_username=channel_username,
            placement_price=placement_price,
        )
        if user_record and user_record.gender and user_record.age_group:
            await message.answer(i18n.general.registration.already())
            return
        await dialog_manager.start(
            state=GeneralRegistrationSG.gender,
            mode=StartMode.RESET_STACK,
        )
        return

    # 4. Обязательная анкета для первого входа
    if user_role == UserRole.USER:
        has_profile = bool(
            user_record
            and user_record.gender
            and user_record.age_group
        )
        if not has_profile:
            await dialog_manager.start(
                state=AccountSG.intro,
                mode=StartMode.RESET_STACK,
                data={"force_profile": True},
            )
            return

    # 5. Стандартный запуск диалога
    await dialog_manager.start(
        state=StartSG.start,
        mode=StartMode.RESET_STACK
    )


@commands_router.message(Command('help'))
async def process_help_command(
    message: Message,
    dialog_manager: DialogManager,
    i18n: TranslatorRunner
) -> None:
    await message.answer(
        text=i18n.help.command(),
    )


@commands_router.callback_query(
    lambda callback: callback.data == PROFILE_NUDGE_CONTINUE_CALLBACK
)
async def process_profile_nudge_continue(
    callback: CallbackQuery,
    dialog_manager: DialogManager,
    i18n: TranslatorRunner,
    db: DB,
) -> None:
    user = callback.from_user
    if not user:
        await callback.answer()
        return

    user_record = await db.users.get_user_record(user_id=user.id)
    has_profile = bool(user_record and user_record.gender and user_record.age_group)
    if has_profile:
        await callback.answer(i18n.general.registration.already())
        await dialog_manager.start(
            state=StartSG.start,
            mode=StartMode.RESET_STACK,
        )
        return

    await callback.answer()
    await dialog_manager.start(
        state=AccountSG.intro,
        mode=StartMode.RESET_STACK,
        data={"force_profile": True},
    )
