import logging
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.enums.partner_requests import PartnerRequestStatus
from app.infrastructure.database.models.partner_requests import PartnerRequestsModel
from app.infrastructure.database.models.users import UsersModel

logger = logging.getLogger(__name__)


class _PartnerRequestsDB:
    __tablename__ = "partner_requests"

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_request(self, *, user_id: int) -> PartnerRequestsModel | None:
        stmt = select(PartnerRequestsModel).where(PartnerRequestsModel.user_id == user_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_request(self, *, user_id: int) -> None:
        stmt = (
            insert(PartnerRequestsModel)
            .values(
                user_id=user_id,
                status=PartnerRequestStatus.PENDING,
            )
            .on_conflict_do_nothing(index_elements=["user_id"])
        )
        await self.session.execute(stmt)
        logger.info(
            "Partner request created. db='%s', user_id=%d, date_time='%s'",
            self.__tablename__,
            user_id,
            datetime.now(timezone.utc),
        )

    async def list_pending_requests(self) -> list[PartnerRequestsModel]:
        stmt = (
            select(PartnerRequestsModel)
            .where(PartnerRequestsModel.status == PartnerRequestStatus.PENDING)
            .order_by(PartnerRequestsModel.created.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_pending_requests_with_usernames(
        self,
    ) -> list[tuple[int, str | None]]:
        stmt = (
            select(
                PartnerRequestsModel.user_id,
                UsersModel.username,
            )
            .join(UsersModel, UsersModel.user_id == PartnerRequestsModel.user_id)
            .where(PartnerRequestsModel.status == PartnerRequestStatus.PENDING)
            .order_by(PartnerRequestsModel.created.asc())
        )
        result = await self.session.execute(stmt)
        return [(row[0], row[1]) for row in result.all()]

    async def set_pending(self, *, user_id: int) -> None:
        stmt = (
            update(PartnerRequestsModel)
            .where(PartnerRequestsModel.user_id == user_id)
            .values(
                status=PartnerRequestStatus.PENDING,
                reviewed_by=None,
                reviewed_at=None,
            )
        )
        await self.session.execute(stmt)
        logger.info(
            "Partner request reset. db='%s', user_id=%d, status=%s",
            self.__tablename__,
            user_id,
            PartnerRequestStatus.PENDING.value,
        )

    async def set_approved(self, *, user_id: int, approved_by: int) -> None:
        stmt = (
            update(PartnerRequestsModel)
            .where(PartnerRequestsModel.user_id == user_id)
            .values(
                status=PartnerRequestStatus.APPROVED,
                reviewed_by=approved_by,
                reviewed_at=datetime.now(timezone.utc),
            )
        )
        await self.session.execute(stmt)
        logger.info(
            "Partner request approved. db='%s', user_id=%d, approved_by=%d",
            self.__tablename__,
            user_id,
            approved_by,
        )

    async def set_rejected(self, *, user_id: int, rejected_by: int) -> None:
        stmt = (
            update(PartnerRequestsModel)
            .where(PartnerRequestsModel.user_id == user_id)
            .values(
                status=PartnerRequestStatus.REJECTED,
                reviewed_by=rejected_by,
                reviewed_at=datetime.now(timezone.utc),
            )
        )
        await self.session.execute(stmt)
        logger.info(
            "Partner request rejected. db='%s', user_id=%d, rejected_by=%d",
            self.__tablename__,
            user_id,
            rejected_by,
        )
