import logging

from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, Message
from aiogram_dialog import DialogManager, StartMode
from fluentogram import TranslatorRunner

from app.bot.dialogs.start.event_dialogs import (
    EVENT_DIALOG_OPEN_CALLBACK,
    get_dialog_context_for_user,
)
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

    user_record: UsersModel | None = await db.users.get_user_record(
        user_id=message.from_user.id
    )
    if user_record is None:
        await db.users.add(
            user_id=message.from_user.id,
            username=message.from_user.username,
            role=UserRole.USER,
        )
    elif user_record.username != message.from_user.username:
        await db.users.update_username(
            user_id=message.from_user.id,
            username=message.from_user.username,
        )

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

    await dialog_manager.start(
        state=StartSG.start,
        mode=StartMode.RESET_STACK,
    )


@commands_router.message(Command("help"))
async def process_help_command(
    message: Message,
    i18n: TranslatorRunner,
) -> None:
    await message.answer(
        text=i18n.help.command(),
    )


@commands_router.callback_query(
    lambda callback: callback.data
    and callback.data.startswith(f"{EVENT_DIALOG_OPEN_CALLBACK}:")
)
async def process_event_dialog_open_callback(
    callback: CallbackQuery,
    dialog_manager: DialogManager,
    i18n: TranslatorRunner,
    db: DB,
) -> None:
    user = callback.from_user
    if user is None or not callback.data:
        return

    parts = callback.data.split(":")
    if len(parts) != 3:
        await callback.answer(i18n.partner.event.dialog.inaccessible())
        return

    try:
        event_id = int(parts[1])
        participant_user_id = int(parts[2])
    except ValueError:
        await callback.answer(i18n.partner.event.dialog.inaccessible())
        return

    context, is_organizer_view = await get_dialog_context_for_user(
        db=db,
        current_user_id=user.id,
        event_id=event_id,
        participant_user_id=participant_user_id,
    )
    if context is None:
        await callback.answer(i18n.partner.event.dialog.inaccessible())
        return

    await callback.answer()
    await dialog_manager.start(
        state=(
            StartSG.admin_event_dialog
            if is_organizer_view
            else StartSG.user_event_dialog
        ),
        data={
            "event_id": event_id,
            "participant_user_id": participant_user_id,
        },
        mode=StartMode.RESET_STACK,
    )
