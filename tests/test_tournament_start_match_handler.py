"""Tests for the Tournament Dashboard's ▶️ Start Match button handler
(Sprint 16, Step 2) — tourn_dash_start_match, callback tourn:start_match:{id}.

The handler is a thin wrapper: it calls TournamentService.start_match()
and maps the returned (game, error_key) onto Telegram. All authorization
and lifecycle rules under test here already live in TournamentService/
MatchLifecycleService (Sprint 14) — this file verifies the mapping, not
re-verifying the underlying rules (already covered in
test_tournament_service.py).
"""
from datetime import date, time
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.bot.handlers.admin.tournaments import tourn_dash_start_match
from backend.app.database.models.game import GameStatus
from backend.app.database.models.operator_permission import OperatorRole
from backend.app.database.models.tournament import TournamentStatus
from backend.app.database.repositories.game_repository import GameRepository
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


class _FakeMessage:
    def __init__(self) -> None:
        self.edited: list[tuple[str, object]] = []

    async def edit_text(self, text, reply_markup=None, parse_mode=None):
        self.edited.append((text, reply_markup))
        return self


class _FakeCallback:
    def __init__(self, data: str, user_id: int) -> None:
        self.data = data
        self.from_user = SimpleNamespace(id=user_id)
        self.message = _FakeMessage()
        self.answer = AsyncMock()


async def _make_player(session: AsyncSession, telegram_id: int, name: str = "Player") -> int:
    svc = PlayerService(session)
    player, _ = await svc.get_or_create(PlayerCreate(telegram_id=telegram_id, first_name=name))
    await svc.update_profile(
        telegram_id,
        PlayerUpdate(language="en", skill_level=3.5, home_area="Downtown", preferred_courts=["High Park"]),
    )
    await session.commit()
    return player.id


async def _setup_bracket(session: AsyncSession, organizer_telegram_id: int, start_id: int) -> int:
    """Coach-organized 4-player tournament, round 1 generated. Returns
    the id of round 1's first Game (status OPEN)."""
    organizer_id = await _make_player(session, organizer_telegram_id, "Organizer")
    await PlayersService(session).set_verified_coach(organizer_id, True)
    await session.commit()

    tsvc = TournamentService(session)
    tournament = await tsvc.create_tournament(
        organizer_telegram_id,
        TournamentCreate(
            name="Handler Cup", area="Downtown", court="High Park",
            start_date=date(2026, 8, 1), start_time=time(10, 0),
            registration_deadline=date(2026, 7, 20), max_players=14,
        ),
    )
    await session.commit()
    lifecycle = TournamentLifecycleService(session)
    await lifecycle.transition(tournament.id, TournamentStatus.REGISTRATION_OPEN)
    for i in range(4):
        tid = start_id + i
        await _make_player(session, tid, f"Player{i}")
        await tsvc.register_player(tournament.id, tid)
    await lifecycle.transition(tournament.id, TournamentStatus.REGISTRATION_CLOSED)
    success, error_key = await tsvc.generate_matches(tournament.id)
    assert success is True, error_key

    round_1 = await GameRepository(session).get_games_by_tournament_round(tournament.id, 1)
    return round_1[0].id


@pytest.mark.asyncio
async def test_organizer_starts_match(session: AsyncSession) -> None:
    organizer_telegram_id = 14001
    game_id = await _setup_bracket(session, organizer_telegram_id, start_id=14100)

    callback = _FakeCallback(data=f"tourn:start_match:{game_id}", user_id=organizer_telegram_id)
    await tourn_dash_start_match(callback, session)

    assert len(callback.message.edited) == 1
    text, keyboard = callback.message.edited[0]
    assert "In Progress" in text
    buttons = {btn.callback_data for row in keyboard.inline_keyboard for btn in row}
    assert f"tourn:enter_result:{game_id}" in buttons
    callback.answer.assert_awaited_once_with()

    game = await GameRepository(session).get_by_id(game_id)
    assert game.status == GameStatus.IN_PROGRESS


@pytest.mark.asyncio
async def test_admin_starts_match(session: AsyncSession) -> None:
    organizer_telegram_id = 14201
    admin_telegram_id = 14202
    game_id = await _setup_bracket(session, organizer_telegram_id, start_id=14300)

    with _with_pin() as mock:
        mock.return_value.admin_pin = TEST_PIN
        await AdminSessionService(session).attempt_login(admin_telegram_id, OperatorRole.OWNER, TEST_PIN)
        await session.commit()

        callback = _FakeCallback(data=f"tourn:start_match:{game_id}", user_id=admin_telegram_id)
        await tourn_dash_start_match(callback, session)

    assert len(callback.message.edited) == 1
    assert "In Progress" in callback.message.edited[0][0]

    game = await GameRepository(session).get_by_id(game_id)
    assert game.status == GameStatus.IN_PROGRESS


@pytest.mark.asyncio
async def test_unauthorized_player_cannot_start_match(session: AsyncSession) -> None:
    """PD-001 — never a Player, even one registered in this tournament."""
    organizer_telegram_id = 14401
    game_id = await _setup_bracket(session, organizer_telegram_id, start_id=14500)

    callback = _FakeCallback(data=f"tourn:start_match:{game_id}", user_id=14500)  # a registered player
    await tourn_dash_start_match(callback, session)

    assert callback.message.edited == []
    callback.answer.assert_awaited_once()
    args, kwargs = callback.answer.call_args
    assert kwargs.get("show_alert") is True
    assert "Organizer" in args[0]

    game = await GameRepository(session).get_by_id(game_id)
    assert game.status == GameStatus.OPEN  # unchanged


@pytest.mark.asyncio
async def test_already_started_match_shows_error(session: AsyncSession) -> None:
    organizer_telegram_id = 14601
    game_id = await _setup_bracket(session, organizer_telegram_id, start_id=14700)

    first = _FakeCallback(data=f"tourn:start_match:{game_id}", user_id=organizer_telegram_id)
    await tourn_dash_start_match(first, session)
    assert len(first.message.edited) == 1

    second = _FakeCallback(data=f"tourn:start_match:{game_id}", user_id=organizer_telegram_id)
    await tourn_dash_start_match(second, session)

    assert second.message.edited == []  # no further edit — the error path, not success
    second.answer.assert_awaited_once()
    args, kwargs = second.answer.call_args
    assert kwargs.get("show_alert") is True
    assert "can't be started" in args[0]

    game = await GameRepository(session).get_by_id(game_id)
    assert game.status == GameStatus.IN_PROGRESS  # still just the one transition


@pytest.mark.asyncio
async def test_invalid_game_id_shows_error(session: AsyncSession) -> None:
    organizer_telegram_id = 14801
    await _make_player(session, organizer_telegram_id, "Organizer")

    callback = _FakeCallback(data="tourn:start_match:999999", user_id=organizer_telegram_id)
    await tourn_dash_start_match(callback, session)

    assert callback.message.edited == []
    callback.answer.assert_awaited_once()
    args, kwargs = callback.answer.call_args
    assert kwargs.get("show_alert") is True
    assert "not be found" in args[0]
