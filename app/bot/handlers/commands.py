import logging

from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message
from aiogram_dialog import DialogManager, StartMode
from fluentogram import TranslatorRunner

from app.bot.enums.roles import UserRole
from app.bot.handlers.event_chats import (
    handle_event_chat_start,
    parse_event_chat_start_payload,
)
from app.bot.services.general_registration import parse_general_start_payload
from app.bot.states.account import AccountSG
from app.bot.states.general_registration import GeneralRegistrationSG
from app.bot.states.start import StartSG
from app.infrastructure.database.database.db import DB
from app.infrastructure.database.models.users import UsersModel

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

    # 3. Попытка обработки рекламной ссылки
    general_payload = parse_general_start_payload(message.text)
    if general_payload and user_role == UserRole.USER:
        if user_record and user_record.gender and user_record.age_group:
            await message.answer(i18n.general.registration.already())
            return
        placement_date, channel_username, placement_price = general_payload
        await dialog_manager.start(
            state=GeneralRegistrationSG.gender,
            mode=StartMode.RESET_STACK,
            data={
                "adv_payload": {
                    "placement_date": placement_date,
                    "channel_username": channel_username,
                    "placement_price": placement_price,
                }
            },
        )
        return

    # 4. Обязательная анкета для первого входа
    if user_role == UserRole.USER:
        has_profile = bool(
            user_record
            and user_record.gender
            and user_record.age_group
            and user_record.intent
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
