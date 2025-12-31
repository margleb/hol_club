import logging
from dataclasses import dataclass

from sqlalchemy import case, func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models.events import EventsModel
from app.infrastructure.database.models.event_registrations import (
    EventRegistrationsModel,
)
from app.infrastructure.database.models.event_interesting_sources import (
    EventInterestingSourcesModel,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class UserEventListItem:
    event_id: int
    name: str
    event_datetime: str
    is_paid: bool
    channel_id: int | None
    channel_message_id: int | None


@dataclass(frozen=True)
class EventRegistrationListItem:
    user_id: int
    is_paid: bool
    receipt: str | None


@dataclass(frozen=True)
class EventInterestingSource:
    placement_date: str
    channel_username: str
    placement_price: str


class _EventRegistrationsDB:
    __tablename__ = "event_interesting"

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_registration(
        self,
        *,
        event_id: int,
        user_id: int,
        source: str,
        is_registered: bool = True,
    ) -> bool:
        stmt = (
            insert(EventRegistrationsModel)
            .values(
                event_id=event_id,
                user_id=user_id,
                source=source,
                is_registered=is_registered,
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

    async def store_interest_source(
        self,
        *,
        event_id: int,
        user_id: int,
        placement_date: str,
        channel_username: str,
        placement_price: str,
    ) -> bool:
        stmt = (
            insert(EventInterestingSourcesModel)
            .values(
                event_id=event_id,
                user_id=user_id,
                placement_date=placement_date,
                channel_username=channel_username,
                placement_price=placement_price,
            )
            .on_conflict_do_nothing(index_elements=["event_id", "user_id"])
            .returning(EventInterestingSourcesModel.id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def get_interest_source(
        self,
        *,
        event_id: int,
        user_id: int,
    ) -> EventInterestingSource | None:
        stmt = (
            select(
                EventInterestingSourcesModel.placement_date,
                EventInterestingSourcesModel.channel_username,
                EventInterestingSourcesModel.placement_price,
            )
            .where(EventInterestingSourcesModel.event_id == event_id)
            .where(EventInterestingSourcesModel.user_id == user_id)
        )
        result = await self.session.execute(stmt)
        row = result.one_or_none()
        if row is None:
            return None
        mapping = row._mapping
        return EventInterestingSource(
            placement_date=mapping[EventInterestingSourcesModel.placement_date],
            channel_username=mapping[EventInterestingSourcesModel.channel_username],
            placement_price=mapping[EventInterestingSourcesModel.placement_price],
        )

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
            .where(EventRegistrationsModel.is_registered.is_(True))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_user_event_list(
        self,
        *,
        user_id: int,
    ) -> list[UserEventListItem]:
        stmt = (
            select(
                EventsModel.id,
                EventsModel.name,
                EventsModel.event_datetime,
                EventsModel.channel_id,
                EventsModel.channel_message_id,
                EventRegistrationsModel.is_paid,
            )
            .join(EventsModel, EventsModel.id == EventRegistrationsModel.event_id)
            .where(EventRegistrationsModel.user_id == user_id)
            .where(EventRegistrationsModel.is_registered.is_(True))
            .order_by(EventsModel.event_datetime.asc())
        )
        result = await self.session.execute(stmt)
        items = []
        for row in result.all():
            mapping = row._mapping
            items.append(
                UserEventListItem(
                    event_id=mapping[EventsModel.id],
                    name=mapping[EventsModel.name],
                    event_datetime=mapping[EventsModel.event_datetime],
                    is_paid=mapping[EventRegistrationsModel.is_paid],
                    channel_id=mapping[EventsModel.channel_id],
                    channel_message_id=mapping[EventsModel.channel_message_id],
                )
            )
        return items

    async def get_event_registrations_list(
        self,
        *,
        event_id: int,
    ) -> list[EventRegistrationListItem]:
        stmt = (
            select(
                EventRegistrationsModel.user_id,
                EventRegistrationsModel.is_paid,
                EventRegistrationsModel.receipt,
            )
            .where(EventRegistrationsModel.event_id == event_id)
            .where(EventRegistrationsModel.is_registered.is_(True))
            .order_by(EventRegistrationsModel.created.asc())
        )
        result = await self.session.execute(stmt)
        items = []
        for row in result.all():
            mapping = row._mapping
            items.append(
                EventRegistrationListItem(
                    user_id=mapping[EventRegistrationsModel.user_id],
                    is_paid=mapping[EventRegistrationsModel.is_paid],
                    receipt=mapping[EventRegistrationsModel.receipt],
                )
            )
        return items

    async def get_partner_event_registration_counts(
        self,
        *,
        partner_user_id: int,
    ) -> dict[int, tuple[int, int]]:
        stmt = (
            select(
                EventsModel.id.label("event_id"),
                func.count(EventRegistrationsModel.id).label("total"),
                func.coalesce(
                    func.sum(
                        case(
                            (
                                (
                                    EventRegistrationsModel.is_paid.is_(True)
                                    & EventRegistrationsModel.receipt.is_not(None)
                                    & (EventRegistrationsModel.receipt != "")
                                ),
                                1,
                            ),
                            else_=0,
                        )
                    ),
                    0,
                ).label("paid"),
            )
            .join(EventsModel, EventsModel.id == EventRegistrationsModel.event_id)
            .where(EventsModel.partner_user_id == partner_user_id)
            .where(EventRegistrationsModel.is_registered.is_(True))
            .group_by(EventsModel.id)
        )
        result = await self.session.execute(stmt)
        counts: dict[int, tuple[int, int]] = {}
        for row in result.all():
            mapping = row._mapping
            counts[int(mapping["event_id"])] = (
                int(mapping["paid"] or 0),
                int(mapping["total"] or 0),
            )
        return counts

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
            .where(EventRegistrationsModel.is_registered.is_(True))
            .where(EventRegistrationsModel.is_paid.is_(False))
            .values(is_paid=True)
            .returning(
                EventRegistrationsModel.id,
            )
        )
        result = await self.session.execute(stmt)
        row = result.one_or_none()
        if row is not None:
            mapping = row._mapping
            registration_id = mapping[EventRegistrationsModel.id]
            logger.info(
                "Event registration marked paid. db='%s', id=%d, event_id=%d, user_id=%d",
                self.__tablename__,
                registration_id,
                event_id,
                user_id,
            )
            return True
        return False

    async def mark_registered(
        self,
        *,
        event_id: int,
        user_id: int,
    ) -> bool:
        stmt = (
            update(EventRegistrationsModel)
            .where(EventRegistrationsModel.event_id == event_id)
            .where(EventRegistrationsModel.user_id == user_id)
            .where(EventRegistrationsModel.is_registered.is_(False))
            .values(is_registered=True)
            .returning(
                EventRegistrationsModel.id,
            )
        )
        result = await self.session.execute(stmt)
        row = result.one_or_none()
        if row is not None:
            mapping = row._mapping
            registration_id = mapping[EventRegistrationsModel.id]
            logger.info(
                "Event marked registered. db='%s', id=%d, event_id=%d, user_id=%d",
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
        current_stmt = (
            select(
                EventRegistrationsModel.receipt,
            )
            .where(EventRegistrationsModel.event_id == event_id)
            .where(EventRegistrationsModel.user_id == user_id)
            .where(EventRegistrationsModel.is_registered.is_(True))
        )
        current_result = await self.session.execute(current_stmt)
        current_row = current_result.one_or_none()
        if current_row is None:
            return False
        current_mapping = current_row._mapping

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
