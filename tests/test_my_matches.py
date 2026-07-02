"""Tests for Sprint 6.1 – My Matches (Upcoming)."""
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
    match_date: date = date(2026, 9, 1),
    match_time: time = time(18, 0),
    match_type: MatchType = MatchType.SINGLES,
) -> int:
    game = await GameService(session).create_game(
        creator_telegram_id=organizer_tid,
        data=GameCreate(
            court="High Park Court 3",
            area="Downtown",
            date=match_date,
            time=match_time,
            match_type=match_type,
        ),
    )
    assert game is not None
    return game.id


async def _force_status(session, game_id: int, status: GameStatus) -> None:
    """Force a game to a specific status, bypassing normal lifecycle rules."""
    from backend.app.database.repositories.game_repository import GameRepository
    await GameRepository(session).update_status(game_id, status)


async def _add_accepted_player(session, game_id: int, player_id: int) -> None:
    await GamePlayerRepository(session).add_player_to_game(game_id, player_id, GamePlayerStatus.ACCEPTED)


# ── No upcoming matches ───────────────────────────────────────────────────────

async def test_no_upcoming_matches_returns_empty(session):
    """Player with no games returns an empty list."""
    await _make_player(session, 1001)
    result = await GameService(session).get_my_upcoming_matches(1001)
    assert result == []


async def test_unknown_player_returns_empty(session):
    """Unknown telegram_id returns an empty list without error."""
    result = await GameService(session).get_my_upcoming_matches(99999)
    assert result == []


# ── Single upcoming match ─────────────────────────────────────────────────────

async def test_organizer_sees_their_open_match(session):
    """Organizer sees their own OPEN match."""
    await _make_player(session, 2001)
    game_id = await _make_open_game(session, 2001)

    result = await GameService(session).get_my_upcoming_matches(2001)

    assert len(result) == 1
    game, count = result[0]
    assert game.id == game_id
    assert game.status == GameStatus.OPEN
    assert count == 1  # only the organizer


async def test_accepted_invitee_sees_match(session):
    """Player who accepted an invitation sees that match."""
    await _make_player(session, 3001, "Organizer")
    pid_b = await _make_player(session, 3002, "Invitee")
    game_id = await _make_open_game(session, 3001)
    await _add_accepted_player(session, game_id, pid_b)

    result = await GameService(session).get_my_upcoming_matches(3002)

    assert len(result) == 1
    game, count = result[0]
    assert game.id == game_id
    assert count == 2  # organizer + accepted invitee


# ── Sprint 10.3 — immediate visibility regression ───────────────────────────────
# Root cause: GameService.create_game() used to leave a new match in DRAFT
# status, and get_my_upcoming_matches() explicitly excludes DRAFT. Only the
# Organize Match bot handler remembered to call MatchLifecycleService to open
# it — any other caller (e.g. the REST API) left the match permanently
# invisible. create_game() now opens the match itself, so these tests call it
# with NO manual transition afterward, exactly reproducing the reported bug.

async def test_newly_created_match_appears_immediately_for_organizer(session):
    """A match created via create_game() alone (no manual OPEN transition)
    must appear immediately in the organizer's My Matches list."""
    await _make_player(session, 20001, "Organizer")
    game = await GameService(session).create_game(
        creator_telegram_id=20001,
        data=GameCreate(
            court="High Park Court 3",
            area="Downtown",
            date=date(2026, 9, 1),
            time=time(18, 0),
            match_type=MatchType.SINGLES,
        ),
    )
    assert game is not None
    assert game.status == GameStatus.OPEN  # visible immediately, not DRAFT

    result = await GameService(session).get_my_upcoming_matches(20001)

    assert len(result) == 1
    assert result[0][0].id == game.id


async def test_joined_match_appears_immediately_for_joiner(session):
    """A match another player joins via join_match() must appear immediately
    in the joiner's My Matches list — not just for the organizer."""
    await _make_player(session, 20002, "Organizer")
    await _make_player(session, 20003, "Joiner")
    game = await GameService(session).create_game(
        creator_telegram_id=20002,
        data=GameCreate(
            court="High Park Court 3",
            area="Downtown",
            date=date(2026, 9, 1),
            time=time(18, 0),
            match_type=MatchType.SINGLES,
        ),
    )
    assert game is not None

    _, err = await GameService(session).join_match(game.id, 20003)
    assert err == ""

    result = await GameService(session).get_my_upcoming_matches(20003)

    assert len(result) == 1
    assert result[0][0].id == game.id


async def test_invited_not_yet_accepted_not_shown(session):
    """Player with only INVITED status does not see the match."""
    await _make_player(session, 4001, "Organizer")
    pid_b = await _make_player(session, 4002, "Invitee")
    game_id = await _make_open_game(session, 4001)

    await GamePlayerRepository(session).add_player_to_game(
        game_id, pid_b, GamePlayerStatus.INVITED
    )

    result = await GameService(session).get_my_upcoming_matches(4002)
    assert result == []


