from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Enum, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.bot.enums.roles import UserRole
from app.infrastructure.database.models.base import BaseModel


class UsersModel(BaseModel):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    username: Mapped[str | None] = mapped_column(String(64))
    created: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    gender: Mapped[str | None] = mapped_column(String(16))
    age_group: Mapped[str | None] = mapped_column(String(32))
    intent: Mapped[str | None] = mapped_column(String(16))
    role: Mapped[UserRole] = mapped_column(
        Enum(
            UserRole,
            values_callable=lambda enum: [item.value for item in enum],
            native_enum=False,
        ),
        nullable=False,
    )
    is_alive: Mapped[bool] = mapped_column(Boolean, nullable=False)
    is_blocked: Mapped[bool] = mapped_column(Boolean, nullable=False)
