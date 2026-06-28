"""Tests for Sprint 3.2 – Find Players for a Match."""
import pytest

from backend.app.database.models.game import MatchType
from backend.app.database.repositories.game_repository import GamePlayerRepository, GameRepository
from backend.app.database.repositories.player_repository import PlayerRepository
from backend.app.schemas.game import GameCreate
from backend.app.schemas.player import PlayerCreate, PlayerUpdate
from backend.app.services.game_service import GameService
from backend.app.services.player_service import PlayerService


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _make_player(session, telegram_id: int, area: str, level: float, first_name: str = "Player") -> None:
    svc = PlayerService(session)
    await svc.get_or_create(PlayerCreate(telegram_id=telegram_id, first_name=first_name))
    await svc.update_profile(
        telegram_id,
        PlayerUpdate(language="en", skill_level=level, home_area=area, preferred_courts=["High Park"]),
    )


async def _make_game(session, organizer_id: int, area: str, level: float) -> int:
    from datetime import date, time
    game = await GameService(session).create_game(
        creator_telegram_id=organizer_id,
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


# ── Repository: find_players_for_match ────────────────────────────────────────

async def test_repo_returns_matching_players(session):
    await _make_player(session, 1001, "Downtown", 3.0, "Anton")
    repo = PlayerRepository(session)
    results = await repo.find_players_for_match(area="Downtown", level=3.0, exclude_player_ids=set())
    assert any(p.first_name == "Anton" for p in results)


async def test_repo_filters_by_area(session):
    await _make_player(session, 1002, "Etobicoke", 3.0, "Maria")
    repo = PlayerRepository(session)
    results = await repo.find_players_for_match(area="Downtown", level=3.0, exclude_player_ids=set())
    assert not any(p.first_name == "Maria" for p in results)


async def test_repo_filters_by_level_outside_tolerance(session):
    await _make_player(session, 1003, "Downtown", 2.0, "Alex")
    repo = PlayerRepository(session)
    results = await repo.find_players_for_match(area="Downtown", level=3.0, exclude_player_ids=set())
    assert not any(p.first_name == "Alex" for p in results)


async def test_repo_includes_level_at_boundary(session):
    await _make_player(session, 1004, "Downtown", 2.5, "Sam")
    await _make_player(session, 1005, "Downtown", 3.5, "Lee")
    repo = PlayerRepository(session)
    results = await repo.find_players_for_match(area="Downtown", level=3.0, exclude_player_ids=set())
    names = {p.first_name for p in results}
    assert "Sam" in names
    assert "Lee" in names


async def test_repo_excludes_by_id(session):
    svc = PlayerService(session)
    player, _ = await svc.get_or_create(PlayerCreate(telegram_id=1006, first_name="Excluded"))
    await svc.update_profile(1006, PlayerUpdate(language="en", skill_level=3.0, home_area="Downtown", preferred_courts=["High Park"]))
    repo = PlayerRepository(session)
    results = await repo.find_players_for_match(area="Downtown", level=3.0, exclude_player_ids={player.id})
    assert not any(p.id == player.id for p in results)


# ── Repository: get_participant_player_ids ────────────────────────────────────

async def test_get_participant_ids(session):
    await _make_player(session, 2001, "Downtown", 3.0, "Organizer")
    game_id = await _make_game(session, organizer_id=2001, area="Downtown", level=3.0)
    svc = PlayerService(session)
    organizer, _ = await svc.get_or_create(PlayerCreate(telegram_id=2001, first_name="Organizer"))
    gp_repo = GamePlayerRepository(session)
    ids = await gp_repo.get_participant_player_ids(game_id)
    assert organizer.id in ids


async def test_get_participant_ids_empty_game(session):
    gp_repo = GamePlayerRepository(session)
    ids = await gp_repo.get_participant_player_ids(99999)
    assert ids == []


# ── Service: find_players_for_match ──────────────────────────────────────────

async def test_service_excludes_organizer(session):
    await _make_player(session, 3001, "Downtown", 3.0, "Organizer")
    game_id = await _make_game(session, organizer_id=3001, area="Downtown", level=3.0)
    results = await GameService(session).find_players_for_match(game_id, organizer_telegram_id=3001)
    assert not any(c.first_name == "Organizer" for c in results)


async def test_service_returns_matching_candidate(session):
    await _make_player(session, 3002, "North York", 3.0, "Organizer2")
    await _make_player(session, 3003, "North York", 3.0, "Candidate")
    game_id = await _make_game(session, organizer_id=3002, area="North York", level=3.0)
    results = await GameService(session).find_players_for_match(game_id, organizer_telegram_id=3002)
    assert any(c.first_name == "Candidate" for c in results)


async def test_service_returns_empty_for_unknown_game(session):
    results = await GameService(session).find_players_for_match(99999, organizer_telegram_id=1)
    assert results == []


async def test_service_excludes_wrong_area(session):
    await _make_player(session, 3004, "Etobicoke", 3.0, "Organizer3")
    await _make_player(session, 3005, "Scarborough", 3.0, "WrongArea")
    game_id = await _make_game(session, organizer_id=3004, area="Etobicoke", level=3.0)
    results = await GameService(session).find_players_for_match(game_id, organizer_telegram_id=3004)
    assert not any(c.first_name == "WrongArea" for c in results)


async def test_service_excludes_existing_participants(session):
    await _make_player(session, 3006, "Downtown", 3.0, "Organizer4")
    await _make_player(session, 3007, "Downtown", 3.0, "Participant")
    game_id = await _make_game(session, organizer_id=3006, area="Downtown", level=3.0)
    # Manually add Participant to the game
    svc = PlayerService(session)
    participant, _ = await svc.get_or_create(PlayerCreate(telegram_id=3007, first_name="Participant"))
    gp_repo = GamePlayerRepository(session)
    from backend.app.database.models.game import GamePlayerStatus
    await gp_repo.add_player_to_game(game_id, participant.id, GamePlayerStatus.INVITED)
    results = await GameService(session).find_players_for_match(game_id, organizer_telegram_id=3006)
    assert not any(c.first_name == "Participant" for c in results)
