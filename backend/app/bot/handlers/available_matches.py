"""Available Matches handler — browse, filter, paginate, and join open matches."""
import logging
from datetime import date

from aiogram import F, Router
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.bot.handlers.helpers import get_player_lang
from backend.app.bot.handlers.my_matches import _date_label, _status_label
from backend.app.bot.keyboards.keyboards import (
    available_match_card_keyboard,
    available_matches_filter_category_keyboard,
    available_matches_filters_keyboard,
    available_matches_nav_keyboard,
    leave_match_done_keyboard,
)
from backend.app.bot.states.states import AvailableMatchesStates
from backend.app.bot.texts import t
from backend.app.database.models.game import MatchType
from backend.app.services.game_service import GameService
from backend.app.services.player_service import PlayerService

logger = logging.getLogger(__name__)
router = Router(name="available_matches")

_TRIGGER_TEXTS = {"🎾 Available Matches", "🎾 Доступні матчі", "🎾 Доступные матчи"}
_PAGE_SIZE = 5
_DEFAULT_FILTERS = {"area": "home", "date": "today", "match_type": None, "level": "default"}
_CATEGORY_TITLE_KEYS = {
    "area": "available_matches_choose_area",
    "date": "available_matches_choose_date",
    "level": "available_matches_choose_level",
    "type": "available_matches_choose_match_type",
}


def _match_type_key(match_type: MatchType) -> str:
    return "om_match_type_singles" if match_type == MatchType.SINGLES else "om_match_type_doubles"


async def _resolve_filters(filters: dict, player) -> tuple[str | None, date | None, MatchType | None, bool]:
    """Translate the stored filter selections into query parameters."""
    area_value = filters.get("area", "home")
    if area_value == "any":
        area = None
    elif area_value == "home":
        area = player.home_area
    else:
        area = area_value

    on_date = date.today() if filters.get("date", "today") == "today" else None
    match_type = MatchType(filters["match_type"]) if filters.get("match_type") else None
    apply_level_filter = filters.get("level", "default") != "any"
    return area, on_date, match_type, apply_level_filter


async def _render_available_matches(
    message: Message, session: AsyncSession, state: FSMContext, telegram_id: int, lang: str, page: int
) -> None:
    """Fetch and send one page of Available Matches. Shared by entry, filter-apply, and pagination paths."""
    player = await PlayerService(session).get_by_telegram_id(telegram_id)
    if not player:
        return

    data = await state.get_data()
    filters = data.get("filters", dict(_DEFAULT_FILTERS))
    area, on_date, match_type, apply_level_filter = await _resolve_filters(filters, player)

    async def _fetch(requested_page: int) -> tuple[list, int]:
        return await GameService(session).get_available_matches(
            telegram_id,
            area=area,
            on_date=on_date,
            match_type=match_type,
            apply_level_filter=apply_level_filter,
            page=requested_page,
            page_size=_PAGE_SIZE,
        )

    matches, total = await _fetch(page)
    last_page = (total + _PAGE_SIZE - 1) // _PAGE_SIZE  # 0 when there are no matches at all

    # Never leave the player on an invalid page (e.g. the page emptied out
    # because a match was joined/filled/expired since it was last rendered).
    if last_page == 0:
        page = 1
    elif page > last_page:
        page = last_page
        matches, total = await _fetch(page)  # land on the nearest valid page with real matches

    await state.set_state(AvailableMatchesStates.browsing)
    await state.update_data(filters=filters, current_page=page)

    await message.answer(t("available_matches_header", lang, count=total), parse_mode="Markdown")

    if not matches:
        await message.answer(t("available_matches_empty", lang), parse_mode="Markdown")
        return

    for game, committed_count in matches:
        level_display = game.required_level if game.required_level is not None else "—"
        card = t(
            "available_matches_card",
            lang,
            match_type=t(_match_type_key(game.match_type), lang),
            level=level_display,
            date=_date_label(game.date, lang),
            time=game.time.strftime("%H:%M"),
            area=game.area,
            court=game.court,
            players_joined=committed_count,
            players_total=game.required_players,
            status=_status_label(game.status, lang),
        )
        await message.answer(
            card, reply_markup=available_match_card_keyboard(lang, game.id), parse_mode="Markdown"
        )

    total_pages = max(1, last_page)
    await message.answer(
        t("available_matches_page_indicator", lang, page=page, total_pages=total_pages),
        reply_markup=available_matches_nav_keyboard(
            lang, page, has_prev=page > 1, has_next=page < total_pages
        ),
    )


