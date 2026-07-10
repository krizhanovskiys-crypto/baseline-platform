"""Tests for the Tournament Dashboard's 🏆 Enter Result flow
(Sprint 16, Step 3) — tourn_dash_enter_result_prompt
(tourn:enter_result:{game_id}) and tourn_dash_select_winner
(tourn:winner:{game_id}:{player_id}).

Both handlers are thin wrappers: the prompt handler only builds the
"Who won?" view from already-fetched match data; the winner-selection
handler calls TournamentService.complete_match() and re-renders
current state via the existing show_tournament_details() orchestration
— no duplicated authorization, validation, or bracket logic. All of
that is already covered at the service level
(test_tournament_service.py); this file verifies the Telegram mapping.
"""
import itertools
from datetime import date, time
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.bot.handlers.admin.tournaments import tourn_dash_enter_result_prompt, tourn_dash_select_winner
from backend.app.database.models.game import GameStatus
from backend.app.database.models.operator_permission import OperatorRole
from backend.app.database.models.tournament import TournamentStatus
from backend.app.database.repositories.game_repository import GamePlayerRepository, GameRepository
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


_id_counter = itertools.count(1)


class _FakeMessage:
    def __init__(self, chat_log: list) -> None:
        self.msg_id = next(_id_counter)
        self.edited: list[tuple[str, object]] = []
        self._chat_log = chat_log

    async def edit_text(self, text, reply_markup=None, parse_mode=None):
        self.edited.append((text, reply_markup))
        return self

    async def answer(self, text, reply_markup=None, parse_mode=None):
        new_msg = _FakeMessage(self._chat_log)
        new_msg.edited.append((text, reply_markup))  # reuse .edited as "content" for SEND too
        self._chat_log.append(new_msg)
        return new_msg


class _FakeCallback:
    def __init__(self, data: str, user_id: int, message: _FakeMessage) -> None:
        self.data = data
        self.from_user = SimpleNamespace(id=user_id)
        self.message = message
        self.answer = AsyncMock()


class _FakeBot:
    async def send_message(self, *args, **kwargs) -> None:
        return None


async def _make_player(session: AsyncSession, telegram_id: int, name: str = "Player") -> int:
    svc = PlayerService(session)
    player, _ = await svc.get_or_create(PlayerCreate(telegram_id=telegram_id, first_name=name))
    await svc.update_profile(
        telegram_id,
        PlayerUpdate(language="en", skill_level=3.5, home_area="Downtown", preferred_courts=["High Park"]),
    )
    await session.commit()
    return player.id


