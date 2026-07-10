"""Tests for TournamentService — Tournament Platform v1, Phase 1
(Sprint 12). Focused on the CTO's explicit mandatory requirements for
Generate Matches (shuffle, even-count-only, status-gated, idempotent,
auto-transitions to IN_PROGRESS), the centralized permission check, and
the lifecycle transitions.
"""
from datetime import date, time, timedelta
from unittest.mock import patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.exceptions import InvalidTournamentTransitionError
from backend.app.database.models.operator_permission import OperatorRole
from backend.app.database.models.tournament import TournamentStatus
from backend.app.database.repositories.game_repository import GamePlayerRepository, GameRepository
from backend.app.schemas.player import PlayerCreate, PlayerUpdate
from backend.app.schemas.tournament import TournamentCreate, TournamentUpdate
from backend.app.services import admin_session_service as svc_module
from backend.app.services.admin_session_service import AdminSessionService
from backend.app.services.permission_service import PermissionService
from backend.app.services.player_service import PlayerService
from backend.app.services.tournament_lifecycle_service import TournamentLifecycleService
from backend.app.services.tournament_service import TournamentService

TEST_PIN = "4242"


@pytest.fixture(autouse=True)
def _clear_process_global_state():
    svc_module._sessions.clear()
    svc_module._attempts.clear()
    yield
    svc_module._sessions.clear()
    svc_module._attempts.clear()


def _with_pin():
    return patch("backend.app.services.admin_session_service.get_settings")


async def _make_player(session: AsyncSession, telegram_id: int, name: str = "Player") -> int:
    svc = PlayerService(session)
    player, _ = await svc.get_or_create(PlayerCreate(telegram_id=telegram_id, first_name=name))
    await svc.update_profile(
        telegram_id,
        PlayerUpdate(language="en", skill_level=3.5, home_area="Downtown", preferred_courts=["High Park"]),
    )
    await session.commit()
    return player.id


async def _make_tournament(
    session: AsyncSession, organizer_telegram_id: int, max_players: int = 4, deadline_days: int = 7
) -> int:
    service = TournamentService(session)
    tournament = await service.create_tournament(
        organizer_telegram_id,
        TournamentCreate(
            name="Summer Cup",
            area="Downtown",
            court="High Park",
            start_date=date.today() + timedelta(days=14),
            start_time=time(10, 0),
            registration_deadline=date.today() + timedelta(days=deadline_days),
            max_players=max_players,
        ),
    )
    await session.commit()
    return tournament.id


async def _register_n_players(session: AsyncSession, tournament_id: int, n: int, start_id: int) -> list[int]:
    service = TournamentService(session)
    telegram_ids = []
    for i in range(n):
        tid = start_id + i
        await _make_player(session, tid, f"Player{tid}")
        await service.register_player(tournament_id, tid)
        telegram_ids.append(tid)
    await session.commit()
    return telegram_ids


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_lifecycle_forward_transitions_succeed(session: AsyncSession) -> None:
    organizer = await _make_player(session, 1001)
    tournament_id = await _make_tournament(session, 1001)
    lifecycle = TournamentLifecycleService(session)

    result = await lifecycle.transition(tournament_id, TournamentStatus.REGISTRATION_OPEN)
    assert result.status == TournamentStatus.REGISTRATION_OPEN


@pytest.mark.asyncio
async def test_lifecycle_rejects_backward_transition(session: AsyncSession) -> None:
    """Unlike GameStatus, Tournament transitions are strictly forward —
    no reopening a closed registration."""
    await _make_player(session, 1002)
    tournament_id = await _make_tournament(session, 1002)
    lifecycle = TournamentLifecycleService(session)
    await lifecycle.transition(tournament_id, TournamentStatus.REGISTRATION_OPEN)
    await lifecycle.transition(tournament_id, TournamentStatus.REGISTRATION_CLOSED)

    with pytest.raises(InvalidTournamentTransitionError):
        await lifecycle.transition(tournament_id, TournamentStatus.REGISTRATION_OPEN)


