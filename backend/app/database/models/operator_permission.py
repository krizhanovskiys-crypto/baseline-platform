"""Operator permission model — Admin Center authorization.

Kept fully independent of Player: an operator does not need a player
profile, and a player's profile-completeness rules must have no bearing
on whether someone can access Admin Center.
"""
import enum
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Enum, Integer
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from backend.app.database.base import Base


class OperatorRole(str, enum.Enum):
    """Admin Center permission levels. Ordered lowest to highest privilege."""

    MODERATOR = "moderator"
    ADMIN = "admin"
    OWNER = "owner"


class OperatorPermission(Base):
    """Grants a single Telegram ID one Admin Center role."""

    __tablename__ = "operator_permissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False, index=True)
    role: Mapped[OperatorRole] = mapped_column(Enum(OperatorRole), nullable=False)
    granted_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    granted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<OperatorPermission telegram_id={self.telegram_id} role={self.role.value}>"
