import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import ExceptionTypeFilter
from aiogram_dialog import setup_dialogs
from aiogram_dialog.api.exceptions import UnknownIntent, UnknownState
from fluentogram import TranslatorHub

from app.bot.dialogs.events.dialogs import events_dialog
from app.bot.dialogs.account.dialogs import account_dialog
from app.bot.dialogs.registration.dialogs import general_registration_dialog
from app.bot.dialogs.start.dialogs import start_dialog
from app.bot.handlers.commands import commands_router
from app.bot.handlers.event_chats import event_chats_router
from app.bot.handlers.partner_requests import partner_requests_router
from app.bot.handlers.errors import on_unknown_intent, on_unknown_state
from app.bot.i18n.translator_hub import create_translator_hub
from app.bot.middlewares.database import DataBaseMiddleware
from app.bot.middlewares.i18n import TranslatorRunnerMiddleware
from app.infrastructure.cache.connect_to_redis import get_redis_pool
from app.infrastructure.database.connect_to_pg import get_pg_pool
from app.infrastructure.storage.storage.nats_storage import NatsStorage
from app.infrastructure.storage.storage.nats_key_builder import NatsKeyBuilder
from app.infrastructure.storage.nats_connect import connect_to_nats
from app.services.telegram.private_event_chats import EventPrivateChatService
from config.config import settings

logger = logging.getLogger(__name__)


async def main():
    logger.info("Starting bot")

    nc, js = await connect_to_nats(servers=settings.nats.servers)

    storage: NatsStorage = await NatsStorage(
        nc=nc, 
        js=js, 
        key_builder=NatsKeyBuilder(with_destiny=True, separator="_")
    ).create_storage()

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode(settings.bot.parse_mode))
    )
    dp = Dispatcher(storage=storage)

    if settings.cache.use_cache:
        cache_pool = await get_redis_pool(
            db=settings.redis.database,
            host=settings.redis.host,
            port=settings.redis.port,
            username=settings.redis_username,
            password=settings.redis_password,
        )
        dp.workflow_data.update(_cache_pool=cache_pool)

    db_engine, db_session_maker = await get_pg_pool(
        db_name=settings.postgres.db,
        host=settings.postgres.host,
        port=settings.postgres.port,
        user=settings.postgres_user,
        password=settings.postgres_password,
    )
    telethon_api_id_raw = settings.get("telethon_api_id")
    try:
        telethon_api_id = int(telethon_api_id_raw or 0)
    except (TypeError, ValueError):
        telethon_api_id = 0
    event_private_chat_service = EventPrivateChatService(
        api_id=telethon_api_id,
        api_hash=str(settings.get("telethon_api_hash") or ""),
        session=str(settings.get("telethon_session") or ""),
    )
    if not await event_private_chat_service.connect():
        logger.warning("Event private chat service is disabled")

    translator_hub: TranslatorHub = create_translator_hub()

    logger.info("Registering error handlers")
    dp.errors.register(
        on_unknown_intent,
        ExceptionTypeFilter(UnknownIntent),
    )
    dp.errors.register(
        on_unknown_state,
        ExceptionTypeFilter(UnknownState),
    )

    logger.info("Including routers")
    dp.include_routers(
        commands_router,
        event_chats_router,
        partner_requests_router,
        start_dialog,
        events_dialog,
        account_dialog,
        general_registration_dialog,
    )

    logger.info("Including middlewares")
    dp.update.middleware(DataBaseMiddleware())
    dp.update.middleware(TranslatorRunnerMiddleware())
    dp.errors.middleware(DataBaseMiddleware())
    dp.errors.middleware(TranslatorRunnerMiddleware())

    logger.info("Setting up dialogs")
    bg_factory = setup_dialogs(dp)

    # Launch polling
    try:
        await dp.start_polling(
            bot,
            bg_factory=bg_factory,
            bot_locales=sorted(settings.i18n.locales),
            translator_hub=translator_hub,
            _db_sessionmaker=db_session_maker,
            event_private_chat_service=event_private_chat_service,
        )
    except Exception as e:
        logger.exception(e)
    finally:
        await nc.close()
        logger.info('Connection to NATS closed')
        await db_engine.dispose()
        logger.info('Connection to Postgres closed')
        await event_private_chat_service.disconnect()
        if dp.workflow_data.get('_cache_pool'):
            await cache_pool.close()
            logger.info('Connection to Redis closed')
