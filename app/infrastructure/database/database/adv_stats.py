import logging

from sqlalchemy import update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models.adv_stats import AdvStatsModel

logger = logging.getLogger(__name__)


class _AdvStatsDB:
    __tablename__ = "adv_stats"

    def __init__(self, session: AsyncSession):
        self.session = session

    async def increment_registration(
        self,
        *,
        event_id: int,
        placement_date: str,
        channel_username: str,
        placement_price: str,
    ) -> None:
        stmt = (
            insert(AdvStatsModel)
            .values(
                event_id=event_id,
                placement_date=placement_date,
                channel_username=channel_username,
                placement_price=placement_price,
                registrations_count=1,
                paid_count=0,
                confirmed_count=0,
            )
            .on_conflict_do_update(
                index_elements=[
                    "event_id",
                    "placement_date",
                    "channel_username",
                    "placement_price",
                ],
                set_={
                    "registrations_count": AdvStatsModel.registrations_count + 1,
                },
            )
            .returning(AdvStatsModel.id)
        )
        result = await self.session.execute(stmt)
        stat_id = result.scalar_one_or_none()
        if stat_id is not None:
            logger.info(
                "Adv stats registration updated. db='%s', id=%d, event_id=%d",
                self.__tablename__,
                stat_id,
                event_id,
            )

    async def increment_paid(
        self,
        *,
        event_id: int,
        placement_date: str,
        channel_username: str,
        placement_price: str,
    ) -> None:
        stmt = (
            update(AdvStatsModel)
            .where(AdvStatsModel.event_id == event_id)
            .where(AdvStatsModel.placement_date == placement_date)
            .where(AdvStatsModel.channel_username == channel_username)
            .where(AdvStatsModel.placement_price == placement_price)
            .values(paid_count=AdvStatsModel.paid_count + 1)
            .returning(AdvStatsModel.id)
        )
        result = await self.session.execute(stmt)
        stat_id = result.scalar_one_or_none()
        if stat_id is not None:
            logger.info(
                "Adv stats paid updated. db='%s', id=%d, event_id=%d",
                self.__tablename__,
                stat_id,
                event_id,
            )
        else:
            logger.warning(
                "Adv stats paid update skipped; row missing. event_id=%d, date=%s, channel=%s",
                event_id,
                placement_date,
                channel_username,
            )

    async def increment_confirmed(
        self,
        *,
        event_id: int,
        placement_date: str,
        channel_username: str,
        placement_price: str,
    ) -> None:
        stmt = (
            update(AdvStatsModel)
            .where(AdvStatsModel.event_id == event_id)
            .where(AdvStatsModel.placement_date == placement_date)
            .where(AdvStatsModel.channel_username == channel_username)
            .where(AdvStatsModel.placement_price == placement_price)
            .values(confirmed_count=AdvStatsModel.confirmed_count + 1)
            .returning(AdvStatsModel.id)
        )
        result = await self.session.execute(stmt)
        stat_id = result.scalar_one_or_none()
        if stat_id is not None:
            logger.info(
                "Adv stats confirmed updated. db='%s', id=%d, event_id=%d",
                self.__tablename__,
                stat_id,
                event_id,
            )
        else:
            logger.warning(
                "Adv stats confirmed update skipped; row missing. event_id=%d, date=%s, channel=%s",
                event_id,
                placement_date,
                channel_username,
            )
