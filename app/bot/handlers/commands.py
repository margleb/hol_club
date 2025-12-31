import logging
from datetime import datetime, timedelta, timezone
from urllib.parse import unquote

from aiogram import Bot, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from aiogram_dialog import DialogManager, StartMode
from fluentogram import TranslatorRunner
from taskiq import ScheduledTask
from taskiq_redis import RedisScheduleSource

from app.bot.enums.roles import UserRole
from app.bot.filters.dialog_filters import DialogStateFilter, DialogStateGroupFilter
from app.bot.states.settings import SettingsSG
from app.bot.dialogs.events.utils import build_event_text
from app.bot.states.start import StartSG
from app.infrastructure.database.database.db import DB
from app.infrastructure.database.models.events import EventsModel
from app.infrastructure.database.models.users import UsersModel
from app.services.delay_service.publisher import delay_message_deletion
from app.services.scheduler.tasks import (
    dynamic_periodic_task,
    scheduled_task,
    simple_task,
)
from app.bot.handlers.event_registrations import EVENT_REGISTER_CALLBACK
from nats.js.client import JetStreamContext

logger = logging.getLogger(__name__)

commands_router = Router()


def _extract_start_payload(text: str | None) -> str | None:
    if not text:
        return None
    text = text.strip()
    if " " in text:
        _, payload = text.split(maxsplit=1)
        return payload.strip() or None
    if "?" in text:
        _, payload = text.split("?", 1)
        return payload.strip() or None
    return None


def _parse_outer_start_payload(payload: str | None) -> tuple[int, str, str, str] | None:
    if not payload:
        return None
    payload = unquote(payload.strip())
    if not payload:
        return None
    if payload.startswith("start="):
        payload = payload.split("=", 1)[1]
    payload = payload.strip()
    if not payload:
        return None
    left, sep, price = payload.rpartition("_")
    if not sep or not price:
        return None
    parts = left.split("_", 2)
    if len(parts) != 3:
        return None
    event_id_raw, placement_date, channel_username = parts
    if not placement_date or not channel_username:
        return None
    try:
        event_id = int(event_id_raw)
    except ValueError:
        return None
    channel_username = channel_username.lstrip("@")
    if not channel_username:
        return None
    return event_id, placement_date, channel_username, price


async def _maybe_register_outer_start(
    *,
    db: DB,
    user_id: int,
    user_role: UserRole,
    message_text: str | None,
) -> tuple[bool, EventsModel] | None:
    if user_role != UserRole.USER:
        return None
    payload = _parse_outer_start_payload(_extract_start_payload(message_text))
    if not payload:
        return None
    event_id, placement_date, channel_username, placement_price = payload
    event = await db.events.get_event_by_id(event_id=event_id)
    if event is None:
        return None
    created = await db.event_registrations.create_registration(
        event_id=event_id,
        user_id=user_id,
        source="outer",
        is_registered=False,
    )
    if created:
        await db.event_registrations.store_interest_source(
            event_id=event_id,
            user_id=user_id,
            placement_date=placement_date,
            channel_username=channel_username,
            placement_price=placement_price,
        )
        await db.adv_stats.increment_interesting(
            event_id=event_id,
            placement_date=placement_date,
            channel_username=channel_username,
            placement_price=placement_price,
        )
    return created, event


def _build_outer_start_keyboard(
    *,
    i18n: TranslatorRunner,
    event_id: int,
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=i18n.partner.event.register.button(),
                    callback_data=f"{EVENT_REGISTER_CALLBACK}:{event_id}",
                )
            ]
        ]
    )


def _build_event_payload(event: EventsModel) -> dict:
    return {
        "name": event.name,
        "datetime": event.event_datetime,
        "address": event.address,
        "description": event.description,
        "is_paid": event.is_paid,
        "price": event.price,
        "age_group": event.age_group,
    }


