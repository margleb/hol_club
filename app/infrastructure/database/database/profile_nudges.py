import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import exists, or_, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.enums.roles import UserRole
from app.infrastructure.database.models.profile_nudges import ProfileNudgesModel
from app.infrastructure.database.models.users import UsersModel

logger = logging.getLogger(__name__)


class _ProfileNudgesDB:
    __tablename__ = "profile_nudges"

    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_due_users(
        self,
        *,
        first_delay_minutes: int,
        remind_delay_hours: int,
        max_attempts: int,
        limit: int,
    ) -> list[tuple[int, int]]:
        if limit <= 0 or max_attempts <= 0:
            return []

        now = datetime.now(timezone.utc)
        first_cutoff = now - timedelta(minutes=max(first_delay_minutes, 0))
        remind_cutoff = now - timedelta(hours=max(remind_delay_hours, 0))

        stmt = (
            select(
                UsersModel.user_id,
                UsersModel.created,
                ProfileNudgesModel.attempts,
                ProfileNudgesModel.last_sent_at,
                ProfileNudgesModel.completed_at,
            )
            .outerjoin(ProfileNudgesModel, ProfileNudgesModel.user_id == UsersModel.user_id)
            .where(UsersModel.role == UserRole.USER)
            .where(UsersModel.is_alive.is_(True))
            .where(UsersModel.is_blocked.is_(False))
            .where(or_(UsersModel.gender.is_(None), UsersModel.age_group.is_(None)))
            .order_by(UsersModel.created.asc())
        )
        result = await self.session.execute(stmt)

        due: list[tuple[int, int]] = []
        for user_id, created_at, attempts_raw, last_sent_at, completed_at in result.all():
            if completed_at is not None:
                continue
            attempts = int(attempts_raw or 0)
            if attempts >= max_attempts:
                continue
            if attempts == 0:
                if created_at and created_at <= first_cutoff:
                    due.append((int(user_id), 1))
            elif last_sent_at is None or last_sent_at <= remind_cutoff:
                due.append((int(user_id), attempts + 1))
            if len(due) >= limit:
                break
        return due

    async def mark_sent(self, *, user_id: int) -> None:
        now = datetime.now(timezone.utc)
        stmt = (
            insert(ProfileNudgesModel)
            .values(
                user_id=user_id,
                attempts=1,
                last_sent_at=now,
            )
            .on_conflict_do_update(
                index_elements=["user_id"],
                set_={
                    "attempts": ProfileNudgesModel.attempts + 1,
                    "last_sent_at": now,
                    "completed_at": None,
                },
            )
        )
        await self.session.execute(stmt)
        logger.info(
            "Profile nudge marked as sent. db='%s', user_id=%d",
            self.__tablename__,
            user_id,
        )

    async def mark_completed_for_filled_profiles(self) -> int:
        now = datetime.now(timezone.utc)
        has_complete_profile = exists(
            select(UsersModel.user_id)
            .where(UsersModel.user_id == ProfileNudgesModel.user_id)
            .where(UsersModel.gender.is_not(None))
            .where(UsersModel.age_group.is_not(None))
        )
        stmt = (
            update(ProfileNudgesModel)
            .where(ProfileNudgesModel.completed_at.is_(None))
            .where(has_complete_profile)
            .values(completed_at=now)
        )
        result = await self.session.execute(stmt)
        updated = int(result.rowcount or 0)
        if updated:
            logger.info(
                "Profile nudges marked completed. db='%s', count=%d",
                self.__tablename__,
                updated,
            )
        return updated
