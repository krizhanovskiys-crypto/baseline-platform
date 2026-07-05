"""Admin Center — Players module (Sprint 11 Phase 3.0), the first
real Admin Center module beyond Testing/System.

Every lookup, page, and search goes through PlayersService — this module
never touches PlayerRepository or the ORM directly (Handlers ->
PlayersService -> Repositories, per the Admin Center Architecture
decision in docs/PRODUCT_DECISIONS.md).
"""
import math

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.markdown import markdown_decoration
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.bot.handlers.admin.common import authorized_role, lang_for
from backend.app.bot.handlers.admin.dashboard import show_dashboard
from backend.app.bot.keyboards.keyboards import (
    player_details_keyboard,
    players_browse_keyboard,
    players_root_keyboard,
    players_search_results_keyboard,
)
from backend.app.bot.states.states import AdminPlayersStates
from backend.app.bot.texts import t
from backend.app.schemas.player import PlayerRead
from backend.app.services.players_service import PAGE_SIZE, PlayersService

router = Router(name="admin_players")

_EMPTY = "—"


def _format_level(level: float | None) -> str:
    return f"{level:.1f}" if level is not None else _EMPTY


def _format_bool(value: bool, lang: str) -> str:
    return t("players_yes", lang) if value else t("players_no", lang)


def _md(value: str) -> str:
    """Escape a free-text, user-controlled value before it goes into a
    parse_mode="Markdown" message. Telegram usernames routinely contain
    underscores, and first_name/custom court names are unrestricted free
    text — any Markdown special character in an unescaped value breaks
    entity parsing (a single "_" reads as an unterminated italic span)
    and raises TelegramBadRequest: "can't parse entities". Every other
    screen in the bot only ever puts fixed, code-controlled strings
    (labels, enums) into Markdown text, so this project has no prior
    escaping helper — aiogram, already a project dependency, ships one,
    and reusing it here is the fix, not a new invention."""
    return markdown_decoration.quote(value)


def _format_details(player: PlayerRead, lang: str) -> str:
    return t(
        "players_details_header",
        lang,
        telegram_id=player.telegram_id,
        name=_md(player.first_name),
        username=f"@{_md(player.username)}" if player.username else _EMPTY,
        languages=" • ".join(player.spoken_languages) if player.spoken_languages else _EMPTY,
        level=_format_level(player.skill_level),
        home_area=player.home_area or _EMPTY,
        courts=_md(", ".join(player.preferred_courts)) if player.preferred_courts else _EMPTY,
        available_now=_format_bool(player.available_now, lang),
        profile_complete_emoji="✅" if player.is_profile_complete else "⚠️",
        profile_complete=_format_bool(player.is_profile_complete, lang),
        registration_date=player.created_at.strftime("%Y-%m-%d"),
    )


def _format_browse_row(player: PlayerRead, index: int, lang: str) -> str:
    return t(
        "players_browse_row",
        lang,
        index=index,
        name=_md(player.first_name),
        telegram_id=player.telegram_id,
        area=player.home_area or _EMPTY,
        level=_format_level(player.skill_level),
    )


async def _show_root(message: Message, session: AsyncSession, lang: str, state: FSMContext) -> None:
    await state.clear()
    total = await PlayersService(session).count_all()
    await message.answer(
        t("players_header", lang, total=total),
        reply_markup=players_root_keyboard(lang),
        parse_mode="Markdown",
    )


async def _show_browse_page(
    message: Message, session: AsyncSession, lang: str, state: FSMContext, page: int
) -> None:
    service = PlayersService(session)
    players, total = await service.get_page(page)
    total_pages = max(1, math.ceil(total / PAGE_SIZE))

    # Never leave the operator on an invalid page (e.g. players were
    # deleted since) — land on the nearest valid page, same pattern as
    # Available Matches' pagination.
    if page > total_pages:
        page = total_pages
        players, total = await service.get_page(page)

    await state.set_state(AdminPlayersStates.browsing)
    await state.update_data(current_page=page)

    rows = "\n\n".join(
        _format_browse_row(player, index=(page - 1) * PAGE_SIZE + i + 1, lang=lang)
        for i, player in enumerate(players)
    )
    header = t("players_browse_header", lang, page=page, total_pages=total_pages)
    text = f"{header}\n\n{rows}" if players else header

    await message.answer(
        text,
        reply_markup=players_browse_keyboard(
            lang, players, page, has_prev=page > 1, has_next=page < total_pages
        ),
        parse_mode="Markdown",
    )


async def _show_details(message: Message, session: AsyncSession, lang: str, player_id: int) -> None:
    player = await PlayersService(session).get_by_id(player_id)
    if player is None:
        await message.answer(t("players_no_results", lang))
        return

    await message.answer(
        _format_details(player, lang),
        reply_markup=player_details_keyboard(lang, player.id, player.is_verified_coach),
        parse_mode="Markdown",
    )


# ---------------------------------------------------------------------------
# Entry from the Dashboard
# ---------------------------------------------------------------------------

