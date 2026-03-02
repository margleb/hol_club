import logging
from datetime import datetime, timezone

from sqlalchemy import delete, select, update
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
        organizer_user_id: int,
        name: str,
        event_datetime: str,
        address: str,
        description: str,
        is_paid: bool,
        price: str | None,
        commission_percent: int,
        age_group: str | None,
        photo_file_id: str | None,
        fingerprint: str,
        prepay_percent: int | None = None,
        prepay_fixed_free: int | None = None,
    ) -> int | None:
        stmt = (
            insert(EventsModel)
            .values(
                organizer_user_id=organizer_user_id,
                name=name,
                event_datetime=event_datetime,
                address=address,
                description=description,
                is_paid=is_paid,
                price=price,
                commission_percent=commission_percent,
                age_group=age_group,
                prepay_percent=prepay_percent,
                prepay_fixed_free=prepay_fixed_free,
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
                "Event created. db='%s', event_id=%d, organizer_user_id=%d",
                self.__tablename__,
                event_id,
                organizer_user_id,
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

    async def mark_event_private_chat(
        self,
        *,
        event_id: int,
        chat_id: int,
        invite_link: str,
    ) -> None:
        stmt = (
            update(EventsModel)
            .where(EventsModel.id == event_id)
            .values(
                male_chat_id=chat_id,
                male_thread_id=None,
                male_message_id=None,
                male_chat_username=None,
                female_chat_id=chat_id,
                female_thread_id=None,
                female_message_id=None,
                female_chat_username=None,
                private_chat_invite_link=invite_link,
            )
        )
        await self.session.execute(stmt)
        logger.info(
            "Event private chat saved. db='%s', event_id=%d",
            self.__tablename__,
            event_id,
        )

    async def delete_event(self, *, event_id: int) -> None:
        stmt = delete(EventsModel).where(EventsModel.id == event_id)
        await self.session.execute(stmt)
        logger.info(
            "Event deleted. db='%s', event_id=%d",
            self.__tablename__,
            event_id,
        )

    async def get_event_by_id(
        self,
        *,
        event_id: int,
        for_update: bool = False,
    ) -> EventsModel | None:
        stmt = select(EventsModel).where(EventsModel.id == event_id)
        if for_update:
            stmt = stmt.with_for_update()
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_event_by_channel_message(
        self,
        *,
        channel_id: int,
        message_id: int,
    ) -> EventsModel | None:
        stmt = (
            select(EventsModel)
            .where(EventsModel.channel_id == channel_id)
            .where(EventsModel.channel_message_id == message_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_organizer_upcoming(
        self,
        *,
        organizer_user_id: int,
        limit: int = 10,
        offset: int = 0,
    ) -> list[EventsModel]:
        now = datetime.now().strftime("%Y.%m.%d %H:%M")
        stmt = (
            select(EventsModel)
            .where(EventsModel.organizer_user_id == organizer_user_id)
            .where(EventsModel.event_datetime >= now)
            .order_by(EventsModel.event_datetime.asc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
