"""Release Announcement middleware (Sprint 13.1) — the one place that
intercepts an update, ahead of any router, when a player has an
outdated last_seen_version. Runs after DatabaseMiddleware (needs
data["session"]) and before every router, so the announcement appears
"automatically on any normal interaction" without the user ever
needing to send /start.

The middleware only ever decides *whether* to intercept — the actual
comparison lives in ReleaseAnnouncementService.should_show_announcement,
not duplicated here. Once intercepted, it renders the first screen and
returns without calling the wrapped handler; the second screen and the
"mark seen, show Main Menu" logic live in
bot/handlers/release_announcement.py, reached like any other callback.
"""
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject, Update

from backend.app.bot.handlers.helpers import get_player_lang
from backend.app.bot.presenters.release_announcement import build_announcement_view
from backend.app.services.player_service import PlayerService
from backend.app.services.release_announcement_service import ReleaseAnnouncementService

_ANNOUNCEMENT_CALLBACK_PREFIX = "announce:"


def _unwrap(event: TelegramObject) -> Message | CallbackQuery | None:
    """Registered via dp.update.middleware(...), this middleware
    receives the outer Update object, not the inner Message/
    CallbackQuery directly — unlike a router-level middleware. Unwrap
    it once, here, rather than re-deriving this in every helper."""
    if isinstance(event, Update):
        return event.message or event.callback_query
    if isinstance(event, (Message, CallbackQuery)):
        return event
    return None


def _extract_telegram_id(event: TelegramObject) -> int | None:
    inner = _unwrap(event)
    if inner is not None and inner.from_user:
        return inner.from_user.id
    return None


def _is_announcement_callback(event: TelegramObject) -> bool:
    inner = _unwrap(event)
    return isinstance(inner, CallbackQuery) and bool(inner.data) and inner.data.startswith(_ANNOUNCEMENT_CALLBACK_PREFIX)


class ReleaseAnnouncementMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if _is_announcement_callback(event):
            return await handler(event, data)

        telegram_id = _extract_telegram_id(event)
        session = data.get("session")
        if telegram_id is None or session is None:
            return await handler(event, data)

        service = ReleaseAnnouncementService(session)
        if not await service.should_show_announcement(telegram_id):
            return await handler(event, data)

        release = service.get_current_release()
        if release is None:
            return await handler(event, data)

        player = await PlayerService(session).get_by_telegram_id(telegram_id)
        lang = get_player_lang(player)
        view = build_announcement_view(lang, release)

        inner = _unwrap(event)
        target = inner.message if isinstance(inner, CallbackQuery) else inner
        if target is not None:
            await target.answer(view.text, reply_markup=view.keyboard, parse_mode="Markdown")
        if isinstance(inner, CallbackQuery):
            await inner.answer()
        return None
