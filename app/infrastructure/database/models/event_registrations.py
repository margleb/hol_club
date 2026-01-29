from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Enum, Integer, func
from sqlalchemy.orm import Mapped, mapped_column

from app.bot.enums.event_registrations import EventRegistrationStatus
from app.infrastructure.database.models.base import BaseModel


class EventRegistrationsModel(BaseModel):
    __tablename__ = "event_registrations"

    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[int] = mapped_column(Integer, nullable=False)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    status: Mapped[EventRegistrationStatus] = mapped_column(
        Enum(
            EventRegistrationStatus,
            values_callable=lambda enum: [item.value for item in enum],
            name="eventregistrationstatus",
            native_enum=False,
        ),
        nullable=False,
    )
    amount: Mapped[int | None] = mapped_column(Integer)
    created: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    paid_confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    attended_confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
