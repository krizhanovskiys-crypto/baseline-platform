"""Release Announcement handlers (Sprint 13.1) — the two callbacks the
announcement screens use. The middleware
(bot/middlewares/release_announcement.py) is what shows the first
screen automatically; this router only handles what happens once the
user presses a button on it.

"Continue" is the same callback_data from both screens (the first
screen's Continue and What's New's own Continue) — both do the exact
same thing, so there is one handler, not two.
"""
from aiogram import F, Router
from aiogram.types import CallbackQuery

from backend.app.bot.handlers.helpers import get_player_lang, send_main_menu
from backend.app.bot.presenters.release_announcement import build_whats_new_view
from backend.app.services.player_service import PlayerService
from backend.app.services.release_announcement_service import ReleaseAnnouncementService

router = Router(name="release_announcement")


@router.callback_query(F.data == "announce:whats_new")
async def announce_whats_new(callback: CallbackQuery, session) -> None:
    if not callback.from_user or not callback.message:
        await callback.answer()
        return

    service = ReleaseAnnouncementService(session)
    release = service.get_current_release()
    if release is None:
        await callback.answer()
        return

    player = await PlayerService(session).get_by_telegram_id(callback.from_user.id)
    lang = get_player_lang(player)
    view = build_whats_new_view(lang, release)
    await callback.message.answer(view.text, reply_markup=view.keyboard, parse_mode="Markdown")
    await callback.answer()


@router.callback_query(F.data == "announce:continue")
async def announce_continue(callback: CallbackQuery, session) -> None:
    if not callback.from_user or not callback.message:
        await callback.answer()
        return

    await ReleaseAnnouncementService(session).mark_seen(callback.from_user.id)

    player = await PlayerService(session).get_by_telegram_id(callback.from_user.id)
    lang = get_player_lang(player)
    await send_main_menu(callback.message, lang)
    await callback.answer()
