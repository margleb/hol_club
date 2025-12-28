import logging

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models.event_registrations import (
    EventRegistrationsModel,
)

logger = logging.getLogger(__name__)


class _EventRegistrationsDB:
    __tablename__ = "event_registrations"

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_registration(
        self,
        *,
        event_id: int,
        user_id: int,
        source: str,
    ) -> bool:
        stmt = (
            insert(EventRegistrationsModel)
            .values(
                event_id=event_id,
                user_id=user_id,
                source=source,
                is_paid=False,
            )
            .on_conflict_do_nothing(index_elements=["event_id", "user_id"])
            .returning(EventRegistrationsModel.id)
        )
        result = await self.session.execute(stmt)
        registration_id = result.scalar_one_or_none()
        if registration_id is not None:
            logger.info(
                "Event registration created. db='%s', id=%d, event_id=%d, user_id=%d",
                self.__tablename__,
                registration_id,
                event_id,
                user_id,
            )
            return True
        return False

    async def get_registration(
        self,
        *,
        event_id: int,
        user_id: int,
    ) -> EventRegistrationsModel | None:
        stmt = (
            select(EventRegistrationsModel)
            .where(EventRegistrationsModel.event_id == event_id)
            .where(EventRegistrationsModel.user_id == user_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def mark_paid(
        self,
        *,
        event_id: int,
        user_id: int,
    ) -> bool:
        stmt = (
            update(EventRegistrationsModel)
            .where(EventRegistrationsModel.event_id == event_id)
            .where(EventRegistrationsModel.user_id == user_id)
            .where(EventRegistrationsModel.is_paid.is_(False))
            .values(is_paid=True)
            .returning(EventRegistrationsModel.id)
        )
        result = await self.session.execute(stmt)
        registration_id = result.scalar_one_or_none()
        if registration_id is not None:
            logger.info(
                "Event registration marked paid. db='%s', id=%d, event_id=%d, user_id=%d",
                self.__tablename__,
                registration_id,
                event_id,
                user_id,
            )
            return True
        return False

    async def set_receipt(
        self,
        *,
        event_id: int,
        user_id: int,
        receipt: str,
    ) -> bool:
        stmt = (
            update(EventRegistrationsModel)
            .where(EventRegistrationsModel.event_id == event_id)
            .where(EventRegistrationsModel.user_id == user_id)
            .values(receipt=receipt)
            .returning(EventRegistrationsModel.id)
        )
        result = await self.session.execute(stmt)
        registration_id = result.scalar_one_or_none()
        if registration_id is not None:
            logger.info(
                "Event registration receipt stored. db='%s', id=%d, event_id=%d, user_id=%d",
                self.__tablename__,
                registration_id,
                event_id,
                user_id,
            )
            return True
        return False