# ---------------------------------------------------------------------------
# Centralized permission checks — deliberately two separate methods
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_can_create_tournament_false_for_regular_player(session: AsyncSession) -> None:
    await _make_player(session, 2001)
    service = TournamentService(session)
    assert await service.can_create_tournament(2001) is False


@pytest.mark.asyncio
async def test_can_create_tournament_true_for_verified_coach(session: AsyncSession) -> None:
    player_id = await _make_player(session, 2002)
    from backend.app.services.players_service import PlayersService

    await PlayersService(session).set_verified_coach(player_id, True)
    await session.commit()

    service = TournamentService(session)
    assert await service.can_create_tournament(2002) is True


@pytest.mark.asyncio
async def test_can_create_tournament_true_for_admin_with_active_session(session: AsyncSession) -> None:
    await PermissionService(session).seed_owners([2003])
    await session.commit()
    with _with_pin() as mock:
        mock.return_value.admin_pin = TEST_PIN
        admin_sessions = AdminSessionService(session)
        await admin_sessions.attempt_login(2003, OperatorRole.OWNER, TEST_PIN)
        await session.commit()

        service = TournamentService(session)
        assert await service.can_create_tournament(2003) is True


@pytest.mark.asyncio
async def test_can_create_tournament_false_for_operator_without_active_session(session: AsyncSession) -> None:
    """Holding an OperatorPermission role alone isn't enough — the PIN
    session gate is not optional, same as every other Admin Center
    module."""
    await PermissionService(session).seed_owners([2004])
    await session.commit()

    service = TournamentService(session)
    assert await service.can_create_tournament(2004) is False


# ---------------------------------------------------------------------------
# Ownership-aware permission — Coach manages only tournaments they created
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_can_manage_tournament_true_for_owning_coach(session: AsyncSession) -> None:
    from backend.app.services.players_service import PlayersService

    organizer_id = await _make_player(session, 2101, "Coach")
    await PlayersService(session).set_verified_coach(organizer_id, True)
    await session.commit()

    service = TournamentService(session)
    assert await service.can_manage_tournament(2101, organizer_id) is True


@pytest.mark.asyncio
async def test_can_manage_tournament_false_for_non_owning_coach(session: AsyncSession) -> None:
    """A Verified Coach may create tournaments, but may only manage the
    ones they themselves organized — not another coach's."""
    from backend.app.services.players_service import PlayersService

    owner_id = await _make_player(session, 2201, "OwnerCoach")
    other_coach_id = await _make_player(session, 2202, "OtherCoach")
    await PlayersService(session).set_verified_coach(owner_id, True)
    await PlayersService(session).set_verified_coach(other_coach_id, True)
    await session.commit()

    service = TournamentService(session)
    assert await service.can_manage_tournament(2202, owner_id) is False


@pytest.mark.asyncio
async def test_can_manage_tournament_true_for_admin_regardless_of_ownership(session: AsyncSession) -> None:
    owner_id = await _make_player(session, 2301, "Coach")
    await PermissionService(session).seed_owners([2302])
    await session.commit()
    with _with_pin() as mock:
        mock.return_value.admin_pin = TEST_PIN
        admin_sessions = AdminSessionService(session)
        await admin_sessions.attempt_login(2302, OperatorRole.OWNER, TEST_PIN)
        await session.commit()

        service = TournamentService(session)
        assert await service.can_manage_tournament(2302, owner_id) is True


# ---------------------------------------------------------------------------
# Generate Matches — the CTO's explicit mandatory rules
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_generate_matches_requires_registration_closed_status(session: AsyncSession) -> None:
    await _make_player(session, 3001)
    tournament_id = await _make_tournament(session, 3001, max_players=4)
    service = TournamentService(session)
    # Still DRAFT — never opened or closed.
    success, error_key = await service.generate_matches(tournament_id)
    assert success is False
    assert error_key == "tournament_generate_wrong_status"


