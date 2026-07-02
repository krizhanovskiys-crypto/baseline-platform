"""Tests for automatic analytics tracking triggered by other services."""
import pytest
from datetime import date, time

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database.models.game import MatchType
from backend.app.insights.repository import AnalyticsEventRepository
from backend.app.schemas.game import GameCreate
from backend.app.schemas.player import PlayerCreate, PlayerUpdate
from backend.app.services.game_service import GameService
from backend.app.services.player_service import PlayerService


@pytest.mark.asyncio
async def test_get_or_create_tracks_user_registered(session: AsyncSession) -> None:
    service = PlayerService(session)
    player, created = await service.get_or_create(
        PlayerCreate(telegram_id=9001, first_name="Alice")
    )
    await session.commit()
    assert created is True

    events = await AnalyticsEventRepository(session).get_all()
    assert len(events) == 1
    assert events[0].event == "user_registered"
    assert events[0].user_id == player.id


@pytest.mark.asyncio
async def test_get_or_create_existing_player_does_not_retrack(session: AsyncSession) -> None:
    service = PlayerService(session)
    data = PlayerCreate(telegram_id=9002, first_name="Bob")
    await service.get_or_create(data)
    await session.commit()
    await service.get_or_create(data)
    await session.commit()

    events = await AnalyticsEventRepository(session).get_all()
    assert len([e for e in events if e.event == "user_registered"]) == 1


@pytest.mark.asyncio
async def test_update_profile_tracks_profile_completed_once(session: AsyncSession) -> None:
    service = PlayerService(session)
    await service.get_or_create(PlayerCreate(telegram_id=9003, first_name="Carol"))
    await session.commit()

    # Partial update — profile still incomplete, no event yet.
    await service.update_profile(9003, PlayerUpdate(language="en"))
    await session.commit()

    events = await AnalyticsEventRepository(session).get_all()
    assert "profile_completed" not in {e.event for e in events}

    # Completes the profile — event fires.
    await service.update_profile(
        9003,
        PlayerUpdate(skill_level=3.5, home_area="Downtown", preferred_courts=["Other"]),
    )
    await session.commit()

    # A further update no longer fires it again.
    await service.update_profile(9003, PlayerUpdate(home_area="North York"))
    await session.commit()

    events = await AnalyticsEventRepository(session).get_all()
    completed = [e for e in events if e.event == "profile_completed"]
    assert len(completed) == 1


@pytest.mark.asyncio
async def test_create_game_tracks_game_created(session: AsyncSession) -> None:
    player_svc = PlayerService(session)
    player, _ = await player_svc.get_or_create(PlayerCreate(telegram_id=9004, first_name="Dave"))
    await player_svc.update_profile(
        9004,
        PlayerUpdate(language="en", skill_level=3.0, home_area="Downtown", preferred_courts=["Other"]),
    )
    await session.commit()

    game_svc = GameService(session)
    game = await game_svc.create_game(
        creator_telegram_id=9004,
        data=GameCreate(
            court="Ramsden Park",
            area="Downtown",
            date=date(2025, 9, 15),
            time=time(10, 0),
            match_type=MatchType.SINGLES,
        ),
    )
    await session.commit()
    assert game is not None

    events = await AnalyticsEventRepository(session).get_all()
    created_events = [e for e in events if e.event == "game_created"]
    assert len(created_events) == 1
    assert created_events[0].user_id == player.id
    assert created_events[0].event_metadata == {"game_id": game.id}
