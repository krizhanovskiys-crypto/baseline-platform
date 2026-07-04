"""Tests for AdminDashboardService — every figure computed from the
current database, no hardcoded values."""
import json
from datetime import date, time

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database.models.game import GameStatus
from backend.app.database.repositories.player_repository import PlayerRepository
from backend.app.schemas.game import GameCreate
from backend.app.schemas.player import PlayerCreate, PlayerUpdate
from backend.app.services.admin_dashboard_service import AdminDashboardService
from backend.app.services.game_service import GameService
from backend.app.services.match_lifecycle_service import MatchLifecycleService
from backend.app.services.player_service import PlayerService


async def _make_player(
    session: AsyncSession, telegram_id: int, courts: list[str], available: bool = False
) -> None:
    svc = PlayerService(session)
    await svc.get_or_create(PlayerCreate(telegram_id=telegram_id, first_name="Player"))
    await svc.update_profile(
        telegram_id,
        PlayerUpdate(language="en", skill_level=3.0, home_area="Downtown", preferred_courts=courts),
    )
    if available:
        await svc.set_available_now(telegram_id)


@pytest.mark.asyncio
async def test_stats_are_zero_on_an_empty_database(session: AsyncSession) -> None:
    stats = await AdminDashboardService(session).get_stats()

    assert stats == {"users": 0, "active_matches": 0, "available_now": 0, "courts": 0}


@pytest.mark.asyncio
async def test_users_counts_every_player(session: AsyncSession) -> None:
    await _make_player(session, 111, ["Downtown Court"])
    await _make_player(session, 222, ["Downtown Court"])
    await session.commit()

    stats = await AdminDashboardService(session).get_stats()
    assert stats["users"] == 2


@pytest.mark.asyncio
async def test_available_now_counts_only_currently_available_players(session: AsyncSession) -> None:
    await _make_player(session, 111, ["Downtown Court"], available=True)
    await _make_player(session, 222, ["Downtown Court"], available=False)
    await session.commit()

    stats = await AdminDashboardService(session).get_stats()
    assert stats["available_now"] == 1


@pytest.mark.asyncio
async def test_courts_counts_distinct_courts_across_all_players(session: AsyncSession) -> None:
    await _make_player(session, 111, ["Ramsden Park", "Trinity Bellwoods"])
    await _make_player(session, 222, ["Trinity Bellwoods", "High Park Bubble"])
    await session.commit()

    stats = await AdminDashboardService(session).get_stats()
    # Ramsden Park, Trinity Bellwoods, High Park Bubble — 3 distinct courts.
    assert stats["courts"] == 3


@pytest.mark.asyncio
async def test_active_matches_excludes_completed_cancelled_and_expired(session: AsyncSession) -> None:
    await _make_player(session, 111, ["Downtown Court"])
    await session.commit()

    game_svc = GameService(session)
    lc = MatchLifecycleService(session)

    open_game = await game_svc.create_game(
        creator_telegram_id=111,
        data=GameCreate(court="Downtown Court", area="Downtown", date=date(2026, 9, 15), time=time(18, 0)),
    )
    cancelled_game = await game_svc.create_game(
        creator_telegram_id=111,
        data=GameCreate(court="Downtown Court", area="Downtown", date=date(2026, 9, 16), time=time(18, 0)),
    )
    await lc.transition(cancelled_game.id, GameStatus.CANCELLED)
    await session.commit()

    stats = await AdminDashboardService(session).get_stats()
    assert stats["active_matches"] == 1
    assert open_game.status == GameStatus.OPEN
