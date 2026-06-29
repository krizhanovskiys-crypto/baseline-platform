"""My Matches and Match Details handlers."""
import logging
from datetime import date, timedelta

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.bot.handlers.helpers import get_player_lang
from aiogram.exceptions import TelegramAPIError

from backend.app.bot.keyboards.keyboards import (
    back_to_menu_keyboard,
    leave_match_done_keyboard,
    match_details_keyboard,
    my_match_card_keyboard,
)
from backend.app.bot.texts import t
from backend.app.database.models.game import GameStatus, MatchType
from backend.app.services.game_service import GameService
from backend.app.services.player_service import PlayerService

logger = logging.getLogger(__name__)
router = Router(name="my_matches")

_TRIGGER_TEXTS = {"📋 My Matches", "📋 Мої матчі", "📋 Мои матчи"}

_STATUS_KEYS: dict[GameStatus, str] = {
    GameStatus.OPEN: "status_open",
    GameStatus.PARTIALLY_FILLED: "status_partially_filled",
    GameStatus.FULL: "status_full",
    GameStatus.CONFIRMED: "status_confirmed",
}

_STATUS_BADGE_KEYS: dict[GameStatus, str] = {
    GameStatus.OPEN: "status_badge_open",
    GameStatus.PARTIALLY_FILLED: "status_badge_partially_filled",
    GameStatus.FULL: "status_badge_full",
    GameStatus.CONFIRMED: "status_badge_confirmed",
    GameStatus.CANCELLED: "status_badge_cancelled",
    GameStatus.EXPIRED: "status_badge_expired",
}


def _status_label(status: GameStatus, lang: str) -> str:
    return t(_STATUS_KEYS.get(status, "error_generic"), lang)


def _status_badge(status: GameStatus, lang: str) -> str:
    return t(_STATUS_BADGE_KEYS.get(status, "error_generic"), lang)


def _slots_line(free_slots: int, lang: str) -> str:
    if free_slots == 1:
        return t("match_details_1_player_needed", lang)
    if free_slots > 1:
        return t("match_details_players_needed", lang, n=free_slots)
    return ""


def _date_label(match_date: date, lang: str) -> str:
    today = date.today()
    if match_date == today:
        return t("om_btn_today", lang)
    if match_date == today + timedelta(days=1):
        return t("om_btn_tomorrow", lang)
    return f"{match_date.strftime('%B')} {match_date.day}"


async def _render_my_matches(
    message: Message, session: AsyncSession, telegram_id: int, lang: str
) -> None:
    """Fetch and send the upcoming matches list. Shared by message and back-callback paths."""
    matches = await GameService(session).get_my_upcoming_matches(telegram_id)

    if not matches:
        await message.answer(
            t("my_matches_empty", lang),
            reply_markup=back_to_menu_keyboard(lang),
            parse_mode="Markdown",
        )
        return

    await message.answer(t("my_matches_header", lang), parse_mode="Markdown")

    for game, committed_count in matches:
        match_type_key = (
            "om_match_type_singles"
            if game.match_type == MatchType.SINGLES
            else "om_match_type_doubles"
        )
        card = t(
            "my_matches_card",
            lang,
            match_type=t(match_type_key, lang),
            date=_date_label(game.date, lang),
            time=game.time.strftime("%H:%M"),
            court=game.court,
            players_joined=committed_count,
            players_total=game.required_players,
            status=_status_label(game.status, lang),
        )
        await message.answer(
            card,
            reply_markup=my_match_card_keyboard(lang, game.id),
            parse_mode="Markdown",
        )


# ── My Matches — message trigger ──────────────────────────────────────────────

@router.message(F.text.in_(_TRIGGER_TEXTS))
async def my_matches_handler(message: Message, session: AsyncSession) -> None:
    user = message.from_user
    if not user:
        return

    player = await PlayerService(session).get_by_telegram_id(user.id)
    lang = get_player_lang(player)

    if not player or not player.is_profile_complete:
        await message.answer(t("profile_not_complete_action", lang), parse_mode="Markdown")
        return

    await _render_my_matches(message, session, user.id, lang)


# ── Match Details — open card ─────────────────────────────────────────────────

