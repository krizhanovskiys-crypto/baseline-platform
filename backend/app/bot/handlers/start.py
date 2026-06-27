"""Handlers for /start command and onboarding flow."""
import logging

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.bot.handlers.helpers import send_main_menu
from backend.app.bot.keyboards.keyboards import (
    area_keyboard,
    courts_keyboard,
    language_keyboard,
    skill_level_keyboard,
)
from backend.app.bot.states.states import OnboardingStates
from backend.app.bot.texts import t
from backend.app.schemas.player import PlayerCreate, PlayerUpdate
from backend.app.services.player_service import PlayerService

logger = logging.getLogger(__name__)
router = Router(name="start")


async def _start_onboarding(message: Message, state: FSMContext) -> None:
    """Begin the onboarding wizard from step 1."""
    await state.set_state(OnboardingStates.choose_language)
    await message.answer(t("choose_language"), reply_markup=language_keyboard(), parse_mode="Markdown")


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, session: AsyncSession) -> None:
    """Handle /start — create player if new, show menu or start onboarding."""
    user = message.from_user
    if not user:
        return

    service = PlayerService(session)
    player, created = await service.get_or_create(
        PlayerCreate(
            telegram_id=user.id,
            username=user.username,
            first_name=user.first_name or "Player",
        )
    )

    if created or not player.is_profile_complete:
        lang = player.language or "en"
        await message.answer(
            t("welcome_new", lang),
            parse_mode="Markdown",
        )
        await _start_onboarding(message, state)
    else:
        lang = player.language or "en"
        await message.answer(
            t("welcome_back", lang, name=player.first_name),
            parse_mode="Markdown",
        )
        await send_main_menu(message, lang)


# ── Step 1: Language ─────────────────────────────────────────────────────────

@router.callback_query(OnboardingStates.choose_language, F.data.startswith("lang:"))
async def onboarding_language(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    lang = callback.data.split(":")[1]  # type: ignore[union-attr]
    await state.update_data(language=lang)
    await callback.message.edit_reply_markup()  # type: ignore[union-attr]
    await state.set_state(OnboardingStates.choose_level)
    await callback.message.answer(  # type: ignore[union-attr]
        t("choose_level", lang),
        reply_markup=skill_level_keyboard(lang),
        parse_mode="Markdown",
    )
    await callback.answer()


# ── Step 2: Level ────────────────────────────────────────────────────────────

@router.callback_query(OnboardingStates.choose_level, F.data.startswith("level:"))
async def onboarding_level(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    level_str = callback.data.split(":")[1]  # type: ignore[union-attr]
    data = await state.get_data()
    lang = data.get("language", "en")
    await state.update_data(skill_level=float(level_str))
    await callback.message.edit_reply_markup()  # type: ignore[union-attr]
    await state.set_state(OnboardingStates.choose_area)
    await callback.message.answer(  # type: ignore[union-attr]
        t("choose_area", lang),
        reply_markup=area_keyboard(lang),
        parse_mode="Markdown",
    )
    await callback.answer()


# ── Step 3: Area ─────────────────────────────────────────────────────────────

@router.callback_query(OnboardingStates.choose_area, F.data.startswith("area:"))
async def onboarding_area(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    area = callback.data.split(":", 1)[1]  # type: ignore[union-attr]
    data = await state.get_data()
    lang = data.get("language", "en")
    await state.update_data(home_area=area, selected_courts=[])
    await callback.message.edit_reply_markup()  # type: ignore[union-attr]
    await state.set_state(OnboardingStates.choose_courts)
    await callback.message.answer(  # type: ignore[union-attr]
        t("choose_courts", lang),
        reply_markup=courts_keyboard(lang, []),
        parse_mode="Markdown",
    )
    await callback.answer()


# ── Step 4: Courts (multi-select) ────────────────────────────────────────────

@router.callback_query(OnboardingStates.choose_courts, F.data.startswith("court_toggle:"))
async def onboarding_court_toggle(callback: CallbackQuery, state: FSMContext) -> None:
    court = callback.data.split(":", 1)[1]  # type: ignore[union-attr]
    data = await state.get_data()
    lang = data.get("language", "en")
    selected: list[str] = data.get("selected_courts", [])

    if court in selected:
        selected.remove(court)
    else:
        selected.append(court)

    await state.update_data(selected_courts=selected)
    await callback.message.edit_reply_markup(  # type: ignore[union-attr]
        reply_markup=courts_keyboard(lang, selected)
    )
    await callback.answer()


@router.callback_query(OnboardingStates.choose_courts, F.data == "courts_done")
async def onboarding_courts_done(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
) -> None:
    data = await state.get_data()
    lang = data.get("language", "en")
    selected_courts: list[str] = data.get("selected_courts", [])

    service = PlayerService(session)
    user = callback.from_user
    if not user:
        return

    await service.update_profile(
        telegram_id=user.id,
        data=PlayerUpdate(
            language=lang,
            skill_level=data.get("skill_level"),
            home_area=data.get("home_area"),
            preferred_courts=selected_courts or ["Other"],
        ),
    )

    await state.clear()
    await callback.message.edit_reply_markup()  # type: ignore[union-attr]
    await callback.message.answer(t("profile_complete", lang), parse_mode="Markdown")  # type: ignore[union-attr]
    await send_main_menu(callback.message, lang)  # type: ignore[union-attr]
    await callback.answer()
