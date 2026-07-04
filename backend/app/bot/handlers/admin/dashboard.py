"""Admin Center Dashboard — the permanent root of Admin Center
(Sprint 11 Phase 2.2). Replaces the Testing menu as the screen an
operator lands on after PIN login.

Every stat is computed live via AdminDashboardService — no caching, no
hardcoded values. Matches/Tournaments/Coaches/Courts are placeholder
"Coming Soon" buttons until their own modules ship (Players shipped in
Phase 3.0 — its own callback is handled entirely in players.py, not
here); Testing and System are the existing modules, reached by calling
into them directly rather than duplicating their content here.
"""
from aiogram import F, Router
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.bot.handlers.admin.common import authorized_role, lang_for
from backend.app.bot.handlers.admin.testing import show_testing_menu
from backend.app.bot.handlers.helpers import send_main_menu
from backend.app.bot.keyboards.keyboards import dashboard_keyboard
from backend.app.bot.texts import t
from backend.app.core.config import get_settings
from backend.app.core.uptime import get_uptime_display
from backend.app.core.version import APP_VERSION
from backend.app.services.admin_dashboard_service import AdminDashboardService
from backend.app.services.admin_session_service import AdminSessionService

router = Router(name="admin_dashboard")

_COMING_SOON_CALLBACKS = {
    "dashboard:matches",
    "dashboard:tournaments",
    "dashboard:coaches",
    "dashboard:courts",
}


async def show_dashboard(message: Message, session: AsyncSession, lang: str) -> None:
    """The Admin Center root screen. Called after successful PIN login
    and whenever /dev is re-invoked with an already-valid session."""
    env_key = "admin_env_production" if get_settings().is_production else "admin_env_development"
    stats = await AdminDashboardService(session).get_stats()

    await message.answer(
        t(
            "admin_dashboard",
            lang,
            environment=t(env_key, lang),
            version=APP_VERSION,
            uptime=get_uptime_display(),
            **stats,
        ),
        reply_markup=dashboard_keyboard(lang),
        parse_mode="Markdown",
    )


@router.callback_query(F.data.in_(_COMING_SOON_CALLBACKS))
async def dashboard_coming_soon(callback: CallbackQuery, session: AsyncSession) -> None:
    if not callback.from_user or not await authorized_role(session, callback.from_user.id):
        return

    lang = await lang_for(session, callback.from_user.id)
    await callback.message.answer(t("dashboard_coming_soon", lang))  # type: ignore[union-attr]
    await callback.answer()


@router.callback_query(F.data == "dashboard:testing")
async def dashboard_open_testing(callback: CallbackQuery, session: AsyncSession) -> None:
    if not callback.from_user or not await authorized_role(session, callback.from_user.id):
        return

    lang = await lang_for(session, callback.from_user.id)
    await show_testing_menu(callback.message, lang)  # type: ignore[union-attr]
    await callback.answer()


@router.callback_query(F.data == "dashboard:exit")
async def dashboard_exit(callback: CallbackQuery, session: AsyncSession) -> None:
    if not callback.from_user or not await authorized_role(session, callback.from_user.id):
        return

    lang = await lang_for(session, callback.from_user.id)
    await AdminSessionService(session).logout(callback.from_user.id)
    await send_main_menu(callback.message, lang)  # type: ignore[union-attr]
    await callback.answer()