@pytest.mark.asyncio
async def test_generate_matches_rejects_odd_player_count(session: AsyncSession) -> None:
    await _make_player(session, 3101)
    tournament_id = await _make_tournament(session, 3101, max_players=10)
    lifecycle = TournamentLifecycleService(session)
    await lifecycle.transition(tournament_id, TournamentStatus.REGISTRATION_OPEN)
    await _register_n_players(session, tournament_id, 3, start_id=3200)  # odd
    await lifecycle.transition(tournament_id, TournamentStatus.REGISTRATION_CLOSED)

    service = TournamentService(session)
    success, error_key = await service.generate_matches(tournament_id)
    assert success is False
    assert error_key == "tournament_generate_invalid_player_count"

    games = await GameRepository(session).get_games_by_tournament(tournament_id)
    assert games == []


@pytest.mark.asyncio
async def test_generate_matches_rejects_even_but_non_power_of_two_player_count(session: AsyncSession) -> None:
    """Single Elimination only supports player counts that are a power
    of two — 6 is even but not a valid bracket size (Sprint 14, Step 2:
    byes are out of scope)."""
    await _make_player(session, 3151)
    tournament_id = await _make_tournament(session, 3151, max_players=10)
    lifecycle = TournamentLifecycleService(session)
    await lifecycle.transition(tournament_id, TournamentStatus.REGISTRATION_OPEN)
    await _register_n_players(session, tournament_id, 6, start_id=3250)
    await lifecycle.transition(tournament_id, TournamentStatus.REGISTRATION_CLOSED)

    service = TournamentService(session)
    success, error_key = await service.generate_matches(tournament_id)
    assert success is False
    assert error_key == "tournament_generate_invalid_player_count"

    games = await GameRepository(session).get_games_by_tournament(tournament_id)
    assert games == []


@pytest.mark.asyncio
async def test_generate_matches_pairs_every_registered_player_exactly_once(session: AsyncSession) -> None:
    await _make_player(session, 3301)
    tournament_id = await _make_tournament(session, 3301, max_players=10)
    lifecycle = TournamentLifecycleService(session)
    await lifecycle.transition(tournament_id, TournamentStatus.REGISTRATION_OPEN)
    telegram_ids = await _register_n_players(session, tournament_id, 8, start_id=3400)
    await lifecycle.transition(tournament_id, TournamentStatus.REGISTRATION_CLOSED)

    service = TournamentService(session)
    success, error_key = await service.generate_matches(tournament_id)
    assert success is True
    assert error_key == ""

    games = await GameRepository(session).get_games_by_tournament(tournament_id)
    assert len(games) == 4  # 8 players -> 4 matches

    from backend.app.database.repositories.game_repository import GamePlayerRepository
    from backend.app.database.repositories.player_repository import PlayerRepository

    organizer = await PlayerRepository(session).get_by_telegram_id(3301)

    gp_repo = GamePlayerRepository(session)
    all_participant_ids: list[int] = []
    for game in games:
        # Every generated Game must belong to the Tournament Organizer —
        # never to either pair player, and the organizer here (3301) is
        # not one of the 8 registered players (3400-3407), so this also
        # confirms the organizer isn't wrongly added as a participant.
        assert game.creator_id == organizer.id
        assert game.round == 1
        participant_ids = await gp_repo.get_participant_player_ids(game.id)
        assert len(participant_ids) == 2  # each generated match pairs exactly two players
        assert organizer.id not in participant_ids
        all_participant_ids.extend(participant_ids)

    player_repo_ids = set(all_participant_ids)
    assert len(all_participant_ids) == len(player_repo_ids) == 8  # every player appears exactly once


