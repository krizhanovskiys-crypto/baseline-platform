"""Regression test for a bug caught during Tournament Platform v1's
final release verification: Admin Center's Add Player / Remove Player
success messages rendered player.first_name directly into
parse_mode="Markdown" text without escaping — the same TelegramBadRequest
"can't parse entities" bug class already fixed for Player Details
(docs/PRODUCT_DECISIONS.md) and Player names in the Registration Closed
Notification. A first_name with an unpaired Markdown special character
must not crash either screen.
"""
from datetime import date, time
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from aiogram.fsm.storage.memory import MemoryStorage
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.bot.handlers.admin.tournaments import tourn_add_player_submit, tourn_remove_player
from backend.app.bot.states.states import AdminTournamentsStates
from backend.app.database.models.operator_permission import OperatorRole
from backend.app.database.models.tournament import TournamentStatus
from backend.app.schemas.player import PlayerCreate, PlayerUpdate
from backend.app.schemas.tournament import TournamentCreate
from backend.app.services import admin_session_service as svc_module
from backend.app.services.admin_session_service import AdminSessionService
from backend.app.services.permission_service import PermissionService
from backend.app.services.player_service import PlayerService
from backend.app.services.tournament_lifecycle_service import TournamentLifecycleService
from backend.app.services.tournament_service import TournamentService

_UNESCAPED_NAME = "john_doe_smith"  # unpaired underscores — the exact shape that crashes unescaped Markdown
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


def _make_state(user_id: int) -> FSMContext:
    return FSMContext(storage=MemoryStorage(), key=StorageKey(bot_id=1, chat_id=user_id, user_id=user_id))


class _FakeMessage:
    def __init__(self) -> None:
        self.sent: list[str] = []

    async def answer(self, text, reply_markup=None, parse_mode=None):
        self.sent.append(text)
        return self


class _FakeCallback:
    def __init__(self, data: str, user_id: int) -> None:
        self.data = data
        self.from_user = SimpleNamespace(id=user_id)
        self.message = _FakeMessage()
        self.answer = AsyncMock()


class _FakeBot:
    async def send_message(self, *args, **kwargs) -> None:
        return None


async def _make_admin_with_active_session(session: AsyncSession, telegram_id: int) -> None:
    """Holding OperatorPermission alone isn't enough — can_manage_tournament()
    requires an active PIN session, same bar as every other Admin Center
    action."""
    await PermissionService(session).seed_owners([telegram_id])
    await session.commit()
    with _with_pin() as mock:
        mock.return_value.admin_pin = TEST_PIN
        await AdminSessionService(session).attempt_login(telegram_id, OperatorRole.OWNER, TEST_PIN)
        await session.commit()


async def _make_organizer_and_tournament(session: AsyncSession, telegram_id: int) -> int:
    svc = PlayerService(session)
    await svc.get_or_create(PlayerCreate(telegram_id=telegram_id, first_name="Organizer"))
    await svc.update_profile(
        telegram_id, PlayerUpdate(language="en", skill_level=3.5, home_area="Downtown", preferred_courts=[])
    )
    await session.commit()
    tournament = await TournamentService(session).create_tournament(
        telegram_id,
        TournamentCreate(
            name="Cup", area="Downtown", court="High Park",
            start_date=date(2026, 8, 1), start_time=time(10, 0),
            registration_deadline=date(2026, 7, 20), max_players=4,
        ),
    )
    await session.commit()
    await TournamentLifecycleService(session).transition(tournament.id, TournamentStatus.REGISTRATION_OPEN)
    await session.commit()
    return tournament.id


@pytest.mark.asyncio
async def test_add_player_success_message_escapes_first_name(session: AsyncSession) -> None:
    admin_id = 9001
    await _make_admin_with_active_session(session, admin_id)
    tournament_id = await _make_organizer_and_tournament(session, 9002)

    svc = PlayerService(session)
    await svc.get_or_create(PlayerCreate(telegram_id=9003, first_name=_UNESCAPED_NAME, username=_UNESCAPED_NAME))
    await session.commit()

    state = _make_state(admin_id)
    await state.set_state(AdminTournamentsStates.enter_add_player_search)
    await state.update_data(lang="en", add_player_tournament_id=tournament_id)

    message = _FakeMessage()
    message.text = _UNESCAPED_NAME
    message.from_user = SimpleNamespace(id=admin_id)

    # Must not raise — the bug was an unescaped first_name reaching
    # Telegram's Markdown parser, not something this in-process test can
    # trigger a TelegramBadRequest for directly, but it confirms the
    # rendered text is the escaped form, not the raw one.
    await tourn_add_player_submit(message, session, state, _FakeBot())

    assert any("\\_" in text for text in message.sent), message.sent


@pytest.mark.asyncio
async def test_remove_player_success_message_escapes_first_name(session: AsyncSession) -> None:
    admin_id = 9101
    await _make_admin_with_active_session(session, admin_id)
    tournament_id = await _make_organizer_and_tournament(session, 9102)

    svc = PlayerService(session)
    player, _ = await svc.get_or_create(
        PlayerCreate(telegram_id=9103, first_name=_UNESCAPED_NAME, username=_UNESCAPED_NAME)
    )
    await session.commit()
    registered, _ = await TournamentService(session).register_player(tournament_id, 9103)
    assert registered is True
    await session.commit()

    callback = _FakeCallback(data=f"tourn:remove_player:{tournament_id}:{player.id}", user_id=admin_id)
    await tourn_remove_player(callback, session)

    assert any("\\_" in text for text in callback.message.sent), callback.message.sent
