from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, String, UniqueConstraint, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.models.base import BaseModel


class EventInterestingModel(BaseModel):
    __tablename__ = "event_interesting"
    __table_args__ = (
        UniqueConstraint("event_id", "user_id", name="uq_event_interesting"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[int] = mapped_column(nullable=False)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    source: Mapped[str] = mapped_column(String(16), nullable=False)
    adv_placement_date: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
    )
    adv_channel_username: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )
    adv_placement_price: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
    )
    adv_created: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    is_registered: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )
    is_paid: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )
    receipt: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