@pytest.mark.asyncio
async def test_generate_matches_transitions_tournament_to_in_progress(session: AsyncSession) -> None:
    await _make_player(session, 3501)
    tournament_id = await _make_tournament(session, 3501, max_players=4)
    lifecycle = TournamentLifecycleService(session)
    await lifecycle.transition(tournament_id, TournamentStatus.REGISTRATION_OPEN)
    await _register_n_players(session, tournament_id, 2, start_id=3600)
    await lifecycle.transition(tournament_id, TournamentStatus.REGISTRATION_CLOSED)

    service = TournamentService(session)
    await service.generate_matches(tournament_id)

    tournament = await service.get_tournament(tournament_id)
    assert tournament.status == TournamentStatus.IN_PROGRESS


@pytest.mark.asyncio
async def test_generate_matches_is_idempotent(session: AsyncSession) -> None:
    """Calling it twice must not create duplicate games — the second
    call must fail with tournament_generate_already_done, and the
    tournament's IN_PROGRESS transition (already applied) must not be
    attempted again."""
    await _make_player(session, 3701)
    tournament_id = await _make_tournament(session, 3701, max_players=4)
    lifecycle = TournamentLifecycleService(session)
    await lifecycle.transition(tournament_id, TournamentStatus.REGISTRATION_OPEN)
    await _register_n_players(session, tournament_id, 2, start_id=3800)
    await lifecycle.transition(tournament_id, TournamentStatus.REGISTRATION_CLOSED)

    service = TournamentService(session)
    first_success, _ = await service.generate_matches(tournament_id)
    assert first_success is True

    games_after_first = await GameRepository(session).get_games_by_tournament(tournament_id)
    assert len(games_after_first) == 1

    # Second call: status is now IN_PROGRESS, so the status guard alone
    # would already reject it — the explicit idempotency guard is the
    # one that must fire if this method is ever reached in that status.
    second_success, second_error = await service.generate_matches(tournament_id)
    assert second_success is False

    games_after_second = await GameRepository(session).get_games_by_tournament(tournament_id)
    assert len(games_after_second) == 1  # unchanged — no duplicate games created


@pytest.mark.asyncio
async def test_generate_matches_idempotent_even_if_status_were_still_closed(session: AsyncSession) -> None:
    """Directly exercises the idempotency guard itself: force the status
    back to REGISTRATION_CLOSED (bypassing the lifecycle service, as a
    test-only simulation of a retried call) and confirm the existing-
    games check — not just the status check — is what stops it."""
    await _make_player(session, 3901)
    tournament_id = await _make_tournament(session, 3901, max_players=4)
    lifecycle = TournamentLifecycleService(session)
    await lifecycle.transition(tournament_id, TournamentStatus.REGISTRATION_OPEN)
    await _register_n_players(session, tournament_id, 2, start_id=4000)
    await lifecycle.transition(tournament_id, TournamentStatus.REGISTRATION_CLOSED)

    service = TournamentService(session)
    await service.generate_matches(tournament_id)

    # Simulate "still closed" by writing the status directly (test-only).
    from backend.app.database.repositories.tournament_repository import TournamentRepository

    await TournamentRepository(session).update_status(tournament_id, TournamentStatus.REGISTRATION_CLOSED)
    await session.commit()

    success, error_key = await service.generate_matches(tournament_id)
    assert success is False
    assert error_key == "tournament_generate_already_done"

    games = await GameRepository(session).get_games_by_tournament(tournament_id)
    assert len(games) == 1


# ---------------------------------------------------------------------------
# Registration auto-close
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_registration_auto_closes_when_max_players_reached(session: AsyncSession) -> None:
    await _make_player(session, 4101)
    tournament_id = await _make_tournament(session, 4101, max_players=2)
    lifecycle = TournamentLifecycleService(session)
    await lifecycle.transition(tournament_id, TournamentStatus.REGISTRATION_OPEN)

    service = TournamentService(session)
    await _make_player(session, 4200, "P1")
    registered_1, closed_1 = await service.register_player(tournament_id, 4200)
    assert registered_1 is True
    assert closed_1 is False

    await _make_player(session, 4201, "P2")
    registered_2, closed_2 = await service.register_player(tournament_id, 4201)
    assert registered_2 is True
    assert closed_2 is True  # second registration reaches max_players=2

    tournament = await service.get_tournament(tournament_id)
    assert tournament.status == TournamentStatus.REGISTRATION_CLOSED


