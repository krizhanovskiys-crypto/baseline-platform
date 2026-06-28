"""Organize Match wizard handler — 6-step guided match creation."""
import logging
from datetime import date, datetime, time, timedelta

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.bot.handlers.helpers import get_player_lang, send_main_menu
from backend.app.bot.keyboards.keyboards import (
    om_confirm_keyboard,
    om_court_keyboard,
    om_date_keyboard,
    om_level_keyboard,
    om_players_keyboard,
    om_success_keyboard,
    om_time_keyboard,
    skill_level_keyboard,
)
from backend.app.bot.states.states import OrganizeMatchStates
from backend.app.bot.texts import t
from backend.app.database.models.game import MatchType
from backend.app.schemas.game import GameCreate
from backend.app.services.game_service import GameService
from backend.app.services.player_service import PlayerService

logger = logging.getLogger(__name__)
router = Router(name="organize_match")

_TRIGGER_TEXTS = {"🎾 Organize Match", "🎾 Організувати матч", "🎾 Организовать матч"}


# ── Step helpers ─────────────────────────────────────────────────────────────

async def _go_to_time(target: Message, state: FSMContext, lang: str) -> None:
    await state.set_state(OrganizeMatchStates.choose_time)
    await target.answer(t("om_choose_time", lang), reply_markup=om_time_keyboard(lang), parse_mode="Markdown")


async def _go_to_court(target: Message, state: FSMContext, lang: str, session: AsyncSession, user_id: int) -> None:
    await state.set_state(OrganizeMatchStates.choose_court)
    player = await PlayerService(session).get_by_telegram_id(user_id)
    courts = player.preferred_courts if player and player.preferred_courts else []
    await state.update_data(courts_shown=courts)
    await target.answer(t("om_choose_court", lang), reply_markup=om_court_keyboard(lang, courts), parse_mode="Markdown")


async def _go_to_level(target: Message, state: FSMContext, lang: str, session: AsyncSession, user_id: int) -> None:
    await state.set_state(OrganizeMatchStates.choose_level)
    player = await PlayerService(session).get_by_telegram_id(user_id)
    level = float(player.skill_level) if player and player.skill_level else 3.0
    await state.update_data(level=level)
    await target.answer(
        t("om_choose_level", lang, level=level),
        reply_markup=om_level_keyboard(lang, level),
        parse_mode="Markdown",
    )


async def _go_to_players(target: Message, state: FSMContext, lang: str) -> None:
    await state.set_state(OrganizeMatchStates.choose_players)
    await target.answer(t("om_choose_players", lang), reply_markup=om_players_keyboard(lang), parse_mode="Markdown")


async def _go_to_confirm(target: Message, state: FSMContext, lang: str) -> None:
    await state.set_state(OrganizeMatchStates.confirm)
    data = await state.get_data()
    players = int(data.get("players", 2))
    match_type_key = "om_match_type_singles" if players == 2 else "om_match_type_doubles"
    text = t(
        "om_confirm",
        lang,
        date_label=data.get("date_label", ""),
        time=data.get("time_str", ""),
        court=data.get("court", ""),
        level=data.get("level", ""),
        players=players,
        match_type=t(match_type_key, lang),
    )
    await target.answer(text, reply_markup=om_confirm_keyboard(lang), parse_mode="Markdown")


# ── Entry ────────────────────────────────────────────────────────────────────

@router.message(F.text.in_(_TRIGGER_TEXTS))
async def organize_match_start(message: Message, state: FSMContext, session: AsyncSession) -> None:
    user = message.from_user
    if not user:
        return
    player = await PlayerService(session).get_by_telegram_id(user.id)
    lang = get_player_lang(player)
    if not player or not player.is_profile_complete:
        await message.answer(t("profile_not_complete_action", lang), parse_mode="Markdown")
        return
    await state.set_state(OrganizeMatchStates.choose_date)
    await state.update_data(lang=lang)
    await message.answer(t("om_choose_date", lang), reply_markup=om_date_keyboard(lang), parse_mode="Markdown")


# ── Step 1: Date ──────────────────────────────────────────────────────────────

