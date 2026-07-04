"""Tests for the Admin Center Dashboard handler (Sprint 11 Phase 2.2) —
the permanent root screen after PIN login."""
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.bot.handlers.admin.dashboard import (
    dashboard_coming_soon,
    dashboard_exit,
    dashboard_open_testing,
    show_dashboard,
)
from backend.app.core.version import APP_VERSION
from backend.app.database.models.operator_permission import OperatorPermission, OperatorRole
from backend.app.database.repositories.operator_permission_repository import (
    OperatorPermissionRepository,
)
from backend.app.services import admin_session_service as svc_module
from backend.app.services.admin_session_service import AdminSessionService


@pytest.fixture(autouse=True)
def _clear_process_global_state():
    svc_module._sessions.clear()
    svc_module._attempts.clear()
    yield
    svc_module._sessions.clear()
    svc_module._attempts.clear()


class _FakeMessage:
    def __init__(self) -> None:
        self.sent: list[tuple[str, object]] = []

    async def answer(self, text, reply_markup=None, parse_mode=None):
        self.sent.append((text, reply_markup))
        return self


class _FakeCallback:
    def __init__(self, user_id: int) -> None:
        self.from_user = SimpleNamespace(id=user_id)
        self.message = _FakeMessage()
        self.answer = AsyncMock()


async def _seed_and_login(session: AsyncSession, telegram_id: int) -> None:
    await OperatorPermissionRepository(session).add(
        OperatorPermission(telegram_id=telegram_id, role=OperatorRole.ADMIN)
    )
    await session.commit()
    await AdminSessionService(session).create_session(telegram_id, OperatorRole.ADMIN)


# ---------------------------------------------------------------------------
# show_dashboard() content
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_dashboard_shows_environment_version_and_stats(session: AsyncSession) -> None:
    message = _FakeMessage()
    await show_dashboard(message, session, "en")

    assert len(message.sent) == 1
    text, markup = message.sent[0]
    assert "Admin Center" in text
    assert "Environment" in text
    assert "Development" in text  # get_settings() defaults to non-production in tests
    assert APP_VERSION in text
    assert "Uptime" in text
    assert "Users: 0" in text
    assert "Active Matches: 0" in text
    assert "Available Now: 0" in text
    assert "Courts: 0" in text
    assert markup is not None


# ---------------------------------------------------------------------------
# Coming Soon placeholders
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_coming_soon_requires_an_active_session(session: AsyncSession) -> None:
    callback = _FakeCallback(user_id=111)
    callback.data = "dashboard:players"

    await dashboard_coming_soon(callback, session)

    assert callback.message.sent == []
    callback.answer.assert_not_called()


@pytest.mark.asyncio
async def test_coming_soon_shown_for_every_placeholder_button(session: AsyncSession) -> None:
    await _seed_and_login(session, 111)

    for target in ["players", "matches", "tournaments", "coaches", "courts"]:
        callback = _FakeCallback(user_id=111)
        callback.data = f"dashboard:{target}"

        await dashboard_coming_soon(callback, session)

        assert len(callback.message.sent) == 1
        text, _ = callback.message.sent[0]
        assert "Coming Soon" in text


# ---------------------------------------------------------------------------
# Testing routes to the existing Testing module
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_dashboard_testing_button_opens_testing_menu(session: AsyncSession) -> None:
    await _seed_and_login(session, 111)
    callback = _FakeCallback(user_id=111)

    await dashboard_open_testing(callback, session)

    assert len(callback.message.sent) == 1
    text, markup = callback.message.sent[0]
    assert "Admin Center" in text  # dev_menu_header ("Admin Center") — Testing's own submenu
    assert markup is not None


# ---------------------------------------------------------------------------
# Exit terminates the session
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_dashboard_exit_terminates_the_session(session: AsyncSession) -> None:
    await _seed_and_login(session, 111)
    admin_sessions = AdminSessionService(session)
    callback = _FakeCallback(user_id=111)

    await dashboard_exit(callback, session)
    await session.commit()

    assert await admin_sessions.validate_session(111) is None
    assert len(callback.message.sent) == 1


@pytest.mark.asyncio
async def test_dashboard_exit_requires_an_active_session(session: AsyncSession) -> None:
    callback = _FakeCallback(user_id=999)
    await dashboard_exit(callback, session)

    assert callback.message.sent == []
    callback.answer.assert_not_called()
