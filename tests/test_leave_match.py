"""Tests for Sprint 6.3 — Leave Match service method."""
from datetime import date, time

import pytest

from backend.app.database.models.game import GamePlayerStatus, GameStatus, MatchType
from backend.app.database.repositories.game_repository import GamePlayerRepository
from backend.app.schemas.game import GameCreate
from backend.app.schemas.player import PlayerCreate, PlayerUpdate
from backend.app.services.game_service import GameService
from backend.app.services.invitation_service import InvitationService
from backend.app.services.match_lifecycle_service import MatchLifecycleService
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


async def _make_open_game(session, organizer_tid: int, match_type: MatchType = MatchType.SINGLES) -> int:
    game = await GameService(session).create_game(
        creator_telegram_id=organizer_tid,
        data=GameCreate(
            court="High Park Court 3",
            area="Downtown",
            date=date(2026, 9, 1),
            time=time(18, 0),
            match_type=match_type,
            required_level=3.0,
        ),
    )
    assert game is not None
    return game.id


async def _accept_invitation(session, game_id: int, invitee_tid: int) -> None:
    """Invite a player and have them accept — adds a committed GamePlayer row."""
    invitee = await PlayerService(session).get_by_telegram_id(invitee_tid)
    assert invitee is not None
    inv = await InvitationService(session).create_invitation(game_id, invitee.id)
    assert inv is not None
    await InvitationService(session).accept(inv.id, invitee_tid)


# ── Error cases ───────────────────────────────────────────────────────────────

async def test_leave_game_not_found(session):
    await _make_player(session, 1001)
    _, err = await GameService(session).leave_match(99999, 1001)
    assert err == "leave_match_not_allowed"


async def test_leave_organizer_cannot_leave(session):
    await _make_player(session, 2001, "Organizer")
    await _make_player(session, 2002, "Participant")
    game_id = await _make_open_game(session, 2001)
    await _accept_invitation(session, game_id, 2002)

    _, err = await GameService(session).leave_match(game_id, 2001)
    assert err == "leave_match_organizer"


async def test_leave_not_a_participant(session):
    """Outsider tries to leave a PARTIALLY_FILLED match they never joined."""
    await _make_player(session, 3001, "Organizer")
    await _make_player(session, 3002, "Participant")
    await _make_player(session, 3003, "Outsider")
    game_id = await _make_open_game(session, 3001, MatchType.DOUBLES)
    await _accept_invitation(session, game_id, 3002)  # game is now PARTIALLY_FILLED

    _, err = await GameService(session).leave_match(game_id, 3003)
    assert err == "leave_match_not_participant"


async def test_leave_wrong_status_cancelled(session):
    await _make_player(session, 4001, "Organizer")
    await _make_player(session, 4002, "Participant")
    game_id = await _make_open_game(session, 4001)
    await _accept_invitation(session, game_id, 4002)
    await MatchLifecycleService(session).transition(game_id, GameStatus.CANCELLED)

    _, err = await GameService(session).leave_match(game_id, 4002)
    assert err == "leave_match_not_allowed"


# ── Successful leave — lifecycle transitions ──────────────────────────────────

async def test_leave_singles_full_to_open(session):
    """Singles: last non-organizer leaves FULL match → OPEN (skips PARTIALLY_FILLED)."""
    await _make_player(session, 5001, "Organizer")
    await _make_player(session, 5002, "Participant")
    game_id = await _make_open_game(session, 5001, MatchType.SINGLES)
    await _accept_invitation(session, game_id, 5002)  # singles: 2/2 → FULL

    gp_repo = GamePlayerRepository(session)
    assert await gp_repo.count_committed_players(game_id) == 2

    updated, err = await GameService(session).leave_match(game_id, 5002)
    assert err == ""
    assert updated is not None
    assert updated.status == GameStatus.OPEN
    assert await gp_repo.count_committed_players(game_id) == 1


async def test_leave_doubles_full_to_partially_filled(session):
    """Doubles: one leaves FULL (4) → PARTIALLY_FILLED (3)."""
    await _make_player(session, 6001, "Organizer")
    await _make_player(session, 6002, "P2")
    await _make_player(session, 6003, "P3")
    await _make_player(session, 6004, "P4")
    game_id = await _make_open_game(session, 6001, MatchType.DOUBLES)
    await _accept_invitation(session, game_id, 6002)
    await _accept_invitation(session, game_id, 6003)
    await _accept_invitation(session, game_id, 6004)  # 4/4 → FULL

    gp_repo = GamePlayerRepository(session)
    assert await gp_repo.count_committed_players(game_id) == 4

    updated, err = await GameService(session).leave_match(game_id, 6004)
    assert err == ""
    assert updated.status == GameStatus.PARTIALLY_FILLED
    assert await gp_repo.count_committed_players(game_id) == 3