@router.callback_query(OrganizeMatchStates.choose_date, F.data == "om_date:today")
async def om_date_today(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data.get("lang", "en")
    today = date.today()
    await state.update_data(date_label=t("om_btn_today", lang), date_iso=today.isoformat())
    await _go_to_time(callback.message, state, lang)  # type: ignore[arg-type]
    await callback.answer()


@router.callback_query(OrganizeMatchStates.choose_date, F.data == "om_date:tomorrow")
async def om_date_tomorrow(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data.get("lang", "en")
    tomorrow = date.today() + timedelta(days=1)
    await state.update_data(date_label=t("om_btn_tomorrow", lang), date_iso=tomorrow.isoformat())
    await _go_to_time(callback.message, state, lang)  # type: ignore[arg-type]
    await callback.answer()


@router.callback_query(OrganizeMatchStates.choose_date, F.data == "om_date:other")
async def om_date_other(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data.get("lang", "en")
    await state.set_state(OrganizeMatchStates.enter_custom_date)
    await callback.message.answer(t("om_enter_date", lang), parse_mode="Markdown")  # type: ignore[union-attr]
    await callback.answer()


@router.message(OrganizeMatchStates.enter_custom_date)
async def om_custom_date(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data.get("lang", "en")
    text = (message.text or "").strip()
    try:
        parsed = datetime.strptime(text, "%d.%m.%Y").date()
    except ValueError:
        await message.answer(t("om_error_date", lang), parse_mode="Markdown")
        return
    await state.update_data(date_label=text, date_iso=parsed.isoformat())
    await _go_to_time(message, state, lang)


# ── Step 2: Time ──────────────────────────────────────────────────────────────

@router.callback_query(OrganizeMatchStates.choose_time, F.data == "om_time:other")
async def om_time_other(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data.get("lang", "en")
    await state.set_state(OrganizeMatchStates.enter_custom_time)
    await callback.message.answer(t("om_enter_time", lang), parse_mode="Markdown")  # type: ignore[union-attr]
    await callback.answer()


@router.callback_query(OrganizeMatchStates.choose_time, F.data.startswith("om_time:"))
async def om_time_preset(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    data = await state.get_data()
    lang = data.get("lang", "en")
    time_str = callback.data.split(":", 1)[1]  # type: ignore[union-attr]
    await state.update_data(time_str=time_str)
    await _go_to_court(callback.message, state, lang, session, callback.from_user.id)  # type: ignore[arg-type]
    await callback.answer()


@router.message(OrganizeMatchStates.enter_custom_time)
async def om_custom_time(message: Message, state: FSMContext, session: AsyncSession) -> None:
    data = await state.get_data()
    lang = data.get("lang", "en")
    text = (message.text or "").strip()
    try:
        datetime.strptime(text, "%H:%M")
    except ValueError:
        await message.answer(t("om_error_time", lang), parse_mode="Markdown")
        return
    await state.update_data(time_str=text)
    await _go_to_court(message, state, lang, session, message.from_user.id)  # type: ignore[union-attr]


# ── Step 3: Court ─────────────────────────────────────────────────────────────

@router.callback_query(OrganizeMatchStates.choose_court, F.data == "om:court_custom")
async def om_court_other(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data.get("lang", "en")
    await state.set_state(OrganizeMatchStates.enter_custom_court)
    await callback.message.answer(t("om_enter_court", lang), parse_mode="Markdown")  # type: ignore[union-attr]
    await callback.answer()


@router.callback_query(OrganizeMatchStates.choose_court, F.data.startswith("om_court:"))
async def om_court_preset(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    data = await state.get_data()
    lang = data.get("lang", "en")
    idx = int(callback.data.split(":")[1])  # type: ignore[union-attr]
    courts_shown: list[str] = data.get("courts_shown", [])
    if idx < 0 or idx >= len(courts_shown):
        await callback.answer()
        return
    await state.update_data(court=courts_shown[idx])
    await _go_to_level(callback.message, state, lang, session, callback.from_user.id)  # type: ignore[arg-type]
    await callback.answer()


@router.message(OrganizeMatchStates.enter_custom_court)
async def om_custom_court(message: Message, state: FSMContext, session: AsyncSession) -> None:
    data = await state.get_data()
    lang = data.get("lang", "en")
    court = (message.text or "").strip()
    if not court:
        return
    await state.update_data(court=court)
    await _go_to_level(message, state, lang, session, message.from_user.id)  # type: ignore[union-attr]


# ── Step 4: Level ─────────────────────────────────────────────────────────────

@router.callback_query(OrganizeMatchStates.choose_level, F.data == "om_level:use_mine")
async def om_level_use_mine(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data.get("lang", "en")
    await _go_to_players(callback.message, state, lang)  # type: ignore[arg-type]
    await callback.answer()


@router.callback_query(OrganizeMatchStates.choose_level, F.data == "om_level:change")
async def om_level_change(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data.get("lang", "en")
    await state.set_state(OrganizeMatchStates.enter_custom_level)
    await callback.message.answer(  # type: ignore[union-attr]
        t("choose_level", lang),
        reply_markup=skill_level_keyboard(lang),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(OrganizeMatchStates.enter_custom_level, F.data.startswith("level:"))
async def om_custom_level(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data.get("lang", "en")
    level = float(callback.data.split(":")[1])  # type: ignore[union-attr]
    await state.update_data(level=level)
    await _go_to_players(callback.message, state, lang)  # type: ignore[arg-type]
    await callback.answer()


# ── Step 5: Players ──────────────────────────────────────────────────────────

@router.callback_query(OrganizeMatchStates.choose_players, F.data.startswith("om_players:"))
async def om_players(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data.get("lang", "en")
    players = int(callback.data.split(":")[1])  # type: ignore[union-attr]
    await state.update_data(players=players)
    await _go_to_confirm(callback.message, state, lang)  # type: ignore[arg-type]
    await callback.answer()


# ── Step 6: Confirm ──────────────────────────────────────────────────────────

@router.callback_query(OrganizeMatchStates.confirm, F.data == "om:confirm")
async def om_do_confirm(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    data = await state.get_data()
    lang = data.get("lang", "en")
    user = callback.from_user
    if not user:
        await callback.answer()
        return

    player = await PlayerService(session).get_by_telegram_id(user.id)
    if not player:
        await callback.answer()
        return

    players = int(data.get("players", 2))
    match_type = MatchType.SINGLES if players == 2 else MatchType.DOUBLES

    try:
        match_date = date.fromisoformat(data["date_iso"])
        h, m = map(int, data["time_str"].split(":"))
        match_time = time(h, m)
    except (KeyError, ValueError):
        await callback.message.answer(t("error_generic", lang), parse_mode="Markdown")  # type: ignore[union-attr]
        await callback.answer()
        return

    game = await GameService(session).create_game(
        creator_telegram_id=user.id,
        data=GameCreate(
            court=data.get("court", ""),
            area=player.home_area or "Other",
            date=match_date,
            time=match_time,
            match_type=match_type,
            required_level=data.get("level"),
        ),
    )

    await state.clear()

    if not game:
        await callback.message.answer(t("error_generic", lang), parse_mode="Markdown")  # type: ignore[union-attr]
        await callback.answer()
        return

    match_type_key = "om_match_type_singles" if players == 2 else "om_match_type_doubles"
    text = t(
        "om_success",
        lang,
        date_label=data.get("date_label", ""),
        time=data.get("time_str", ""),
        court=data.get("court", ""),
        level=data.get("level", ""),
        players=players,
        match_type=t(match_type_key, lang),
    )
    await callback.message.answer(text, reply_markup=om_success_keyboard(lang, game.id), parse_mode="Markdown")  # type: ignore[union-attr]
    logger.info("Match created id=%s by telegram_id=%s", game.id, user.id)
    await callback.answer()


@router.callback_query(OrganizeMatchStates.confirm, F.data == "om:cancel")
async def om_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data.get("lang", "en")
    await state.clear()
    await callback.message.answer(t("cancelled", lang), parse_mode="Markdown")  # type: ignore[union-attr]
    await send_main_menu(callback.message, lang)  # type: ignore[arg-type]
    await callback.answer()


# ── Success screen callbacks ──────────────────────────────────────────────────

@router.callback_query(F.data == "om:my_matches")
async def om_my_matches(callback: CallbackQuery, session: AsyncSession) -> None:
    user_id = callback.from_user.id
    player = await PlayerService(session).get_by_telegram_id(user_id)
    lang = get_player_lang(player)

    matches = await GameService(session).get_my_matches(user_id)
    if not matches:
        await callback.message.answer(t("om_no_matches", lang), parse_mode="Markdown")  # type: ignore[union-attr]
        await callback.answer()
        return

    today = date.today()
    tomorrow = today + timedelta(days=1)

    lines = [t("om_my_matches_header", lang)]
    for match in matches:
        if match.date == today:
            date_label = t("om_btn_today", lang)
        elif match.date == tomorrow:
            date_label = t("om_btn_tomorrow", lang)
        else:
            date_label = match.date.strftime("%d.%m.%Y")
        players_total = 4 if match.match_type == MatchType.DOUBLES else 2
        lines.append(t(
            "om_match_item",
            lang,
            date_label=date_label,
            time=match.time.strftime("%H:%M"),
            court=match.court,
            players_joined=1,
            players_total=players_total,
        ))
    await callback.message.answer("\n\n".join(lines), parse_mode="Markdown")  # type: ignore[union-attr]
    await callback.answer()


@router.callback_query(F.data == "om:menu")
async def om_to_menu(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    await state.clear()
    player = await PlayerService(session).get_by_telegram_id(callback.from_user.id)
    lang = get_player_lang(player)
    await send_main_menu(callback.message, lang)  # type: ignore[arg-type]
    await callback.answer()
