"""Tests for Sprint 6.5 — Lazy match expiration."""
from datetime import date, time

from backend.app.database.models.game import GameStatus, MatchType
from backend.app.schemas.game import GameCreate
from backend.app.schemas.player import PlayerCreate, PlayerUpdate
from backend.app.services.game_service import GameService
from backend.app.services.invitation_service import InvitationService
from backend.app.services.match_lifecycle_service import MatchLifecycleService
from backend.app.services.player_service import PlayerService

_PAST = date(2020, 1, 1)    # guaranteed past
_FUTURE = date(2099, 1, 1)  # guaranteed future
_TIME = time(10, 0)


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _make_player(session, tid: int, name: str = "Player") -> int:
    svc = PlayerService(session)
    player, _ = await svc.get_or_create(PlayerCreate(telegram_id=tid, first_name=name))
    await svc.update_profile(
        tid,
        PlayerUpdate(language="en", skill_level=3.0, home_area="Downtown", preferred_courts=["High Park"]),
    )
    return player.id


async def _make_game_at(
    session,
    organizer_tid: int,
    match_date: date,
    target_status: GameStatus,
    match_type: MatchType = MatchType.SINGLES,
) -> int:
    game = await GameService(session).create_game(
        creator_telegram_id=organizer_tid,
        data=GameCreate(
            court="High Park Court 1",
            area="Downtown",
            date=match_date,
            time=_TIME,
            match_type=match_type,
        ),
    )
    assert game is not None
    # create_game() already opens the match, so the path starts from OPEN.
    lc = MatchLifecycleService(session)
    path = {
        GameStatus.OPEN:             [],
        GameStatus.PARTIALLY_FILLED: [GameStatus.PARTIALLY_FILLED],
        GameStatus.FULL:             [GameStatus.PARTIALLY_FILLED, GameStatus.FULL],
        GameStatus.CONFIRMED:        [GameStatus.PARTIALLY_FILLED, GameStatus.FULL, GameStatus.CONFIRMED],
    }
    for s in path.get(target_status, []):
        await lc.transition(game.id, s)
    return game.id


# ── expire_if_stale — all four expirable statuses ─────────────────────────────

async def test_expire_stale_open(session):
    await _make_player(session, 1001)
    game_id = await _make_game_at(session, 1001, _PAST, GameStatus.OPEN)
    expired = await MatchLifecycleService(session).expire_if_stale(game_id)
    assert expired is True
    game = await GameService(session).get_game(game_id)
    assert game.status == GameStatus.EXPIRED


async def test_expire_stale_partially_filled(session):
    await _make_player(session, 2001)
    game_id = await _make_game_at(session, 2001, _PAST, GameStatus.PARTIALLY_FILLED)
    expired = await MatchLifecycleService(session).expire_if_stale(game_id)
    assert expired is True
    game = await GameService(session).get_game(game_id)
    assert game.status == GameStatus.EXPIRED


async def test_expire_stale_full(session):
    await _make_player(session, 3001)
    game_id = await _make_game_at(session, 3001, _PAST, GameStatus.FULL)
    expired = await MatchLifecycleService(session).expire_if_stale(game_id)
    assert expired is True
    game = await GameService(session).get_game(game_id)
    assert game.status == GameStatus.EXPIRED


async def test_expire_stale_confirmed(session):
    await _make_player(session, 4001)
    game_id = await _make_game_at(session, 4001, _PAST, GameStatus.CONFIRMED)
    expired = await MatchLifecycleService(session).expire_if_stale(game_id)
    assert expired is True
    game = await GameService(session).get_game(game_id)
    assert game.status == GameStatus.EXPIRED


# ── expire_if_stale — must NOT expire ────────────────────────────────────────

async def test_future_game_not_expired(session):
    await _make_player(session, 5001)
    game_id = await _make_game_at(session, 5001, _FUTURE, GameStatus.OPEN)
    expired = await MatchLifecycleService(session).expire_if_stale(game_id)
    assert expired is False
    game = await GameService(session).get_game(game_id)
    assert game.status == GameStatus.OPEN


