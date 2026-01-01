import logging
from datetime import datetime, timedelta, timezone

from aiogram import Bot, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from aiogram_dialog import DialogManager, StartMode
from fluentogram import TranslatorRunner
from taskiq import ScheduledTask
from taskiq_redis import RedisScheduleSource

from app.bot.enums.roles import UserRole
from app.bot.filters.dialog_filters import DialogStateFilter, DialogStateGroupFilter
from app.bot.services.event_interesting import (
    maybe_interesting_outer_start,
    show_event_to_outer_user,
)
from app.bot.states.settings import SettingsSG
from app.bot.states.start import StartSG
from app.infrastructure.database.database.db import DB
from app.infrastructure.database.models.users import UsersModel
from app.services.delay_service.publisher import delay_message_deletion
from app.services.scheduler.tasks import (
    dynamic_periodic_task,
    scheduled_task,
    simple_task,
)
from nats.js.client import JetStreamContext

logger = logging.getLogger(__name__)

commands_router = Router()


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

    # 1. Инициализация/получение пользователя
    user_record: UsersModel | None = await db.users.get_user_record(
        user_id=message.from_user.id
    )
    if user_record is None:
        await db.users.add(
            user_id=message.from_user.id,
            language=message.from_user.language_code,
            role=UserRole.USER
        )
        user_role = UserRole.USER
    else:
        user_role = user_record.role

    # 2. Попытка обработки рекламной ссылки
    outer_result = await maybe_interesting_outer_start(
        db=db,
        user_id=message.from_user.id,
        user_role=user_role,
        message_text=message.text,
    )

    # 3. Если это рекламная ссылка и регистрация создана
    if outer_result:
        created, event = outer_result
        if created:
            # Выносим логику показа события в отдельную функцию
            await show_event_to_outer_user(
                bot=bot,
                user_id=message.from_user.id,
                event=event,
                i18n=i18n,
                logger=logger,
            )
            return

    # 4. Стандартный запуск диалога
    await dialog_manager.start(
        state=StartSG.start,
        mode=StartMode.RESET_STACK
    )


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
