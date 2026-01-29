import logging
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.enums.event_registrations import EventRegistrationStatus
from app.infrastructure.database.models.users import UsersModel
from app.infrastructure.database.models.events import EventsModel
from app.infrastructure.database.models.event_registrations import EventRegistrationsModel

logger = logging.getLogger(__name__)


class _EventRegistrationsDB:
    __tablename__ = "event_registrations"

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_user_event(
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

    async def create(
        self,
        *,
        event_id: int,
        user_id: int,
        status: EventRegistrationStatus,
        amount: int | None = None,
    ) -> None:
        stmt = (
            insert(EventRegistrationsModel)
            .values(
                event_id=event_id,
                user_id=user_id,
                status=status,
                amount=amount,
            )
            .on_conflict_do_nothing(
                index_elements=["event_id", "user_id"]
            )
        )
        await self.session.execute(stmt)
        logger.info(
            "Event registration created. db='%s', event_id=%d, user_id=%d, status=%s",
            self.__tablename__,
            event_id,
            user_id,
            status.value,
        )

    async def update_status(
        self,
        *,
        event_id: int,
        user_id: int,
        status: EventRegistrationStatus,
    ) -> None:
        stmt = (
            update(EventRegistrationsModel)
            .where(EventRegistrationsModel.event_id == event_id)
            .where(EventRegistrationsModel.user_id == user_id)
            .values(status=status)
        )
        await self.session.execute(stmt)
        logger.info(
            "Event registration updated. db='%s', event_id=%d, user_id=%d, status=%s",
            self.__tablename__,
            event_id,
            user_id,
            status.value,
        )

    async def mark_paid_confirmed(
        self,
        *,
        event_id: int,
        user_id: int,
    ) -> None:
        stmt = (
            update(EventRegistrationsModel)
            .where(EventRegistrationsModel.event_id == event_id)
            .where(EventRegistrationsModel.user_id == user_id)
            .values(
                status=EventRegistrationStatus.CONFIRMED,
                paid_confirmed_at=datetime.now(timezone.utc),
            )
        )
        await self.session.execute(stmt)
        logger.info(
            "Event registration payment confirmed. db='%s', event_id=%d, user_id=%d",
            self.__tablename__,
            event_id,
            user_id,
        )

    async def mark_attended_confirmed(
        self,
        *,
        event_id: int,
        user_id: int,
    ) -> None:
        stmt = (
            update(EventRegistrationsModel)
            .where(EventRegistrationsModel.event_id == event_id)
            .where(EventRegistrationsModel.user_id == user_id)
            .values(
                status=EventRegistrationStatus.ATTENDED_CONFIRMED,
                attended_confirmed_at=datetime.now(timezone.utc),
            )
        )
        await self.session.execute(stmt)
        logger.info(
            "Event attendance confirmed. db='%s', event_id=%d, user_id=%d",
            self.__tablename__,
            event_id,
            user_id,
        )

    async def list_by_event_and_status(
        self,
        *,
        event_id: int,
        status: EventRegistrationStatus,
    ) -> list[tuple[int, str | None, EventRegistrationStatus, int | None]]:
        stmt = (
            select(
                EventRegistrationsModel.user_id,
                UsersModel.username,
                EventRegistrationsModel.status,
                EventRegistrationsModel.amount,
            )
            .join(UsersModel, UsersModel.user_id == EventRegistrationsModel.user_id)
            .where(EventRegistrationsModel.event_id == event_id)
            .where(EventRegistrationsModel.status == status)
            .order_by(EventRegistrationsModel.created.asc())
        )
        result = await self.session.execute(stmt)
        return [
            (row[0], row[1], row[2], row[3])
            for row in result.all()
        ]

    async def list_user_events(
        self,
        *,
        user_id: int,
        statuses: list[EventRegistrationStatus],
    ) -> list[tuple[int, str, str, EventRegistrationStatus, bool]]:
        stmt = (
            select(
                EventRegistrationsModel.event_id,
                EventsModel.name,
                EventsModel.event_datetime,
                EventRegistrationsModel.status,
                EventsModel.is_paid,
            )
            .join(EventsModel, EventsModel.id == EventRegistrationsModel.event_id)
            .where(EventRegistrationsModel.user_id == user_id)
            .where(EventRegistrationsModel.status.in_(statuses))
            .order_by(EventsModel.event_datetime.asc())
        )
        result = await self.session.execute(stmt)
        return [
            (row[0], row[1], row[2], row[3], row[4])
            for row in result.all()
        ]
