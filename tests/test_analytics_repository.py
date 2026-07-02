"""Tests for AnalyticsEventRepository."""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.insights.repository import AnalyticsEventRepository


@pytest.mark.asyncio
async def test_create_event(session: AsyncSession) -> None:
    repo = AnalyticsEventRepository(session)
    event = await repo.create(user_id=1, event="user_registered")
    await session.commit()

    assert event.id is not None
    assert event.user_id == 1
    assert event.event == "user_registered"
    assert event.event_metadata is None
    assert event.created_at is not None


@pytest.mark.asyncio
async def test_create_event_with_metadata(session: AsyncSession) -> None:
    repo = AnalyticsEventRepository(session)
    event = await repo.create(user_id=2, event="game_created", metadata={"game_id": 42})
    await session.commit()

    fetched = await repo.get_by_id(event.id)
    assert fetched is not None
    assert fetched.event_metadata == {"game_id": 42}


@pytest.mark.asyncio
async def test_get_all_events(session: AsyncSession) -> None:
    repo = AnalyticsEventRepository(session)
    await repo.create(user_id=1, event="user_registered")
    await repo.create(user_id=1, event="profile_completed")
    await session.commit()

    events = await repo.get_all()
    assert len(events) == 2