@commands_router.message(CommandStart())
async def process_start_command(
    message: Message,
    dialog_manager: DialogManager,
    i18n: TranslatorRunner,
    db: DB,
    bot: Bot,
) -> None:
    if not message.from_user:
        return
    user_record: UsersModel | None = await db.users.get_user_record(user_id=message.from_user.id)
    if user_record is None:
        await db.users.add(
            user_id=message.from_user.id, 
            language=message.from_user.language_code,
            role=UserRole.USER
        )
        user_role = UserRole.USER
    else:
        user_role = user_record.role
    outer_result = await _maybe_register_outer_start(
        db=db,
        user_id=message.from_user.id,
        user_role=user_role,
        message_text=message.text,
    )
    if outer_result:
        created, event = outer_result
        if created:
            outer_keyboard = _build_outer_start_keyboard(
                i18n=i18n,
                event_id=event.id,
            )
            if event.channel_id and event.channel_message_id:
                try:
                    await bot.copy_message(
                        chat_id=message.from_user.id,
                        from_chat_id=event.channel_id,
                        message_id=event.channel_message_id,
                        reply_markup=outer_keyboard,
                    )
                    return
                except Exception as exc:
                    logger.warning(
                        "Failed to copy event announcement to user %s: %s",
                        message.from_user.id,
                        exc,
                    )
            event_text = build_event_text(_build_event_payload(event), i18n)
            try:
                if event.photo_file_id:
                    await bot.send_photo(
                        message.from_user.id,
                        photo=event.photo_file_id,
                        caption=event_text,
                        reply_markup=outer_keyboard,
                    )
                else:
                    await bot.send_message(
                        message.from_user.id,
                        text=event_text,
                        reply_markup=outer_keyboard,
                    )
            except Exception as exc:
                logger.warning(
                    "Failed to send event announcement to user %s: %s",
                    message.from_user.id,
                    exc,
                )
            return
    await dialog_manager.start(state=StartSG.start, mode=StartMode.RESET_STACK)


# Этот хэндлер будет срабатывать на команду /del
@commands_router.message(Command('del'))
async def send_and_del_message(
    message: Message, 
    i18n: TranslatorRunner, 
    js: JetStreamContext, 
    delay_del_subject: str
) -> None:
    
    delay = 3
    msg: Message = await message.answer(text=i18n.will.delete(delay=delay))
    
    await delay_message_deletion(
        js=js,  
        chat_id=msg.chat.id, 
        message_id=msg.message_id,
        subject=delay_del_subject, 
        delay=delay
    )


@commands_router.message(Command('simple'))
async def task_handler(
    message: Message, 
    i18n: TranslatorRunner, 
    redis_source: RedisScheduleSource
) -> None:
    await simple_task.kiq()
    await message.answer(text=i18n.simple.task())


@commands_router.message(Command('delay'))
async def delay_task_handler(
    message: Message, 
    i18n: TranslatorRunner, 
    redis_source: RedisScheduleSource
) -> None:
    await scheduled_task.schedule_by_time(
        source=redis_source, 
        time=datetime.now(timezone.utc) + timedelta(seconds=5)
    )
    await message.answer(text=i18n.task.soon())


@commands_router.message(Command('periodic'))
async def dynamic_periodic_task_handler(
    message: Message,
    i18n: TranslatorRunner,
    state: FSMContext,
    redis_source: RedisScheduleSource
) -> None:
    periodic_task: ScheduledTask = await dynamic_periodic_task.schedule_by_cron(
        source=redis_source, 
        cron='*/2 * * * *'
    )

    data: dict = await state.get_data()
    if data.get('periodic_tasks') is None:
        data['periodic_tasks'] = []
    
    data['periodic_tasks'].append(periodic_task.schedule_id)

    await state.set_data(data)

    await message.answer(text=i18n.periodic.task())


@commands_router.message(Command('del_periodic'))
async def delete_all_periodic_tasks_handler(
    message: Message,
    i18n: TranslatorRunner,
    state: FSMContext,
    redis_source: RedisScheduleSource
) -> None:
    data = await state.get_data()
    if data.get('periodic_tasks') is None:
        await message.answer(text=i18n.no.periodic.tasks())
    else:
        for task_id in data.get('periodic_tasks'):
            await redis_source.delete_schedule(task_id)
        await message.answer(text=i18n.periodic.tasks.deleted())


@commands_router.message(~DialogStateGroupFilter(state_group=SettingsSG), Command('lang'))
async def process_lang_command_sg(
    message: Message,
    dialog_manager: DialogManager,
    i18n: TranslatorRunner
) -> None:
    await dialog_manager.start(state=SettingsSG.lang)


@commands_router.message(
        DialogStateGroupFilter(state_group=SettingsSG), 
        ~DialogStateFilter(state=SettingsSG.lang), 
        Command('lang')
    )
async def process_lang_command(
    message: Message,
    dialog_manager: DialogManager,
    i18n: TranslatorRunner
) -> None:
    await dialog_manager.switch_to(state=SettingsSG.lang)


@commands_router.message(Command('help'))
async def process_help_command(
    message: Message,
    dialog_manager: DialogManager,
    i18n: TranslatorRunner
) -> None:
    await message.answer(
        text=i18n.help.command(),
    )
