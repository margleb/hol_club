from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.models.base import BaseModel


class AdvStatsModel(BaseModel):
    __tablename__ = "adv_stats"
    __table_args__ = (
        UniqueConstraint(
            "placement_date",
            "channel_username",
            "placement_price",
            name="uq_adv_stats_date_channel_price",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    placement_date: Mapped[str] = mapped_column(String(32), nullable=False)
    channel_username: Mapped[str] = mapped_column(String(64), nullable=False)
    placement_price: Mapped[str] = mapped_column(String(32), nullable=False)
    register_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="0",
    )
    created: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class AdvRegistrationModel(BaseModel):
    __tablename__ = "adv_registrations"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "placement_date",
            "channel_username",
            "placement_price",
            name="uq_adv_registrations_user_date_channel_price",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    placement_date: Mapped[str] = mapped_column(String(32), nullable=False)
    channel_username: Mapped[str] = mapped_column(String(64), nullable=False)
    placement_price: Mapped[str] = mapped_column(String(32), nullable=False)
    registered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
