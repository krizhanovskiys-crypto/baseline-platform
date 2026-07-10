"""API tests for the Tournament Write API (Sprint 15, Step 2):
POST /api/v1/games/{game_id}/start, POST /api/v1/games/{game_id}/complete.

Both endpoints are thin wrappers over TournamentService.start_match()/
complete_match() — no authorization or bracket logic lives in the
router itself, so these tests exercise the same rules already covered
at the service level (test_tournament_service.py), but through the
actual HTTP layer: status codes, request/response shape, and that the
router's error_key -> HTTP status mapping is correct. Real in-memory
SQLite via the shared `session` fixture, no mocks except the PIN
setting needed to establish an Admin Center session (same pattern as
test_tournament_service.py).
"""
from datetime import date, time, timedelta
from unittest.mock import patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.app import app
from backend.app.database.models.operator_permission import OperatorRole
from backend.app.database.models.tournament import TournamentStatus
from backend.app.database.repositories.game_repository import GamePlayerRepository, GameRepository
from backend.app.database.session import get_db_session
from backend.app.schemas.player import PlayerCreate, PlayerUpdate
from backend.app.schemas.tournament import TournamentCreate
from backend.app.services import admin_session_service as svc_module
from backend.app.services.admin_session_service import AdminSessionService
from backend.app.services.player_service import PlayerService
from backend.app.services.players_service import PlayersService
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


@pytest_asyncio.fixture
async def client(session: AsyncSession):
    async def _override_get_db_session():
        yield session

    app.dependency_overrides[get_db_session] = _override_get_db_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


async def _make_player(session: AsyncSession, telegram_id: int, name: str = "Player") -> int:
    svc = PlayerService(session)
    player, _ = await svc.get_or_create(PlayerCreate(telegram_id=telegram_id, first_name=name))
    await svc.update_profile(
        telegram_id,
        PlayerUpdate(language="en", skill_level=3.5, home_area="Downtown", preferred_courts=["High Park"]),
    )
    await session.commit()
    return player.id


async def _setup_bracket(
    session: AsyncSession, organizer_telegram_id: int, n_players: int = 4, start_id: int = 9500
) -> int:
    """Coach-organized tournament, registration closed, round 1
    generated — ready for start/complete calls. Returns tournament_id."""
    organizer_id = await _make_player(session, organizer_telegram_id, "Organizer")
    await PlayersService(session).set_verified_coach(organizer_id, True)
    await session.commit()

    tsvc = TournamentService(session)
    tournament = await tsvc.create_tournament(
        organizer_telegram_id,
        TournamentCreate(
            name="Bracket Cup",
            area="Downtown",
            court="High Park",
            start_date=date.today() + timedelta(days=14),
            start_time=time(10, 0),
            registration_deadline=date.today() + timedelta(days=7),
            max_players=n_players + 10,
        ),
    )
    await session.commit()
    lifecycle = TournamentLifecycleService(session)
    await lifecycle.transition(tournament.id, TournamentStatus.REGISTRATION_OPEN)
    for i in range(n_players):
        tid = start_id + i
        await _make_player(session, tid, f"Player{i}")
        await tsvc.register_player(tournament.id, tid)
    await lifecycle.transition(tournament.id, TournamentStatus.REGISTRATION_CLOSED)
    success, error_key = await tsvc.generate_matches(tournament.id)
    assert success is True, error_key
    return tournament.id