async def test_leave_doubles_partially_filled_to_open(session):
    """Doubles: last non-organizer leaves PARTIALLY_FILLED → OPEN."""
    await _make_player(session, 7001, "Organizer")
    await _make_player(session, 7002, "Participant")
    game_id = await _make_open_game(session, 7001, MatchType.DOUBLES)
    await _accept_invitation(session, game_id, 7002)  # 2/4 → PARTIALLY_FILLED

    gp_repo = GamePlayerRepository(session)
    assert await gp_repo.count_committed_players(game_id) == 2

    updated, err = await GameService(session).leave_match(game_id, 7002)
    assert err == ""
    assert updated.status == GameStatus.OPEN
    assert await gp_repo.count_committed_players(game_id) == 1


async def test_leave_removes_game_player_row(session):
    """After leaving, the player's GamePlayer row is deleted."""
    await _make_player(session, 8001, "Organizer")
    await _make_player(session, 8002, "Leaver")
    game_id = await _make_open_game(session, 8001)
    await _accept_invitation(session, game_id, 8002)

    leaver = await PlayerService(session).get_by_telegram_id(8002)
    assert leaver is not None

    gp_repo = GamePlayerRepository(session)
    assert await gp_repo.get_participation(game_id, leaver.id) is not None

    await GameService(session).leave_match(game_id, 8002)

    assert await gp_repo.get_participation(game_id, leaver.id) is None


async def test_leave_match_no_longer_appears_in_my_matches(session):
    """After leaving, the match is absent from the ex-participant's My Matches."""
    await _make_player(session, 9001, "Organizer")
    await _make_player(session, 9002, "Leaver")
    game_id = await _make_open_game(session, 9001)
    await _accept_invitation(session, game_id, 9002)

    matches_before = await GameService(session).get_my_upcoming_matches(9002)
    assert any(g.id == game_id for g, _ in matches_before)

    await GameService(session).leave_match(game_id, 9002)

    matches_after = await GameService(session).get_my_upcoming_matches(9002)
    assert not any(g.id == game_id for g, _ in matches_after)


# ── Leaving a CONFIRMED match ─────────────────────────────────────────────────

async def _confirm_game(session, game_id: int, organizer_tid: int) -> None:
    """Advance a FULL game to CONFIRMED status via GameService."""
    updated, _, err = await GameService(session).confirm_match(game_id, organizer_tid)
    assert err == "", f"confirm_match returned error: {err}"
    assert updated is not None and updated.status == GameStatus.CONFIRMED


async def test_leave_confirmed_singles_to_open(session):
    """Leaving a CONFIRMED singles match (2→1 players) reverts status to OPEN."""
    await _make_player(session, 10001, "Organizer")
    await _make_player(session, 10002, "Participant")
    game_id = await _make_open_game(session, 10001, MatchType.SINGLES)
    await _accept_invitation(session, game_id, 10002)  # FULL (2/2)
    await _confirm_game(session, game_id, 10001)

    updated, err = await GameService(session).leave_match(game_id, 10002)
    assert err == ""
    assert updated is not None
    assert updated.status == GameStatus.OPEN

    gp_repo = GamePlayerRepository(session)
    assert await gp_repo.count_committed_players(game_id) == 1


async def test_leave_confirmed_doubles_to_partially_filled(session):
    """Leaving a CONFIRMED doubles match (4→3 players) reverts status to PARTIALLY_FILLED."""
    await _make_player(session, 11001, "Organizer")
    await _make_player(session, 11002, "P2")
    await _make_player(session, 11003, "P3")
    await _make_player(session, 11004, "P4")
    game_id = await _make_open_game(session, 11001, MatchType.DOUBLES)
    await _accept_invitation(session, game_id, 11002)
    await _accept_invitation(session, game_id, 11003)
    await _accept_invitation(session, game_id, 11004)  # FULL (4/4)
    await _confirm_game(session, game_id, 11001)

    updated, err = await GameService(session).leave_match(game_id, 11004)
    assert err == ""
    assert updated is not None
    assert updated.status == GameStatus.PARTIALLY_FILLED

    gp_repo = GamePlayerRepository(session)
    assert await gp_repo.count_committed_players(game_id) == 3


async def test_leave_confirmed_organizer_still_blocked(session):
    """Organizer still cannot leave even a CONFIRMED match."""
    await _make_player(session, 12001, "Organizer")
    await _make_player(session, 12002, "Participant")
    game_id = await _make_open_game(session, 12001, MatchType.SINGLES)
    await _accept_invitation(session, game_id, 12002)
    await _confirm_game(session, game_id, 12001)

    _, err = await GameService(session).leave_match(game_id, 12001)
    assert err == "leave_match_organizer"
