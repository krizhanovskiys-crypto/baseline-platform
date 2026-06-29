"""Tests for Sprint 5.2 – Automatic Match Lifecycle Transitions."""
import pytest
from datetime import date, time

from backend.app.database.models.game import Game, GamePlayerStatus, GameStatus, MatchType
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
    """Create a game in OPEN status (DRAFT → OPEN via lifecycle)."""
    game = await GameService(session).create_game(
        creator_telegram_id=organizer_tid,
        data=GameCreate(
            court="High Park",
            area="Downtown",
            date=date(2026, 9, 1),
            time=time(18, 0),
            match_type=match_type,
        ),
    )
    assert game is not None
    await MatchLifecycleService(session).transition(game.id, GameStatus.OPEN)
    return game.id


async def _invite_and_accept(session, game_id: int, invitee_tid: int) -> tuple:
    """Create an invitation for invitee_tid and accept it. Returns accept() result."""
    from backend.app.services.player_service import PlayerService as PS
    player = await PS(session).get_by_telegram_id(invitee_tid)
    svc = InvitationService(session)
    inv = await svc.create_invitation(game_id, player.id)
    assert inv is not None
    return await svc.accept(inv.id, invitee_tid)


# ── required_players property ─────────────────────────────────────────────────

async def test_required_players_singles(session):
    await _make_player(session, 2001)
    game_id = await _make_open_game(session, 2001, MatchType.SINGLES)
    from backend.app.database.repositories.game_repository import GameRepository
    game = await GameRepository(session).get_by_id(game_id)
    assert game.required_players == 2


async def test_required_players_doubles(session):
    await _make_player(session, 2002)
    game_id = await _make_open_game(session, 2002, MatchType.DOUBLES)
    from backend.app.database.repositories.game_repository import GameRepository
    game = await GameRepository(session).get_by_id(game_id)
    assert game.required_players == 4


# ── OPEN → PARTIALLY_FILLED ───────────────────────────────────────────────────

async def test_open_to_partially_filled_on_first_accept(session):
    """First player accepting a doubles invitation transitions game OPEN → PARTIALLY_FILLED."""
    await _make_player(session, 3001, "Organizer")
    await _make_player(session, 3002, "PlayerA")
    game_id = await _make_open_game(session, 3001, MatchType.DOUBLES)

    _, error, new_status = await _invite_and_accept(session, game_id, 3002)

    assert error == ""
    assert new_status is None  # not yet FULL (doubles needs 4 players)

    from backend.app.database.repositories.game_repository import GameRepository
    game = await GameRepository(session).get_by_id(game_id)
    assert game.status == GameStatus.PARTIALLY_FILLED


# ── PARTIALLY_FILLED → FULL (singles) ────────────────────────────────────────

async def test_singles_becomes_full_on_first_accept(session):
    """Singles only needs 2 players: creator + 1 accept → FULL in one step."""
    await _make_player(session, 4001, "Organizer")
    await _make_player(session, 4002, "PlayerA")
    game_id = await _make_open_game(session, 4001, MatchType.SINGLES)

    _, error, new_status = await _invite_and_accept(session, game_id, 4002)

    assert error == ""
    assert new_status == GameStatus.FULL

    from backend.app.database.repositories.game_repository import GameRepository
    game = await GameRepository(session).get_by_id(game_id)
    assert game.status == GameStatus.FULL


# ── PARTIALLY_FILLED → FULL (doubles) ────────────────────────────────────────

async def test_doubles_becomes_full_on_third_accept(session):
    """Doubles needs 4 players: creator + 3 accepts → FULL on the third accept."""
    await _make_player(session, 5001, "Organizer")
    await _make_player(session, 5002, "PlayerA")
    await _make_player(session, 5003, "PlayerB")
    await _make_player(session, 5004, "PlayerC")
    game_id = await _make_open_game(session, 5001, MatchType.DOUBLES)

    _, _, s1 = await _invite_and_accept(session, game_id, 5002)
    assert s1 is None  # 2/4 — PARTIALLY_FILLED

    _, _, s2 = await _invite_and_accept(session, game_id, 5003)
    assert s2 is None  # 3/4 — still PARTIALLY_FILLED

    _, _, s3 = await _invite_and_accept(session, game_id, 5004)
    assert s3 == GameStatus.FULL  # 4/4 — FULL

    from backend.app.database.repositories.game_repository import GameRepository
    game = await GameRepository(session).get_by_id(game_id)
    assert game.status == GameStatus.FULL


