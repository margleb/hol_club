import logging
from dataclasses import dataclass

from sqlalchemy import case, func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models.events import EventsModel
from app.infrastructure.database.models.event_registrations import (
    EventInterestingModel,
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


class _EventInterestingDB:
    __tablename__ = "event_interesting"

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_interesting(
        self,
        *,
        event_id: int,
        user_id: int,
        username: str | None,
        source: str,
        is_registered: bool = True,
    ) -> bool:
        stmt = (
            insert(EventInterestingModel)
            .values(
                event_id=event_id,
                user_id=user_id,
                username=username,
                source=source,
                is_registered=is_registered,
                is_paid=False,
            )
            .on_conflict_do_nothing(index_elements=["event_id", "user_id"])
            .returning(EventInterestingModel.id)
        )
        result = await self.session.execute(stmt)
        registration_id = result.scalar_one_or_none()
        if registration_id is not None:
            logger.info(
                "Event interesting created. db='%s', id=%d, event_id=%d, user_id=%d",
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
            update(EventInterestingModel)
            .where(EventInterestingModel.event_id == event_id)
            .where(EventInterestingModel.user_id == user_id)
            .values(
                adv_placement_date=placement_date,
                adv_channel_username=channel_username,
                adv_placement_price=placement_price,
                adv_created=func.now(),
            )
            .returning(EventInterestingModel.id)
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
                EventInterestingModel.adv_placement_date,
                EventInterestingModel.adv_channel_username,
                EventInterestingModel.adv_placement_price,
            )
            .where(EventInterestingModel.event_id == event_id)
            .where(EventInterestingModel.user_id == user_id)
        )
        result = await self.session.execute(stmt)
        row = result.one_or_none()
        if row is None:
            return None
        mapping = row._mapping
        placement_date = mapping[EventInterestingModel.adv_placement_date]
        channel_username = mapping[EventInterestingModel.adv_channel_username]
        placement_price = mapping[EventInterestingModel.adv_placement_price]
        if not placement_date or not channel_username or not placement_price:
            return None
        return EventInterestingSource(
            placement_date=placement_date,
            channel_username=channel_username,
            placement_price=placement_price,
        )

    async def get_registration(
        self,
        *,
        event_id: int,
        user_id: int,
    ) -> EventInterestingModel | None:
        stmt = (
            select(EventInterestingModel)
            .where(EventInterestingModel.event_id == event_id)
            .where(EventInterestingModel.user_id == user_id)
            .where(EventInterestingModel.is_registered.is_(True))
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
                EventInterestingModel.is_paid,
            )
            .join(EventsModel, EventsModel.id == EventInterestingModel.event_id)
            .where(EventInterestingModel.user_id == user_id)
            .where(EventInterestingModel.is_registered.is_(True))
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
                    is_paid=mapping[EventInterestingModel.is_paid],
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
                EventInterestingModel.user_id,
                EventInterestingModel.is_paid,
                EventInterestingModel.receipt,
            )
            .where(EventInterestingModel.event_id == event_id)
            .where(EventInterestingModel.is_registered.is_(True))
            .order_by(EventInterestingModel.created.asc())
        )
        result = await self.session.execute(stmt)
        items = []
        for row in result.all():
            mapping = row._mapping
            items.append(
                EventRegistrationListItem(
                    user_id=mapping[EventInterestingModel.user_id],
                    is_paid=mapping[EventInterestingModel.is_paid],
                    receipt=mapping[EventInterestingModel.receipt],
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
                func.count(EventInterestingModel.id).label("total"),
                func.coalesce(
                    func.sum(
                        case(
                            (
                                (
                                    EventInterestingModel.is_paid.is_(True)
                                    & EventInterestingModel.receipt.is_not(None)
                                    & (EventInterestingModel.receipt != "")
                                ),
                                1,
                            ),
                            else_=0,
                        )
                    ),
                    0,
                ).label("paid"),
            )
            .join(EventsModel, EventsModel.id == EventInterestingModel.event_id)
            .where(EventsModel.partner_user_id == partner_user_id)
            .where(EventInterestingModel.is_registered.is_(True))
            .group_by(EventsModel.id)
        )
        result = await self.session.execute(stmt)
        counts: dict[int, tuple[int, int]] = {}
        for row in result.all():
            mapping = row._mapping
            counts[int(mapping["event_id"])] = (
                int(mapping["total"] or 0),
                int(mapping["paid"] or 0),
            )
        return counts

    async def mark_paid(
        self,
        *,
        event_id: int,
        user_id: int,
    ) -> bool:
        stmt = (
            update(EventInterestingModel)
            .where(EventInterestingModel.event_id == event_id)
            .where(EventInterestingModel.user_id == user_id)
            .where(EventInterestingModel.is_registered.is_(True))
            .where(EventInterestingModel.is_paid.is_(False))
            .values(is_paid=True)
            .returning(
                EventInterestingModel.id,
            )
        )
        result = await self.session.execute(stmt)
        row = result.one_or_none()
        if row is not None:
            mapping = row._mapping
            registration_id = mapping[EventInterestingModel.id]
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
            update(EventInterestingModel)
            .where(EventInterestingModel.event_id == event_id)
            .where(EventInterestingModel.user_id == user_id)
            .where(EventInterestingModel.is_registered.is_(False))
            .values(is_registered=True)
            .returning(
                EventInterestingModel.id,
            )
        )
        result = await self.session.execute(stmt)
        row = result.one_or_none()
        if row is not None:
            mapping = row._mapping
            registration_id = mapping[EventInterestingModel.id]
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
    ) -> tuple[bool, bool]:
        current_stmt = (
            select(
                EventInterestingModel.receipt,
            )
            .where(EventInterestingModel.event_id == event_id)
            .where(EventInterestingModel.user_id == user_id)
            .where(EventInterestingModel.is_registered.is_(True))
        )
        current_result = await self.session.execute(current_stmt)
        current_row = current_result.one_or_none()
        if current_row is None:
            return False, False
        current_mapping = current_row._mapping
        had_receipt = bool(current_mapping[EventInterestingModel.receipt])

        stmt = (
            update(EventInterestingModel)
            .where(EventInterestingModel.event_id == event_id)
            .where(EventInterestingModel.user_id == user_id)
            .values(receipt=receipt)
            .returning(EventInterestingModel.id)
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
            return True, not had_receipt
        return False, False
