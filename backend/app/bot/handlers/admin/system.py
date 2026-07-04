"""Admin Center — System tools. Environment + running version visibility
today (confirm what's actually deployed on this instance); Manage
Operators (grant/revoke Admin/Moderator) is a later phase, per
docs/ARCHITECTURE.md's Admin Center module layout.
"""
from aiogram import F, Router
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.bot.handlers.admin.common import authorized_role, lang_for
from backend.app.bot.texts import t
from backend.app.core.config import get_settings
from backend.app.core.version import APP_VERSION

router = Router(name="admin_system")


@router.callback_query(F.data == "dev:system")
async def dev_system(callback: CallbackQuery, session: AsyncSession) -> None:
    if not callback.from_user or not await authorized_role(session, callback.from_user.id):
        return

    lang = await lang_for(session, callback.from_user.id)
    env_key = "admin_env_production" if get_settings().is_production else "admin_env_development"
    await callback.message.answer(  # type: ignore[union-attr]
        t("admin_system_info", lang, environment=t(env_key, lang), version=APP_VERSION),
        parse_mode="Markdown",
    )
    await callback.answer()
