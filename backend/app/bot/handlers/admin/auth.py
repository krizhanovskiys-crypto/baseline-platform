"""Admin Center access flow — hidden /dev command (technical alias; all
user-facing text says "Admin Center").

Cross-cutting for every Admin Center module: PermissionService checked
first — an unknown Telegram ID gets no reply at all, exactly like an
unrecognized command (CLAUDE.md's existing "never add a fallback
handler" rule, not a new exception to it). A confirmed operator with no
active session is prompted for the Admin PIN; only a correct PIN opens
Admin Center. Session/PIN/lockout state and auth-event auditing all live
in AdminSessionService — this module never touches that state directly.

Every other Admin Center module (testing.py today; players.py,
matches.py, courts.py, tournaments.py, coaches.py, system.py as they
ship) imports `authorized_role`/`lang_for` from `admin/common.py` rather
than re-implementing the session check — see docs/ARCHITECTURE.md's
Admin Center module layout rule.
"""
import logging
import math

from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.bot.handlers.admin.common import lang_for
from backend.app.bot.handlers.admin.testing import show_admin_menu
from backend.app.bot.states.states import AdminAuthStates
from backend.app.bot.texts import t
from backend.app.database.models.operator_permission import OperatorRole
from backend.app.services.admin_session_service import AdminSessionService, LoginResult
from backend.app.services.permission_service import PermissionService

logger = logging.getLogger(__name__)
router = Router(name="admin_auth")


async def _lockout_minutes_remaining(admin_sessions: AdminSessionService, telegram_id: int) -> int | None:
    remaining = await admin_sessions.is_locked_out(telegram_id)
    if remaining is None:
        return None
    return max(1, math.ceil(remaining.total_seconds() / 60))


@router.message(Command("dev"))
async def cmd_dev(message: Message, session: AsyncSession, state: FSMContext) -> None:
    user = message.from_user
    if not user:
        return

    role = await PermissionService(session).get_role(user.id)
    if role is None:
        # Behave exactly as if /dev does not exist. No "Access denied".
        return

    admin_sessions = AdminSessionService(session)
    lang = await lang_for(session, user.id)

    lockout_minutes = await _lockout_minutes_remaining(admin_sessions, user.id)
    if lockout_minutes is not None:
        await message.answer(t("admin_locked_out", lang, minutes=lockout_minutes), parse_mode="Markdown")
        return

    if await admin_sessions.validate_session(user.id) is not None:
        await message.answer(t("admin_session_active", lang), parse_mode="Markdown")
        await show_admin_menu(message, lang)
        return

    await state.set_state(AdminAuthStates.enter_pin)
    await state.update_data(operator_role=role.value)
    await message.answer(t("admin_pin_prompt", lang), parse_mode="Markdown")


@router.message(AdminAuthStates.enter_pin)
async def admin_enter_pin(message: Message, session: AsyncSession, state: FSMContext) -> None:
    user = message.from_user
    if not user or not message.text:
        return

    data = await state.get_data()
    role = OperatorRole(data["operator_role"])
    lang = await lang_for(session, user.id)

    admin_sessions = AdminSessionService(session)
    result = await admin_sessions.attempt_login(user.id, role, message.text.strip())

    if result is LoginResult.SUCCESS:
        await state.clear()
        await message.answer(t("admin_session_started", lang), parse_mode="Markdown")
        await show_admin_menu(message, lang)
        logger.info("Admin Center session started for telegram_id=%s", user.id)
        return

    if result is LoginResult.LOCKED_OUT:
        await state.clear()
        lockout_minutes = await _lockout_minutes_remaining(admin_sessions, user.id)
        await message.answer(
            t("admin_locked_out", lang, minutes=lockout_minutes or 10), parse_mode="Markdown"
        )
        return

    # WRONG_PIN — stay in the same state and prompt again.
    await message.answer(t("admin_pin_wrong", lang), parse_mode="Markdown")


@router.message(Command("exit_admin"))
async def cmd_exit_admin(message: Message, session: AsyncSession) -> None:
    user = message.from_user
    if not user:
        return

    if not await PermissionService(session).is_operator(user.id):
        return

    await AdminSessionService(session).logout(user.id)
    lang = await lang_for(session, user.id)
    await message.answer(t("admin_session_ended", lang), parse_mode="Markdown")
    logger.info("Admin Center session ended for telegram_id=%s", user.id)