@router.callback_query(F.data == "dashboard:players")
async def players_open_from_dashboard(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    if not callback.from_user or not await authorized_role(session, callback.from_user.id):
        return

    lang = await lang_for(session, callback.from_user.id)
    await _show_root(callback.message, session, lang, state)  # type: ignore[arg-type]
    await callback.answer()


@router.callback_query(F.data == "players:root")
async def players_back_to_root(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    if not callback.from_user or not await authorized_role(session, callback.from_user.id):
        return

    lang = await lang_for(session, callback.from_user.id)
    await _show_root(callback.message, session, lang, state)  # type: ignore[arg-type]
    await callback.answer()


@router.callback_query(F.data == "players:back_to_dashboard")
async def players_back_to_dashboard(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    if not callback.from_user or not await authorized_role(session, callback.from_user.id):
        return

    await state.clear()
    lang = await lang_for(session, callback.from_user.id)
    await show_dashboard(callback.message, session, lang)  # type: ignore[arg-type]
    await callback.answer()


# ---------------------------------------------------------------------------
# Browse Players
# ---------------------------------------------------------------------------

@router.callback_query(F.data == "players:browse")
async def players_browse(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    if not callback.from_user or not await authorized_role(session, callback.from_user.id):
        return

    lang = await lang_for(session, callback.from_user.id)
    await _show_browse_page(callback.message, session, lang, state, page=1)  # type: ignore[arg-type]
    await callback.answer()


@router.callback_query(AdminPlayersStates.browsing, F.data.regexp(r"^players:page:\d+$"))
async def players_page(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    if not callback.from_user or not await authorized_role(session, callback.from_user.id):
        return

    page = int(callback.data.split(":")[2])  # type: ignore[union-attr]
    lang = await lang_for(session, callback.from_user.id)
    await _show_browse_page(callback.message, session, lang, state, page=page)  # type: ignore[arg-type]
    await callback.answer()


# ---------------------------------------------------------------------------
# Search Player
# ---------------------------------------------------------------------------

@router.callback_query(F.data == "players:search")
async def players_search_prompt(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    if not callback.from_user or not await authorized_role(session, callback.from_user.id):
        return

    lang = await lang_for(session, callback.from_user.id)
    await state.set_state(AdminPlayersStates.enter_search)
    await callback.message.answer(t("players_search_prompt", lang), parse_mode="Markdown")  # type: ignore[union-attr]
    await callback.answer()


@router.message(AdminPlayersStates.enter_search)
async def players_search_submit(message: Message, session: AsyncSession, state: FSMContext) -> None:
    user = message.from_user
    if not user or not message.text:
        return
    if not await authorized_role(session, user.id):
        return

    lang = await lang_for(session, user.id)
    await state.clear()

    results = await PlayersService(session).search(message.text)

    if not results:
        await message.answer(t("players_no_results", lang))
        return

    if len(results) == 1:
        await _show_details(message, session, lang, results[0].id)
        return

    await message.answer(
        t("players_search_results_header", lang, count=len(results)),
        reply_markup=players_search_results_keyboard(lang, results),
        parse_mode="Markdown",
    )


# ---------------------------------------------------------------------------
# Player Details
# ---------------------------------------------------------------------------

@router.callback_query(F.data.regexp(r"^players:open:\d+$"))
async def players_open_details(callback: CallbackQuery, session: AsyncSession) -> None:
    if not callback.from_user or not await authorized_role(session, callback.from_user.id):
        return

    player_id = int(callback.data.split(":")[2])  # type: ignore[union-attr]
    lang = await lang_for(session, callback.from_user.id)
    await _show_details(callback.message, session, lang, player_id)  # type: ignore[arg-type]
    await callback.answer()


# ---------------------------------------------------------------------------
# Coach Verification (Sprint 12) — Player Details' first Actions-layer
# action. Coach is a Player Badge, not a separate entity: this only ever
# flips Player.is_verified_coach through PlayersService.
# ---------------------------------------------------------------------------

@router.callback_query(F.data.regexp(r"^players:verify_coach:\d+$"))
async def players_verify_coach(callback: CallbackQuery, session: AsyncSession) -> None:
    if not callback.from_user or not await authorized_role(session, callback.from_user.id):
        return

    player_id = int(callback.data.split(":")[2])  # type: ignore[union-attr]
    lang = await lang_for(session, callback.from_user.id)
    player = await PlayersService(session).set_verified_coach(player_id, True)
    if player is None:
        await callback.answer()
        return
    await callback.message.answer(  # type: ignore[union-attr]
        t("players_coach_verified", lang, name=_md(player.first_name)), parse_mode="Markdown"
    )
    await _show_details(callback.message, session, lang, player_id)  # type: ignore[arg-type]
    await callback.answer()


@router.callback_query(F.data.regexp(r"^players:revoke_coach:\d+$"))
async def players_revoke_coach(callback: CallbackQuery, session: AsyncSession) -> None:
    if not callback.from_user or not await authorized_role(session, callback.from_user.id):
        return

    player_id = int(callback.data.split(":")[2])  # type: ignore[union-attr]
    lang = await lang_for(session, callback.from_user.id)
    player = await PlayersService(session).set_verified_coach(player_id, False)
    if player is None:
        await callback.answer()
        return
    await callback.message.answer(  # type: ignore[union-attr]
        t("players_coach_revoked", lang, name=_md(player.first_name)), parse_mode="Markdown"
    )
    await _show_details(callback.message, session, lang, player_id)  # type: ignore[arg-type]
    await callback.answer()
