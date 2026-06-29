"""Tests for Sprint 5.3 – Organizer Confirmation."""
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


async def _make_game_at_status(
    session,
    organizer_tid: int,
    target_status: GameStatus,
    match_type: MatchType = MatchType.SINGLES,
) -> int:
    """Create a game and force it to the requested status via MatchLifecycleService."""
    game = await GameService(session).create_game(
        creator_telegram_id=organizer_tid,
        data=GameCreate(
            court="High Park Court 3",
            area="Downtown",
            date=date(2026, 9, 15),
            time=time(18, 0),
            match_type=match_type,
        ),
    )
    assert game is not None
    lc = MatchLifecycleService(session)
    path = {
        GameStatus.OPEN: [GameStatus.OPEN],
        GameStatus.PARTIALLY_FILLED: [GameStatus.OPEN, GameStatus.PARTIALLY_FILLED],
        GameStatus.FULL: [GameStatus.OPEN, GameStatus.PARTIALLY_FILLED, GameStatus.FULL],
    }
    for status in path.get(target_status, []):
        await lc.transition(game.id, status)
    return game.id


async def _add_accepted_player(session, game_id: int, player_id: int) -> None:
    """Insert a GamePlayer row with ACCEPTED status (simulates invitation acceptance)."""
    gp_repo = GamePlayerRepository(session)
    await gp_repo.add_player_to_game(game_id, player_id, GamePlayerStatus.ACCEPTED)


# ── FULL → CONFIRMED ──────────────────────────────────────────────────────────

async def test_confirm_match_success(session):
    """Organizer confirms a FULL singles match → status becomes CONFIRMED."""
    await _make_player(session, 1001, "Organizer")
    player_id = await _make_player(session, 1002, "PlayerA")
    game_id = await _make_game_at_status(session, 1001, GameStatus.FULL)
    await _add_accepted_player(session, game_id, player_id)

    svc = GameService(session)
    game, players, error = await svc.confirm_match(game_id, 1001)

    assert error == ""
    assert game is not None
    assert game.status == GameStatus.CONFIRMED


async def test_confirm_match_returns_committed_players(session):
    """confirm_match returns all committed players (organizer + accepted)."""
    await _make_player(session, 2001, "Organizer")
    pid_a = await _make_player(session, 2002, "PlayerA")
    pid_b = await _make_player(session, 2003, "PlayerB")
    game_id = await _make_game_at_status(session, 2001, GameStatus.FULL)
    await _add_accepted_player(session, game_id, pid_a)
    await _add_accepted_player(session, game_id, pid_b)

    _, players, error = await GameService(session).confirm_match(game_id, 2001)

    assert error == ""
    player_tids = {p.telegram_id for p in players}
    assert 2001 in player_tids  # organizer included
    assert 2002 in player_tids
    assert 2003 in player_tids


async def test_confirm_match_not_organizer_returns_error(session):
    """Non-organizer cannot confirm."""
    await _make_player(session, 3001, "Organizer")
    await _make_player(session, 3002, "OtherPlayer")
    game_id = await _make_game_at_status(session, 3001, GameStatus.FULL)

    _, _, error = await GameService(session).confirm_match(game_id, 3002)

    assert error == "confirm_match_not_yours"


async def test_confirm_match_wrong_status_returns_error(session):
    """Confirming a non-FULL game returns an error."""
    await _make_player(session, 4001, "Organizer")
    game_id = await _make_game_at_status(session, 4001, GameStatus.OPEN)

    _, _, error = await GameService(session).confirm_match(game_id, 4001)

    assert error == "confirm_match_wrong_status"


async def test_confirm_match_duplicate_prevented(session):
    """Confirming an already-CONFIRMED game returns an error."""
    await _make_player(session, 5001, "Organizer")
    player_id = await _make_player(session, 5002, "PlayerA")
    game_id = await _make_game_at_status(session, 5001, GameStatus.FULL)
    await _add_accepted_player(session, game_id, player_id)

    svc = GameService(session)
    _, _, first_error = await svc.confirm_match(game_id, 5001)
    assert first_error == ""

    _, _, second_error = await svc.confirm_match(game_id, 5001)
    assert second_error == "confirm_match_wrong_status"


# ── Organizer note optional ───────────────────────────────────────────────────

async def test_confirm_match_note_is_optional(session):
    """Service confirms successfully regardless of whether a note is provided."""
    await _make_player(session, 6001, "Organizer")
    player_id = await _make_player(session, 6002, "PlayerA")
    game_id = await _make_game_at_status(session, 6001, GameStatus.FULL)
    await _add_accepted_player(session, game_id, player_id)

    # Service itself doesn't know about the note (handler responsibility).
    # Just confirm that the service call succeeds without note-related args.
    game, players, error = await GameService(session).confirm_match(game_id, 6001)
    assert error == ""
    assert game.status == GameStatus.CONFIRMED


