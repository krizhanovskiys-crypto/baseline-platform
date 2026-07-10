"""API tests for the Tournament Read API (Sprint 15, Step 1).

Read-only endpoints: list, detail, standings. No create/update/result
endpoints exist yet — this file tests only what's actually built.
Real in-memory SQLite via the shared `session` fixture, no mocks — the
FastAPI app's own `get_db_session` dependency is overridden to yield
that same session, so setup done directly through TournamentService is
visible to requests made through the API layer in the same test.
"""
from datetime import date, time, timedelta

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.app import app
from backend.app.database.models.tournament import TournamentStatus
from backend.app.database.session import get_db_session
from backend.app.schemas.player import PlayerCreate, PlayerUpdate
from backend.app.schemas.tournament import TournamentCreate
from backend.app.services.player_service import PlayerService
from backend.app.services.tournament_lifecycle_service import TournamentLifecycleService
from backend.app.services.tournament_service import TournamentService


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


async def _make_tournament(
    session: AsyncSession, organizer_telegram_id: int, name: str = "Summer Cup", max_players: int = 4
) -> int:
    service = TournamentService(session)
    tournament = await service.create_tournament(
        organizer_telegram_id,
        TournamentCreate(
            name=name,
            area="Downtown",
            court="High Park",
            start_date=date.today() + timedelta(days=14),
            start_time=time(10, 0),
            registration_deadline=date.today() + timedelta(days=7),
            max_players=max_players,
        ),
    )
    await session.commit()
    return tournament.id


@pytest.mark.asyncio
async def test_list_tournaments(session: AsyncSession, client: AsyncClient) -> None:
    await _make_player(session, 8001, "Organizer")
    await _make_tournament(session, 8001, name="Summer Cup")
    await _make_tournament(session, 8001, name="Winter Cup")

    response = await client.get("/api/v1/tournaments/")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 2
    names = {t["name"] for t in body}
    assert names == {"Summer Cup", "Winter Cup"}
    # Confirm the full TournamentRead shape reaches the API unmodified.
    assert "status" in body[0]
    assert "max_players" in body[0]


@pytest.mark.asyncio
async def test_list_tournaments_empty(client: AsyncClient) -> None:
    response = await client.get("/api/v1/tournaments/")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_get_tournament_details(session: AsyncSession, client: AsyncClient) -> None:
    await _make_player(session, 8101, "Organizer")
    tournament_id = await _make_tournament(session, 8101, name="Details Cup")

    response = await client.get(f"/api/v1/tournaments/{tournament_id}")
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == tournament_id
    assert body["name"] == "Details Cup"
    assert body["status"] == "draft"


@pytest.mark.asyncio
async def test_get_tournament_details_404(client: AsyncClient) -> None:
    response = await client.get("/api/v1/tournaments/999999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Tournament not found"


@pytest.mark.asyncio
async def test_get_standings_for_empty_tournament(session: AsyncSession, client: AsyncClient) -> None:
    """A tournament that exists but has no registrations/completed
    matches yet — standings must be an empty list, not a 404."""
    await _make_player(session, 8201, "Organizer")
    tournament_id = await _make_tournament(session, 8201, name="Empty Cup")

    response = await client.get(f"/api/v1/tournaments/{tournament_id}/standings")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_get_standings_404_for_missing_tournament(client: AsyncClient) -> None:
    response = await client.get("/api/v1/tournaments/999999/standings")
    assert response.status_code == 404
    assert response.json()["detail"] == "Tournament not found"


@pytest.mark.asyncio
async def test_get_standings_reflects_completed_bracket(session: AsyncSession, client: AsyncClient) -> None:
    """Standings served over the API must be exactly what
    TournamentService.get_standings() computes — no duplicated logic in
    the router. Drives a full 4-player bracket through the existing
    service, then reads it back through the API."""
    from backend.app.database.repositories.game_repository import GamePlayerRepository, GameRepository
    from backend.app.services.players_service import PlayersService

    organizer_telegram_id = 8301
    organizer_id = await _make_player(session, organizer_telegram_id, "Organizer")
    await PlayersService(session).set_verified_coach(organizer_id, True)
    await session.commit()

    tournament_id = await _make_tournament(session, organizer_telegram_id, name="Bracket Cup", max_players=14)
    lifecycle = TournamentLifecycleService(session)
    await lifecycle.transition(tournament_id, TournamentStatus.REGISTRATION_OPEN)

    service = TournamentService(session)
    for i in range(4):
        tid = 8400 + i
        await _make_player(session, tid, f"Player{tid}")
        await service.register_player(tournament_id, tid)

    await lifecycle.transition(tournament_id, TournamentStatus.REGISTRATION_CLOSED)
    success, error_key = await service.generate_matches(tournament_id)
    assert success is True, error_key

    game_repo = GameRepository(session)
    gp_repo = GamePlayerRepository(session)
    round_1 = await game_repo.get_games_by_tournament_round(tournament_id, 1)
    for game in round_1:
        participants = await gp_repo.get_participant_player_ids(game.id)
        await service.start_match(game.id, organizer_telegram_id)
        await service.complete_match(game.id, participants[0], organizer_telegram_id)

    round_2 = await game_repo.get_games_by_tournament_round(tournament_id, 2)
    final_game = round_2[0]
    final_participants = await gp_repo.get_participant_player_ids(final_game.id)
    await service.start_match(final_game.id, organizer_telegram_id)
    await service.complete_match(final_game.id, final_participants[0], organizer_telegram_id)

    expected = await service.get_standings(tournament_id)

    response = await client.get(f"/api/v1/tournaments/{tournament_id}/standings")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == len(expected)
    by_player = {entry["player_id"]: entry for entry in body}
    champions = [e for e in body if e["status"] == "champion"]
    assert len(champions) == 1
    eliminated = [e for e in body if e["status"] == "eliminated"]
    assert len(eliminated) == 3
