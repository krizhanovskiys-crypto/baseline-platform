"""Admin Center session lifecycle: PIN validation, 30-minute sessions,
failed-attempt lockout, and audit logging of every auth/session event.

Session and lockout state is intentionally process-global, in-memory
state — module-level dicts, not instance attributes — because a service
instance is created fresh per request (matching every other service in
this codebase), but a session must survive between one request and the
next. This mirrors aiogram's own FSM `MemoryStorage`: an accepted,
existing trade-off in this codebase, not a new one. If Baseline ever runs
more than one bot process, this must move to a shared store (e.g. Redis)
— flagged here, not solved here.

Deliberately separate from PermissionService: this is authentication/
session-lifecycle, not role authorization. PermissionService answers
"what role does this person have"; this service answers "are they
currently logged into Admin Center."
"""
import enum
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import get_settings
from backend.app.database.models.admin_audit_log import AuditAction
from backend.app.database.models.operator_permission import OperatorRole
from backend.app.database.repositories.admin_audit_log_repository import AdminAuditLogRepository

SESSION_DURATION = timedelta(minutes=30)
LOCKOUT_DURATION = timedelta(minutes=10)
MAX_FAILED_ATTEMPTS = 3


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class _Session:
    role: OperatorRole
    expires_at: datetime


@dataclass
class _AttemptState:
    failed_count: int = 0
    locked_until: datetime | None = None


# Process-global — see module docstring.
_sessions: dict[int, _Session] = {}
_attempts: dict[int, _AttemptState] = {}


class LoginResult(str, enum.Enum):
    SUCCESS = "success"
    WRONG_PIN = "wrong_pin"
    LOCKED_OUT = "locked_out"


class AdminSessionService:
    """Owns the Admin Center session/PIN lifecycle. Never bypassed by a
    handler talking to the in-memory stores directly."""

    def __init__(self, session: AsyncSession) -> None:
        self._audit_repo = AdminAuditLogRepository(session)

    async def is_locked_out(self, telegram_id: int) -> timedelta | None:
        """Return remaining lockout time if locked, else None."""
        state = _attempts.get(telegram_id)
        if state and state.locked_until and state.locked_until > _now():
            return state.locked_until - _now()
        return None

    async def attempt_login(
        self, telegram_id: int, role: OperatorRole, submitted_pin: str
    ) -> LoginResult:
        """Validate a submitted PIN, tracking consecutive failures and
        locking out after MAX_FAILED_ATTEMPTS. Never compares against an
        unset/empty ADMIN_PIN — a blank submission must never "match" a
        missing configuration."""
        if await self.is_locked_out(telegram_id) is not None:
            return LoginResult.LOCKED_OUT

        configured_pin = get_settings().admin_pin
        if not configured_pin or submitted_pin != configured_pin:
            state = _attempts.setdefault(telegram_id, _AttemptState())
            state.failed_count += 1
            await self._audit(telegram_id, AuditAction.FAILED_PIN)
            if state.failed_count >= MAX_FAILED_ATTEMPTS:
                state.locked_until = _now() + LOCKOUT_DURATION
                state.failed_count = 0
                await self._audit(telegram_id, AuditAction.LOCK_ACTIVATED)
                return LoginResult.LOCKED_OUT
            return LoginResult.WRONG_PIN

        _attempts.pop(telegram_id, None)
        await self.create_session(telegram_id, role)
        await self._audit(telegram_id, AuditAction.LOGIN_SUCCESS)
        return LoginResult.SUCCESS

    async def create_session(self, telegram_id: int, role: OperatorRole) -> None:
        _sessions[telegram_id] = _Session(role=role, expires_at=_now() + SESSION_DURATION)

    async def validate_session(self, telegram_id: int) -> OperatorRole | None:
        """Return the active role if a valid, non-expired session exists.
        Expires it lazily (checked on read, no background job — the same
        pattern MatchLifecycleService.expire_if_stale() already uses)."""
        existing = _sessions.get(telegram_id)
        if existing is None:
            return None
        if existing.expires_at <= _now():
            await self.expire_session(telegram_id, reason=AuditAction.SESSION_TIMEOUT)
            return None
        return existing.role

    async def expire_session(
        self, telegram_id: int, reason: AuditAction = AuditAction.SESSION_TIMEOUT
    ) -> None:
        """Remove a session, if one exists, and audit why."""
        if _sessions.pop(telegram_id, None) is not None:
            await self._audit(telegram_id, reason)

    async def logout(self, telegram_id: int) -> None:
        """/exit_admin — immediately destroys the current session."""
        await self.expire_session(telegram_id, reason=AuditAction.LOGOUT)

    async def _audit(self, telegram_id: int, action: AuditAction) -> None:
        await self._audit_repo.log(telegram_id, action.value)