# ── Roster locked after CONFIRMED ────────────────────────────────────────────

async def test_roster_locked_after_confirmation(session):
    """InvitationService.create_invitation returns None for CONFIRMED games."""
    await _make_player(session, 7001, "Organizer")
    pid_a = await _make_player(session, 7002, "PlayerA")
    pid_b = await _make_player(session, 7003, "NewPlayer")
    game_id = await _make_game_at_status(session, 7001, GameStatus.FULL)
    await _add_accepted_player(session, game_id, pid_a)

    svc = GameService(session)
    _, _, error = await svc.confirm_match(game_id, 7001)
    assert error == ""

    # Now try to invite a new player — must be rejected
    inv_svc = InvitationService(session)
    result = await inv_svc.create_invitation(game_id, pid_b)
    assert result is None


async def test_invitation_allowed_when_open(session):
    """InvitationService.create_invitation still works for OPEN games."""
    await _make_player(session, 8001, "Organizer")
    pid_a = await _make_player(session, 8002, "PlayerA")
    game_id = await _make_game_at_status(session, 8001, GameStatus.OPEN)

    inv_svc = InvitationService(session)
    result = await inv_svc.create_invitation(game_id, pid_a)
    assert result is not None


async def test_invitation_allowed_when_partially_filled(session):
    """InvitationService.create_invitation works for PARTIALLY_FILLED games."""
    await _make_player(session, 9001, "Organizer")
    pid_a = await _make_player(session, 9002, "PlayerA")
    game_id = await _make_game_at_status(session, 9001, GameStatus.PARTIALLY_FILLED)

    inv_svc = InvitationService(session)
    result = await inv_svc.create_invitation(game_id, pid_a)
    assert result is not None


# ── Cancel Match ──────────────────────────────────────────────────────────────

async def test_cancel_match_success(session):
    """Organizer cancels a FULL match → status becomes CANCELLED."""
    await _make_player(session, 10001, "Organizer")
    game_id = await _make_game_at_status(session, 10001, GameStatus.FULL)

    game, error = await GameService(session).cancel_match(game_id, 10001)

    assert error == ""
    assert game is not None
    assert game.status == GameStatus.CANCELLED


async def test_cancel_match_not_organizer_returns_error(session):
    """Non-organizer cannot cancel."""
    await _make_player(session, 11001, "Organizer")
    await _make_player(session, 11002, "Other")
    game_id = await _make_game_at_status(session, 11001, GameStatus.FULL)

    _, error = await GameService(session).cancel_match(game_id, 11002)

    assert error == "cancel_match_not_yours"


async def test_cancel_match_already_cancelled_returns_error(session):
    """Cancelling an already-cancelled match returns an error."""
    await _make_player(session, 12001, "Organizer")
    game_id = await _make_game_at_status(session, 12001, GameStatus.FULL)

    svc = GameService(session)
    _, first_error = await svc.cancel_match(game_id, 12001)
    assert first_error == ""

    _, second_error = await svc.cancel_match(game_id, 12001)
    assert second_error == "cancel_match_not_cancellable"


async def test_cancel_confirmed_match_success(session):
    """Organizer can cancel a CONFIRMED match (roster unlock not required for cancel)."""
    await _make_player(session, 13001, "Organizer")
    pid_a = await _make_player(session, 13002, "PlayerA")
    game_id = await _make_game_at_status(session, 13001, GameStatus.FULL)
    await _add_accepted_player(session, game_id, pid_a)

    svc = GameService(session)
    _, _, _ = await svc.confirm_match(game_id, 13001)

    game, error = await svc.cancel_match(game_id, 13001)
    assert error == ""
    assert game.status == GameStatus.CANCELLED


# ── get_roster ────────────────────────────────────────────────────────────────

async def test_get_roster_returns_committed_players(session):
    """get_roster returns game details and all ACCEPTED/CONFIRMED players."""
    await _make_player(session, 14001, "Organizer")
    pid_a = await _make_player(session, 14002, "PlayerA")
    game_id = await _make_game_at_status(session, 14001, GameStatus.FULL)
    await _add_accepted_player(session, game_id, pid_a)

    game, players = await GameService(session).get_roster(game_id)

    assert game is not None
    assert game.id == game_id
    tids = {p.telegram_id for p in players}
    assert 14001 in tids
    assert 14002 in tids


