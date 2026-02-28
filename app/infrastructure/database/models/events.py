from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Integer, String, Text, func
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
    prepay_percent: Mapped[int | None] = mapped_column(Integer)
    prepay_fixed_free: Mapped[int | None] = mapped_column(Integer)
    age_group: Mapped[str | None] = mapped_column(String(32))
    photo_file_id: Mapped[str | None] = mapped_column(String(255))
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    channel_id: Mapped[int | None] = mapped_column(BigInteger)
    channel_message_id: Mapped[int | None] = mapped_column(BigInteger)
    male_chat_id: Mapped[int | None] = mapped_column(BigInteger)
    male_thread_id: Mapped[int | None] = mapped_column(BigInteger)
    male_message_id: Mapped[int | None] = mapped_column(BigInteger)
    male_chat_username: Mapped[str | None] = mapped_column(String(255))
    female_chat_id: Mapped[int | None] = mapped_column(BigInteger)
    female_thread_id: Mapped[int | None] = mapped_column(BigInteger)
    female_message_id: Mapped[int | None] = mapped_column(BigInteger)
    female_chat_username: Mapped[str | None] = mapped_column(String(255))
    private_chat_invite_link: Mapped[str | None] = mapped_column(String(255))
    created: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