@pytest.mark.asyncio
async def test_organizer_can_start_match(session: AsyncSession, client: AsyncClient) -> None:
    organizer_telegram_id = 9601
    tournament_id = await _setup_bracket(session, organizer_telegram_id, start_id=9700)
    round_1 = await GameRepository(session).get_games_by_tournament_round(tournament_id, 1)
    game_id = round_1[0].id

    response = await client.post(
        f"/api/v1/games/{game_id}/start", params={"organizer_telegram_id": organizer_telegram_id}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == game_id
    assert body["status"] == "in_progress"


@pytest.mark.asyncio
async def test_organizer_can_complete_match(session: AsyncSession, client: AsyncClient) -> None:
    organizer_telegram_id = 9801
    tournament_id = await _setup_bracket(session, organizer_telegram_id, start_id=9900)
    round_1 = await GameRepository(session).get_games_by_tournament_round(tournament_id, 1)
    game = round_1[0]
    participants = await GamePlayerRepository(session).get_participant_player_ids(game.id)

    await client.post(f"/api/v1/games/{game.id}/start", params={"organizer_telegram_id": organizer_telegram_id})
    response = await client.post(
        f"/api/v1/games/{game.id}/complete",
        params={"winner_player_id": participants[0], "organizer_telegram_id": organizer_telegram_id},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert body["winner_player_id"] == participants[0]


@pytest.mark.asyncio
async def test_admin_can_complete_match(session: AsyncSession, client: AsyncClient) -> None:
    """Admin (an active Admin Center session, the same mechanism the
    bot itself uses — no separate REST auth exists yet) may complete a
    match even though they didn't organize the tournament."""
    organizer_telegram_id = 10001
    admin_telegram_id = 10002
    tournament_id = await _setup_bracket(session, organizer_telegram_id, start_id=10100)
    round_1 = await GameRepository(session).get_games_by_tournament_round(tournament_id, 1)
    game = round_1[0]
    participants = await GamePlayerRepository(session).get_participant_player_ids(game.id)

    await client.post(f"/api/v1/games/{game.id}/start", params={"organizer_telegram_id": organizer_telegram_id})

    with _with_pin() as mock:
        mock.return_value.admin_pin = TEST_PIN
        await AdminSessionService(session).attempt_login(admin_telegram_id, OperatorRole.OWNER, TEST_PIN)
        await session.commit()

        response = await client.post(
            f"/api/v1/games/{game.id}/complete",
            params={"winner_player_id": participants[0], "organizer_telegram_id": admin_telegram_id},
        )
    assert response.status_code == 200
    assert response.json()["status"] == "completed"


@pytest.mark.asyncio
async def test_player_forbidden_from_starting_match(session: AsyncSession, client: AsyncClient) -> None:
    """PD-001 — never a Player, even one registered in the tournament."""
    organizer_telegram_id = 10201
    tournament_id = await _setup_bracket(session, organizer_telegram_id, start_id=10300)
    round_1 = await GameRepository(session).get_games_by_tournament_round(tournament_id, 1)
    game = round_1[0]

    response = await client.post(
        f"/api/v1/games/{game.id}/start", params={"organizer_telegram_id": 10300}  # a registered player
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_player_forbidden_from_completing_match(session: AsyncSession, client: AsyncClient) -> None:
    organizer_telegram_id = 10401
    tournament_id = await _setup_bracket(session, organizer_telegram_id, start_id=10500)
    round_1 = await GameRepository(session).get_games_by_tournament_round(tournament_id, 1)
    game = round_1[0]
    participants = await GamePlayerRepository(session).get_participant_player_ids(game.id)
    await client.post(f"/api/v1/games/{game.id}/start", params={"organizer_telegram_id": organizer_telegram_id})

    response = await client.post(
        f"/api/v1/games/{game.id}/complete",
        params={"winner_player_id": participants[0], "organizer_telegram_id": 10500},  # a registered player
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_invalid_winner_returns_400(session: AsyncSession, client: AsyncClient) -> None:
    organizer_telegram_id = 10601
    tournament_id = await _setup_bracket(session, organizer_telegram_id, start_id=10700)
    round_1 = await GameRepository(session).get_games_by_tournament_round(tournament_id, 1)
    game = round_1[0]
    await client.post(f"/api/v1/games/{game.id}/start", params={"organizer_telegram_id": organizer_telegram_id})

    organizer_player_id = await _make_player(session, organizer_telegram_id)  # not a match participant
    response = await client.post(
        f"/api/v1/games/{game.id}/complete",
        params={"winner_player_id": organizer_player_id, "organizer_telegram_id": organizer_telegram_id},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "tournament_match_winner_not_participant"


@pytest.mark.asyncio
async def test_completing_an_already_completed_match_returns_409(
    session: AsyncSession, client: AsyncClient
) -> None:
    organizer_telegram_id = 10801
    tournament_id = await _setup_bracket(session, organizer_telegram_id, start_id=10900)
    round_1 = await GameRepository(session).get_games_by_tournament_round(tournament_id, 1)
    game = round_1[0]
    participants = await GamePlayerRepository(session).get_participant_player_ids(game.id)
    await client.post(f"/api/v1/games/{game.id}/start", params={"organizer_telegram_id": organizer_telegram_id})
    first = await client.post(
        f"/api/v1/games/{game.id}/complete",
        params={"winner_player_id": participants[0], "organizer_telegram_id": organizer_telegram_id},
    )
    assert first.status_code == 200

    second = await client.post(
        f"/api/v1/games/{game.id}/complete",
        params={"winner_player_id": participants[0], "organizer_telegram_id": organizer_telegram_id},
    )
    assert second.status_code == 409
    assert second.json()["detail"] == "tournament_match_wrong_status"


@pytest.mark.asyncio
async def test_starting_an_already_started_match_returns_409(session: AsyncSession, client: AsyncClient) -> None:
    organizer_telegram_id = 11001
    tournament_id = await _setup_bracket(session, organizer_telegram_id, start_id=11100)
    round_1 = await GameRepository(session).get_games_by_tournament_round(tournament_id, 1)
    game = round_1[0]
    first = await client.post(
        f"/api/v1/games/{game.id}/start", params={"organizer_telegram_id": organizer_telegram_id}
    )
    assert first.status_code == 200

    second = await client.post(
        f"/api/v1/games/{game.id}/start", params={"organizer_telegram_id": organizer_telegram_id}
    )
    assert second.status_code == 409


@pytest.mark.asyncio
async def test_start_404_for_non_tournament_game(client: AsyncClient) -> None:
    response = await client.post("/api/v1/games/999999/start", params={"organizer_telegram_id": 1})
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_completing_round_generates_next_round(session: AsyncSession, client: AsyncClient) -> None:
    organizer_telegram_id = 11201
    tournament_id = await _setup_bracket(session, organizer_telegram_id, start_id=11300)
    game_repo = GameRepository(session)
    gp_repo = GamePlayerRepository(session)
    round_1 = await game_repo.get_games_by_tournament_round(tournament_id, 1)
    assert len(round_1) == 2

    for game in round_1:
        participants = await gp_repo.get_participant_player_ids(game.id)
        await client.post(f"/api/v1/games/{game.id}/start", params={"organizer_telegram_id": organizer_telegram_id})
        response = await client.post(
            f"/api/v1/games/{game.id}/complete",
            params={"winner_player_id": participants[0], "organizer_telegram_id": organizer_telegram_id},
        )
        assert response.status_code == 200

    round_2 = await game_repo.get_games_by_tournament_round(tournament_id, 2)
    assert len(round_2) == 1  # 2 round-1 winners -> 1 final match


@pytest.mark.asyncio
async def test_completing_final_match_marks_tournament_completed(
    session: AsyncSession, client: AsyncClient
) -> None:
    organizer_telegram_id = 11401
    tournament_id = await _setup_bracket(session, organizer_telegram_id, start_id=11500)
    game_repo = GameRepository(session)
    gp_repo = GamePlayerRepository(session)
    round_1 = await game_repo.get_games_by_tournament_round(tournament_id, 1)

    for game in round_1:
        participants = await gp_repo.get_participant_player_ids(game.id)
        await client.post(f"/api/v1/games/{game.id}/start", params={"organizer_telegram_id": organizer_telegram_id})
        await client.post(
            f"/api/v1/games/{game.id}/complete",
            params={"winner_player_id": participants[0], "organizer_telegram_id": organizer_telegram_id},
        )

    round_2 = await game_repo.get_games_by_tournament_round(tournament_id, 2)
    final_game = round_2[0]
    final_participants = await gp_repo.get_participant_player_ids(final_game.id)
    await client.post(
        f"/api/v1/games/{final_game.id}/start", params={"organizer_telegram_id": organizer_telegram_id}
    )
    response = await client.post(
        f"/api/v1/games/{final_game.id}/complete",
        params={"winner_player_id": final_participants[0], "organizer_telegram_id": organizer_telegram_id},
    )
    assert response.status_code == 200

    tournament_response = await client.get(f"/api/v1/tournaments/{tournament_id}")
    assert tournament_response.json()["status"] == "completed"

    standings_response = await client.get(f"/api/v1/tournaments/{tournament_id}/standings")
    champions = [e for e in standings_response.json() if e["status"] == "champion"]
    assert len(champions) == 1
    assert champions[0]["player_id"] == final_participants[0]
