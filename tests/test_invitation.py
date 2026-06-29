"""Tests for Sprint 3.3 – Match Invitations."""
import pytest
from datetime import date, time

from backend.app.database.models.game import GamePlayerStatus, MatchType
from backend.app.database.models.invitation import InvitationStatus
from backend.app.database.repositories.game_repository import GamePlayerRepository
from backend.app.database.repositories.invitation_repository import InvitationRepository
from backend.app.schemas.game import GameCreate
from backend.app.schemas.player import PlayerCreate, PlayerUpdate
from backend.app.services.game_service import GameService
from backend.app.services.invitation_service import InvitationService
from backend.app.services.player_service import PlayerService


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _make_player(session, telegram_id: int, area: str = "Downtown", level: float = 3.0, first_name: str = "Player") -> int:
    svc = PlayerService(session)
    player, _ = await svc.get_or_create(PlayerCreate(telegram_id=telegram_id, first_name=first_name))
    await svc.update_profile(
        telegram_id,
        PlayerUpdate(language="en", skill_level=level, home_area=area, preferred_courts=["High Park"]),
    )
    return player.id


async def _make_game(session, organizer_telegram_id: int, area: str = "Downtown", level: float = 3.0) -> int:
    game = await GameService(session).create_game(
        creator_telegram_id=organizer_telegram_id,
        data=GameCreate(
            court="High Park",
            area=area,
            date=date(2026, 8, 1),
            time=time(18, 0),
            match_type=MatchType.SINGLES,
            required_level=level,
        ),
    )
    assert game is not None
    return game.id


# ── InvitationRepository ──────────────────────────────────────────────────────

async def test_repo_create_invitation(session):
    org_id = await _make_player(session, 1001, first_name="Organizer")
    inv_id = await _make_player(session, 1002, first_name="Invitee")
    game_id = await _make_game(session, 1001)

    repo = InvitationRepository(session)
    inv = await repo.create(game_id, inv_id)

    assert inv.id is not None
    assert inv.game_id == game_id
    assert inv.player_id == inv_id
    assert inv.status == InvitationStatus.PENDING
    assert inv.responded_at is None


async def test_repo_get_by_game_and_player(session):
    await _make_player(session, 1001)
    inv_id = await _make_player(session, 1002)
    game_id = await _make_game(session, 1001)

    repo = InvitationRepository(session)
    await repo.create(game_id, inv_id)

    result = await repo.get_by_game_and_player(game_id, inv_id)
    assert result is not None
    assert result.player_id == inv_id


async def test_repo_get_by_game_and_player_not_found(session):
    repo = InvitationRepository(session)
    result = await repo.get_by_game_and_player(999, 999)
    assert result is None


async def test_repo_update_status(session):
    from datetime import datetime
    await _make_player(session, 1001)
    inv_player_id = await _make_player(session, 1002)
    game_id = await _make_game(session, 1001)

    repo = InvitationRepository(session)
    inv = await repo.create(game_id, inv_player_id)

    responded = datetime(2026, 8, 1, 12, 0)
    updated = await repo.update_status(inv.id, InvitationStatus.ACCEPTED, responded)

    assert updated is not None
    assert updated.status == InvitationStatus.ACCEPTED
    assert updated.responded_at == responded


# ── InvitationService.create_invitation ──────────────────────────────────────

async def test_service_create_invitation_success(session):
    await _make_player(session, 1001)
    inv_player_id = await _make_player(session, 1002)
    game_id = await _make_game(session, 1001)

    svc = InvitationService(session)
    inv = await svc.create_invitation(game_id, inv_player_id)

    assert inv is not None
    assert inv.status == InvitationStatus.PENDING


async def test_service_create_invitation_duplicate_returns_none(session):
    await _make_player(session, 1001)
    inv_player_id = await _make_player(session, 1002)
    game_id = await _make_game(session, 1001)

    svc = InvitationService(session)
    first = await svc.create_invitation(game_id, inv_player_id)
    second = await svc.create_invitation(game_id, inv_player_id)

    assert first is not None
    assert second is None


async def test_service_create_invitation_existing_participant_returns_none(session):
    await _make_player(session, 1001)
    inv_player_id = await _make_player(session, 1002)
    game_id = await _make_game(session, 1001)

    gp_repo = GamePlayerRepository(session)
    await gp_repo.add_player_to_game(game_id, inv_player_id, GamePlayerStatus.CONFIRMED)

    svc = InvitationService(session)
    result = await svc.create_invitation(game_id, inv_player_id)
    assert result is None


