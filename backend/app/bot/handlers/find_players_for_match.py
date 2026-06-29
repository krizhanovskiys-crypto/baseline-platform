"""Find Players for Match handler — browse and select candidate players."""
import logging

from aiogram import F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.bot.handlers.helpers import get_player_lang, send_main_menu
from backend.app.bot.keyboards.keyboards import (
    fpm_after_select_keyboard,
    fpm_card_keyboard,
    fpm_empty_keyboard,
    fpm_selected_list_keyboard,
    invitation_keyboard,
)
from backend.app.bot.states.states import FindPlayersForMatchStates
from backend.app.bot.texts import t
from backend.app.services.game_service import GameService
from backend.app.services.invitation_service import InvitationService
from backend.app.services.player_service import PlayerService

logger = logging.getLogger(__name__)
router = Router(name="find_players_for_match")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_card_text(candidates: list[dict], idx: int, lang: str) -> str:
    c = candidates[idx]
    header = t("fpm_found", lang, total=len(candidates))
    card = t("fpm_browse_card", lang, name=c["first_name"], level=c["skill_level"], area=c["home_area"])
    return f"{header}\n\n{card}"


def _make_card_keyboard(candidates: list[dict], idx: int, lang: str) -> object:
    total = len(candidates)
    return fpm_card_keyboard(
        lang=lang,
        player_id=candidates[idx]["id"],
        show_prev=idx > 0,
        show_next=idx < total - 1,
    )


def _get_name(candidates: list[dict], player_id: int) -> str:
    for c in candidates:
        if c["id"] == player_id:
            return c["first_name"]
    return "?"


def _get_telegram_id(candidates: list[dict], player_id: int) -> int | None:
    for c in candidates:
        if c["id"] == player_id:
            return c.get("telegram_id")
    return None


# ── Entry: fpm:start:{game_id} ────────────────────────────────────────────────

