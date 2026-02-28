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
from app.bot.states.start import StartSG
from app.infrastructure.database.database.db import DB
from app.infrastructure.database.models.users import UsersModel
from app.services.telegram.private_event_chats import EventPrivateChatService

logger = logging.getLogger(__name__)

commands_router = Router()


@commands_router.message(CommandStart())
async def process_start_command(
    message: Message,
    dialog_manager: DialogManager,
    i18n: TranslatorRunner,
    db: DB,
    event_private_chat_service: EventPrivateChatService | None = None,
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
    else:
        if user_record.username != message.from_user.username:
            await db.users.update_username(
                user_id=message.from_user.id,
                username=message.from_user.username,
            )

    # 2. Попытка обработки event chat ссылки
    event_chat_id = parse_event_chat_start_payload(message.text)
    if event_chat_id is not None:
        await handle_event_chat_start(
            message=message,
            i18n=i18n,
            db=db,
            event_id=event_chat_id,
            event_private_chat_service=event_private_chat_service,
        )
        return

    # 3. Стандартный запуск диалога
    await dialog_manager.start(
        state=StartSG.start,
        mode=StartMode.RESET_STACK
    )


@commands_router.message(Command('help'))
async def process_help_command(
    message: Message,
    i18n: TranslatorRunner
) -> None:
    await message.answer(
        text=i18n.help.command(),
    )
