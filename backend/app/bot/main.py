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

from backend.app.bot.handlers import available_now, dev, find_partner, find_players_for_match, organize_match, profile, start
from backend.app.bot.middlewares.database import DatabaseMiddleware
from backend.app.core.config import get_settings
from backend.app.core.logging import setup_logging
from backend.app.database.session import create_all_tables

logger = logging.getLogger(__name__)


def build_dispatcher() -> Dispatcher:
    """Construct and configure the Aiogram Dispatcher."""
    dp = Dispatcher(storage=MemoryStorage())

    # Register middleware on all updates
    dp.update.middleware(DatabaseMiddleware())

    # Register all routers
    dp.include_router(dev.router)
    dp.include_router(start.router)
    dp.include_router(profile.router)
    dp.include_router(find_partner.router)
    dp.include_router(organize_match.router)
    dp.include_router(find_players_for_match.router)
    dp.include_router(available_now.router)

    return dp


async def main() -> None:
    """Start the bot in long-polling mode."""
    setup_logging()
    settings = get_settings()

    if not settings.bot_token:
        raise RuntimeError("BOT_TOKEN is not set.  Copy .env.example to .env and fill it in.")

    # Ensure DB tables exist on startup
    await create_all_tables()

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN),
    )
    dp = build_dispatcher()

    logger.info("Starting Baseline bot...")
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    asyncio.run(main())
