import asyncio
import logging
from contextlib import suppress

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
from app.services.advcake.poller import start_advcake_poller
from app.services.profile_nudges.poller import start_profile_nudges_poller
from config.config import settings

logger = logging.getLogger(__name__)


def _to_int(value: object, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _to_bool(value: object, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


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

    advcake_task = None
    advcake_settings = settings.get("advcake", {}) or {}
    advcake_api_key = str(advcake_settings.get("api_key") or "").strip()
    advcake_interval = int(advcake_settings.get("poll_interval_seconds") or 600)
    advcake_days = int(advcake_settings.get("days") or 2)
    if advcake_api_key:
        advcake_task = asyncio.create_task(
            start_advcake_poller(
                bot=bot,
                db_sessionmaker=db_session_maker,
                translator_hub=translator_hub,
                api_key=advcake_api_key,
                event_private_chat_service=event_private_chat_service,
                poll_interval_seconds=advcake_interval,
                days=advcake_days,
            )
        )
        logger.info("AdvCake poller started")
    else:
        logger.info("AdvCake poller disabled: missing api key")

    profile_nudges_task = None
    profile_nudges_settings = settings.get("profile_nudges", {}) or {}
    profile_nudges_enabled = _to_bool(
        profile_nudges_settings.get("enabled"),
        True,
    )
    if profile_nudges_enabled:
        profile_nudges_task = asyncio.create_task(
            start_profile_nudges_poller(
                bot=bot,
                db_sessionmaker=db_session_maker,
                translator_hub=translator_hub,
                poll_interval_seconds=_to_int(
                    profile_nudges_settings.get("poll_interval_seconds"),
                    600,
                ),
                first_delay_minutes=_to_int(
                    profile_nudges_settings.get("first_delay_minutes"),
                    15,
                ),
                remind_delay_hours=_to_int(
                    profile_nudges_settings.get("remind_delay_hours"),
                    24,
                ),
                max_attempts=_to_int(
                    profile_nudges_settings.get("max_attempts"),
                    2,
                ),
                batch_size=_to_int(
                    profile_nudges_settings.get("batch_size"),
                    200,
                ),
            )
        )
        logger.info("Profile nudges poller started")
    else:
        logger.info("Profile nudges poller disabled")

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
        if profile_nudges_task:
            profile_nudges_task.cancel()
            with suppress(asyncio.CancelledError):
                await profile_nudges_task
        if advcake_task:
            advcake_task.cancel()
            with suppress(asyncio.CancelledError):
                await advcake_task
        await nc.close()
        logger.info('Connection to NATS closed')
        await db_engine.dispose()
        logger.info('Connection to Postgres closed')
        await event_private_chat_service.disconnect()
        if dp.workflow_data.get('_cache_pool'):
            await cache_pool.close()
            logger.info('Connection to Redis closed')