async def _setup_bracket(session: AsyncSession, organizer_telegram_id: int, start_id: int, n_players: int = 4) -> int:
    """Coach-organized tournament, round 1 generated. Returns tournament_id."""
    organizer_id = await _make_player(session, organizer_telegram_id, "Organizer")
    await PlayersService(session).set_verified_coach(organizer_id, True)
    await session.commit()

    tsvc = TournamentService(session)
    tournament = await tsvc.create_tournament(
        organizer_telegram_id,
        TournamentCreate(
            name="Result Cup", area="Downtown", court="High Park",
            start_date=date(2026, 8, 1), start_time=time(10, 0),
            registration_deadline=date(2026, 7, 20), max_players=n_players + 10,
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
async def test_enter_result_prompt_shows_who_won_with_two_buttons(session: AsyncSession) -> None:
    organizer_telegram_id = 15001
    tournament_id = await _setup_bracket(session, organizer_telegram_id, start_id=15100)
    round_1 = await GameRepository(session).get_games_by_tournament_round(tournament_id, 1)
    game = round_1[0]
    service = TournamentService(session)
    await service.start_match(game.id, organizer_telegram_id)
    participants = await GamePlayerRepository(session).get_participant_player_ids(game.id)

    chat_log: list = []
    message = _FakeMessage(chat_log)
    callback = _FakeCallback(data=f"tourn:enter_result:{game.id}", user_id=organizer_telegram_id, message=message)
    await tourn_dash_enter_result_prompt(callback, session)

    assert len(message.edited) == 1
    text, keyboard = message.edited[0]
    assert "Who won" in text
    buttons = [(btn.text, btn.callback_data) for row in keyboard.inline_keyboard for btn in row]
    assert len(buttons) == 2
    callback_datas = {cb for _, cb in buttons}
    assert callback_datas == {f"tourn:winner:{game.id}:{pid}" for pid in participants}


@pytest.mark.asyncio
async def test_organizer_selects_winner(session: AsyncSession) -> None:
    organizer_telegram_id = 15201
    tournament_id = await _setup_bracket(session, organizer_telegram_id, start_id=15300)
    round_1 = await GameRepository(session).get_games_by_tournament_round(tournament_id, 1)
    game = round_1[0]
    service = TournamentService(session)
    await service.start_match(game.id, organizer_telegram_id)
    participants = await GamePlayerRepository(session).get_participant_player_ids(game.id)
    winner_id = participants[0]

    chat_log: list = []
    message = _FakeMessage(chat_log)
    callback = _FakeCallback(
        data=f"tourn:winner:{game.id}:{winner_id}", user_id=organizer_telegram_id, message=message
    )
    await tourn_dash_select_winner(callback, session, _FakeBot())

    # The tapped message is edited into a short winner confirmation.
    assert len(message.edited) == 1
    assert "Winner" in message.edited[0][0]
    # A fresh dashboard re-render follows, as new messages.
    assert len(chat_log) > 0

    refreshed_game = await GameRepository(session).get_by_id(game.id)
    assert refreshed_game.status == GameStatus.COMPLETED
    assert refreshed_game.winner_player_id == winner_id


@pytest.mark.asyncio
async def test_admin_selects_winner(session: AsyncSession) -> None:
    organizer_telegram_id = 15401
    admin_telegram_id = 15402
    tournament_id = await _setup_bracket(session, organizer_telegram_id, start_id=15500)
    round_1 = await GameRepository(session).get_games_by_tournament_round(tournament_id, 1)
    game = round_1[0]
    service = TournamentService(session)
    await service.start_match(game.id, organizer_telegram_id)
    participants = await GamePlayerRepository(session).get_participant_player_ids(game.id)
    winner_id = participants[0]

    with _with_pin() as mock:
        mock.return_value.admin_pin = TEST_PIN
        await AdminSessionService(session).attempt_login(admin_telegram_id, OperatorRole.OWNER, TEST_PIN)
        await session.commit()

        chat_log: list = []
        message = _FakeMessage(chat_log)
        callback = _FakeCallback(
            data=f"tourn:winner:{game.id}:{winner_id}", user_id=admin_telegram_id, message=message
        )
        await tourn_dash_select_winner(callback, session, _FakeBot())

    assert "Winner" in message.edited[0][0]
    refreshed_game = await GameRepository(session).get_by_id(game.id)
    assert refreshed_game.status == GameStatus.COMPLETED


@pytest.mark.asyncio
async def test_player_forbidden_from_selecting_winner(session: AsyncSession) -> None:
    """PD-001 — never a Player, even one registered in this tournament."""
    organizer_telegram_id = 15601
    tournament_id = await _setup_bracket(session, organizer_telegram_id, start_id=15700)
    round_1 = await GameRepository(session).get_games_by_tournament_round(tournament_id, 1)
    game = round_1[0]
    service = TournamentService(session)
    await service.start_match(game.id, organizer_telegram_id)
    participants = await GamePlayerRepository(session).get_participant_player_ids(game.id)

    chat_log: list = []
    message = _FakeMessage(chat_log)
    callback = _FakeCallback(
        data=f"tourn:winner:{game.id}:{participants[0]}", user_id=15700, message=message  # a registered player
    )
    await tourn_dash_select_winner(callback, session, _FakeBot())

    assert message.edited == []
    assert chat_log == []
    callback.answer.assert_awaited_once()
    args, kwargs = callback.answer.call_args
    assert kwargs.get("show_alert") is True
    assert "Organizer" in args[0]

    refreshed_game = await GameRepository(session).get_by_id(game.id)
    assert refreshed_game.status == GameStatus.IN_PROGRESS  # unchanged


@pytest.mark.asyncio
async def test_invalid_winner_shows_error(session: AsyncSession) -> None:
    organizer_telegram_id = 15801
    tournament_id = await _setup_bracket(session, organizer_telegram_id, start_id=15900)
    round_1 = await GameRepository(session).get_games_by_tournament_round(tournament_id, 1)
    game = round_1[0]
    service = TournamentService(session)
    await service.start_match(game.id, organizer_telegram_id)

    organizer_player_id = await _make_player(session, organizer_telegram_id)  # not a match participant

    chat_log: list = []
    message = _FakeMessage(chat_log)
    callback = _FakeCallback(
        data=f"tourn:winner:{game.id}:{organizer_player_id}", user_id=organizer_telegram_id, message=message
    )
    await tourn_dash_select_winner(callback, session, _FakeBot())

    assert message.edited == []
    args, kwargs = callback.answer.call_args
    assert kwargs.get("show_alert") is True
    assert "part of this match" in args[0]


@pytest.mark.asyncio
async def test_completed_game_shows_error(session: AsyncSession) -> None:
    organizer_telegram_id = 16001
    tournament_id = await _setup_bracket(session, organizer_telegram_id, start_id=16100)
    round_1 = await GameRepository(session).get_games_by_tournament_round(tournament_id, 1)
    game = round_1[0]
    service = TournamentService(session)
    await service.start_match(game.id, organizer_telegram_id)
    participants = await GamePlayerRepository(session).get_participant_player_ids(game.id)
    await service.complete_match(game.id, participants[0], organizer_telegram_id)

    chat_log: list = []
    message = _FakeMessage(chat_log)
    callback = _FakeCallback(
        data=f"tourn:winner:{game.id}:{participants[0]}", user_id=organizer_telegram_id, message=message
    )
    await tourn_dash_select_winner(callback, session, _FakeBot())

    assert message.edited == []
    args, kwargs = callback.answer.call_args
    assert kwargs.get("show_alert") is True
    assert "already been completed" in args[0]


@pytest.mark.asyncio
async def test_next_round_appears_after_completing_round(session: AsyncSession) -> None:
    organizer_telegram_id = 16201
    tournament_id = await _setup_bracket(session, organizer_telegram_id, start_id=16300)
    game_repo = GameRepository(session)
    gp_repo = GamePlayerRepository(session)
    round_1 = await game_repo.get_games_by_tournament_round(tournament_id, 1)
    service = TournamentService(session)

    # Complete the first round-1 match directly through the service —
    # only the SECOND completion (through the handler) is under test.
    game_a, game_b = round_1
    participants_a = await gp_repo.get_participant_player_ids(game_a.id)
    await service.start_match(game_a.id, organizer_telegram_id)
    await service.complete_match(game_a.id, participants_a[0], organizer_telegram_id)

    participants_b = await gp_repo.get_participant_player_ids(game_b.id)
    await service.start_match(game_b.id, organizer_telegram_id)

    chat_log: list = []
    message = _FakeMessage(chat_log)
    callback = _FakeCallback(
        data=f"tourn:winner:{game_b.id}:{participants_b[0]}", user_id=organizer_telegram_id, message=message
    )
    await tourn_dash_select_winner(callback, session, _FakeBot())

    round_2 = await game_repo.get_games_by_tournament_round(tournament_id, 2)
    assert len(round_2) == 1  # the final, generated automatically by complete_match()

    rendered_texts = [text for m in chat_log for text, _ in m.edited]
    assert any("Round 2" in text for text in rendered_texts)


@pytest.mark.asyncio
async def test_champion_appears_when_tournament_completes(session: AsyncSession) -> None:
    organizer_telegram_id = 16401
    tournament_id = await _setup_bracket(session, organizer_telegram_id, start_id=16500, n_players=2)
    round_1 = await GameRepository(session).get_games_by_tournament_round(tournament_id, 1)
    game = round_1[0]
    service = TournamentService(session)
    await service.start_match(game.id, organizer_telegram_id)
    participants = await GamePlayerRepository(session).get_participant_player_ids(game.id)

    chat_log: list = []
    message = _FakeMessage(chat_log)
    callback = _FakeCallback(
        data=f"tourn:winner:{game.id}:{participants[0]}", user_id=organizer_telegram_id, message=message
    )
    await tourn_dash_select_winner(callback, session, _FakeBot())

    rendered_texts = [text for m in chat_log for text, _ in m.edited]
    assert any("Champion" in text for text in rendered_texts)


@pytest.mark.asyncio
async def test_tournament_marked_completed_after_final_match(session: AsyncSession) -> None:
    organizer_telegram_id = 16601
    tournament_id = await _setup_bracket(session, organizer_telegram_id, start_id=16700, n_players=2)
    round_1 = await GameRepository(session).get_games_by_tournament_round(tournament_id, 1)
    game = round_1[0]
    service = TournamentService(session)
    await service.start_match(game.id, organizer_telegram_id)
    participants = await GamePlayerRepository(session).get_participant_player_ids(game.id)

    chat_log: list = []
    message = _FakeMessage(chat_log)
    callback = _FakeCallback(
        data=f"tourn:winner:{game.id}:{participants[0]}", user_id=organizer_telegram_id, message=message
    )
    await tourn_dash_select_winner(callback, session, _FakeBot())

    tournament = await service.get_tournament(tournament_id)
    assert tournament.status == TournamentStatus.COMPLETED
