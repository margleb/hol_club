import logging
from datetime import datetime, timezone

from sqlalchemy import delete, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models.events import EventsModel

logger = logging.getLogger(__name__)


class _EventsDB:
    __tablename__ = "events"

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_event(
        self,
        *,
        partner_user_id: int,
        name: str,
        event_datetime: str,
        address: str,
        description: str,
        is_paid: bool,
        price: str | None,
        age_group: str | None,
        notify_users: bool,
        photo_file_id: str | None,
        fingerprint: str,
    ) -> int | None:
        stmt = (
            insert(EventsModel)
            .values(
                partner_user_id=partner_user_id,
                name=name,
                event_datetime=event_datetime,
                address=address,
                description=description,
                is_paid=is_paid,
                price=price,
                age_group=age_group,
                notify_users=notify_users,
                photo_file_id=photo_file_id,
                fingerprint=fingerprint,
            )
            .on_conflict_do_nothing(index_elements=["fingerprint"])
            .returning(EventsModel.id)
        )
        result = await self.session.execute(stmt)
        event_id = result.scalar_one_or_none()
        if event_id is not None:
            logger.info(
                "Event created. db='%s', event_id=%d, partner_user_id=%d",
                self.__tablename__,
                event_id,
                partner_user_id,
            )
        return event_id

    async def mark_event_published(
        self,
        *,
        event_id: int,
        channel_id: int,
        channel_message_id: int,
    ) -> None:
        stmt = (
            update(EventsModel)
            .where(EventsModel.id == event_id)
            .values(
                channel_id=channel_id,
                channel_message_id=channel_message_id,
                published_at=datetime.now(timezone.utc),
            )
        )
        await self.session.execute(stmt)
        logger.info(
            "Event published. db='%s', event_id=%d, channel_id=%d, message_id=%d",
            self.__tablename__,
            event_id,
            channel_id,
            channel_message_id,
        )

    async def delete_event(self, *, event_id: int) -> None:
        stmt = delete(EventsModel).where(EventsModel.id == event_id)
        await self.session.execute(stmt)
        logger.info(
            "Event deleted. db='%s', event_id=%d",
            self.__tablename__,
            event_id,
        )
