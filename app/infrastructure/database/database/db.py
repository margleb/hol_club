from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.database.partner_requests import _PartnerRequestsDB
from app.infrastructure.database.database.users import _UsersDB


class DB:
    def __init__(self, session: AsyncSession) -> None:
        self.users = _UsersDB(session=session)