@router.callback_query(F.data.regexp(r"^match:open:\d+$"))
async def match_open_handler(callback: CallbackQuery, session: AsyncSession) -> None:
    game_id = int(callback.data.split(":")[2])  # type: ignore[union-attr]
    user_tid = callback.from_user.id
    player = await PlayerService(session).get_by_telegram_id(user_tid)
    lang = get_player_lang(player)

    details = await GameService(session).get_match_details(game_id)
    if not details:
        await callback.answer(t("match_not_found", lang), show_alert=True)
        return

    # Role detection from MatchDetails DTO — no extra queries needed.
    is_organizer = any(p.is_organizer and p.telegram_id == user_tid for p in details.players)
    is_participant = any(p.telegram_id == user_tid for p in details.players)
    role = "organizer" if is_organizer else "participant" if is_participant else "other"

    match_type_key = (
        "om_match_type_singles"
        if details.game.match_type == MatchType.SINGLES
        else "om_match_type_doubles"
    )
    level_display = str(details.game.required_level) if details.game.required_level else "—"
    players_text = "\n".join(
        f"👑 {p.name}" if p.is_organizer else f"👤 {p.name}"
        for p in details.players
    ) or "—"
    free_slots = details.game.required_players - details.committed_count

    card = t(
        "match_details_card",
        lang,
        match_type=t(match_type_key, lang),
        date=_date_label(details.game.date, lang),
        time=details.game.time.strftime("%H:%M"),
        area=details.game.area,
        court=details.game.court,
        level=level_display,
        status=_status_badge(details.game.status, lang),
        organizer=details.organizer_name,
        count=details.committed_count,
        total=details.game.required_players,
        players=players_text,
        slots_line=_slots_line(free_slots, lang),
    )

    await callback.answer()
    await callback.message.answer(  # type: ignore[union-attr]
        card,
        reply_markup=match_details_keyboard(lang, role, game_id),
        parse_mode="Markdown",
    )


# ── Match Details — back to list ──────────────────────────────────────────────

@router.callback_query(F.data == "my_matches:back")
async def my_matches_back_handler(callback: CallbackQuery, session: AsyncSession) -> None:
    player = await PlayerService(session).get_by_telegram_id(callback.from_user.id)
    lang = get_player_lang(player)
    await callback.answer()
    await _render_my_matches(callback.message, session, callback.from_user.id, lang)  # type: ignore[arg-type]


# ── Match Details — cancel ────────────────────────────────────────────────────

@router.callback_query(F.data.regexp(r"^match:cancel:\d+$"))
async def match_cancel_handler(callback: CallbackQuery, session: AsyncSession) -> None:
    if not callback.data or not callback.message:
        return
    game_id = int(callback.data.split(":")[2])
    player = await PlayerService(session).get_by_telegram_id(callback.from_user.id)
    lang = get_player_lang(player)

    _, error_key = await GameService(session).cancel_match(game_id, callback.from_user.id)
    if error_key:
        await callback.answer(t(error_key, lang), show_alert=True)
        return

    await callback.answer()
    await callback.message.edit_text(t("cancel_match_done", lang), parse_mode="Markdown")


# ── Match Details — leave ─────────────────────────────────────────────────────

@router.callback_query(F.data.regexp(r"^match:leave:\d+$"))
async def match_leave_handler(callback: CallbackQuery, session: AsyncSession) -> None:
    if not callback.data or not callback.message:
        return
    game_id = int(callback.data.split(":")[2])
    user_tid = callback.from_user.id

    player = await PlayerService(session).get_by_telegram_id(user_tid)
    lang = get_player_lang(player)

    _, error_key = await GameService(session).leave_match(game_id, user_tid)
    if error_key:
        await callback.answer(t(error_key, lang), show_alert=True)
        return

    # Notify organizer (best-effort — delivery failure does not block the leave).
    game = await GameService(session).get_game(game_id)
    if game:
        organizer = await PlayerService(session).get_by_id(game.creator_id)
        if organizer and organizer.telegram_id != user_tid:
            organizer_lang = organizer.language or "en"
            leaver_name = player.first_name if player else "A player"
            try:
                await callback.bot.send_message(
                    organizer.telegram_id,
                    t("leave_match_notification", organizer_lang, name=leaver_name),
                )
            except TelegramAPIError:
                logger.warning("Could not notify organizer telegram_id=%s", organizer.telegram_id)

    await callback.answer()
    try:
        await callback.message.edit_text(
            t("leave_match_done", lang),
            reply_markup=leave_match_done_keyboard(lang),
            parse_mode="Markdown",
        )
    except TelegramAPIError:
        logger.warning("Could not edit leave confirmation for telegram_id=%s", user_tid)


# ── Match Details — join (placeholder) ───────────────────────────────────────

@router.callback_query(F.data.regexp(r"^match:join:\d+$"))
async def match_join_handler(callback: CallbackQuery, session: AsyncSession) -> None:
    player = await PlayerService(session).get_by_telegram_id(callback.from_user.id)
    lang = get_player_lang(player)
    await callback.answer(t("feature_not_yet", lang), show_alert=True)
