"""Tests for GameService."""
import pytest
from datetime import date, time

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database.models.game import MatchType
from backend.app.schemas.game import GameCreate
from backend.app.schemas.player import PlayerCreate, PlayerUpdate
from backend.app.database.models.game import GameStatus
from backend.app.services.game_service import GameService
from backend.app.services.match_lifecycle_service import MatchLifecycleService
from backend.app.services.player_service import PlayerService


async def _make_player(session: AsyncSession, tid: int, name: str) -> None:
    svc = PlayerService(session)
    await svc.get_or_create(PlayerCreate(telegram_id=tid, first_name=name))
    await svc.update_profile(
        tid,
        PlayerUpdate(language="en", skill_level=3.0, home_area="Downtown", preferred_courts=["Other"]),
    )
    await session.commit()


@pytest.mark.asyncio
async def test_create_game(session: AsyncSession) -> None:
    await _make_player(session, 5001, "Alice")
    game_svc = GameService(session)

    game = await game_svc.create_game(
        creator_telegram_id=5001,
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
    assert game.court == "Ramsden Park"
    assert game.area == "Downtown"


@pytest.mark.asyncio
async def test_create_game_unknown_player(session: AsyncSession) -> None:
    game_svc = GameService(session)
    result = await game_svc.create_game(
        creator_telegram_id=999,
        data=GameCreate(
            court="X",
            area="Downtown",
            date=date(2025, 9, 15),
            time=time(10, 0),
        ),
    )
    assert result is None


@pytest.mark.asyncio
async def test_create_game_starts_as_draft(session: AsyncSession) -> None:
    await _make_player(session, 5002, "Bob")
    game = await GameService(session).create_game(
        creator_telegram_id=5002,
        data=GameCreate(court="A", area="Downtown", date=date(2025, 10, 1), time=time(9, 0)),
    )
    assert game is not None
    assert game.status == GameStatus.DRAFT


@pytest.mark.asyncio
async def test_get_open_games(session: AsyncSession) -> None:
    await _make_player(session, 5003, "Bob")
    game_svc = GameService(session)
    lifecycle = MatchLifecycleService(session)

    for court in ["A", "B", "C"]:
        game = await game_svc.create_game(
            creator_telegram_id=5003,
            data=GameCreate(court=court, area="Downtown", date=date(2025, 10, 1), time=time(9, 0)),
        )
        await lifecycle.transition(game.id, GameStatus.OPEN)
    await session.commit()

    games = await game_svc.get_open_games()
    assert len(games) == 3

    downtown = await game_svc.get_open_games(area="Downtown")
    assert len(downtown) == 3

    north = await game_svc.get_open_games(area="North York")
    assert len(north) == 0
