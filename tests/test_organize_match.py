"""Tests for Organize Match — GameService.get_my_matches() and match creation."""
from datetime import date, time

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.schemas.game import GameCreate
from backend.app.schemas.player import PlayerCreate, PlayerUpdate
from backend.app.services.game_service import GameService
from backend.app.services.player_service import PlayerService


async def _create_player(session: AsyncSession, telegram_id: int, name: str) -> None:
    svc = PlayerService(session)
    await svc.get_or_create(PlayerCreate(telegram_id=telegram_id, first_name=name))
    await svc.update_profile(
        telegram_id,
        PlayerUpdate(
            language="en",
            skill_level=3.5,
            home_area="Downtown",
            preferred_courts=["High Park", "Ramsden Park"],
        ),
    )
    await session.commit()


async def _make_game(session: AsyncSession, telegram_id: int, court: str = "High Park") -> None:
    await GameService(session).create_game(
        creator_telegram_id=telegram_id,
        data=GameCreate(
            court=court,
            area="Downtown",
            date=date(2026, 8, 10),
            time=time(19, 0),
        ),
    )
    await session.commit()


@pytest.mark.asyncio
async def test_get_my_matches_empty(session: AsyncSession) -> None:
    """Returns empty list when the player has no matches."""
    matches = await GameService(session).get_my_matches(9999)
    assert matches == []


@pytest.mark.asyncio
async def test_get_my_matches_unknown_player(session: AsyncSession) -> None:
    """Returns empty list when the telegram_id doesn't exist."""
    matches = await GameService(session).get_my_matches(1)
    assert matches == []


@pytest.mark.asyncio
async def test_get_my_matches_returns_created_game(session: AsyncSession) -> None:
    """Returns games created by the player."""
    await _create_player(session, 7001, "Alice")
    await _make_game(session, 7001, "High Park")

    matches = await GameService(session).get_my_matches(7001)

    assert len(matches) == 1
    assert matches[0].court == "High Park"
    assert matches[0].area == "Downtown"


@pytest.mark.asyncio
async def test_get_my_matches_multiple(session: AsyncSession) -> None:
    """Returns all games created by the player, not other players' games."""
    await _create_player(session, 7002, "Bob")
    await _create_player(session, 7003, "Carol")

    await _make_game(session, 7002, "Court A")
    await _make_game(session, 7002, "Court B")
    await _make_game(session, 7003, "Court C")  # another player's game

    bob_matches = await GameService(session).get_my_matches(7002)
    carol_matches = await GameService(session).get_my_matches(7003)

    assert len(bob_matches) == 2
    assert {m.court for m in bob_matches} == {"Court A", "Court B"}
    assert len(carol_matches) == 1
    assert carol_matches[0].court == "Court C"


@pytest.mark.asyncio
async def test_create_game_sets_match_type_from_players(session: AsyncSession) -> None:
    """Doubles match type is set correctly for a 4-player game."""
    from backend.app.database.models.game import MatchType

    await _create_player(session, 7004, "Dan")
    game = await GameService(session).create_game(
        creator_telegram_id=7004,
        data=GameCreate(
            court="Ramsden Park",
            area="Downtown",
            date=date(2026, 8, 15),
            time=time(18, 0),
            match_type=MatchType.DOUBLES,
        ),
    )
    await session.commit()

    assert game is not None
    assert game.match_type == MatchType.DOUBLES


@pytest.mark.asyncio
async def test_create_game_uses_player_area(session: AsyncSession) -> None:
    """Game can be created with the player's home_area as the area field."""
    await _create_player(session, 7005, "Eve")
    player = await PlayerService(session).get_by_telegram_id(7005)
    assert player is not None

    game = await GameService(session).create_game(
        creator_telegram_id=7005,
        data=GameCreate(
            court="Withrow Park",
            area=player.home_area or "Other",
            date=date(2026, 8, 20),
            time=time(20, 0),
        ),
    )
    await session.commit()

    assert game is not None
    assert game.area == "Downtown"