async def test_cancelled_past_game_not_expired(session):
    """CANCELLED is terminal — expiry never touches it regardless of date."""
    await _make_player(session, 6001)
    game_id = await _make_game_at(session, 6001, _PAST, GameStatus.OPEN)
    await MatchLifecycleService(session).transition(game_id, GameStatus.CANCELLED)
    expired = await MatchLifecycleService(session).expire_if_stale(game_id)
    assert expired is False
    game = await GameService(session).get_game(game_id)
    assert game.status == GameStatus.CANCELLED


async def test_already_expired_game_idempotent(session):
    """expire_if_stale on an already-EXPIRED game returns False without error."""
    await _make_player(session, 7001)
    game_id = await _make_game_at(session, 7001, _PAST, GameStatus.OPEN)
    await MatchLifecycleService(session).transition(game_id, GameStatus.EXPIRED)
    expired = await MatchLifecycleService(session).expire_if_stale(game_id)
    assert expired is False


# ── get_my_upcoming_matches — lazy expiry ────────────────────────────────────

async def test_past_match_absent_from_my_matches(session):
    """A past-dated OPEN match is expired and excluded from My Matches in one call."""
    await _make_player(session, 8001)
    game_id = await _make_game_at(session, 8001, _PAST, GameStatus.OPEN)
    matches = await GameService(session).get_my_upcoming_matches(8001)
    assert not any(g.id == game_id for g, _ in matches)
    game = await GameService(session).get_game(game_id)
    assert game.status == GameStatus.EXPIRED


async def test_future_match_present_in_my_matches(session):
    await _make_player(session, 9001)
    game_id = await _make_game_at(session, 9001, _FUTURE, GameStatus.OPEN)
    matches = await GameService(session).get_my_upcoming_matches(9001)
    assert any(g.id == game_id for g, _ in matches)


async def test_multiple_statuses_all_expire_on_my_matches(session):
    """All four pre-start statuses are expired in a single get_my_upcoming_matches call."""
    await _make_player(session, 10001)
    ids = [
        await _make_game_at(session, 10001, _PAST, GameStatus.OPEN),
        await _make_game_at(session, 10001, _PAST, GameStatus.PARTIALLY_FILLED),
        await _make_game_at(session, 10001, _PAST, GameStatus.FULL),
        await _make_game_at(session, 10001, _PAST, GameStatus.CONFIRMED),
    ]
    matches = await GameService(session).get_my_upcoming_matches(10001)
    present_ids = {g.id for g, _ in matches}
    for gid in ids:
        assert gid not in present_ids
        game = await GameService(session).get_game(gid)
        assert game.status == GameStatus.EXPIRED


# ── confirm_match blocked by expiry ──────────────────────────────────────────

async def test_confirm_past_full_match_returns_wrong_status(session):
    """confirm_match on a past FULL match expires it first — status is then not FULL."""
    await _make_player(session, 11001)
    game_id = await _make_game_at(session, 11001, _PAST, GameStatus.FULL)
    _, _, error = await GameService(session).confirm_match(game_id, 11001)
    assert error == "confirm_match_wrong_status"
    game = await GameService(session).get_game(game_id)
    assert game.status == GameStatus.EXPIRED


# ── cancel_match — EXPIRED takes precedence ───────────────────────────────────

async def test_cancel_past_open_match_becomes_expired(session):
    """EXPIRED takes precedence over CANCELLED for past matches."""
    await _make_player(session, 12001)
    game_id = await _make_game_at(session, 12001, _PAST, GameStatus.OPEN)
    _, error = await GameService(session).cancel_match(game_id, 12001)
    assert error == "cancel_match_not_cancellable"
    game = await GameService(session).get_game(game_id)
    assert game.status == GameStatus.EXPIRED


# ── invitation accept blocked by expiry ──────────────────────────────────────

async def test_accept_invitation_for_expired_match_rejected(session):
    """Accepting an invitation after the match has passed returns inv_game_expired."""
    await _make_player(session, 13001, "Organizer")
    invitee_id = await _make_player(session, 13002, "Invitee")
    game_id = await _make_game_at(session, 13001, _PAST, GameStatus.OPEN)

    inv_svc = InvitationService(session)
    inv = await inv_svc.create_invitation(game_id, invitee_id)
    assert inv is not None, "Invitation must be created while game is still OPEN in DB"

    _, error, _ = await inv_svc.accept(inv.id, 13002)
    assert error == "inv_game_expired"
    game = await GameService(session).get_game(game_id)
    assert game.status == GameStatus.EXPIRED