@pytest.mark.asyncio
async def test_registration_auto_closes_when_deadline_passed(session: AsyncSession) -> None:
    await _make_player(session, 4301)
    tournament_id = await _make_tournament(session, 4301, max_players=10, deadline_days=-1)
    lifecycle = TournamentLifecycleService(session)
    await lifecycle.transition(tournament_id, TournamentStatus.REGISTRATION_OPEN)

    service = TournamentService(session)
    just_closed = await service.check_and_auto_close(tournament_id)
    assert just_closed is True

    tournament = await service.get_tournament(tournament_id)
    assert tournament.status == TournamentStatus.REGISTRATION_CLOSED


@pytest.mark.asyncio
async def test_register_player_rejected_once_registration_closed(session: AsyncSession) -> None:
    await _make_player(session, 4401)
    tournament_id = await _make_tournament(session, 4401, max_players=4)
    lifecycle = TournamentLifecycleService(session)
    await lifecycle.transition(tournament_id, TournamentStatus.REGISTRATION_OPEN)
    await lifecycle.transition(tournament_id, TournamentStatus.REGISTRATION_CLOSED)

    await _make_player(session, 4500, "Late")
    service = TournamentService(session)
    registered, _ = await service.register_player(tournament_id, 4500)
    assert registered is False


# ---------------------------------------------------------------------------
# Browse ordering — status group first, then date within each group
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_tournaments_orders_by_status_group_then_date(session: AsyncSession) -> None:
    """REGISTRATION_OPEN/CLOSED/IN_PROGRESS/COMPLETED/CANCELLED (DRAFT
    first, ahead of that list) — never filtered out, only ordered, so a
    future archive view for COMPLETED never needs to touch this query."""
    organizer_id = await _make_player(session, 5001)
    lifecycle = TournamentLifecycleService(session)
    service = TournamentService(session)

    async def _make(name: str, status: TournamentStatus, days_ahead: int) -> int:
        tid = await _make_tournament(session, 5001, max_players=4, deadline_days=1)
        # Rename via direct edit so each tournament is distinguishable.
        await service.edit_tournament(tid, TournamentUpdate(name=name))
        if status != TournamentStatus.DRAFT:
            await lifecycle.transition(tid, TournamentStatus.REGISTRATION_OPEN)
        if status in (TournamentStatus.REGISTRATION_CLOSED, TournamentStatus.IN_PROGRESS, TournamentStatus.COMPLETED, TournamentStatus.CANCELLED):
            await lifecycle.transition(tid, TournamentStatus.REGISTRATION_CLOSED)
        if status in (TournamentStatus.IN_PROGRESS, TournamentStatus.COMPLETED):
            await lifecycle.transition(tid, TournamentStatus.IN_PROGRESS)
        if status == TournamentStatus.COMPLETED:
            await lifecycle.transition(tid, TournamentStatus.COMPLETED)
        if status == TournamentStatus.CANCELLED:
            await lifecycle.transition(tid, TournamentStatus.CANCELLED)
        return tid

    # Inserted in a deliberately scrambled status order.
    await _make("Cancelled", TournamentStatus.CANCELLED, 1)
    await _make("Completed", TournamentStatus.COMPLETED, 1)
    await _make("Draft", TournamentStatus.DRAFT, 1)
    await _make("InProgress", TournamentStatus.IN_PROGRESS, 1)
    await _make("RegClosed", TournamentStatus.REGISTRATION_CLOSED, 1)
    await _make("RegOpen", TournamentStatus.REGISTRATION_OPEN, 1)
    await session.commit()

    tournaments, total = await service.list_tournaments(page=1)
    assert total == 6
    names_in_order = [t.name for t in tournaments]
    assert names_in_order == ["Draft", "RegOpen", "RegClosed", "InProgress", "Completed", "Cancelled"]