@router.callback_query(F.data.startswith("fpm:start:"))
async def fpm_start(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    if not callback.data or not callback.message:
        return
    game_id = int(callback.data.split(":")[-1])
    user = callback.from_user
    if not user:
        return

    player = await PlayerService(session).get_by_telegram_id(user.id)
    lang = get_player_lang(player)

    candidate_schemas = await GameService(session).find_players_for_match(game_id, user.id)
    candidates = [
        {
            "id": c.id,
            "telegram_id": c.telegram_id,
            "first_name": c.first_name,
            "skill_level": float(c.skill_level or 0),
            "home_area": c.home_area or "—",
        }
        for c in candidate_schemas
    ]

    if not candidates:
        await state.clear()
        await callback.message.answer(
            t("fpm_not_found", lang),
            reply_markup=fpm_empty_keyboard(lang),
            parse_mode="Markdown",
        )
        await callback.answer()
        return

    await state.set_state(FindPlayersForMatchStates.browsing)
    await state.set_data({
        "game_id": game_id,
        "lang": lang,
        "candidates": candidates,
        "current_index": 0,
        "selected_ids": [],
    })

    await callback.message.answer(
        _make_card_text(candidates, 0, lang),
        reply_markup=_make_card_keyboard(candidates, 0, lang),
        parse_mode="Markdown",
    )
    await callback.answer()


# ── Navigation ────────────────────────────────────────────────────────────────

@router.callback_query(FindPlayersForMatchStates.browsing, F.data == "fpm:next")
async def fpm_next(callback: CallbackQuery, state: FSMContext) -> None:
    if not callback.message:
        return
    data = await state.get_data()
    lang = data.get("lang", "en")
    candidates: list[dict] = data.get("candidates", [])
    idx = data.get("current_index", 0)

    idx = min(idx + 1, len(candidates) - 1)
    await state.update_data(current_index=idx)

    await callback.message.edit_text(
        _make_card_text(candidates, idx, lang),
        reply_markup=_make_card_keyboard(candidates, idx, lang),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(FindPlayersForMatchStates.browsing, F.data == "fpm:prev")
async def fpm_prev(callback: CallbackQuery, state: FSMContext) -> None:
    if not callback.message:
        return
    data = await state.get_data()
    lang = data.get("lang", "en")
    candidates: list[dict] = data.get("candidates", [])
    idx = data.get("current_index", 0)

    idx = max(idx - 1, 0)
    await state.update_data(current_index=idx)

    await callback.message.edit_text(
        _make_card_text(candidates, idx, lang),
        reply_markup=_make_card_keyboard(candidates, idx, lang),
        parse_mode="Markdown",
    )
    await callback.answer()


# ── Select ────────────────────────────────────────────────────────────────────

@router.callback_query(FindPlayersForMatchStates.browsing, F.data.startswith("fpm:select:"))
async def fpm_select(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    if not callback.data or not callback.message:
        return
    data = await state.get_data()
    lang = data.get("lang", "en")
    game_id: int = data.get("game_id")
    candidates: list[dict] = data.get("candidates", [])
    player_id = int(callback.data.split(":")[-1])
    selected_ids: list[int] = data.get("selected_ids", [])

    if player_id in selected_ids:
        await callback.answer(t("fpm_selected_count", lang, count=len(selected_ids)), show_alert=False)
        return

    invitation = await InvitationService(session).create_invitation(game_id, player_id)
    if invitation is None:
        await callback.answer(t("inv_duplicate", lang), show_alert=False)
        return

    # Invitation is committed — track it regardless of Telegram delivery outcome.
    selected_ids.append(player_id)
    await state.update_data(selected_ids=selected_ids)
    count = len(selected_ids)

    delivery_ok = False
    invitee_telegram_id = _get_telegram_id(candidates, player_id)
    if invitee_telegram_id:
        game = await GameService(session).get_game(game_id)
        invitee = await PlayerService(session).get_by_id(player_id)
        invitee_lang = invitee.language if invitee else "en"
        if game:
            inv_text = t(
                "inv_message",
                invitee_lang,
                date=game.date.strftime("%d.%m.%Y") if game.date else "—",
                time=game.time.strftime("%H:%M") if game.time else "—",
                court=game.court or "—",
                level=game.required_level or "—",
                organizer=callback.from_user.first_name or "Organizer",
            )
            try:
                await callback.bot.send_message(
                    invitee_telegram_id,
                    inv_text,
                    reply_markup=invitation_keyboard(invitee_lang, invitation.id),
                    parse_mode="Markdown",
                )
                delivery_ok = True
            except TelegramAPIError:
                logger.warning("Could not deliver invitation to telegram_id=%s", invitee_telegram_id)

    await callback.message.edit_text(
        t("fpm_selected_count", lang, count=count),
        reply_markup=fpm_after_select_keyboard(lang),
        parse_mode="Markdown",
    )
    if delivery_ok:
        await callback.answer()
    else:
        await callback.answer(t("inv_delivery_failed", lang), show_alert=True)


# ── Post-select actions ───────────────────────────────────────────────────────

@router.callback_query(FindPlayersForMatchStates.browsing, F.data == "fpm:continue")
async def fpm_continue(callback: CallbackQuery, state: FSMContext) -> None:
    if not callback.message:
        return
    data = await state.get_data()
    lang = data.get("lang", "en")
    candidates: list[dict] = data.get("candidates", [])
    idx = data.get("current_index", 0)

    await callback.message.edit_text(
        _make_card_text(candidates, idx, lang),
        reply_markup=_make_card_keyboard(candidates, idx, lang),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(FindPlayersForMatchStates.browsing, F.data == "fpm:view_selected")
async def fpm_view_selected(callback: CallbackQuery, state: FSMContext) -> None:
    if not callback.message:
        return
    data = await state.get_data()
    lang = data.get("lang", "en")
    candidates: list[dict] = data.get("candidates", [])
    selected_ids: list[int] = data.get("selected_ids", [])

    header = t("fpm_selected_header", lang)
    items = "\n".join(
        t("fpm_selected_item", lang, name=_get_name(candidates, pid))
        for pid in selected_ids
    )
    text = f"{header}\n\n{items}" if items else header

    await callback.message.edit_text(
        text,
        reply_markup=fpm_selected_list_keyboard(lang),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(FindPlayersForMatchStates.browsing, F.data == "fpm:back")
async def fpm_back(callback: CallbackQuery, state: FSMContext) -> None:
    if not callback.message:
        return
    data = await state.get_data()
    lang = data.get("lang", "en")
    candidates: list[dict] = data.get("candidates", [])
    idx = data.get("current_index", 0)

    await callback.message.edit_text(
        _make_card_text(candidates, idx, lang),
        reply_markup=_make_card_keyboard(candidates, idx, lang),
        parse_mode="Markdown",
    )
    await callback.answer()


# ── Menu ──────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "fpm:menu")
async def fpm_menu(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    if not callback.message:
        return
    await state.clear()
    player = await PlayerService(session).get_by_telegram_id(callback.from_user.id)
    lang = get_player_lang(player)
    await send_main_menu(callback.message, lang)
    await callback.answer()
