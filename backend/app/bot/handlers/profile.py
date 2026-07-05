"""Profile, Edit Profile, and Settings handlers."""
import logging

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.bot.handlers.available_matches import _edit_screen
from backend.app.bot.handlers.helpers import get_player_lang, send_main_menu
from backend.app.bot.keyboards.keyboards import (
    area_keyboard,
    courts_keyboard,
    edit_profile_keyboard,
    language_keyboard,
    profile_keyboard,
    settings_keyboard,
    skill_level_keyboard,
    spoken_languages_keyboard,
)
from backend.app.bot.presenters.player_card import build_player_card_text
from backend.app.bot.states.states import SettingsStates
from backend.app.bot.texts import t
from backend.app.schemas.player import PlayerRead, PlayerUpdate
from backend.app.services.player_service import PlayerService

logger = logging.getLogger(__name__)
router = Router(name="profile")


@router.message(F.text.in_(["👤 My Profile", "👤 Мій профіль", "👤 Мой профиль"]))
async def show_profile(message: Message, session: AsyncSession) -> None:
    user = message.from_user
    if not user:
        return
    service = PlayerService(session)
    player = await service.get_by_telegram_id(user.id)
    lang = get_player_lang(player)

    if not player or not player.is_profile_complete:
        # Reuses the same honest, correct message every other guarded screen
        # uses (UX-27) — the previous "profile_incomplete" text promised
        # onboarding would start automatically, but nothing actually
        # triggered it.
        await message.answer(t("profile_not_complete_action", lang), parse_mode="Markdown")
        return

    card = build_player_card_text(lang, player)
    await message.answer(
        t("profile_card_header", lang) + card,
        reply_markup=profile_keyboard(lang),
        parse_mode="Markdown",
    )


# ── Edit Profile ───────────────────────────────────────────────────────────────

async def _render_edit_profile(message: Message, player: PlayerRead, lang: str, *, edit: bool) -> None:
    """Show the main Edit Profile screen. `edit=True` updates the existing
    message in place (mirrors the Filters UX); `edit=False` sends a new one
    (used only for the initial entry from the read-only Profile card)."""
    if edit:
        await _edit_screen(message, t("edit_profile_header", lang), edit_profile_keyboard(lang, player))
    else:
        await message.answer(
            t("edit_profile_header", lang),
            reply_markup=edit_profile_keyboard(lang, player),
            parse_mode="Markdown",
        )


@router.callback_query(F.data == "profile:edit")
async def edit_profile(callback: CallbackQuery, session: AsyncSession) -> None:
    """Entry point from the read-only Profile card — opens Edit Profile as a
    new message (the Profile card itself is left untouched)."""
    if not callback.message:
        await callback.answer()
        return
    player = await PlayerService(session).get_by_telegram_id(callback.from_user.id)
    lang = get_player_lang(player)
    await callback.answer()
    if not player:
        return
    await _render_edit_profile(callback.message, player, lang, edit=False)


# ── Edit Profile — Name (free-text field; breaks the in-place edit chain,
#    consistent with every other free-text step in this codebase, e.g.
#    OrganizeMatchStates' enter_custom_* handlers) ──────────────────────────────

