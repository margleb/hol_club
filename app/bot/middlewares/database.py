import logging
from typing import Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import Update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.infrastructure.database.database.db import DB

logger = logging.getLogger(__name__)


class DataBaseMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Update, dict[str, any]], Awaitable[None]],
        event: Update,
        data: dict[str, any]
    ) -> any:
        session_maker: async_sessionmaker = data.get('_db_sessionmaker')

        async with session_maker() as session:
            try:
                data['db'] = DB(session)
                event_from_user = data.get("event_from_user")
                if event_from_user is not None:
                    await data["db"].users.mark_reachable_on_incoming(
                        user_id=event_from_user.id
                    )
                result = await handler(event, data)
                await session.commit()
                return result
            except SQLAlchemyError as e:
                await session.rollback()
                logger.exception('Transaction rolled back due to error: %s', e)
                raise
