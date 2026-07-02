"""Analytics event data access."""
from backend.app.database.models.analytics_event import AnalyticsEvent
from backend.app.database.repositories.base import BaseRepository


class AnalyticsEventRepository(BaseRepository[AnalyticsEvent]):
    """Async repository for AnalyticsEvent entities."""

    model = AnalyticsEvent

    async def create(
        self, user_id: int, event: str, metadata: dict | None = None
    ) -> AnalyticsEvent:
        """Persist a new analytics event."""
        record = AnalyticsEvent(user_id=user_id, event=event, event_metadata=metadata)
        return await self.add(record)
