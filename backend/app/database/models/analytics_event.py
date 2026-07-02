"""Analytics event ORM model."""
from datetime import datetime

from sqlalchemy import JSON, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from backend.app.database.base import Base


class AnalyticsEvent(Base):
    """A single tracked product usage event."""

    __tablename__ = "analytics_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    event: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    # Attribute renamed to avoid colliding with SQLAlchemy's reserved Base.metadata;
    # the underlying column is still named "metadata" per the spec.
    event_metadata: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<AnalyticsEvent id={self.id} user={self.user_id} event={self.event!r}>"
