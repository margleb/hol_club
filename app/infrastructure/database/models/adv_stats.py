from datetime import datetime

from sqlalchemy import DateTime, Integer, String, UniqueConstraint, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.models.base import BaseModel


class AdvStatsModel(BaseModel):
    __tablename__ = "adv_stats"
    __table_args__ = (
        UniqueConstraint(
            "event_id",
            "placement_date",
            "channel_username",
            "placement_price",
            name="uq_adv_stats_event_date_channel_price",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[int] = mapped_column(nullable=False)
    placement_date: Mapped[str] = mapped_column(String(32), nullable=False)
    channel_username: Mapped[str] = mapped_column(String(64), nullable=False)
    placement_price: Mapped[str] = mapped_column(String(32), nullable=False)
    interesting_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )
    register_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )
    paid_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )
    confirmed_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )
    created: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
