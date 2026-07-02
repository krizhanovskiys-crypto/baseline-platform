"""Tests for AnalyticsService."""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.insights.repository import AnalyticsEventRepository
from backend.app.insights.service import AnalyticsService


@pytest.mark.asyncio
async def test_track_event(session: AsyncSession) -> None:
    service = AnalyticsService(session)
    event = await service.track_event(1, "find_partner_opened")
    await session.commit()

    assert event.user_id == 1
    assert event.event == "find_partner_opened"
    assert event.event_metadata is None


@pytest.mark.asyncio
async def test_track_event_with_metadata(session: AsyncSession) -> None:
    service = AnalyticsService(session)
    event = await service.track_event(5, "game_created", {"game_id": 7})
    await session.commit()

    repo = AnalyticsEventRepository(session)
    fetched = await repo.get_by_id(event.id)
    assert fetched is not None
    assert fetched.event_metadata == {"game_id": 7}