@pytest.mark.asyncio
async def test_list_tournaments_orders_by_date_within_same_status(session: AsyncSession) -> None:
    organizer_id = await _make_player(session, 5101)
    service = TournamentService(session)

    async def _make_with_date(name: str, start_date) -> int:
        tournament = await service.create_tournament(
            5101,
            TournamentCreate(
                name=name,
                area="Downtown",
                court="High Park",
                start_date=start_date,
                start_time=time(10, 0),
                registration_deadline=date.today(),
                max_players=4,
            ),
        )
        return tournament.id

    await _make_with_date("Late", date.today() + timedelta(days=30))
    await _make_with_date("Soon", date.today() + timedelta(days=2))
    await _make_with_date("Mid", date.today() + timedelta(days=10))
    await session.commit()

    tournaments, _ = await service.list_tournaments(page=1)
    assert [t.name for t in tournaments] == ["Soon", "Mid", "Late"]


# ---------------------------------------------------------------------------
# Match Lifecycle & Result Flow (Sprint 14, Step 2)
# ---------------------------------------------------------------------------

async def _setup_generated_tournament(
    session: AsyncSession, organizer_telegram_id: int, n_players: int, start_id: int
) -> int:
    """Register n_players (must be a power of two), close registration,
    and generate matches. Returns tournament_id; round 1 Games can then
    be fetched via GameRepository.get_games_by_tournament_round()."""
    from backend.app.services.players_service import PlayersService

    organizer_id = await _make_player(session, organizer_telegram_id, "Organizer")
    await PlayersService(session).set_verified_coach(organizer_id, True)
    await session.commit()

    # max_players is set above n_players so registering exactly n_players
    # doesn't auto-close registration before the explicit transition below.
    tournament_id = await _make_tournament(session, organizer_telegram_id, max_players=n_players + 10)
    lifecycle = TournamentLifecycleService(session)
    await lifecycle.transition(tournament_id, TournamentStatus.REGISTRATION_OPEN)
    await _register_n_players(session, tournament_id, n_players, start_id=start_id)
    await lifecycle.transition(tournament_id, TournamentStatus.REGISTRATION_CLOSED)

    service = TournamentService(session)
    success, error_key = await service.generate_matches(tournament_id)
    assert success is True, error_key
    return tournament_id


@pytest.mark.asyncio
async def test_start_match_transitions_open_to_in_progress(session: AsyncSession) -> None:
    organizer_telegram_id = 6001
    tournament_id = await _setup_generated_tournament(session, organizer_telegram_id, 4, start_id=6100)

    game_repo = GameRepository(session)
    round_1 = await game_repo.get_games_by_tournament_round(tournament_id, 1)
    assert len(round_1) == 2

    service = TournamentService(session)
    updated, error_key = await service.start_match(round_1[0].id, organizer_telegram_id)
    assert error_key == ""
    assert updated is not None

    from backend.app.database.models.game import GameStatus

    refreshed = await game_repo.get_by_id(round_1[0].id)
    assert refreshed.status == GameStatus.IN_PROGRESS


@pytest.mark.asyncio
async def test_start_match_rejected_for_non_organizer(session: AsyncSession) -> None:
    """PD-001 — only the Tournament Organizer may drive match state."""
    organizer_telegram_id = 6201
    tournament_id = await _setup_generated_tournament(session, organizer_telegram_id, 4, start_id=6300)

    game_repo = GameRepository(session)
    round_1 = await game_repo.get_games_by_tournament_round(tournament_id, 1)

    intruder_telegram_id = 6300  # one of the registered players, not the organizer
    service = TournamentService(session)
    updated, error_key = await service.start_match(round_1[0].id, intruder_telegram_id)
    assert updated is None
    assert error_key == "tournament_match_forbidden"

    from backend.app.database.models.game import GameStatus

    refreshed = await game_repo.get_by_id(round_1[0].id)
    assert refreshed.status == GameStatus.OPEN  # unchanged


