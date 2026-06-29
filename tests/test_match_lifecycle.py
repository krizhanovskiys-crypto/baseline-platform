"""Tests for Sprint 5.1 – Match Lifecycle State Machine."""
import pytest
from datetime import date, time

from backend.app.core.exceptions import InvalidTransitionError
from backend.app.database.models.game import Game, GameStatus, MatchType
from backend.app.database.repositories.game_repository import GameRepository
from backend.app.services.match_lifecycle_service import MatchLifecycleService


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _make_game(session, status: GameStatus = GameStatus.OPEN) -> int:
    """Create a bare Game row with the requested status (bypasses GameService)."""
    from backend.app.database.models.player import Player
    player = Player(telegram_id=9000 + id(status), first_name="Organizer")
    session.add(player)
    await session.flush()
    await session.refresh(player)

    game = Game(
        creator_id=player.id,
        court="High Park",
        area="Downtown",
        date=date(2026, 9, 1),
        time=time(18, 0),
        match_type=MatchType.SINGLES,
        status=status,
    )
    session.add(game)
    await session.flush()
    await session.refresh(game)
    return game.id


# ── Valid transitions ─────────────────────────────────────────────────────────

async def test_draft_to_open(session):
    game_id = await _make_game(session, GameStatus.DRAFT)
    svc = MatchLifecycleService(session)
    result = await svc.transition(game_id, GameStatus.OPEN)
    assert result.status == GameStatus.OPEN


async def test_open_to_partially_filled(session):
    game_id = await _make_game(session, GameStatus.OPEN)
    result = await MatchLifecycleService(session).transition(game_id, GameStatus.PARTIALLY_FILLED)
    assert result.status == GameStatus.PARTIALLY_FILLED


async def test_partially_filled_to_full(session):
    game_id = await _make_game(session, GameStatus.PARTIALLY_FILLED)
    result = await MatchLifecycleService(session).transition(game_id, GameStatus.FULL)
    assert result.status == GameStatus.FULL


async def test_full_to_confirmed(session):
    game_id = await _make_game(session, GameStatus.FULL)
    result = await MatchLifecycleService(session).transition(game_id, GameStatus.CONFIRMED)
    assert result.status == GameStatus.CONFIRMED


async def test_confirmed_to_in_progress(session):
    game_id = await _make_game(session, GameStatus.CONFIRMED)
    result = await MatchLifecycleService(session).transition(game_id, GameStatus.IN_PROGRESS)
    assert result.status == GameStatus.IN_PROGRESS


async def test_confirmed_to_open(session):
    game_id = await _make_game(session, GameStatus.CONFIRMED)
    result = await MatchLifecycleService(session).transition(game_id, GameStatus.OPEN)
    assert result.status == GameStatus.OPEN


async def test_confirmed_to_partially_filled(session):
    game_id = await _make_game(session, GameStatus.CONFIRMED)
    result = await MatchLifecycleService(session).transition(game_id, GameStatus.PARTIALLY_FILLED)
    assert result.status == GameStatus.PARTIALLY_FILLED


async def test_in_progress_to_completed(session):
    game_id = await _make_game(session, GameStatus.IN_PROGRESS)
    result = await MatchLifecycleService(session).transition(game_id, GameStatus.COMPLETED)
    assert result.status == GameStatus.COMPLETED


async def test_draft_to_cancelled(session):
    game_id = await _make_game(session, GameStatus.DRAFT)
    result = await MatchLifecycleService(session).transition(game_id, GameStatus.CANCELLED)
    assert result.status == GameStatus.CANCELLED


async def test_open_to_cancelled(session):
    game_id = await _make_game(session, GameStatus.OPEN)
    result = await MatchLifecycleService(session).transition(game_id, GameStatus.CANCELLED)
    assert result.status == GameStatus.CANCELLED


async def test_partially_filled_to_cancelled(session):
    game_id = await _make_game(session, GameStatus.PARTIALLY_FILLED)
    result = await MatchLifecycleService(session).transition(game_id, GameStatus.CANCELLED)
    assert result.status == GameStatus.CANCELLED


async def test_full_to_cancelled(session):
    game_id = await _make_game(session, GameStatus.FULL)
    result = await MatchLifecycleService(session).transition(game_id, GameStatus.CANCELLED)
    assert result.status == GameStatus.CANCELLED


async def test_confirmed_to_cancelled(session):
    game_id = await _make_game(session, GameStatus.CONFIRMED)
    result = await MatchLifecycleService(session).transition(game_id, GameStatus.CANCELLED)
    assert result.status == GameStatus.CANCELLED


async def test_open_to_expired(session):
    game_id = await _make_game(session, GameStatus.OPEN)
    result = await MatchLifecycleService(session).transition(game_id, GameStatus.EXPIRED)
    assert result.status == GameStatus.EXPIRED


