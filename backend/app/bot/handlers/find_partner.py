"""Find Partner handler — Search Mode entry, Smart Filter, one-at-a-time browsing."""
import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.bot.handlers.available_matches import _edit_screen
from backend.app.bot.handlers.helpers import get_player_lang, send_main_menu
from backend.app.bot.keyboards.keyboards import (
    area_keyboard,
    courts_keyboard,
    level_tolerance_keyboard,
    partner_card_keyboard,
    search_mode_keyboard,
    smart_filter_keyboard,
)
from backend.app.bot.states.states import FindPartnerStates
from backend.app.bot.texts import t
from backend.app.schemas.player import PlayerRead
from backend.app.services.player_service import PlayerService

logger = logging.getLogger(__name__)
router = Router(name="find_partner")

_TRIGGER_TEXTS = {"🔍 Find Partner", "🔍 Знайти партнера", "🔍 Найти партнёра"}

# A tolerance large enough to cover the entire NTRP range (2.0-7.0), used to
# express "Any" level for Smart Filter without changing find_partners'
# signature or the matching algorithm itself.
_LEVEL_ANY_TOLERANCE = 99.0

_DEFAULT_SMART_FILTERS = {"area": "home", "courts": None, "level": "default"}


def _build_card(partner: PlayerRead, lang: str, total: int) -> tuple[str, object]:
    """Return (text, keyboard) for a partner card."""
    level_indicator = "🟢" if partner.level_source == "coach_verified" else "🔵"
    languages = " • ".join(partner.spoken_languages or []) or "—"

    courts_list = partner.preferred_courts or []
    if not courts_list:
        courts = "—"
    else:
        courts = " • ".join(courts_list[:2])
        remaining = len(courts_list) - 2
        if remaining > 0:
            courts += "\n" + t("partner_card_more_courts", lang, count=remaining)

    text = t(
        "partner_card_v2",
        lang,
        name=partner.first_name,
        level=partner.skill_level,
        level_indicator=level_indicator,
        languages=languages,
        courts=courts,
        matches=partner.matches_played,
    )
    keyboard = partner_card_keyboard(lang, partner.username, show_next=total > 1)
    return text, keyboard


async def _run_search_and_show_first_card(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    telegram_id: int,
    lang: str,
    *,
    area: str,
    skill_level: float,
    my_courts: list[str],
    level_tolerance: float = 0.5,
) -> None:
    """Run the existing find_partners search and show the first card.

    Identical to the pre-Sprint-7.2 entry-point behaviour; only the caller
    decides which area/skill_level/my_courts/level_tolerance to pass in —
    the search and pagination logic themselves are unchanged.
    """
    service = PlayerService(session)
    partners = await service.find_partners(
        telegram_id=telegram_id,
        area=area,
        skill_level=skill_level,
        my_courts=my_courts,
        level_tolerance=level_tolerance,
    )

    if not partners:
        await message.answer(t("no_partners_friendly", lang), parse_mode="Markdown")
        return

    partner_ids = [p.telegram_id for p in partners]
    await state.set_state(FindPartnerStates.browsing)
    await state.update_data(partner_ids=partner_ids, index=0, lang=lang)

    text, keyboard = _build_card(partners[0], lang, total=len(partners))
    await message.answer(text, reply_markup=keyboard, parse_mode="Markdown")


# ── Entry point — Search Mode screen ────────────────────────────────────────────

@router.message(F.text.in_(_TRIGGER_TEXTS))
async def find_partner(message: Message, session: AsyncSession) -> None:
    user = message.from_user
    if not user:
        return

    service = PlayerService(session)
    player = await service.get_by_telegram_id(user.id)
    lang = get_player_lang(player)

    if not player or not player.is_profile_complete:
        await message.answer(t("profile_not_complete_action", lang), parse_mode="Markdown")
        return

    await message.answer(
        t("fp_search_mode_header", lang), reply_markup=search_mode_keyboard(lang), parse_mode="Markdown"
    )


