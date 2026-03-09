import logging
from datetime import datetime, timezone

from sqlalchemy import delete, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models.events import EventsModel
from app.utils.datetime import compute_private_chat_delete_at, now_utc

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
        event_datetime: datetime,
        address: str,
        description: str,
        price: str,
        commission_percent: int,
        age_group: str | None,
        photo_file_id: str | None,
        fingerprint: str,
        publish_target: str,
    ) -> int | None:
        stmt = (
            insert(EventsModel)
            .values(
                organizer_user_id=organizer_user_id,
                name=name,
                event_datetime=event_datetime,
                address=address,
                description=description,
                price=price,
                commission_percent=commission_percent,
                age_group=age_group,
                photo_file_id=photo_file_id,
                fingerprint=fingerprint,
                publish_target=publish_target,
                private_chat_delete_at=compute_private_chat_delete_at(event_datetime),
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
        channel_id: int | None = None,
        channel_message_id: int | None = None,
    ) -> None:
        values: dict[str, object] = {
            "published_at": datetime.now(timezone.utc),
        }
        if channel_id is not None:
            values["channel_id"] = channel_id
        if channel_message_id is not None:
            values["channel_message_id"] = channel_message_id
        stmt = (
            update(EventsModel)
            .where(EventsModel.id == event_id)
            .values(**values)
        )
        await self.session.execute(stmt)
        logger.info(
            "Event published. db='%s', event_id=%d, channel_id=%s, message_id=%s",
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
                private_chat_deleted_at=None,
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
        now = now_utc()
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

    async def list_private_chats_due_for_deletion(
        self,
        *,
        delete_before: datetime,
        limit: int = 20,
    ) -> list[EventsModel]:
        stmt = (
            select(EventsModel)
            .where(EventsModel.private_chat_delete_at.is_not(None))
            .where(EventsModel.private_chat_delete_at <= delete_before)
            .where(EventsModel.private_chat_deleted_at.is_(None))
            .where(
                (EventsModel.male_chat_id.is_not(None))
                | (EventsModel.female_chat_id.is_not(None))
                | (EventsModel.private_chat_invite_link.is_not(None))
            )
            .order_by(EventsModel.private_chat_delete_at.asc(), EventsModel.id.asc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def mark_private_chat_deleted(
        self,
        *,
        event_id: int,
        deleted_at: datetime | None = None,
    ) -> None:
        stmt = (
            update(EventsModel)
            .where(EventsModel.id == event_id)
            .values(
                male_chat_id=None,
                male_thread_id=None,
                male_message_id=None,
                male_chat_username=None,
                female_chat_id=None,
                female_thread_id=None,
                female_message_id=None,
                female_chat_username=None,
                private_chat_invite_link=None,
                private_chat_deleted_at=deleted_at or datetime.now(timezone.utc),
            )
        )
        await self.session.execute(stmt)
        logger.info(
            "Event private chat deleted. db='%s', event_id=%d",
            self.__tablename__,
            event_id,
        )