async def test_partially_filled_to_expired(session):
    game_id = await _make_game(session, GameStatus.PARTIALLY_FILLED)
    result = await MatchLifecycleService(session).transition(game_id, GameStatus.EXPIRED)
    assert result.status == GameStatus.EXPIRED


# ── Invalid transitions ───────────────────────────────────────────────────────

async def test_open_to_confirmed_invalid(session):
    game_id = await _make_game(session, GameStatus.OPEN)
    with pytest.raises(InvalidTransitionError) as exc_info:
        await MatchLifecycleService(session).transition(game_id, GameStatus.CONFIRMED)
    assert exc_info.value.from_status == GameStatus.OPEN
    assert exc_info.value.to_status == GameStatus.CONFIRMED


async def test_draft_to_full_invalid(session):
    game_id = await _make_game(session, GameStatus.DRAFT)
    with pytest.raises(InvalidTransitionError):
        await MatchLifecycleService(session).transition(game_id, GameStatus.FULL)


async def test_in_progress_to_cancelled_invalid(session):
    game_id = await _make_game(session, GameStatus.IN_PROGRESS)
    with pytest.raises(InvalidTransitionError):
        await MatchLifecycleService(session).transition(game_id, GameStatus.CANCELLED)


async def test_completed_to_open_invalid(session):
    game_id = await _make_game(session, GameStatus.COMPLETED)
    with pytest.raises(InvalidTransitionError):
        await MatchLifecycleService(session).transition(game_id, GameStatus.OPEN)


async def test_cancelled_to_open_invalid(session):
    game_id = await _make_game(session, GameStatus.CANCELLED)
    with pytest.raises(InvalidTransitionError):
        await MatchLifecycleService(session).transition(game_id, GameStatus.OPEN)


async def test_expired_to_open_invalid(session):
    game_id = await _make_game(session, GameStatus.EXPIRED)
    with pytest.raises(InvalidTransitionError):
        await MatchLifecycleService(session).transition(game_id, GameStatus.OPEN)


async def test_draft_to_expired_invalid(session):
    game_id = await _make_game(session, GameStatus.DRAFT)
    with pytest.raises(InvalidTransitionError):
        await MatchLifecycleService(session).transition(game_id, GameStatus.EXPIRED)


# ── Duplicate transitions (same → same) ──────────────────────────────────────

async def test_open_to_open_duplicate(session):
    game_id = await _make_game(session, GameStatus.OPEN)
    with pytest.raises(InvalidTransitionError):
        await MatchLifecycleService(session).transition(game_id, GameStatus.OPEN)


async def test_confirmed_to_confirmed_duplicate(session):
    game_id = await _make_game(session, GameStatus.CONFIRMED)
    with pytest.raises(InvalidTransitionError):
        await MatchLifecycleService(session).transition(game_id, GameStatus.CONFIRMED)


async def test_completed_to_completed_duplicate(session):
    game_id = await _make_game(session, GameStatus.COMPLETED)
    with pytest.raises(InvalidTransitionError):
        await MatchLifecycleService(session).transition(game_id, GameStatus.COMPLETED)


# ── Skipped transitions ───────────────────────────────────────────────────────

async def test_draft_skips_to_confirmed(session):
    game_id = await _make_game(session, GameStatus.DRAFT)
    with pytest.raises(InvalidTransitionError):
        await MatchLifecycleService(session).transition(game_id, GameStatus.CONFIRMED)


async def test_open_skips_to_in_progress(session):
    game_id = await _make_game(session, GameStatus.OPEN)
    with pytest.raises(InvalidTransitionError):
        await MatchLifecycleService(session).transition(game_id, GameStatus.IN_PROGRESS)


async def test_open_skips_to_completed(session):
    game_id = await _make_game(session, GameStatus.OPEN)
    with pytest.raises(InvalidTransitionError):
        await MatchLifecycleService(session).transition(game_id, GameStatus.COMPLETED)


async def test_partially_filled_skips_to_confirmed(session):
    game_id = await _make_game(session, GameStatus.PARTIALLY_FILLED)
    with pytest.raises(InvalidTransitionError):
        await MatchLifecycleService(session).transition(game_id, GameStatus.CONFIRMED)


# ── Game not found ────────────────────────────────────────────────────────────

async def test_transition_unknown_game_raises(session):
    with pytest.raises(ValueError, match="not found"):
        await MatchLifecycleService(session).transition(99999, GameStatus.OPEN)


# ── InvalidTransitionError carries context ────────────────────────────────────

async def test_exception_carries_status_context(session):
    # FULL → EXPIRED is not a valid transition; use it to verify exception carries status context.
    game_id = await _make_game(session, GameStatus.FULL)
    with pytest.raises(InvalidTransitionError) as exc_info:
        await MatchLifecycleService(session).transition(game_id, GameStatus.EXPIRED)
    err = exc_info.value
    assert err.from_status == GameStatus.FULL
    assert err.to_status == GameStatus.EXPIRED
    assert "full" in str(err)
    assert "expired" in str(err)
