from datetime import datetime

from sqlalchemy import BigInteger, DateTime, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.models.base import BaseModel


class EventInterestingSourcesModel(BaseModel):
    __tablename__ = "event_interesting_sources"
    __table_args__ = (
        UniqueConstraint("event_id", "user_id", name="uq_event_interesting_sources"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[int] = mapped_column(nullable=False)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    placement_date: Mapped[str] = mapped_column(String(32), nullable=False)
    channel_username: Mapped[str] = mapped_column(String(64), nullable=False)
    placement_price: Mapped[str] = mapped_column(String(32), nullable=False)
    created: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
