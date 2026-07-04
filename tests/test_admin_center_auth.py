"""Tests for the /dev and /exit_admin handler flow (Sprint 11 Phase 2.1).

Covers the access flow only: PermissionService gate, PIN prompt, wrong
PIN, lockout, session reuse, and /exit_admin. The underlying PIN/session/
lockout logic itself is covered in test_admin_session_service.py; here we
verify the handler wires it correctly and stays silent for non-operators.
"""
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from aiogram.fsm.storage.memory import MemoryStorage
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.bot.handlers.admin.auth import admin_enter_pin, cmd_dev, cmd_exit_admin
from backend.app.bot.handlers.admin.testing import dev_stats
from backend.app.bot.states.states import AdminAuthStates
from backend.app.database.models.operator_permission import OperatorPermission, OperatorRole
from backend.app.database.repositories.operator_permission_repository import (
    OperatorPermissionRepository,
)
from backend.app.services import admin_session_service as svc_module
from backend.app.services.admin_session_service import AdminSessionService
from backend.app.services.permission_service import PermissionService

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
    def __init__(self, text: str | None, user_id: int) -> None:
        self.text = text
        self.from_user = SimpleNamespace(id=user_id)
        self.sent: list[tuple[str, object]] = []

    async def answer(self, text, reply_markup=None, parse_mode=None):
        self.sent.append((text, reply_markup))
        return self


class _FakeCallback:
    def __init__(self, user_id: int) -> None:
        self.from_user = SimpleNamespace(id=user_id)
        self.message = _FakeMessage(None, user_id)
        self.answer = AsyncMock()


async def _seed_operator(session: AsyncSession, telegram_id: int, role: str = "admin") -> None:
    await OperatorPermissionRepository(session).add(
        OperatorPermission(telegram_id=telegram_id, role=OperatorRole(role))
    )
    await session.commit()


# ---------------------------------------------------------------------------
# Non-operator: /dev behaves exactly like an unknown command
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_dev_is_silent_for_unknown_telegram_id(session: AsyncSession) -> None:
    message = _FakeMessage("/dev", user_id=999)
    state = _make_state(999)

    await cmd_dev(message, session, state)

    assert message.sent == []
    assert await state.get_state() is None


@pytest.mark.asyncio
async def test_exit_admin_is_silent_for_unknown_telegram_id(session: AsyncSession) -> None:
    message = _FakeMessage("/exit_admin", user_id=999)
    await cmd_exit_admin(message, session)
    assert message.sent == []


# ---------------------------------------------------------------------------
# Operator: PIN prompt, wrong PIN, correct PIN
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_dev_prompts_for_pin_for_a_confirmed_operator(session: AsyncSession) -> None:
    await _seed_operator(session, 111)
    message = _FakeMessage("/dev", user_id=111)
    state = _make_state(111)

    await cmd_dev(message, session, state)

    assert len(message.sent) == 1
    assert await state.get_state() == AdminAuthStates.enter_pin


@pytest.mark.asyncio
async def test_wrong_pin_reprompts_without_starting_a_session(session: AsyncSession) -> None:
    await _seed_operator(session, 111)
    with _with_pin() as mock:
        mock.return_value.admin_pin = TEST_PIN
        state = _make_state(111)
        await state.set_state(AdminAuthStates.enter_pin)
        await state.update_data(operator_role="admin")

        message = _FakeMessage("0000", user_id=111)
        await admin_enter_pin(message, session, state)

        assert len(message.sent) == 1
        # Still waiting for a PIN — not cleared, not authorized.
        assert await state.get_state() == AdminAuthStates.enter_pin
        assert await PermissionService(session).is_operator(111) is True


@pytest.mark.asyncio
async def test_correct_pin_starts_session_and_shows_menu(session: AsyncSession) -> None:
    await _seed_operator(session, 111)
    with _with_pin() as mock:
        mock.return_value.admin_pin = TEST_PIN
        state = _make_state(111)
        await state.set_state(AdminAuthStates.enter_pin)
        await state.update_data(operator_role="admin")

        message = _FakeMessage(TEST_PIN, user_id=111)
        await admin_enter_pin(message, session, state)

        # One message confirming the session, one showing the menu.
        assert len(message.sent) == 2
        assert await state.get_state() is None
        assert svc_module._sessions[111] is not None


@pytest.mark.asyncio
async def test_re_invoking_dev_with_active_session_skips_pin(session: AsyncSession) -> None:
    await _seed_operator(session, 111)
    await AdminSessionService(session).create_session(111, OperatorRole.ADMIN)

    message = _FakeMessage("/dev", user_id=111)
    state = _make_state(111)
    await cmd_dev(message, session, state)

    # No PIN prompt — straight to an "already active" ack + the menu.
    assert len(message.sent) == 2
    assert await state.get_state() is None


# ---------------------------------------------------------------------------
# Lockout surfaced through /dev
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_dev_shows_lockout_message_without_prompting_for_pin(session: AsyncSession) -> None:
    await _seed_operator(session, 111)
    with _with_pin() as mock:
        mock.return_value.admin_pin = TEST_PIN
        admin_sessions = AdminSessionService(session)
        for _ in range(3):
            await admin_sessions.attempt_login(111, OperatorRole.ADMIN, "wrong")
        await session.commit()

        message = _FakeMessage("/dev", user_id=111)
        state = _make_state(111)
        await cmd_dev(message, session, state)

        assert len(message.sent) == 1
        assert await state.get_state() is None  # never prompted for a PIN


# ---------------------------------------------------------------------------
# Existing Testing tools require an active session, not just an operator role
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_dev_stats_callback_requires_an_active_session(session: AsyncSession) -> None:
    await _seed_operator(session, 111)
    callback = _FakeCallback(user_id=111)

    await dev_stats(callback, session)

    assert callback.message.sent == []
    callback.answer.assert_not_called()


@pytest.mark.asyncio
async def test_dev_stats_callback_works_with_an_active_session(session: AsyncSession) -> None:
    await _seed_operator(session, 111)
    await AdminSessionService(session).create_session(111, OperatorRole.ADMIN)
    callback = _FakeCallback(user_id=111)

    await dev_stats(callback, session)

    assert len(callback.message.sent) == 1
    callback.answer.assert_awaited_once()


# ---------------------------------------------------------------------------
# /exit_admin
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_exit_admin_ends_an_active_session(session: AsyncSession) -> None:
    await _seed_operator(session, 111)
    admin_sessions = AdminSessionService(session)
    await admin_sessions.create_session(111, OperatorRole.ADMIN)

    message = _FakeMessage("/exit_admin", user_id=111)
    await cmd_exit_admin(message, session)
    await session.commit()

    assert len(message.sent) == 1
    assert await admin_sessions.validate_session(111) is None