@pytest.mark.asyncio
async def test_complete_match_records_winner_and_transitions_completed(session: AsyncSession) -> None:
    organizer_telegram_id = 6401
    tournament_id = await _setup_generated_tournament(session, organizer_telegram_id, 4, start_id=6500)

    game_repo = GameRepository(session)
    gp_repo = GamePlayerRepository(session)
    round_1 = await game_repo.get_games_by_tournament_round(tournament_id, 1)
    game = round_1[0]
    participants = await gp_repo.get_participant_player_ids(game.id)
    winner_id = participants[0]

    service = TournamentService(session)
    await service.start_match(game.id, organizer_telegram_id)
    updated, error_key = await service.complete_match(game.id, winner_id, organizer_telegram_id)
    assert error_key == ""
    assert updated is not None
    assert updated.winner_player_id == winner_id

    from backend.app.database.models.game import GameStatus

    refreshed = await game_repo.get_by_id(game.id)
    assert refreshed.status == GameStatus.COMPLETED
    assert refreshed.winner_player_id == winner_id


@pytest.mark.asyncio
async def test_complete_match_rejects_winner_not_in_match(session: AsyncSession) -> None:
    organizer_telegram_id = 6601
    tournament_id = await _setup_generated_tournament(session, organizer_telegram_id, 4, start_id=6700)

    game_repo = GameRepository(session)
    round_1 = await game_repo.get_games_by_tournament_round(tournament_id, 1)
    game = round_1[0]

    service = TournamentService(session)
    await service.start_match(game.id, organizer_telegram_id)

    from backend.app.database.repositories.player_repository import PlayerRepository

    organizer = await PlayerRepository(session).get_by_telegram_id(organizer_telegram_id)
    updated, error_key = await service.complete_match(game.id, organizer.id, organizer_telegram_id)
    assert updated is None
    assert error_key == "tournament_match_winner_not_participant"

    from backend.app.database.models.game import GameStatus

    refreshed = await game_repo.get_by_id(game.id)
    assert refreshed.status == GameStatus.IN_PROGRESS  # unchanged
    assert refreshed.winner_player_id is None


@pytest.mark.asyncio
async def test_complete_match_rejected_for_non_organizer(session: AsyncSession) -> None:
    """PD-001 — result entry is Organizer-controlled only."""
    organizer_telegram_id = 6801
    tournament_id = await _setup_generated_tournament(session, organizer_telegram_id, 4, start_id=6900)

    game_repo = GameRepository(session)
    gp_repo = GamePlayerRepository(session)
    round_1 = await game_repo.get_games_by_tournament_round(tournament_id, 1)
    game = round_1[0]
    participants = await gp_repo.get_participant_player_ids(game.id)

    service = TournamentService(session)
    await service.start_match(game.id, organizer_telegram_id)

    intruder_telegram_id = 6900  # a registered player, not the organizer
    updated, error_key = await service.complete_match(game.id, participants[0], intruder_telegram_id)
    assert updated is None
    assert error_key == "tournament_match_forbidden"


