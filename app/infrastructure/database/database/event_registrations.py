import logging

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