# ── Entry point ────────────────────────────────────────────────────────────────

@router.message(F.text.in_(_TRIGGER_TEXTS))
async def available_matches_handler(message: Message, state: FSMContext, session: AsyncSession) -> None:
    user = message.from_user
    if not user:
        return

    player = await PlayerService(session).get_by_telegram_id(user.id)
    lang = get_player_lang(player)

    if not player or not player.is_profile_complete:
        await message.answer(t("profile_not_complete_action", lang), parse_mode="Markdown")
        return

    await state.update_data(filters=dict(_DEFAULT_FILTERS))
    await _render_available_matches(message, session, state, user.id, lang, page=1)


@router.callback_query(F.data == "available:start")
async def available_start_callback(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    if not callback.message:
        await callback.answer()
        return
    player = await PlayerService(session).get_by_telegram_id(callback.from_user.id)
    lang = get_player_lang(player)
    await callback.answer()

    if not player or not player.is_profile_complete:
        await callback.message.answer(t("profile_not_complete_action", lang), parse_mode="Markdown")
        return

    await _render_available_matches(callback.message, session, state, callback.from_user.id, lang, page=1)


# ── Pagination ───────────────────────────────────────────────────────────────

@router.callback_query(AvailableMatchesStates.browsing, F.data.regexp(r"^available:page:\d+$"))
async def available_page_callback(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    if not callback.data or not callback.message:
        await callback.answer()
        return
    page = int(callback.data.split(":")[2])
    player = await PlayerService(session).get_by_telegram_id(callback.from_user.id)
    lang = get_player_lang(player)
    await callback.answer()
    await _render_available_matches(callback.message, session, state, callback.from_user.id, lang, page=page)


# ── Filters ──────────────────────────────────────────────────────────────────

async def _edit_screen(message: Message, text: str, keyboard) -> None:
    """Edit a message's text+keyboard in place, tolerating Telegram's
    'message is not modified' error when the destination content is identical
    to what's already shown (e.g. re-selecting the active option)."""
    try:
        await message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    except TelegramBadRequest as exc:
        if "message is not modified" not in str(exc):
            raise


async def _show_main_filters_screen(message: Message, filters: dict, lang: str, home_area: str) -> None:
    await _edit_screen(
        message,
        t("available_matches_filters_header", lang),
        available_matches_filters_keyboard(lang, filters, home_area),
    )


@router.callback_query(F.data == "available:filters")
async def available_filters_callback(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    """Entry point from the Available Matches nav bar — opens the main Filters
    screen as a new message (the nav bar message itself is left untouched)."""
    if not callback.message:
        await callback.answer()
        return
    data = await state.get_data()
    filters = data.get("filters", dict(_DEFAULT_FILTERS))
    player = await PlayerService(session).get_by_telegram_id(callback.from_user.id)
    lang = get_player_lang(player)
    home_area = player.home_area if player else ""
    await callback.answer()
    await callback.message.answer(
        t("available_matches_filters_header", lang),
        reply_markup=available_matches_filters_keyboard(lang, filters, home_area),
        parse_mode="Markdown",
    )


@router.callback_query(F.data.regexp(r"^available:filters:open:(area|date|level|type)$"))
async def available_filters_open_category_callback(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
) -> None:
    """Tapping a category row on the main Filters screen opens its dedicated
    single-category selection screen, editing the same message in place."""
    if not callback.data or not callback.message:
        await callback.answer()
        return
    dimension = callback.data.split(":")[3]

    data = await state.get_data()
    filters = data.get("filters", dict(_DEFAULT_FILTERS))
    player = await PlayerService(session).get_by_telegram_id(callback.from_user.id)
    lang = get_player_lang(player)
    home_area = player.home_area if player else ""
    await callback.answer()
    await _edit_screen(
        callback.message,
        t(_CATEGORY_TITLE_KEYS[dimension], lang),
        available_matches_filter_category_keyboard(lang, dimension, filters, home_area),
    )


@router.callback_query(F.data.regexp(r"^available:filter:(area|date|level|type):.+$"))
async def available_filter_set_callback(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    """Selecting an option on a category screen saves it and immediately
    returns to the main Filters screen, showing the updated current value."""
    if not callback.data or not callback.message:
        await callback.answer()
        return
    _, _, dimension, value = callback.data.split(":", 3)

    data = await state.get_data()
    filters = dict(data.get("filters", _DEFAULT_FILTERS))
    if dimension == "type":
        filters["match_type"] = None if value == "any" else value
    else:
        filters[dimension] = value
    await state.update_data(filters=filters)

    player = await PlayerService(session).get_by_telegram_id(callback.from_user.id)
    lang = get_player_lang(player)
    home_area = player.home_area if player else ""
    await callback.answer()
    await _show_main_filters_screen(callback.message, filters, lang, home_area)


@router.callback_query(F.data == "available:filters:back")
async def available_filters_back_callback(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    """Back button on a category screen — returns to the main Filters screen
    without changing any value."""
    if not callback.message:
        await callback.answer()
        return
    data = await state.get_data()
    filters = data.get("filters", dict(_DEFAULT_FILTERS))
    player = await PlayerService(session).get_by_telegram_id(callback.from_user.id)
    lang = get_player_lang(player)
    home_area = player.home_area if player else ""
    await callback.answer()
    await _show_main_filters_screen(callback.message, filters, lang, home_area)


@router.callback_query(F.data == "noop")
async def available_filters_noop_callback(callback: CallbackQuery) -> None:
    """Non-interactive divider button on the Filters screen — label only, no action."""
    await callback.answer()


@router.callback_query(F.data == "available:filters:apply")
async def available_filters_apply_callback(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    if not callback.message:
        await callback.answer()
        return
    player = await PlayerService(session).get_by_telegram_id(callback.from_user.id)
    lang = get_player_lang(player)
    await callback.answer()
    await _render_available_matches(callback.message, session, state, callback.from_user.id, lang, page=1)


# ── Join confirmation ────────────────────────────────────────────────────────

@router.callback_query(F.data.regexp(r"^available:confirm:\d+$"))
async def available_confirm_callback(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    if not callback.data or not callback.message:
        await callback.answer()
        return
    game_id = int(callback.data.split(":")[2])
    user_tid = callback.from_user.id

    player = await PlayerService(session).get_by_telegram_id(user_tid)
    lang = get_player_lang(player)

    game, error_key = await GameService(session).join_match(game_id, user_tid)
    if error_key:
        await callback.answer(t(error_key, lang), show_alert=True)
        return

    # Browsing is over — clear AvailableMatchesStates so no stale filters/page
    # carry into the next time the player opens Available Matches.
    await state.clear()

    # Notify organizer (best-effort — delivery failure does not block the join).
    if game:
        organizer = await PlayerService(session).get_by_id(game.creator_id)
        if organizer and organizer.telegram_id != user_tid:
            organizer_lang = organizer.language or "en"
            joiner_name = player.first_name if player else "A player"
            try:
                await callback.bot.send_message(
                    organizer.telegram_id,
                    t("join_match_notification", organizer_lang, name=joiner_name),
                )
            except TelegramAPIError:
                logger.warning("Could not notify organizer telegram_id=%s", organizer.telegram_id)

    await callback.answer()
    await callback.message.edit_text(
        t("join_success_text", lang),
        reply_markup=leave_match_done_keyboard(lang),
        parse_mode="Markdown",
    )
