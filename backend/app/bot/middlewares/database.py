"""Middleware that injects an AsyncSession into handler data for each update."""
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from backend.app.database.session import get_session


class DatabaseMiddleware(BaseMiddleware):
    """Provide a fresh AsyncSession per Telegram update.

    Handlers access the session via ``data["session"]``.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        async with get_session() as session:
            data["session"] = session
            return await handler(event, data)