@router.callback_query(F.data == "fp:mode:all")
async def fp_mode_all(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    """All Players — the existing search, exactly as it behaved before this sprint."""
    if not callback.message:
        await callback.answer()
        return
    service = PlayerService(session)
    player = await service.get_by_telegram_id(callback.from_user.id)
    lang = get_player_lang(player)
    await callback.answer()
    if not player:
        return
    await _run_search_and_show_first_card(
        callback.message,
        state,
        session,
        callback.from_user.id,
        lang,
        area=player.home_area or "",
        skill_level=player.skill_level or 3.0,
        my_courts=player.preferred_courts or [],
    )


# ── Smart Filter ─────────────────────────────────────────────────────────────

def _resolve_smart_filters(filters: dict, player: PlayerRead) -> dict:
    """Fill in defaults for any keys missing from the stored filter dict."""
    resolved = dict(_DEFAULT_SMART_FILTERS)
    resolved.update(filters)
    if resolved["courts"] is None:
        resolved["courts"] = list(player.preferred_courts or [])
    return resolved


@router.callback_query(F.data == "fp:mode:smart")
async def fp_mode_smart(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    if not callback.message:
        await callback.answer()
        return
    player = await PlayerService(session).get_by_telegram_id(callback.from_user.id)
    lang = get_player_lang(player)
    await callback.answer()
    if not player:
        return
    filters = _resolve_smart_filters({}, player)
    await state.set_state(FindPartnerStates.smart_filter)
    await state.update_data(filters=filters)
    await callback.message.answer(
        t("smart_filter_header", lang),
        reply_markup=smart_filter_keyboard(lang, filters, player.home_area or ""),
        parse_mode="Markdown",
    )


async def _show_smart_filter_screen(message: Message, filters: dict, lang: str, home_area: str) -> None:
    await _edit_screen(message, t("smart_filter_header", lang), smart_filter_keyboard(lang, filters, home_area))


@router.callback_query(F.data == "fp:smartfilter:back")
async def fp_smartfilter_back(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    if not callback.message:
        await callback.answer()
        return
    player = await PlayerService(session).get_by_telegram_id(callback.from_user.id)
    lang = get_player_lang(player)
    data = await state.get_data()
    filters = data.get("filters", dict(_DEFAULT_SMART_FILTERS))
    await callback.answer()
    if not player:
        return
    await _show_smart_filter_screen(callback.message, filters, lang, player.home_area or "")


# ── Smart Filter — Area (reuses the existing Area selector) ────────────────────

@router.callback_query(F.data == "fp:smartfilter:open:area")
async def fp_smartfilter_open_area(callback: CallbackQuery, session: AsyncSession) -> None:
    if not callback.message:
        await callback.answer()
        return
    player = await PlayerService(session).get_by_telegram_id(callback.from_user.id)
    lang = get_player_lang(player)
    await callback.answer()
    await _edit_screen(
        callback.message,
        t("available_matches_choose_area", lang),
        area_keyboard(lang, "fp_smartfilter_area"),
    )


@router.callback_query(FindPartnerStates.smart_filter, F.data.startswith("fp_smartfilter_area:"))
async def fp_smartfilter_save_area(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    if not callback.data or not callback.message:
        await callback.answer()
        return
    area = callback.data.split(":", 1)[1]
    player = await PlayerService(session).get_by_telegram_id(callback.from_user.id)
    lang = get_player_lang(player)
    data = await state.get_data()
    filters = data.get("filters", dict(_DEFAULT_SMART_FILTERS))
    filters["area"] = area
    await state.update_data(filters=filters)
    await callback.answer()
    if not player:
        return
    await _show_smart_filter_screen(callback.message, filters, lang, player.home_area or "")


# ── Smart Filter — Favourite Courts (reuses the existing Courts selector;
#    temporary selection only, never written to the player's profile) ─────────

@router.callback_query(F.data == "fp:smartfilter:open:courts")
async def fp_smartfilter_open_courts(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    if not callback.message:
        await callback.answer()
        return
    player = await PlayerService(session).get_by_telegram_id(callback.from_user.id)
    lang = get_player_lang(player)
    data = await state.get_data()
    filters = _resolve_smart_filters(data.get("filters", {}), player) if player else dict(_DEFAULT_SMART_FILTERS)
    await state.update_data(filters=filters)
    await callback.answer()
    if not player:
        return
    await _edit_screen(callback.message, t("choose_courts", lang), courts_keyboard(lang, filters["courts"]))


@router.callback_query(FindPartnerStates.smart_filter, F.data.startswith("court_toggle:"))
async def fp_smartfilter_court_toggle(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    if not callback.data or not callback.message:
        await callback.answer()
        return
    court = callback.data.split(":", 1)[1]
    player = await PlayerService(session).get_by_telegram_id(callback.from_user.id)
    lang = get_player_lang(player)
    data = await state.get_data()
    filters = data.get("filters", dict(_DEFAULT_SMART_FILTERS))
    selected: list[str] = filters.get("courts") or []
    if court in selected:
        selected.remove(court)
    else:
        selected.append(court)
    filters["courts"] = selected
    await state.update_data(filters=filters)
    await callback.answer()
    await _edit_screen(callback.message, t("choose_courts", lang), courts_keyboard(lang, selected))


@router.callback_query(FindPartnerStates.smart_filter, F.data == "courts_done")
async def fp_smartfilter_courts_done(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    if not callback.message:
        await callback.answer()
        return
    player = await PlayerService(session).get_by_telegram_id(callback.from_user.id)
    lang = get_player_lang(player)
    data = await state.get_data()
    filters = data.get("filters", dict(_DEFAULT_SMART_FILTERS))
    await callback.answer()
    if not player:
        return
    await _show_smart_filter_screen(callback.message, filters, lang, player.home_area or "")


# ── Smart Filter — Level tolerance (±0.5 / ±1.0 / Any) ──────────────────────────

@router.callback_query(F.data == "fp:smartfilter:open:level")
async def fp_smartfilter_open_level(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    if not callback.message:
        await callback.answer()
        return
    player = await PlayerService(session).get_by_telegram_id(callback.from_user.id)
    lang = get_player_lang(player)
    data = await state.get_data()
    filters = data.get("filters", dict(_DEFAULT_SMART_FILTERS))
    await callback.answer()
    await _edit_screen(
        callback.message,
        t("available_matches_choose_level", lang),
        level_tolerance_keyboard(
            lang, filters.get("level", "default"), "fp_smartfilter_level", "fp:smartfilter:back"
        ),
    )


@router.callback_query(FindPartnerStates.smart_filter, F.data.startswith("fp_smartfilter_level:"))
async def fp_smartfilter_save_level(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    if not callback.data or not callback.message:
        await callback.answer()
        return
    value = callback.data.split(":", 1)[1]
    player = await PlayerService(session).get_by_telegram_id(callback.from_user.id)
    lang = get_player_lang(player)
    data = await state.get_data()
    filters = data.get("filters", dict(_DEFAULT_SMART_FILTERS))
    filters["level"] = value
    await state.update_data(filters=filters)
    await callback.answer()
    if not player:
        return
    await _show_smart_filter_screen(callback.message, filters, lang, player.home_area or "")


# ── Smart Filter — Find Players ─────────────────────────────────────────────────

@router.callback_query(F.data == "fp:smartfilter:apply")
async def fp_smartfilter_apply(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    if not callback.message:
        await callback.answer()
        return
    player = await PlayerService(session).get_by_telegram_id(callback.from_user.id)
    lang = get_player_lang(player)
    await callback.answer()
    if not player:
        return

    data = await state.get_data()
    filters = _resolve_smart_filters(data.get("filters", {}), player)
    area = player.home_area if filters["area"] == "home" else filters["area"]
    level_tolerance = {"default": 0.5, "1.0": 1.0, "any": _LEVEL_ANY_TOLERANCE}.get(filters["level"], 0.5)

    await _run_search_and_show_first_card(
        callback.message,
        state,
        session,
        callback.from_user.id,
        lang,
        area=area or "",
        skill_level=player.skill_level or 3.0,
        my_courts=filters["courts"],
        level_tolerance=level_tolerance,
    )


# ── Browsing (unchanged) ─────────────────────────────────────────────────────

@router.callback_query(FindPartnerStates.browsing, F.data == "fp:next")
async def fp_next(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    data = await state.get_data()
    partner_ids: list[int] = data["partner_ids"]
    index: int = (data["index"] + 1) % len(partner_ids)
    lang: str = data.get("lang", "en")
    await state.update_data(index=index)

    service = PlayerService(session)
    partner = await service.get_by_telegram_id(partner_ids[index])
    if not partner:
        await callback.answer()
        return

    text, keyboard = _build_card(partner, lang, total=len(partner_ids))
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")  # type: ignore[union-attr]
    await callback.answer()


@router.callback_query(F.data == "fp:menu")
async def fp_menu(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    await state.clear()
    service = PlayerService(session)
    player = await service.get_by_telegram_id(callback.from_user.id)
    lang = get_player_lang(player)
    await send_main_menu(callback.message, lang)  # type: ignore[union-attr]
    await callback.answer()


@router.callback_query(F.data == "fp:no_contact")
async def fp_no_contact(callback: CallbackQuery, session: AsyncSession) -> None:
    service = PlayerService(session)
    player = await service.get_by_telegram_id(callback.from_user.id)
    lang = get_player_lang(player)
    await callback.answer(t("no_contact_available", lang), show_alert=True)
