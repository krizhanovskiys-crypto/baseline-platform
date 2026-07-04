"""Tests for the Admin Center System module (Environment visibility)."""
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.bot.handlers.admin.system import dev_system
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


@pytest.mark.asyncio
async def test_dev_system_requires_an_active_session(session: AsyncSession) -> None:
    callback = _FakeCallback(user_id=111)
    await dev_system(callback, session)

    assert callback.message.sent == []
    callback.answer.assert_not_called()


@pytest.mark.asyncio
async def test_dev_system_shows_development_environment(session: AsyncSession) -> None:
    await _seed_and_login(session, 111)
    callback = _FakeCallback(user_id=111)

    with patch("backend.app.bot.handlers.admin.system.get_settings") as mock:
        mock.return_value.is_production = False
        await dev_system(callback, session)

    assert len(callback.message.sent) == 1
    text, _ = callback.message.sent[0]
    assert "Development" in text
    assert APP_VERSION in text
    callback.answer.assert_awaited_once()


@pytest.mark.asyncio
async def test_dev_system_shows_production_environment(session: AsyncSession) -> None:
    await _seed_and_login(session, 111)
    callback = _FakeCallback(user_id=111)

    with patch("backend.app.bot.handlers.admin.system.get_settings") as mock:
        mock.return_value.is_production = True
        await dev_system(callback, session)

    text, _ = callback.message.sent[0]
    assert "Production" in text
