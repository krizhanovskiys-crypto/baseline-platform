"""Universal Player Picker (Sprint 12.3) — a reusable platform
component, not owned by Tournament. Any future consumer that needs to
pick a player from a menu (Search vs. browse-by-level) reuses this
router unchanged; only the final "what happens when a player is
selected" action is consumer-specific, resolved from
picker_context_type stored in FSM data when the picker was entered.

Today's only consumer is Tournament's Add Player. Wiring a second
consumer means adding one more branch to _perform_selection() below —
none of the menu, level-grouping, pagination, or exclusion logic is
duplicated or Tournament-specific.

Search itself is NOT reimplemented here: PlayersService.search() (the
existing Admin Center Player Search) and the established three-way
branch (one match / several / none) still live in
bot/handlers/admin/tournaments.py, reused as-is — this module only
adds the menu step in front of it and the new "All Players" level
browsing.
"""
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.markdown import markdown_decoration
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.bot.handlers.admin.common import lang_for
from backend.app.bot.keyboards.keyboards import player_picker_levels_keyboard, player_picker_players_keyboard
from backend.app.bot.states.states import PlayerPickerStates
from backend.app.bot.texts import t
from backend.app.data.player_levels import LEVEL_GROUPS
from backend.app.services.players_service import PAGE_SIZE as PICKER_PAGE_SIZE
from backend.app.services.players_service import PlayersService
from backend.app.services.tournament_service import TournamentService

router = Router(name="player_picker")


def _format_level_label(lang: str, min_level: float, max_level: float | None) -> str:
    if max_level is None:
        return t("picker_level_group_label_plus", lang, min=min_level)
    return t("picker_level_group_label_range", lang, min=min_level, max=max_level)


async def _exclude_ids_for_context(session: AsyncSession, data: dict) -> set[int]:
    """The only consumer-specific lookup in this module: which player
    ids are already "taken" for the active context, so the level list
    excludes them. Extend this (not the rest of the module) for a
    future consumer."""
    if data.get("picker_context_type") == "tournament_add_player":
        registrations = await TournamentService(session).get_registered_players(data["picker_tournament_id"])
        return {r.player_id for r in registrations}
    return set()


async def _perform_selection(session: AsyncSession, data: dict, player_telegram_id: int) -> bool:
    """The only consumer-specific action in this module: what
    "selecting" a player actually does. Extend this for a future
    consumer, same as _exclude_ids_for_context()."""
    if data.get("picker_context_type") == "tournament_add_player":
        return await TournamentService(session).admin_add_player(data["picker_tournament_id"], player_telegram_id)
    return False


async def show_levels(message: Message, session: AsyncSession, state: FSMContext, lang: str) -> None:
    """All Players — SQL-computed counts per configured level group,
    already excluding whatever the active context needs excluded."""
    data = await state.get_data()
    exclude_ids = await _exclude_ids_for_context(session, data)
    counts = await PlayersService(session).level_group_counts(exclude_ids)

    await state.set_state(PlayerPickerStates.browsing_levels)

    groups = [
        (i, _format_level_label(lang, g.min_level, g.max_level), counts[i])
        for i, g in enumerate(LEVEL_GROUPS)
    ]
    back_callback = data.get("picker_menu_callback", "pp:menu")
    await message.answer(
        t("picker_levels_header", lang),
        reply_markup=player_picker_levels_keyboard(lang, groups, back_callback),
        parse_mode="Markdown",
    )


async def show_players_in_level(
    message: Message, session: AsyncSession, state: FSMContext, lang: str, group_index: int, page: int
) -> None:
    """Alphabetical, paginated players within one level group, always
    excluding whatever the active context needs excluded — recomputed
    fresh every time so a just-added player never reappears."""
    data = await state.get_data()
    exclude_ids = await _exclude_ids_for_context(session, data)
    players, total = await PlayersService(session).get_level_group_page(group_index, page, exclude_ids)
    total_pages = max(1, -(-total // PICKER_PAGE_SIZE))

    await state.set_state(PlayerPickerStates.browsing_players)
    await state.update_data(picker_group_index=group_index, picker_page=page)

    group = LEVEL_GROUPS[group_index]
    label = _format_level_label(lang, group.min_level, group.max_level)

    if not players:
        await message.answer(t("picker_players_empty", lang), parse_mode="Markdown")
        return

    await message.answer(
        t("picker_players_header", lang, label=label, page=page, total_pages=total_pages),
        reply_markup=player_picker_players_keyboard(
            lang, players, page, has_prev=page > 1, has_next=page < total_pages,
            group_index=group_index, back_callback="pp:levels",
        ),
        parse_mode="Markdown",
    )


@router.callback_query(F.data == "pp:levels")
async def pp_levels(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    if not callback.from_user or not callback.message:
        await callback.answer()
        return
    lang = await lang_for(session, callback.from_user.id)
    await show_levels(callback.message, session, state, lang)  # type: ignore[arg-type]
    await callback.answer()


@router.callback_query(F.data.regexp(r"^pp:level:\d+:\d+$"))
async def pp_level_page(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    if not callback.from_user or not callback.data or not callback.message:
        await callback.answer()
        return
    _, _, group_index_s, page_s = callback.data.split(":")
    lang = await lang_for(session, callback.from_user.id)
    await show_players_in_level(callback.message, session, state, lang, int(group_index_s), int(page_s))  # type: ignore[arg-type]
    await callback.answer()


@router.callback_query(F.data.regexp(r"^pp:select:\d+$"))
async def pp_select(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    """Tapping a player immediately selects (registers) them — no
    confirmation step — then returns to the same level group and page,
    never the beginning."""
    if not callback.from_user or not callback.data or not callback.message:
        await callback.answer()
        return

    player_id = int(callback.data.split(":")[2])
    lang = await lang_for(session, callback.from_user.id)
    data = await state.get_data()

    player = await PlayersService(session).get_by_id(player_id)
    if player is None:
        await callback.answer()
        return

    added = await _perform_selection(session, data, player.telegram_id)
    key = "tournament_add_player_success" if added else "tournament_add_player_not_registered"
    await callback.message.answer(  # type: ignore[union-attr]
        t(key, lang, name=markdown_decoration.quote(player.first_name)), parse_mode="Markdown"
    )

    group_index = data.get("picker_group_index", 0)
    page = data.get("picker_page", 1)
    await show_players_in_level(callback.message, session, state, lang, group_index, page)  # type: ignore[arg-type]
    await callback.answer()
