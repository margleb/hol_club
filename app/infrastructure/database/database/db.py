from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.database.adv_stats import _AdvStatsDB
from app.infrastructure.database.database.event_registrations import _EventRegistrationsDB
from app.infrastructure.database.database.events import _EventsDB
from app.infrastructure.database.database.partner_requests import _PartnerRequestsDB
from app.infrastructure.database.database.profile_nudges import _ProfileNudgesDB
from app.infrastructure.database.database.users import _UsersDB


class DB:
    def __init__(self, session: AsyncSession) -> None:
        self.users = _UsersDB(session=session)
        self.adv_stats = _AdvStatsDB(session=session)
        self.partner_requests = _PartnerRequestsDB(session=session)
        self.profile_nudges = _ProfileNudgesDB(session=session)
        self.events = _EventsDB(session=session)
        self.event_registrations = _EventRegistrationsDB(session=session)
