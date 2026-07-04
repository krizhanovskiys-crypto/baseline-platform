"""Tests for AdminSessionService — PIN validation, 30-minute sessions,
failed-attempt lockout, and audit logging of every auth/session event.

Session/lockout state is process-global (module-level dicts — see the
service's docstring for why), so every test clears it first via the
autouse fixture below rather than relying on distinct telegram_ids alone.
"""
from datetime import timedelta
from unittest.mock import patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database.models.admin_audit_log import AdminAuditLog, AuditAction
from backend.app.database.models.operator_permission import OperatorRole
from backend.app.services import admin_session_service as svc_module
from backend.app.services.admin_session_service import AdminSessionService, LoginResult

TEST_PIN = "1234"


@pytest.fixture(autouse=True)
def _clear_process_global_state():
    svc_module._sessions.clear()
    svc_module._attempts.clear()
    yield
    svc_module._sessions.clear()
    svc_module._attempts.clear()


def _with_pin():
    return patch("backend.app.services.admin_session_service.get_settings")


async def _audit_actions(session: AsyncSession, telegram_id: int) -> list[str]:
    result = await session.execute(
        select(AdminAuditLog.action).where(AdminAuditLog.telegram_id == telegram_id)
    )
    return [row[0] for row in result.all()]


# ---------------------------------------------------------------------------
# Login / PIN validation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_correct_pin_creates_session_and_logs_login_success(session: AsyncSession) -> None:
    with _with_pin() as mock:
        mock.return_value.admin_pin = TEST_PIN
        svc = AdminSessionService(session)
        result = await svc.attempt_login(111, OperatorRole.ADMIN, TEST_PIN)
        await session.commit()

        assert result is LoginResult.SUCCESS
        assert await svc.validate_session(111) == OperatorRole.ADMIN
        assert await _audit_actions(session, 111) == [AuditAction.LOGIN_SUCCESS.value]


@pytest.mark.asyncio
async def test_wrong_pin_does_not_create_a_session(session: AsyncSession) -> None:
    with _with_pin() as mock:
        mock.return_value.admin_pin = TEST_PIN
        svc = AdminSessionService(session)
        result = await svc.attempt_login(111, OperatorRole.ADMIN, "0000")
        await session.commit()

        assert result is LoginResult.WRONG_PIN
        assert await svc.validate_session(111) is None
        assert await _audit_actions(session, 111) == [AuditAction.FAILED_PIN.value]


@pytest.mark.asyncio
async def test_empty_configured_pin_never_matches_empty_submission(session: AsyncSession) -> None:
    """A blank ADMIN_PIN must never be treated as 'no PIN required'."""
    with _with_pin() as mock:
        mock.return_value.admin_pin = ""
        svc = AdminSessionService(session)
        result = await svc.attempt_login(111, OperatorRole.ADMIN, "")
        await session.commit()

        assert result is LoginResult.WRONG_PIN
        assert await svc.validate_session(111) is None


# ---------------------------------------------------------------------------
# Failed-attempt lockout
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_third_consecutive_failure_locks_out_for_ten_minutes(session: AsyncSession) -> None:
    with _with_pin() as mock:
        mock.return_value.admin_pin = TEST_PIN
        svc = AdminSessionService(session)

        assert await svc.attempt_login(111, OperatorRole.ADMIN, "wrong") is LoginResult.WRONG_PIN
        assert await svc.attempt_login(111, OperatorRole.ADMIN, "wrong") is LoginResult.WRONG_PIN
        result = await svc.attempt_login(111, OperatorRole.ADMIN, "wrong")
        await session.commit()

        assert result is LoginResult.LOCKED_OUT
        remaining = await svc.is_locked_out(111)
        assert remaining is not None
        assert timedelta(minutes=9) < remaining <= timedelta(minutes=10)
        # Every failed attempt is logged, plus the lock activation itself.
        assert await _audit_actions(session, 111) == [
            AuditAction.FAILED_PIN.value,
            AuditAction.FAILED_PIN.value,
            AuditAction.FAILED_PIN.value,
            AuditAction.LOCK_ACTIVATED.value,
        ]


@pytest.mark.asyncio
async def test_locked_out_rejects_even_the_correct_pin(session: AsyncSession) -> None:
    with _with_pin() as mock:
        mock.return_value.admin_pin = TEST_PIN
        svc = AdminSessionService(session)
        for _ in range(3):
            await svc.attempt_login(111, OperatorRole.ADMIN, "wrong")

        result = await svc.attempt_login(111, OperatorRole.ADMIN, TEST_PIN)
        await session.commit()

        assert result is LoginResult.LOCKED_OUT
        assert await svc.validate_session(111) is None


@pytest.mark.asyncio
async def test_successful_login_resets_failed_attempt_counter(session: AsyncSession) -> None:
    with _with_pin() as mock:
        mock.return_value.admin_pin = TEST_PIN
        svc = AdminSessionService(session)
        await svc.attempt_login(111, OperatorRole.ADMIN, "wrong")
        await svc.attempt_login(111, OperatorRole.ADMIN, TEST_PIN)
        await session.commit()

        # Two more wrong attempts after a reset must not trigger a lockout yet.
        assert await svc.attempt_login(111, OperatorRole.ADMIN, "wrong") is LoginResult.WRONG_PIN
        assert await svc.attempt_login(111, OperatorRole.ADMIN, "wrong") is LoginResult.WRONG_PIN
        assert await svc.is_locked_out(111) is None


@pytest.mark.asyncio
async def test_lockout_is_scoped_per_telegram_id(session: AsyncSession) -> None:
    with _with_pin() as mock:
        mock.return_value.admin_pin = TEST_PIN
        svc = AdminSessionService(session)
        for _ in range(3):
            await svc.attempt_login(111, OperatorRole.ADMIN, "wrong")

        # A different operator is unaffected by 111's lockout.
        assert await svc.is_locked_out(222) is None
        assert await svc.attempt_login(222, OperatorRole.ADMIN, TEST_PIN) is LoginResult.SUCCESS


# ---------------------------------------------------------------------------
# Session expiry and logout
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_session_expires_lazily_and_logs_timeout(session: AsyncSession) -> None:
    svc = AdminSessionService(session)
    await svc.create_session(111, OperatorRole.ADMIN)

    # Force the session into the past instead of sleeping 30 minutes.
    svc_module._sessions[111].expires_at -= timedelta(minutes=31)

    role = await svc.validate_session(111)
    await session.commit()

    assert role is None
    assert await _audit_actions(session, 111) == [AuditAction.SESSION_TIMEOUT.value]


@pytest.mark.asyncio
async def test_valid_session_is_not_expired_early(session: AsyncSession) -> None:
    svc = AdminSessionService(session)
    await svc.create_session(111, OperatorRole.MODERATOR)

    assert await svc.validate_session(111) == OperatorRole.MODERATOR


@pytest.mark.asyncio
async def test_logout_destroys_session_immediately_and_logs_logout(session: AsyncSession) -> None:
    svc = AdminSessionService(session)
    await svc.create_session(111, OperatorRole.OWNER)

    await svc.logout(111)
    await session.commit()

    assert await svc.validate_session(111) is None
    assert await _audit_actions(session, 111) == [AuditAction.LOGOUT.value]


@pytest.mark.asyncio
async def test_logout_with_no_active_session_is_a_silent_no_op(session: AsyncSession) -> None:
    svc = AdminSessionService(session)
    await svc.logout(999)
    await session.commit()

    assert await _audit_actions(session, 999) == []
