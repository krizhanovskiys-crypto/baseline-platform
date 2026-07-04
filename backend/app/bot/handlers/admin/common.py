"""Shared helpers for every Admin Center module — imported by auth.py,
testing.py, and every future module (players.py, matches.py, courts.py,
tournaments.py, coaches.py, system.py). Never re-implement these inline;
that's exactly the TECH-001 bug class (duplicated checks silently
drifting out of sync) applied to authorization instead of routing.
"""
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.bot.handlers.helpers import get_player_lang
from backend.app.database.models.operator_permission import OperatorRole
from backend.app.services.admin_session_service import AdminSessionService
from backend.app.services.player_service import PlayerService


async def lang_for(session: AsyncSession, telegram_id: int) -> str:
    """An operator may have no Player record at all, so this always
    falls back to "en" rather than erroring."""
    player = await PlayerService(session).get_by_telegram_id(telegram_id)
    return get_player_lang(player)


async def authorized_role(session: AsyncSession, telegram_id: int) -> OperatorRole | None:
    """Shared guard for every Admin Center action: requires an active
    session, not just an operator role — the PIN gate is not optional
    for any Admin Center module."""
    return await AdminSessionService(session).validate_session(telegram_id)
