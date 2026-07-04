"""Admin Center audit log — session/auth events only in this phase.

Kept as its own model rather than reusing `analytics_events`: an audit
log's retention policy (never pruned) differs from analytics' (may be
aggregated or pruned over time).
"""
import enum
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from backend.app.database.base import Base


class AuditAction(str, enum.Enum):
    """Audit event types. Admin-tool action logging (suspend, cancel,
    verify, ...) is a later phase — this set is auth/session only."""

    LOGIN_SUCCESS = "login_success"
    LOGOUT = "logout"
    SESSION_TIMEOUT = "session_timeout"
    FAILED_PIN = "failed_pin"
    LOCK_ACTIVATED = "lock_activated"


class AdminAuditLog(Base):
    """A single logged Admin Center session/auth event."""

    __tablename__ = "admin_audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<AdminAuditLog telegram_id={self.telegram_id} action={self.action!r}>"
