"""Create Game wizard handler."""
import logging
from datetime import date, time

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.bot.handlers.helpers import get_player_lang, send_main_menu
from backend.app.bot.keyboards.keyboards import (
    area_keyboard,
    confirm_keyboard,
    game_level_keyboard,
    match_type_keyboard,
)
from backend.app.bot.states.states import CreateGameStates
from backend.app.bot.texts import t
from backend.app.database.models.game import MatchType
from backend.app.schemas.game import GameCreate
from backend.app.services.game_service import GameService
from backend.app.services.player_service import PlayerService

logger = logging.getLogger(__name__)
router = Router(name="create_game")

_TRIGGER_TEXTS = {"📅 Create Game", "📅 Створити гру", "📅 Создать игру"}


@router.message(F.text.in_(_TRIGGER_TEXTS))
async def create_game_start(message: Message, state: FSMContext, session: AsyncSession) -> None:
    user = message.from_user
    if not user:
        return
    service = PlayerService(session)
    player = await service.get_by_telegram_id(user.id)
    lang = get_player_lang(player)

    if not player or not player.is_profile_complete:
        await message.answer(t("profile_not_complete_action", lang), parse_mode="Markdown")
        return

    await state.set_state(CreateGameStates.enter_court)
    await state.update_data(lang=lang)
    await message.answer(t("cg_enter_court", lang), parse_mode="Markdown")


@router.message(CreateGameStates.enter_court)
async def cg_enter_court(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data.get("lang", "en")
    await state.update_data(court=message.text)
    await state.set_state(CreateGameStates.choose_area)
    await message.answer(
        t("cg_enter_area", lang),
        reply_markup=area_keyboard(lang, callback_prefix="cg_area"),
        parse_mode="Markdown",
    )


@router.callback_query(CreateGameStates.choose_area, F.data.startswith("cg_area:"))
async def cg_choose_area(callback: CallbackQuery, state: FSMContext) -> None:
    area = callback.data.split(":", 1)[1]  # type: ignore[union-attr]
    data = await state.get_data()
    lang = data.get("lang", "en")
    await state.update_data(area=area)
    await state.set_state(CreateGameStates.enter_date)
    await callback.message.answer(t("cg_enter_date", lang), parse_mode="Markdown")  # type: ignore[union-attr]
    await callback.answer()


@router.message(CreateGameStates.enter_date)
async def cg_enter_date(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data.get("lang", "en")
    try:
        parts = message.text.strip().split(".")  # type: ignore[union-attr]
        parsed_date = date(int(parts[2]), int(parts[1]), int(parts[0]))
    except (ValueError, IndexError):
        await message.answer(t("cg_error_date", lang), parse_mode="Markdown")
        return

    await state.update_data(date=parsed_date.isoformat())
    await state.set_state(CreateGameStates.enter_time)
    await message.answer(t("cg_enter_time", lang), parse_mode="Markdown")


@router.message(CreateGameStates.enter_time)
async def cg_enter_time(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data.get("lang", "en")
    try:
        parts = message.text.strip().split(":")  # type: ignore[union-attr]
        parsed_time = time(int(parts[0]), int(parts[1]))
    except (ValueError, IndexError):
        await message.answer(t("cg_error_time", lang), parse_mode="Markdown")
        return

    await state.update_data(time=parsed_time.strftime("%H:%M"))
    await state.set_state(CreateGameStates.choose_type)
    await message.answer(
        t("cg_choose_type", lang),
        reply_markup=match_type_keyboard(lang),
        parse_mode="Markdown",
    )


@router.callback_query(CreateGameStates.choose_type, F.data.startswith("match_type:"))
async def cg_choose_type(callback: CallbackQuery, state: FSMContext) -> None:
    match_type = callback.data.split(":")[1]  # type: ignore[union-attr]
    data = await state.get_data()
    lang = data.get("lang", "en")
    await state.update_data(match_type=match_type)
    await state.set_state(CreateGameStates.choose_level)
    await callback.message.answer(  # type: ignore[union-attr]
        t("cg_choose_level", lang),
        reply_markup=game_level_keyboard(lang),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(CreateGameStates.choose_level, F.data.startswith("game_level:"))
async def cg_choose_level(callback: CallbackQuery, state: FSMContext) -> None:
    raw = callback.data.split(":")[1]  # type: ignore[union-attr]
    level = None if raw == "skip" else float(raw)
    data = await state.get_data()
    lang = data.get("lang", "en")
    await state.update_data(required_level=level)
    await state.set_state(CreateGameStates.confirm)

    level_display = str(level) if level else "Any"
    match_display = data.get("match_type", "singles").capitalize()
    await callback.message.answer(  # type: ignore[union-attr]
        t(
            "cg_confirm",
            lang,
            court=data.get("court"),
            area=data.get("area"),
            date=data.get("date"),
            time=data.get("time"),
            match_type=match_display,
            level=level_display,
        ),
        reply_markup=confirm_keyboard(lang),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(CreateGameStates.confirm, F.data.startswith("game_confirm:"))
async def cg_confirm(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    answer = callback.data.split(":")[1]  # type: ignore[union-attr]
    data = await state.get_data()
    lang = data.get("lang", "en")

    if answer == "no":
        await state.clear()
        await callback.message.answer(t("cancelled", lang), parse_mode="Markdown")  # type: ignore[union-attr]
        await send_main_menu(callback.message, lang)  # type: ignore[union-attr]
        await callback.answer()
        return

    user = callback.from_user
    if not user:
        return

    # Parse stored strings back to proper types
    game_date = date.fromisoformat(data["date"])
    h, m = data["time"].split(":")
    game_time = time(int(h), int(m))
    match_type = MatchType(data.get("match_type", "singles"))

    game_service = GameService(session)
    game = await game_service.create_game(
        creator_telegram_id=user.id,
        data=GameCreate(
            court=data["court"],
            area=data["area"],
            date=game_date,
            time=game_time,
            match_type=match_type,
            required_level=data.get("required_level"),
        ),
    )

    await state.clear()
    if game:
        await callback.message.answer(t("cg_created", lang, game_id=game.id), parse_mode="Markdown")  # type: ignore[union-attr]
    else:
        await callback.message.answer(t("error_generic", lang), parse_mode="Markdown")  # type: ignore[union-attr]

    await send_main_menu(callback.message, lang)  # type: ignore[union-attr]
    await callback.answer()