@router.callback_query(F.data == "editprofile:name")
async def edit_profile_name_start(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    if not callback.message:
        await callback.answer()
        return
    player = await PlayerService(session).get_by_telegram_id(callback.from_user.id)
    lang = get_player_lang(player)
    await state.set_state(SettingsStates.change_name)
    await callback.answer()
    await callback.message.answer(t("edit_profile_enter_name", lang), parse_mode="Markdown")


@router.message(SettingsStates.change_name)
async def edit_profile_name_save(message: Message, state: FSMContext, session: AsyncSession) -> None:
    user = message.from_user
    if not user:
        return
    service = PlayerService(session)
    player = await service.get_by_telegram_id(user.id)
    lang = get_player_lang(player)

    new_name = (message.text or "").strip()
    if not new_name:
        await message.answer(t("edit_profile_name_error", lang), parse_mode="Markdown")
        return

    await service.update_profile(user.id, PlayerUpdate(first_name=new_name))
    await state.clear()
    updated = await service.get_by_telegram_id(user.id)
    if not updated:
        return
    await _render_edit_profile(message, updated, lang, edit=False)


# ── Edit Profile — Level / Area / Courts (reuse the existing settings:*
#    callbacks and selectors — no duplicate handlers; only the post-save
#    destination changes, from Main Menu to Edit Profile) ──────────────────────

@router.callback_query(F.data == "settings:area")
async def settings_change_area(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    if not callback.message:
        await callback.answer()
        return
    player = await PlayerService(session).get_by_telegram_id(callback.from_user.id)
    lang = get_player_lang(player)
    await state.set_state(SettingsStates.change_area)
    await callback.answer()
    await _edit_screen(callback.message, t("choose_area", lang), area_keyboard(lang, "settings_area"))


@router.callback_query(SettingsStates.change_area, F.data.startswith("settings_area:"))
async def settings_save_area(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    if not callback.data or not callback.message:
        await callback.answer()
        return
    area = callback.data.split(":", 1)[1]
    user = callback.from_user
    service = PlayerService(session)
    await service.update_profile(user.id, PlayerUpdate(home_area=area))
    await state.clear()
    player = await service.get_by_telegram_id(user.id)
    lang = get_player_lang(player)
    await callback.answer()
    if not player:
        return
    await _render_edit_profile(callback.message, player, lang, edit=True)


@router.callback_query(F.data == "settings:level")
async def settings_change_level(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    if not callback.message:
        await callback.answer()
        return
    player = await PlayerService(session).get_by_telegram_id(callback.from_user.id)
    lang = get_player_lang(player)
    await state.set_state(SettingsStates.change_level)
    await callback.answer()
    await _edit_screen(callback.message, t("choose_level", lang), skill_level_keyboard(lang))


@router.callback_query(SettingsStates.change_level, F.data.startswith("level:"))
async def settings_save_level(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    if not callback.data or not callback.message:
        await callback.answer()
        return
    level = float(callback.data.split(":")[1])
    user = callback.from_user
    service = PlayerService(session)
    await service.update_profile(user.id, PlayerUpdate(skill_level=level))
    await state.clear()
    player = await service.get_by_telegram_id(user.id)
    lang = get_player_lang(player)
    await callback.answer()
    if not player:
        return
    await _render_edit_profile(callback.message, player, lang, edit=True)


@router.callback_query(F.data == "settings:courts")
async def settings_change_courts(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    """Courts are scoped to a Tennis Zone. The player's Home Area (set via
    the dedicated "Area" field) already tells us which zone — asking again
    here would be a redundant extra step, so Favourite Courts opens
    straight to that zone's court list. Changing Home Area via "Area"
    changes which zone's courts show here; there is no separate zone
    picker in this flow.

    Backward compatibility: a player without a saved home_area (shouldn't
    normally happen once onboarding is complete, but the field is nullable)
    falls back to the standalone Tennis Zone picker so they're never stuck
    with no way to browse courts.
    """
    if not callback.message:
        await callback.answer()
        return
    player = await PlayerService(session).get_by_telegram_id(callback.from_user.id)
    lang = get_player_lang(player)
    current = player.preferred_courts if player else []
    await callback.answer()
    if not player:
        return

    if player.home_area:
        zone = player.home_area
        await state.set_state(SettingsStates.change_courts)
        await state.update_data(selected_courts=current, lang=lang, courts_zone=zone)
        await _edit_screen(
            callback.message, t("choose_courts", lang, zone=zone), courts_keyboard(lang, zone, current)
        )
    else:
        await state.set_state(SettingsStates.choose_courts_zone)
        await state.update_data(selected_courts=current, lang=lang)
        await _edit_screen(callback.message, t("choose_area", lang), area_keyboard(lang, "settings_courts_zone"))


@router.callback_query(SettingsStates.choose_courts_zone, F.data.startswith("settings_courts_zone:"))
async def settings_choose_courts_zone(callback: CallbackQuery, state: FSMContext) -> None:
    if not callback.data or not callback.message:
        await callback.answer()
        return
    zone = callback.data.split(":", 1)[1]
    data = await state.get_data()
    lang = data.get("lang", "en")
    selected: list[str] = data.get("selected_courts", [])
    await state.update_data(courts_zone=zone)
    await state.set_state(SettingsStates.change_courts)
    await callback.answer()
    await _edit_screen(
        callback.message, t("choose_courts", lang, zone=zone), courts_keyboard(lang, zone, selected)
    )


@router.callback_query(SettingsStates.change_courts, F.data.startswith("court_toggle:"))
async def settings_court_toggle(callback: CallbackQuery, state: FSMContext) -> None:
    if not callback.data or not callback.message:
        await callback.answer()
        return
    court = callback.data.split(":", 1)[1]
    data = await state.get_data()
    lang = data.get("lang", "en")
    zone = data.get("courts_zone", "")
    selected: list[str] = data.get("selected_courts", [])
    if court in selected:
        selected.remove(court)
    else:
        selected.append(court)
    await state.update_data(selected_courts=selected)
    await callback.answer()
    try:
        await callback.message.edit_reply_markup(reply_markup=courts_keyboard(lang, zone, selected))
    except TelegramBadRequest as exc:
        if "message is not modified" not in str(exc):
            raise


@router.callback_query(SettingsStates.change_courts, F.data == "court_add_custom")
async def settings_court_add_custom(callback: CallbackQuery, state: FSMContext) -> None:
    if not callback.message:
        await callback.answer()
        return
    data = await state.get_data()
    lang = data.get("lang", "en")
    await state.set_state(SettingsStates.enter_custom_court)
    await callback.answer()
    await callback.message.answer(t("custom_court_prompt", lang), parse_mode="Markdown")


@router.message(SettingsStates.enter_custom_court)
async def settings_custom_court_submit(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data.get("lang", "en")
    zone = data.get("courts_zone", "")
    court = (message.text or "").strip()
    if not court:
        await message.answer(t("custom_court_empty_error", lang), parse_mode="Markdown")
        return

    selected: list[str] = data.get("selected_courts", [])
    if court not in selected:
        selected.append(court)
    await state.update_data(selected_courts=selected)
    await state.set_state(SettingsStates.change_courts)

    await message.answer(t("custom_court_added", lang), parse_mode="Markdown")
    await message.answer(
        t("choose_courts", lang, zone=zone),
        reply_markup=courts_keyboard(lang, zone, selected),
        parse_mode="Markdown",
    )


@router.callback_query(SettingsStates.change_courts, F.data == "courts_done")
async def settings_courts_done(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    if not callback.message:
        await callback.answer()
        return
    data = await state.get_data()
    selected: list[str] = data.get("selected_courts", [])
    user = callback.from_user
    service = PlayerService(session)
    await service.update_profile(user.id, PlayerUpdate(preferred_courts=selected))
    await state.clear()
    player = await service.get_by_telegram_id(user.id)
    lang = get_player_lang(player)
    await callback.answer()
    if not player:
        return
    await _render_edit_profile(callback.message, player, lang, edit=True)


# ── Edit Profile — Languages (NEW; multi-select like Courts, but spoken
#    languages, not the bot's interface language) ──────────────────────────────

@router.callback_query(F.data == "editprofile:languages")
async def edit_profile_languages_start(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    if not callback.message:
        await callback.answer()
        return
    player = await PlayerService(session).get_by_telegram_id(callback.from_user.id)
    lang = get_player_lang(player)
    current = player.spoken_languages if player else []
    await state.set_state(SettingsStates.change_languages)
    await state.update_data(selected_languages=current, lang=lang)
    await callback.answer()
    await _edit_screen(
        callback.message, t("edit_profile_languages_header", lang), spoken_languages_keyboard(lang, current)
    )


@router.callback_query(SettingsStates.change_languages, F.data.startswith("language_toggle:"))
async def edit_profile_language_toggle(callback: CallbackQuery, state: FSMContext) -> None:
    if not callback.data or not callback.message:
        await callback.answer()
        return
    spoken_lang = callback.data.split(":", 1)[1]
    data = await state.get_data()
    lang = data.get("lang", "en")
    selected: list[str] = data.get("selected_languages", [])
    if spoken_lang in selected:
        selected.remove(spoken_lang)
    else:
        selected.append(spoken_lang)
    await state.update_data(selected_languages=selected)
    await callback.answer()
    try:
        await callback.message.edit_reply_markup(reply_markup=spoken_languages_keyboard(lang, selected))
    except TelegramBadRequest as exc:
        if "message is not modified" not in str(exc):
            raise


@router.callback_query(SettingsStates.change_languages, F.data == "languages_done")
async def edit_profile_languages_done(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    if not callback.message:
        await callback.answer()
        return
    data = await state.get_data()
    selected: list[str] = data.get("selected_languages", [])
    user = callback.from_user
    service = PlayerService(session)
    await service.update_profile(user.id, PlayerUpdate(spoken_languages=selected))
    await state.clear()
    player = await service.get_by_telegram_id(user.id)
    lang = get_player_lang(player)
    await callback.answer()
    if not player:
        return
    await _render_edit_profile(callback.message, player, lang, edit=True)


# ── Settings (interface language only — everything else moved to Edit Profile) ─

@router.message(F.text.in_(["⚙️ Settings", "⚙️ Налаштування", "⚙️ Настройки"]))
async def show_settings(message: Message, session: AsyncSession) -> None:
    user = message.from_user
    if not user:
        return
    service = PlayerService(session)
    player = await service.get_by_telegram_id(user.id)
    lang = get_player_lang(player)
    await message.answer(
        t("settings_header", lang),
        reply_markup=settings_keyboard(lang),
        parse_mode="Markdown",
    )


@router.callback_query(F.data == "settings:language")
async def settings_change_language(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    user = callback.from_user
    service = PlayerService(session)
    player = await service.get_by_telegram_id(user.id)  # type: ignore[union-attr]
    lang = get_player_lang(player)
    await state.set_state(SettingsStates.change_language)
    await callback.message.answer(t("choose_language", lang), reply_markup=language_keyboard(), parse_mode="Markdown")  # type: ignore[union-attr]
    await callback.answer()


@router.callback_query(SettingsStates.change_language, F.data.startswith("lang:"))
async def settings_save_language(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    lang = callback.data.split(":")[1]  # type: ignore[union-attr]
    user = callback.from_user
    service = PlayerService(session)
    await service.update_profile(user.id, PlayerUpdate(language=lang))  # type: ignore[union-attr]
    await state.clear()
    await callback.message.answer(t("settings_saved", lang), parse_mode="Markdown")  # type: ignore[union-attr]
    await send_main_menu(callback.message, lang)  # type: ignore[union-attr]
    await callback.answer()


# ── Generic back-to-menu callback ────────────────────────────────────────────

@router.callback_query(F.data == "menu:main")
async def back_to_main_menu(callback: CallbackQuery, session: AsyncSession) -> None:
    user = callback.from_user
    service = PlayerService(session)
    player = await service.get_by_telegram_id(user.id)  # type: ignore[union-attr]
    lang = get_player_lang(player)
    await send_main_menu(callback.message, lang)  # type: ignore[union-attr]
    await callback.answer()
