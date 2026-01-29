import logging

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models.adv_stats import (
    AdvRegistrationModel,
    AdvStatsModel,
)

logger = logging.getLogger(__name__)


class _AdvStatsDB:
    __tablename__ = "adv_stats"

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def register_general(
        self,
        *,
        user_id: int,
        placement_date: str,
        channel_username: str,
        placement_price: str,
    ) -> bool:
        insert_registration = (
            insert(AdvRegistrationModel)
            .values(
                user_id=user_id,
                placement_date=placement_date,
                channel_username=channel_username,
                placement_price=placement_price,
            )
            .on_conflict_do_nothing(
                index_elements=[
                    "user_id",
                    "placement_date",
                    "channel_username",
                    "placement_price",
                ]
            )
        )
        result = await self.session.execute(insert_registration)
        inserted = bool(result.rowcount)
        if not inserted:
            return False

        upsert_stats = insert(AdvStatsModel).values(
            placement_date=placement_date,
            channel_username=channel_username,
            placement_price=placement_price,
            register_count=1,
        )
        upsert_stats = upsert_stats.on_conflict_do_update(
            index_elements=["placement_date", "channel_username", "placement_price"],
            set_={"register_count": AdvStatsModel.register_count + 1},
        )
        await self.session.execute(upsert_stats)
        logger.info(
            "Adv stats updated. db='%s', placement_date='%s', channel_username='%s', "
            "placement_price='%s'",
            self.__tablename__,
            placement_date,
            channel_username,
            placement_price,
        )
        return True