async def test_get_roster_excludes_invited_players(session):
    """get_roster does not include players with INVITED status."""
    await _make_player(session, 15001, "Organizer")
    pid_a = await _make_player(session, 15002, "PlayerA")
    game_id = await _make_game_at_status(session, 15001, GameStatus.OPEN)

    gp_repo = GamePlayerRepository(session)
    await gp_repo.add_player_to_game(game_id, pid_a, GamePlayerStatus.INVITED)

    _, players = await GameService(session).get_roster(game_id)
    tids = {p.telegram_id for p in players}

    assert 15001 in tids   # organizer is CONFIRMED
    assert 15002 not in tids  # invited only, not committed


# ── Cancel match at all pre-start statuses (Task 3) ──────────────────────────

async def test_cancel_open_match_success(session):
    """Organizer can cancel an OPEN match."""
    await _make_player(session, 16001, "Organizer")
    game_id = await _make_game_at_status(session, 16001, GameStatus.OPEN)

    game, error = await GameService(session).cancel_match(game_id, 16001)

    assert error == ""
    assert game is not None
    assert game.status == GameStatus.CANCELLED


async def test_cancel_partially_filled_singles_success(session):
    """Organizer can cancel a PARTIALLY_FILLED match (singles, direct lifecycle)."""
    await _make_player(session, 17001, "Organizer")
    game_id = await _make_game_at_status(session, 17001, GameStatus.PARTIALLY_FILLED)

    game, error = await GameService(session).cancel_match(game_id, 17001)

    assert error == ""
    assert game is not None
    assert game.status == GameStatus.CANCELLED


async def test_cancel_partially_filled_doubles_success(session):
    """Organizer can cancel a PARTIALLY_FILLED doubles match — the reported bug."""
    await _make_player(session, 18001, "Organizer")
    pid_a = await _make_player(session, 18002, "PlayerA")
    game_id = await _make_game_at_status(session, 18001, GameStatus.PARTIALLY_FILLED, MatchType.DOUBLES)
    await _add_accepted_player(session, game_id, pid_a)

    game, error = await GameService(session).cancel_match(game_id, 18001)

    assert error == ""
    assert game is not None
    assert game.status == GameStatus.CANCELLED


async def test_cancel_in_progress_not_allowed(session):
    """Cancellation is blocked once the match is IN_PROGRESS."""
    await _make_player(session, 19001, "Organizer")
    game_id = await _make_game_at_status(session, 19001, GameStatus.FULL)
    lc = MatchLifecycleService(session)
    await lc.transition(game_id, GameStatus.CONFIRMED)
    await lc.transition(game_id, GameStatus.IN_PROGRESS)

    _, error = await GameService(session).cancel_match(game_id, 19001)

    assert error == "cancel_match_not_cancellable"


# ── Invitation text split by match type (Task 1) ─────────────────────────────

def test_inv_message_singles_en():
    """Singles invitation contains 'singles' and not 'doubles'."""
    from backend.app.bot.texts import t
    text = t("inv_message_singles", "en", date="01.09.2026", time="18:00", court="High Park", level=3.0, organizer="Alex")
    assert "singles" in text.lower()
    assert "doubles" not in text.lower()
    assert "01.09.2026" in text
    assert "High Park" in text


def test_inv_message_doubles_en():
    """Doubles invitation contains 'doubles' and looking-for-players line."""
    from backend.app.bot.texts import t
    text = t("inv_message_doubles", "en", date="01.09.2026", time="18:00", court="High Park", level=3.0, organizer="Alex")
    assert "doubles" in text.lower()
    assert "looking for more players" in text.lower()
    assert "01.09.2026" in text


def test_inv_message_singles_uk():
    from backend.app.bot.texts import t
    text = t("inv_message_singles", "uk", date="01.09.2026", time="18:00", court="High Park", level=3.0, organizer="Alex")
    assert "одиночний" in text.lower()


def test_inv_message_doubles_uk():
    from backend.app.bot.texts import t
    text = t("inv_message_doubles", "uk", date="01.09.2026", time="18:00", court="High Park", level=3.0, organizer="Alex")
    assert "парний" in text.lower()
    assert "шукаємо" in text.lower()


def test_inv_message_singles_ru():
    from backend.app.bot.texts import t
    text = t("inv_message_singles", "ru", date="01.09.2026", time="18:00", court="High Park", level=3.0, organizer="Alex")
    assert "одиночный" in text.lower()


def test_inv_message_doubles_ru():
    from backend.app.bot.texts import t
    text = t("inv_message_doubles", "ru", date="01.09.2026", time="18:00", court="High Park", level=3.0, organizer="Alex")
    assert "парный" in text.lower()
    assert "ищем" in text.lower()
