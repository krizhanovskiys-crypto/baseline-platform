"""Confirm Match, Cancel Match, and View Roster handlers."""
import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.bot.handlers.helpers import get_player_lang
from backend.app.bot.keyboards.keyboards import confirm_note_keyboard, view_roster_keyboard
from backend.app.bot.states.states import ConfirmMatchStates
from backend.app.bot.texts import t
from backend.app.services.game_service import GameService
from backend.app.services.player_service import PlayerService

logger = logging.getLogger(__name__)
router = Router(name="confirm_match")

_NOTE_MAX_LEN = 200


# ── Confirm Match — start ─────────────────────────────────────────────────────

@router.callback_query(F.data.regexp(r"^confirm_match:\d+$"))
async def confirm_match_start(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
) -> None:
    """Ask the organizer for an optional note before confirming."""
    if not callback.data or not callback.message:
        return
    game_id = int(callback.data.split(":")[-1])
    user = callback.from_user

    player = await PlayerService(session).get_by_telegram_id(user.id)
    lang = get_player_lang(player)

    await state.set_state(ConfirmMatchStates.enter_note)
    await state.update_data(game_id=game_id)

    await callback.message.answer(
        t("confirm_ask_note", lang),
        reply_markup=confirm_note_keyboard(lang),
        parse_mode="Markdown",
    )
    await callback.answer()


# ── Confirm Match — skip note ─────────────────────────────────────────────────

@router.callback_query(F.data == "confirm_note:skip", ConfirmMatchStates.enter_note)
async def confirm_match_skip_note(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
) -> None:
    """Confirm the match without an organizer note."""
    if not callback.message:
        return
    data = await state.get_data()
    game_id = data.get("game_id")
    await state.clear()

    user = callback.from_user
    player = await PlayerService(session).get_by_telegram_id(user.id)
    lang = get_player_lang(player)

    await _execute_confirm(callback, session, game_id, user.id, lang, note=None)


# ── Confirm Match — with note ─────────────────────────────────────────────────

@router.message(ConfirmMatchStates.enter_note)
async def confirm_match_with_note(
    message: Message, state: FSMContext, session: AsyncSession
) -> None:
    """Accept the organizer note and confirm the match."""
    note = (message.text or "").strip()
    player = await PlayerService(session).get_by_telegram_id(message.from_user.id)
    lang = get_player_lang(player)

    if len(note) > _NOTE_MAX_LEN:
        await message.answer(t("confirm_note_too_long", lang, length=len(note)))
        return

    data = await state.get_data()
    game_id = data.get("game_id")
    await state.clear()

    await _execute_confirm(message, session, game_id, message.from_user.id, lang, note=note or None)


async def _execute_confirm(
    target: CallbackQuery | Message,
    session: AsyncSession,
    game_id: int,
    organizer_telegram_id: int,
    lang: str,
    note: str | None,
) -> None:
    """Core confirm logic — shared between skip and note-text paths."""
    game_svc = GameService(session)
    game, all_players, error = await game_svc.confirm_match(game_id, organizer_telegram_id)

    reply = target.message if isinstance(target, CallbackQuery) else target

    if error:
        await reply.answer(t(error, lang))
        if isinstance(target, CallbackQuery):
            await target.answer()
        return

    await reply.answer(t("confirm_match_done", lang))
    if isinstance(target, CallbackQuery):
        await target.answer()

    if not game or not all_players:
        return

    date_str = f"{game.date.strftime('%B')} {game.date.day}"
    time_str = game.time.strftime("%H:%M")
    player_names = "\n".join(f"• {p.first_name}" for p in all_players)

    for player in all_players:
        if player.telegram_id == organizer_telegram_id:
            continue
        player_lang = player.language or "en"
        msg = t(
            "confirmed_player_notification",
            player_lang,
            date=date_str,
            time=time_str,
            court=game.court,
            players=player_names,
        )
        if note:
            msg += t("confirmed_player_note_section", player_lang, note=note)
        try:
            bot = target.bot if isinstance(target, CallbackQuery) else target.bot
            await bot.send_message(player.telegram_id, msg, parse_mode="Markdown")
        except Exception:
            logger.warning("Could not notify player telegram_id=%s", player.telegram_id)


# ── Cancel Match ──────────────────────────────────────────────────────────────
# Cancel Match itself lives in my_matches.py (match:cancel: / match:cancel_confirm:)
# — one confirmation + notification flow shared by the Match Details screen and
# the game-full notification's Cancel button (see game_full_keyboard), not two
# independent implementations.


# ── View Roster ───────────────────────────────────────────────────────────────

@router.callback_query(F.data.regexp(r"^view_game:\d+$"))
async def view_roster(callback: CallbackQuery, session: AsyncSession) -> None:
    """Show the current committed roster for a game."""
    if not callback.data or not callback.message:
        return
    game_id = int(callback.data.split(":")[-1])

    player = await PlayerService(session).get_by_telegram_id(callback.from_user.id)
    lang = get_player_lang(player)

    game, players = await GameService(session).get_roster(game_id)

    if not game:
        await callback.answer(t("confirm_match_wrong_status", lang), show_alert=True)
        return

    date_str = f"{game.date.strftime('%B')} {game.date.day}"
    time_str = game.time.strftime("%H:%M")
    player_lines = "\n".join(f"• {p.first_name}" for p in players) or "—"

    msg = t("view_roster_header", lang, date=date_str, time=time_str, court=game.court) + player_lines

    # Returns to this specific match's Match Details, not just the main
    # menu (UX-24) — the user almost certainly navigated here from there.
    await callback.message.answer(msg, reply_markup=view_roster_keyboard(lang, game_id), parse_mode="Markdown")
    await callback.answer()
