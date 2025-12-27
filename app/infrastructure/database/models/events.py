from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.models.base import BaseModel


class EventsModel(BaseModel):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(primary_key=True)
    partner_user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    event_datetime: Mapped[str] = mapped_column(String(32), nullable=False)
    address: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    is_paid: Mapped[bool] = mapped_column(Boolean, nullable=False)
    price: Mapped[str | None] = mapped_column(String(32))
    age_group: Mapped[str | None] = mapped_column(String(32))
    notify_users: Mapped[bool] = mapped_column(Boolean, nullable=False)
    photo_file_id: Mapped[str | None] = mapped_column(String(255))
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    channel_id: Mapped[int | None] = mapped_column(BigInteger)
    channel_message_id: Mapped[int | None] = mapped_column(BigInteger)
    created: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
