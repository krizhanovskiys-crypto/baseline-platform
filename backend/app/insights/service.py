"""Analytics service — records product usage events."""
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database.models.analytics_event import AnalyticsEvent
from backend.app.insights.repository import AnalyticsEventRepository

logger = logging.getLogger(__name__)


class AnalyticsService:
    """Handles event tracking."""

    def __init__(self, session: AsyncSession) -> None:
        self._repo = AnalyticsEventRepository(session)

    async def track_event(
        self, user_id: int, event: str, metadata: dict | None = None
    ) -> AnalyticsEvent:
        """Record a single analytics event."""
        record = await self._repo.create(user_id, event, metadata)
        logger.debug("Tracked event=%s user_id=%s", event, user_id)
        return record
