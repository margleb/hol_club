from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Enum, func
from sqlalchemy.orm import Mapped, mapped_column

from app.bot.enums.partner_requests import PartnerRequestStatus
from app.infrastructure.database.models.base import BaseModel


class PartnerRequestsModel(BaseModel):
    __tablename__ = "partner_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    created: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    status: Mapped[PartnerRequestStatus] = mapped_column(
        Enum(
            PartnerRequestStatus,
            values_callable=lambda enum: [item.value for item in enum],
            name="partnerrequeststatus",
            native_enum=False,
        ),
        nullable=False,
    )
    reviewed_by: Mapped[int | None] = mapped_column(BigInteger)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