# ── InvitationService.accept ──────────────────────────────────────────────────

async def test_service_accept_success(session):
    await _make_player(session, 1001)
    inv_player_id = await _make_player(session, 1002)
    game_id = await _make_game(session, 1001)

    svc = InvitationService(session)
    inv = await svc.create_invitation(game_id, inv_player_id)

    updated, error, _ = await svc.accept(inv.id, 1002)

    assert error == ""
    assert updated is not None
    assert updated.status == InvitationStatus.ACCEPTED
    assert updated.responded_at is not None


async def test_service_accept_adds_to_game_players(session):
    await _make_player(session, 1001)
    inv_player_id = await _make_player(session, 1002)
    game_id = await _make_game(session, 1001)

    svc = InvitationService(session)
    inv = await svc.create_invitation(game_id, inv_player_id)
    await svc.accept(inv.id, 1002)

    gp_repo = GamePlayerRepository(session)
    participation = await gp_repo.get_participation(game_id, inv_player_id)
    assert participation is not None
    assert participation.status == GamePlayerStatus.ACCEPTED


async def test_service_accept_wrong_player_returns_error(session):
    await _make_player(session, 1001)
    inv_player_id = await _make_player(session, 1002)
    await _make_player(session, 1003)
    game_id = await _make_game(session, 1001)

    svc = InvitationService(session)
    inv = await svc.create_invitation(game_id, inv_player_id)

    result, error, _ = await svc.accept(inv.id, 1003)
    assert result is None
    assert error == "inv_not_yours"


async def test_service_accept_already_accepted_returns_error(session):
    await _make_player(session, 1001)
    inv_player_id = await _make_player(session, 1002)
    game_id = await _make_game(session, 1001)

    svc = InvitationService(session)
    inv = await svc.create_invitation(game_id, inv_player_id)
    await svc.accept(inv.id, 1002)

    result, error, _ = await svc.accept(inv.id, 1002)
    assert result is not None  # returns the invitation, not None
    assert error == "inv_already_responded"


async def test_service_accept_nonexistent_invitation_returns_error(session):
    svc = InvitationService(session)
    result, error, _ = await svc.accept(99999, 1001)
    assert result is None
    assert error == "inv_not_found"


# ── InvitationService.decline ─────────────────────────────────────────────────

async def test_service_decline_success(session):
    await _make_player(session, 1001)
    inv_player_id = await _make_player(session, 1002)
    game_id = await _make_game(session, 1001)

    svc = InvitationService(session)
    inv = await svc.create_invitation(game_id, inv_player_id)

    updated, error = await svc.decline(inv.id, 1002)

    assert error == ""
    assert updated is not None
    assert updated.status == InvitationStatus.DECLINED
    assert updated.responded_at is not None


async def test_service_decline_wrong_player_returns_error(session):
    await _make_player(session, 1001)
    inv_player_id = await _make_player(session, 1002)
    await _make_player(session, 1003)
    game_id = await _make_game(session, 1001)

    svc = InvitationService(session)
    inv = await svc.create_invitation(game_id, inv_player_id)

    result, error = await svc.decline(inv.id, 1003)
    assert result is None
    assert error == "inv_not_yours"


async def test_service_decline_already_declined_returns_error(session):
    await _make_player(session, 1001)
    inv_player_id = await _make_player(session, 1002)
    game_id = await _make_game(session, 1001)

    svc = InvitationService(session)
    inv = await svc.create_invitation(game_id, inv_player_id)
    await svc.decline(inv.id, 1002)

    result, error = await svc.decline(inv.id, 1002)
    assert result is None
    assert error == "inv_already_responded"


async def test_service_decline_does_not_add_to_game_players(session):
    await _make_player(session, 1001)
    inv_player_id = await _make_player(session, 1002)
    game_id = await _make_game(session, 1001)

    svc = InvitationService(session)
    inv = await svc.create_invitation(game_id, inv_player_id)
    await svc.decline(inv.id, 1002)

    gp_repo = GamePlayerRepository(session)
    participation = await gp_repo.get_participation(game_id, inv_player_id)
    assert participation is None