# ── Transition happens exactly once ──────────────────────────────────────────

async def test_full_transition_happens_only_once(session):
    """A fifth player accepting for a doubles match does not re-trigger FULL."""
    await _make_player(session, 6001, "Organizer")
    for tid in [6002, 6003, 6004, 6005]:
        await _make_player(session, tid, f"Player{tid}")
    game_id = await _make_open_game(session, 6001, MatchType.DOUBLES)

    # Fill the game
    for tid in [6002, 6003, 6004]:
        await _invite_and_accept(session, game_id, tid)

    # Fifth player (supernumerary) accepts
    _, _, extra_status = await _invite_and_accept(session, game_id, 6005)
    assert extra_status is None  # No second FULL signal


# ── Duplicate ACCEPT ignored ──────────────────────────────────────────────────

async def test_duplicate_accept_returns_error_and_no_transition(session):
    """Pressing Accept twice returns inv_already_responded; no duplicate GamePlayer or transition."""
    await _make_player(session, 7001, "Organizer")
    await _make_player(session, 7002, "PlayerA")
    game_id = await _make_open_game(session, 7001, MatchType.DOUBLES)

    svc = InvitationService(session)
    from backend.app.services.player_service import PlayerService as PS
    player = await PS(session).get_by_telegram_id(7002)
    inv = await svc.create_invitation(game_id, player.id)

    # First accept — valid
    await svc.accept(inv.id, 7002)

    # Second accept — duplicate
    result, error, new_status = await svc.accept(inv.id, 7002)
    assert error == "inv_already_responded"
    assert result is not None  # invitation returned, not None
    assert new_status is None

    # Only one GamePlayer record for this player
    gp_repo = GamePlayerRepository(session)
    participation = await gp_repo.get_participation(game_id, player.id)
    assert participation is not None  # exactly one, not duplicated


# ── Lifecycle based on GamePlayer, not Invitation ────────────────────────────

async def test_lifecycle_uses_gameplayer_not_invitation(session):
    """count_committed_players reflects GamePlayer rows, not Invitation records."""
    await _make_player(session, 8001, "Organizer")
    await _make_player(session, 8002, "PlayerA")
    game_id = await _make_open_game(session, 8001, MatchType.DOUBLES)

    from backend.app.services.player_service import PlayerService as PS
    player = await PS(session).get_by_telegram_id(8002)

    # Create invitation but do NOT accept — no GamePlayer row added
    svc = InvitationService(session)
    await svc.create_invitation(game_id, player.id)

    # Count should only reflect organizer (CONFIRMED), not the pending invitation
    gp_repo = GamePlayerRepository(session)
    count = await gp_repo.count_committed_players(game_id)
    assert count == 1  # only the organizer


async def test_count_committed_includes_accepted_and_confirmed(session):
    """count_committed_players counts both ACCEPTED and CONFIRMED statuses."""
    await _make_player(session, 9001, "Organizer")
    await _make_player(session, 9002, "PlayerA")
    game_id = await _make_open_game(session, 9001, MatchType.DOUBLES)

    gp_repo = GamePlayerRepository(session)
    assert await gp_repo.count_committed_players(game_id) == 1  # organizer only

    # Accept one invitation
    await _invite_and_accept(session, game_id, 9002)
    assert await gp_repo.count_committed_players(game_id) == 2  # organizer + accepted


# ── required_players respected ────────────────────────────────────────────────

async def test_required_players_gates_full_transition(session):
    """Game does not go FULL until committed count == required_players."""
    await _make_player(session, 10001, "Organizer")
    await _make_player(session, 10002, "PlayerA")
    await _make_player(session, 10003, "PlayerB")
    game_id = await _make_open_game(session, 10001, MatchType.DOUBLES)

    # First accept: 2/4 — not full
    _, _, s1 = await _invite_and_accept(session, game_id, 10002)
    assert s1 is None

    from backend.app.database.repositories.game_repository import GameRepository
    game = await GameRepository(session).get_by_id(game_id)
    assert game.status == GameStatus.PARTIALLY_FILLED  # not FULL yet

    # Second accept: 3/4 — still not full
    _, _, s2 = await _invite_and_accept(session, game_id, 10003)
    assert s2 is None
    game = await GameRepository(session).get_by_id(game_id)
    assert game.status == GameStatus.PARTIALLY_FILLED
