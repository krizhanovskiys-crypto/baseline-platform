"""Tests for Sprint 6.2 — Match Details service method."""
from datetime import date, time

import pytest

from backend.app.database.models.game import GamePlayerStatus, GameStatus, MatchType
from backend.app.database.repositories.game_repository import GamePlayerRepository
from backend.app.schemas.game import GameCreate
from backend.app.schemas.player import PlayerCreate, PlayerUpdate
from backend.app.services.game_service import GameService
from backend.app.services.player_service import PlayerService


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _make_player(session, telegram_id: int, first_name: str = "Player") -> int:
    svc = PlayerService(session)
    player, _ = await svc.get_or_create(PlayerCreate(telegram_id=telegram_id, first_name=first_name))
    await svc.update_profile(
        telegram_id,
        PlayerUpdate(language="en", skill_level=3.0, home_area="Downtown", preferred_courts=["High Park"]),
    )
    return player.id


async def _make_open_game(
    session,
    organizer_tid: int,
    match_type: MatchType = MatchType.SINGLES,
    required_level: float | None = 3.0,
) -> int:
    game = await GameService(session).create_game(
        creator_telegram_id=organizer_tid,
        data=GameCreate(
            court="High Park Court 3",
            area="Downtown",
            date=date(2026, 9, 1),
            time=time(18, 0),
            match_type=match_type,
            required_level=required_level,
        ),
    )
    assert game is not None
    return game.id


# ── Not found ─────────────────────────────────────────────────────────────────

async def test_match_details_not_found(session):
    """Returns None when the game_id does not exist."""
    result = await GameService(session).get_match_details(99999)
    assert result is None


# ── Basic structure ───────────────────────────────────────────────────────────

async def test_match_details_returns_game_read(session):
    """MatchDetails.game is a GameRead with the correct id."""
    await _make_player(session, 1001, "Organizer")
    game_id = await _make_open_game(session, 1001)

    details = await GameService(session).get_match_details(game_id)

    assert details is not None
    assert details.game.id == game_id
    assert details.game.status == GameStatus.OPEN
    assert details.game.court == "High Park Court 3"


async def test_match_details_organizer_name(session):
    """organizer_name is the first_name of the game's creator."""
    await _make_player(session, 2001, "Alice")
    game_id = await _make_open_game(session, 2001)

    details = await GameService(session).get_match_details(game_id)

    assert details is not None
    assert details.organizer_name == "Alice"


# ── Player list ───────────────────────────────────────────────────────────────

async def test_match_details_only_organizer(session):
    """When no other players have joined, the list contains only the organizer."""
    await _make_player(session, 3001, "Solo")
    game_id = await _make_open_game(session, 3001)

    details = await GameService(session).get_match_details(game_id)

    assert details is not None
    assert details.committed_count == 1
    assert len(details.players) == 1
    assert details.players[0].name == "Solo"


async def test_match_details_accepted_player_appears(session):
    """A player who accepted an invitation appears in the player list."""
    await _make_player(session, 4001, "Organizer")
    pid_b = await _make_player(session, 4002, "Bob")
    game_id = await _make_open_game(session, 4001)

    await GamePlayerRepository(session).add_player_to_game(
        game_id, pid_b, GamePlayerStatus.ACCEPTED
    )

    details = await GameService(session).get_match_details(game_id)

    assert details is not None
    assert details.committed_count == 2
    assert any(p.name == "Bob" for p in details.players)


async def test_match_details_invited_player_excluded(session):
    """A player with INVITED status (not yet accepted) does not appear in the list."""
    await _make_player(session, 5001, "Organizer")
    pid_b = await _make_player(session, 5002, "Pending")
    game_id = await _make_open_game(session, 5001)

    await GamePlayerRepository(session).add_player_to_game(
        game_id, pid_b, GamePlayerStatus.INVITED
    )

    details = await GameService(session).get_match_details(game_id)

    assert details is not None
    assert details.committed_count == 1
    assert not any(p.name == "Pending" for p in details.players)


async def test_match_details_is_organizer_flag(session):
    """Organizer has is_organizer=True; accepted invitee has is_organizer=False."""
    await _make_player(session, 5101, "Boss")
    pid_b = await _make_player(session, 5102, "Guest")
    game_id = await _make_open_game(session, 5101)

    await GamePlayerRepository(session).add_player_to_game(
        game_id, pid_b, GamePlayerStatus.ACCEPTED
    )

    details = await GameService(session).get_match_details(game_id)

    assert details is not None
    organizer_entries = [p for p in details.players if p.is_organizer]
    guest_entries = [p for p in details.players if not p.is_organizer]
    assert len(organizer_entries) == 1
    assert organizer_entries[0].name == "Boss"
    assert len(guest_entries) == 1
    assert guest_entries[0].name == "Guest"


async def test_match_details_player_telegram_id(session):
    """Each PlayerSummary carries the correct telegram_id."""
    await _make_player(session, 5201, "TelegramUser")
    game_id = await _make_open_game(session, 5201)

    details = await GameService(session).get_match_details(game_id)

    assert details is not None
    assert details.players[0].telegram_id == 5201


# ── required_players via GameRead ─────────────────────────────────────────────

async def test_match_details_singles_required_players(session):
    """game.required_players is 2 for a SINGLES match."""
    await _make_player(session, 6001, "Singles")
    game_id = await _make_open_game(session, 6001, match_type=MatchType.SINGLES)

    details = await GameService(session).get_match_details(game_id)

    assert details is not None
    assert details.game.required_players == 2


async def test_match_details_doubles_required_players(session):
    """game.required_players is 4 for a DOUBLES match."""
    await _make_player(session, 7001, "Doubles")
    game_id = await _make_open_game(session, 7001, match_type=MatchType.DOUBLES)

    details = await GameService(session).get_match_details(game_id)

    assert details is not None
    assert details.game.required_players == 4


# ── Level field ───────────────────────────────────────────────────────────────

async def test_match_details_level_preserved(session):
    """required_level from GameRead matches what was set on creation."""
    await _make_player(session, 8001, "Leveled")
    game_id = await _make_open_game(session, 8001, required_level=3.5)

    details = await GameService(session).get_match_details(game_id)

    assert details is not None
    assert details.game.required_level == 3.5


async def test_match_details_level_none(session):
    """required_level can be None when no level was set."""
    await _make_player(session, 9001, "Open")
    game_id = await _make_open_game(session, 9001, required_level=None)

    details = await GameService(session).get_match_details(game_id)

    assert details is not None
    assert details.game.required_level is None