# ── Multiple matches ──────────────────────────────────────────────────────────

async def test_multiple_matches_returned(session):
    """Player organizing multiple matches sees all of them."""
    await _make_player(session, 5001)
    id1 = await _make_open_game(session, 5001, match_date=date(2026, 9, 1))
    id2 = await _make_open_game(session, 5001, match_date=date(2026, 9, 3))
    id3 = await _make_open_game(session, 5001, match_date=date(2026, 9, 5))

    result = await GameService(session).get_my_upcoming_matches(5001)

    assert len(result) == 3
    game_ids = [g.id for g, _ in result]
    assert id1 in game_ids
    assert id2 in game_ids
    assert id3 in game_ids


# ── Sort order ────────────────────────────────────────────────────────────────

async def test_matches_sorted_by_date_ascending(session):
    """Upcoming matches are sorted by date ascending (soonest first)."""
    await _make_player(session, 6001)
    id_late = await _make_open_game(session, 6001, match_date=date(2026, 10, 1))
    id_early = await _make_open_game(session, 6001, match_date=date(2026, 8, 1))
    id_mid = await _make_open_game(session, 6001, match_date=date(2026, 9, 1))

    result = await GameService(session).get_my_upcoming_matches(6001)

    ids = [g.id for g, _ in result]
    assert ids == [id_early, id_mid, id_late]


async def test_matches_sorted_by_time_within_same_date(session):
    """Matches on the same date are sorted by time ascending."""
    await _make_player(session, 7001)
    id_late = await _make_open_game(session, 7001, match_date=date(2026, 9, 1), match_time=time(20, 0))
    id_early = await _make_open_game(session, 7001, match_date=date(2026, 9, 1), match_time=time(8, 0))
    id_mid = await _make_open_game(session, 7001, match_date=date(2026, 9, 1), match_time=time(14, 0))

    result = await GameService(session).get_my_upcoming_matches(7001)

    ids = [g.id for g, _ in result]
    assert ids == [id_early, id_mid, id_late]


# ── Excluded statuses ─────────────────────────────────────────────────────────

async def test_completed_matches_excluded(session):
    """COMPLETED matches are not returned."""
    await _make_player(session, 8001)
    game_id = await _make_open_game(session, 8001)
    await _force_status(session, game_id, GameStatus.COMPLETED)

    result = await GameService(session).get_my_upcoming_matches(8001)
    assert result == []


async def test_cancelled_matches_excluded(session):
    """CANCELLED matches are not returned."""
    await _make_player(session, 9001)
    game_id = await _make_open_game(session, 9001)
    await _force_status(session, game_id, GameStatus.CANCELLED)

    result = await GameService(session).get_my_upcoming_matches(9001)
    assert result == []


async def test_expired_matches_excluded(session):
    """EXPIRED matches are not returned."""
    await _make_player(session, 10001)
    game_id = await _make_open_game(session, 10001)
    await _force_status(session, game_id, GameStatus.EXPIRED)

    result = await GameService(session).get_my_upcoming_matches(10001)
    assert result == []


# ── All upcoming statuses included ───────────────────────────────────────────

async def test_all_upcoming_statuses_included(session):
    """OPEN, PARTIALLY_FILLED, FULL, and CONFIRMED all appear in results."""
    await _make_player(session, 11001)

    id_open = await _make_open_game(session, 11001, match_date=date(2026, 9, 1))
    id_partial = await _make_open_game(session, 11001, match_date=date(2026, 9, 2))
    await _force_status(session, id_partial, GameStatus.PARTIALLY_FILLED)
    id_full = await _make_open_game(session, 11001, match_date=date(2026, 9, 3))
    await _force_status(session, id_full, GameStatus.FULL)
    id_confirmed = await _make_open_game(session, 11001, match_date=date(2026, 9, 4))
    await _force_status(session, id_confirmed, GameStatus.CONFIRMED)

    result = await GameService(session).get_my_upcoming_matches(11001)

    returned_ids = {g.id for g, _ in result}
    assert id_open in returned_ids
    assert id_partial in returned_ids
    assert id_full in returned_ids
    assert id_confirmed in returned_ids


# ── required_players in GameRead ─────────────────────────────────────────────

async def test_game_read_required_players_singles(session):
    """GameRead.required_players is 2 for a singles match."""
    await _make_player(session, 12001)
    game_id = await _make_open_game(session, 12001, match_type=MatchType.SINGLES)

    result = await GameService(session).get_my_upcoming_matches(12001)
    game, _ = result[0]
    assert game.required_players == 2


async def test_game_read_required_players_doubles(session):
    """GameRead.required_players is 4 for a doubles match."""
    await _make_player(session, 13001)
    game_id = await _make_open_game(session, 13001, match_type=MatchType.DOUBLES)

    result = await GameService(session).get_my_upcoming_matches(13001)
    game, _ = result[0]
    assert game.required_players == 4