@pytest.mark.asyncio
async def test_complete_match_generates_next_round_once_round_finishes(session: AsyncSession) -> None:
    organizer_telegram_id = 7001
    tournament_id = await _setup_generated_tournament(session, organizer_telegram_id, 4, start_id=7100)

    game_repo = GameRepository(session)
    gp_repo = GamePlayerRepository(session)
    round_1 = await game_repo.get_games_by_tournament_round(tournament_id, 1)
    assert len(round_1) == 2

    service = TournamentService(session)

    # Complete only the first game — round 1 isn't fully finished yet.
    game_a = round_1[0]
    participants_a = await gp_repo.get_participant_player_ids(game_a.id)
    await service.start_match(game_a.id, organizer_telegram_id)
    await service.complete_match(game_a.id, participants_a[0], organizer_telegram_id)

    round_2_partial = await game_repo.get_games_by_tournament_round(tournament_id, 2)
    assert round_2_partial == []  # not created yet — round 1 still has an unfinished game

    # Complete the second game — round 1 is now fully finished.
    game_b = round_1[1]
    participants_b = await gp_repo.get_participant_player_ids(game_b.id)
    await service.start_match(game_b.id, organizer_telegram_id)
    await service.complete_match(game_b.id, participants_b[0], organizer_telegram_id)

    round_2 = await game_repo.get_games_by_tournament_round(tournament_id, 2)
    assert len(round_2) == 1  # 2 round-1 winners -> 1 final match

    final_participants = set(await gp_repo.get_participant_player_ids(round_2[0].id))
    assert final_participants == {participants_a[0], participants_b[0]}

    tournament = await service.get_tournament(tournament_id)
    assert tournament.status == TournamentStatus.IN_PROGRESS  # final not played yet


@pytest.mark.asyncio
async def test_complete_final_match_marks_tournament_completed(session: AsyncSession) -> None:
    organizer_telegram_id = 7201
    tournament_id = await _setup_generated_tournament(session, organizer_telegram_id, 4, start_id=7300)

    game_repo = GameRepository(session)
    gp_repo = GamePlayerRepository(session)
    round_1 = await game_repo.get_games_by_tournament_round(tournament_id, 1)
    service = TournamentService(session)

    winners = []
    for game in round_1:
        participants = await gp_repo.get_participant_player_ids(game.id)
        await service.start_match(game.id, organizer_telegram_id)
        await service.complete_match(game.id, participants[0], organizer_telegram_id)
        winners.append(participants[0])

    round_2 = await game_repo.get_games_by_tournament_round(tournament_id, 2)
    assert len(round_2) == 1
    final_game = round_2[0]

    await service.start_match(final_game.id, organizer_telegram_id)
    updated, error_key = await service.complete_match(final_game.id, winners[0], organizer_telegram_id)
    assert error_key == ""

    tournament = await service.get_tournament(tournament_id)
    assert tournament.status == TournamentStatus.COMPLETED

    round_3 = await game_repo.get_games_by_tournament_round(tournament_id, 3)
    assert round_3 == []  # champion determined — no further round generated


@pytest.mark.asyncio
async def test_get_standings_reflects_eliminated_and_champion(session: AsyncSession) -> None:
    organizer_telegram_id = 7401
    tournament_id = await _setup_generated_tournament(session, organizer_telegram_id, 4, start_id=7500)

    game_repo = GameRepository(session)
    gp_repo = GamePlayerRepository(session)
    round_1 = await game_repo.get_games_by_tournament_round(tournament_id, 1)
    service = TournamentService(session)

    winners, losers = [], []
    for game in round_1:
        participants = await gp_repo.get_participant_player_ids(game.id)
        winner_id, loser_id = participants[0], participants[1]
        await service.start_match(game.id, organizer_telegram_id)
        await service.complete_match(game.id, winner_id, organizer_telegram_id)
        winners.append(winner_id)
        losers.append(loser_id)

    round_2 = await game_repo.get_games_by_tournament_round(tournament_id, 2)
    final_game = round_2[0]
    final_participants = await gp_repo.get_participant_player_ids(final_game.id)
    champion_id, runner_up_id = final_participants[0], final_participants[1]
    await service.start_match(final_game.id, organizer_telegram_id)
    await service.complete_match(final_game.id, champion_id, organizer_telegram_id)

    standings = await service.get_standings(tournament_id)
    by_player = {s.player_id: s for s in standings}

    for loser_id in losers:
        assert by_player[loser_id].status == "eliminated"
        assert by_player[loser_id].eliminated_round == 1

    assert by_player[runner_up_id].status == "eliminated"
    assert by_player[runner_up_id].eliminated_round == 2
    assert by_player[champion_id].status == "champion"
    assert by_player[champion_id].eliminated_round is None
