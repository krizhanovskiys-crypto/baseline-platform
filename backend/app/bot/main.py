"""Telegram bot entrypoint.

Run with:
    python -m backend.app.bot.main
"""
import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from backend.app.bot.handlers import available_matches, available_now, confirm_match, find_partner, find_players_for_match, invitation, my_matches, organize_match, player_picker, profile, release_announcement, start, tournament
from backend.app.bot.handlers import admin
from backend.app.bot.middlewares.database import DatabaseMiddleware
from backend.app.bot.middlewares.release_announcement import ReleaseAnnouncementMiddleware
from backend.app.core.config import get_settings
from backend.app.core.logging import setup_logging
from backend.app.database.session import create_all_tables, get_session
from backend.app.services.permission_service import PermissionService

logger = logging.getLogger(__name__)


def build_dispatcher() -> Dispatcher:
    """Construct and configure the Aiogram Dispatcher."""
    dp = Dispatcher(storage=MemoryStorage())

    # Register middleware on all updates. Order matters:
    # ReleaseAnnouncementMiddleware needs data["session"], which
    # DatabaseMiddleware provides, so it must be registered second.
    dp.update.middleware(DatabaseMiddleware())
    dp.update.middleware(ReleaseAnnouncementMiddleware())

    # Register all routers. release_announcement.router is registered
    # first so its two callbacks are matched before any other router
    # that might otherwise claim "announce:*" (none does today, but
    # this keeps intent explicit).
    dp.include_router(release_announcement.router)
    dp.include_router(admin.router)
    dp.include_router(start.router)
    dp.include_router(profile.router)
    dp.include_router(find_partner.router)
    dp.include_router(organize_match.router)
    dp.include_router(find_players_for_match.router)
    dp.include_router(invitation.router)
    dp.include_router(confirm_match.router)
    dp.include_router(my_matches.router)
    dp.include_router(available_now.router)
    dp.include_router(available_matches.router)
    dp.include_router(tournament.router)
    dp.include_router(player_picker.router)

    return dp


async def main() -> None:
    """Start the bot in long-polling mode."""
    setup_logging()
    settings = get_settings()

    if not settings.bot_token:
        raise RuntimeError("BOT_TOKEN is not set.  Copy .env.example to .env and fill it in.")

    # Ensure DB tables exist on startup
    await create_all_tables()

    # Bootstrap Owner(s) from config — every grant after this happens in-app.
    if settings.owner_ids_list:
        async with get_session() as db_session:
            granted = await PermissionService(db_session).seed_owners(settings.owner_ids_list)
            if granted:
                logger.info("Admin Center: seeded %d Owner(s) from OWNER_IDS", granted)

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN),
    )
    dp = build_dispatcher()

    logger.info("Starting Baseline bot...")
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    asyncio.run(main())
