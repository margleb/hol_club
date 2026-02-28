import logging
from datetime import datetime, timezone

from sqlalchemy import delete, or_, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.enums.roles import UserRole
from app.infrastructure.database.models.users import UsersModel

logger = logging.getLogger(__name__)


class _UsersDB:
    __tablename__ = 'users'

    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(
            self,
            *,
            user_id: int,
            username: str | None,
            role: UserRole,
            is_alive: bool = True,
            is_blocked: bool = False
    ) -> None:
        stmt = (
            insert(UsersModel)
            .values(
                user_id=user_id,
                username=username,
                role=role,
                is_alive=is_alive,
                is_blocked=is_blocked,
            )
            .on_conflict_do_nothing(index_elements=["user_id"])
        )
        await self.session.execute(stmt)
        logger.info(
            "User added. db='%s', user_id=%d, date_time='%s', "
            "username='%s', role=%s, is_alive=%s, is_blocked=%s",
            self.__tablename__,
            user_id,
            datetime.now(timezone.utc),
            username,
            role.value,
            is_alive,
            is_blocked,
        )

    async def delete(self, *, user_id: int) -> None:
        stmt = delete(UsersModel).where(UsersModel.user_id == user_id)
        await self.session.execute(stmt)
        logger.info(
            "User deleted. db='%s', user_id='%d'",
            self.__tablename__, user_id
        )

    async def get_user_record(self, *, user_id: int) -> UsersModel | None:
        stmt = select(UsersModel).where(UsersModel.user_id == user_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_alive_status(self, *, user_id: int, is_alive: bool = True) -> None:
        stmt = (
            update(UsersModel)
            .where(UsersModel.user_id == user_id)
            .values(is_alive=is_alive)
        )
        await self.session.execute(stmt)
        logger.info(
            "User updated. db='%s', user_id=%d, is_alive=%s",
            self.__tablename__, user_id, is_alive
        )

    async def update_blocked_status(
        self,
        *,
        user_id: int,
        is_blocked: bool = True,
    ) -> None:
        stmt = (
            update(UsersModel)
            .where(UsersModel.user_id == user_id)
            .values(is_blocked=is_blocked)
        )
        await self.session.execute(stmt)
        logger.info(
            "User updated. db='%s', user_id=%d, is_blocked=%s",
            self.__tablename__, user_id, is_blocked
        )

    async def mark_unreachable(
        self,
        *,
        user_id: int,
        is_blocked: bool,
    ) -> None:
        stmt = (
            update(UsersModel)
            .where(UsersModel.user_id == user_id)
            .where(
                or_(
                    UsersModel.is_alive.is_(True),
                    UsersModel.is_blocked.is_(not is_blocked),
                )
            )
            .values(
                is_alive=False,
                is_blocked=is_blocked,
            )
        )
        result = await self.session.execute(stmt)
        if int(result.rowcount or 0) > 0:
            logger.info(
                "User marked unreachable. db='%s', user_id=%d, is_blocked=%s",
                self.__tablename__, user_id, is_blocked
            )

    async def mark_reachable_on_incoming(self, *, user_id: int) -> None:
        stmt = (
            update(UsersModel)
            .where(UsersModel.user_id == user_id)
            .where(
                or_(
                    UsersModel.is_alive.is_(False),
                    UsersModel.is_blocked.is_(True),
                )
            )
            .values(
                is_alive=True,
                is_blocked=False,
            )
        )
        result = await self.session.execute(stmt)
        if int(result.rowcount or 0) > 0:
            logger.info(
                "User restored on incoming update. db='%s', user_id=%d",
                self.__tablename__, user_id
            )
    
    async def update_username(
        self,
        *,
        user_id: int,
        username: str | None,
    ) -> None:
        stmt = (
            update(UsersModel)
            .where(UsersModel.user_id == user_id)
            .values(username=username)
        )
        await self.session.execute(stmt)
        logger.info(
            "User updated. db='%s', user_id=%d, username='%s'",
            self.__tablename__,
            user_id,
            username,
        )

    async def update_role(
        self,
        *,
        user_id: int,
        role: UserRole,
    ) -> None:
        stmt = (
            update(UsersModel)
            .where(UsersModel.user_id == user_id)
            .values(role=role)
        )
        await self.session.execute(stmt)
        logger.info(
            "User updated. db='%s', user_id=%d, role=%s",
            self.__tablename__, user_id, role.value
        )

    async def get_admin_user_ids(self) -> list[int]:
        stmt = select(UsersModel.user_id).where(UsersModel.role == UserRole.ADMIN)
        result = await self.session.execute(stmt)
        return [row[0] for row in result.all()]

    async def get_active_user_ids(self) -> list[int]:
        stmt = (
            select(UsersModel.user_id)
            .where(UsersModel.is_alive.is_(True))
            .where(UsersModel.is_blocked.is_(False))
        )
        result = await self.session.execute(stmt)
        return [row[0] for row in result.all()]

    async def get_active_user_ids_by_role(
        self,
        *,
        role: UserRole,
    ) -> list[int]:
        stmt = (
            select(UsersModel.user_id)
            .where(UsersModel.is_alive.is_(True))
            .where(UsersModel.is_blocked.is_(False))
            .where(UsersModel.role == role)
        )
        result = await self.session.execute(stmt)
        return [row[0] for row in result.all()]
