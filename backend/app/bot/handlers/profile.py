"""Profile and settings handlers."""
import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.bot.handlers.helpers import get_player_lang, send_main_menu
from backend.app.bot.keyboards.keyboards import (
    area_keyboard,
    courts_keyboard,
    language_keyboard,
    settings_keyboard,
    skill_level_keyboard,
)
from backend.app.bot.states.states import OnboardingStates, SettingsStates
from backend.app.bot.texts import t
from backend.app.schemas.player import PlayerUpdate
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
        await message.answer(t("profile_incomplete", lang), parse_mode="Markdown")
        return

    courts = ", ".join(player.preferred_courts or []) or "—"
    await message.answer(
        t(
            "profile_header",
            lang,
            name=player.first_name,
            level=player.skill_level,
            area=player.home_area or "—",
            courts=courts,
            rating=player.rating,
            matches=player.matches_played,
        ),
        parse_mode="Markdown",
    )


# ── Settings ─────────────────────────────────────────────────────────────────

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


@router.callback_query(F.data == "settings:area")
async def settings_change_area(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    user = callback.from_user
    service = PlayerService(session)
    player = await service.get_by_telegram_id(user.id)  # type: ignore[union-attr]
    lang = get_player_lang(player)
    await state.set_state(SettingsStates.change_area)
    await callback.message.answer(t("choose_area", lang), reply_markup=area_keyboard(lang, "settings_area"), parse_mode="Markdown")  # type: ignore[union-attr]
    await callback.answer()


@router.callback_query(SettingsStates.change_area, F.data.startswith("settings_area:"))
async def settings_save_area(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    area = callback.data.split(":", 1)[1]  # type: ignore[union-attr]
    user = callback.from_user
    service = PlayerService(session)
    player = await service.get_by_telegram_id(user.id)  # type: ignore[union-attr]
    lang = get_player_lang(player)
    await service.update_profile(user.id, PlayerUpdate(home_area=area))  # type: ignore[union-attr]
    await state.clear()
    await callback.message.answer(t("settings_saved", lang), parse_mode="Markdown")  # type: ignore[union-attr]
    await send_main_menu(callback.message, lang)  # type: ignore[union-attr]
    await callback.answer()


@router.callback_query(F.data == "settings:level")
async def settings_change_level(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    user = callback.from_user
    service = PlayerService(session)
    player = await service.get_by_telegram_id(user.id)  # type: ignore[union-attr]
    lang = get_player_lang(player)
    await state.set_state(SettingsStates.change_level)
    await callback.message.answer(t("choose_level", lang), reply_markup=skill_level_keyboard(lang), parse_mode="Markdown")  # type: ignore[union-attr]
    await callback.answer()


@router.callback_query(SettingsStates.change_level, F.data.startswith("level:"))
async def settings_save_level(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    level = float(callback.data.split(":")[1])  # type: ignore[union-attr]
    user = callback.from_user
    service = PlayerService(session)
    player = await service.get_by_telegram_id(user.id)  # type: ignore[union-attr]
    lang = get_player_lang(player)
    await service.update_profile(user.id, PlayerUpdate(skill_level=level))  # type: ignore[union-attr]
    await state.clear()
    await callback.message.answer(t("settings_saved", lang), parse_mode="Markdown")  # type: ignore[union-attr]
    await send_main_menu(callback.message, lang)  # type: ignore[union-attr]
    await callback.answer()


@router.callback_query(F.data == "settings:courts")
async def settings_change_courts(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    user = callback.from_user
    service = PlayerService(session)
    player = await service.get_by_telegram_id(user.id)  # type: ignore[union-attr]
    lang = get_player_lang(player)
    current = player.preferred_courts if player else []
    await state.set_state(SettingsStates.change_courts)
    await state.update_data(selected_courts=current, lang=lang)
    await callback.message.answer(t("choose_courts", lang), reply_markup=courts_keyboard(lang, current), parse_mode="Markdown")  # type: ignore[union-attr]
    await callback.answer()


@router.callback_query(SettingsStates.change_courts, F.data.startswith("court_toggle:"))
async def settings_court_toggle(callback: CallbackQuery, state: FSMContext) -> None:
    court = callback.data.split(":", 1)[1]  # type: ignore[union-attr]
    data = await state.get_data()
    lang = data.get("lang", "en")
    selected: list[str] = data.get("selected_courts", [])
    if court in selected:
        selected.remove(court)
    else:
        selected.append(court)
    await state.update_data(selected_courts=selected)
    await callback.message.edit_reply_markup(reply_markup=courts_keyboard(lang, selected))  # type: ignore[union-attr]
    await callback.answer()


@router.callback_query(SettingsStates.change_courts, F.data == "courts_done")
async def settings_courts_done(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    data = await state.get_data()
    lang = data.get("lang", "en")
    selected: list[str] = data.get("selected_courts", [])
    user = callback.from_user
    service = PlayerService(session)
    await service.update_profile(user.id, PlayerUpdate(preferred_courts=selected or ["Other"]))  # type: ignore[union-attr]
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
