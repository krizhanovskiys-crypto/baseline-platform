"""Tournament Platform v1 (Sprint 12) — Browse, plus (Sprint 12.2) the
role-aware Tournament Menu that is the single entry point for Create
Tournament and My Tournaments too. /dev no longer plays any part in
reaching tournament features for a Verified Coach — the Role Resolver
below is the one place that decides what a given account sees.

Tournament Details itself does not live here or in
bot/handlers/admin/tournaments.py — it's one unified screen,
show_tournament_details() in bot/handlers/helpers.py, opened via
tourn:open:<id> from Browse, My Tournaments, or Admin's own Tournament
Administration alike. There is no separate Player/Admin Details.
"""
from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.markdown import markdown_decoration
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.bot.handlers.admin.common import lang_for
from backend.app.bot.handlers.helpers import (
    get_player_lang,
    notify_tournament_registration_closed,
    send_main_menu,
    show_tournament_details,
)
from backend.app.bot.keyboards.keyboards import tournament_browse_keyboard, tournament_menu_keyboard
from backend.app.bot.states.states import CreateTournamentStates, MyTournamentsStates, TournamentBrowseStates
from backend.app.bot.texts import t
from backend.app.services.player_service import PlayerService
from backend.app.services.tournament_service import PAGE_SIZE, TournamentService

router = Router(name="tournament")


def _md(value: str) -> str:
    """Escape a free-text, organizer-entered value (tournament name)
    before it goes into parse_mode="Markdown" text — same rule as
    Tournament Details' own escaping (docs/PRODUCT_DECISIONS.md)."""
    return markdown_decoration.quote(value)

_TRIGGER_TEXTS = {"🏆 Tournaments", "🏆 Турніри", "🏆 Турниры"}


async def _show_browse(
    message: Message, session: AsyncSession, state: FSMContext, lang: str, page: int
) -> None:
    service = TournamentService(session)
    tournaments, total = await service.list_tournaments(page)
    total_pages = max(1, -(-total // PAGE_SIZE))

    await state.set_state(TournamentBrowseStates.browsing)
    await state.update_data(current_page=page)

    if not tournaments:
        await message.answer(t("tournament_browse_empty", lang), parse_mode="Markdown")
        return

    await message.answer(
        t("tournament_browse_header", lang, total=total),
        reply_markup=tournament_browse_keyboard(
            lang, tournaments, page, has_prev=page > 1, has_next=page < total_pages,
            open_prefix="tourn:open", back_callback="tourn_p:menu",
        ),
        parse_mode="Markdown",
    )


async def _show_my_tournaments(
    message: Message, session: AsyncSession, state: FSMContext, lang: str, telegram_id: int, page: int
) -> None:
    """My Tournaments (Sprint 12.2) — only tournaments organized by this
    Coach, unlike Browse which lists every visible tournament. Opening
    one routes through the existing admin-style Details
    (tourn:open:<id>, bot/handlers/admin/tournaments.py) since these
    are tournaments this account can manage, not just register for."""
    service = TournamentService(session)
    tournaments, total = await service.list_my_tournaments(telegram_id, page)
    total_pages = max(1, -(-total // PAGE_SIZE))

    await state.set_state(MyTournamentsStates.browsing)
    await state.update_data(current_page=page)

    if not tournaments:
        await message.answer(t("tournament_browse_empty", lang), parse_mode="Markdown")
        return

    await message.answer(
        t("tournament_browse_header", lang, total=total),
        reply_markup=tournament_browse_keyboard(
            lang, tournaments, page, has_prev=page > 1, has_next=page < total_pages,
            open_prefix="tourn:open", back_callback="tourn_p:menu",
        ),
        parse_mode="Markdown",
    )


# ── Entry / navigation ────────────────────────────────────────────────────────

@router.message(F.text.in_(_TRIGGER_TEXTS))
async def tournament_menu_entry(message: Message, session: AsyncSession) -> None:
    """The single Role Resolver (Sprint 12.2): one permission check,
    reused unchanged (TournamentService.can_create_tournament), decides
    whether this account sees the Player menu (Browse only) or the
    Coach menu (Create / My Tournaments / Browse) — never duplicated
    elsewhere."""
    user = message.from_user
    if not user:
        return
    player = await PlayerService(session).get_by_telegram_id(user.id)
    lang = get_player_lang(player)
    is_coach = await TournamentService(session).can_create_tournament(user.id)
    await message.answer(
        t("tournament_menu_header", lang),
        reply_markup=tournament_menu_keyboard(lang, is_coach),
        parse_mode="Markdown",
    )


@router.callback_query(F.data == "tourn_p:create")
async def tourn_p_create_start(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    """Create Tournament, started from the Main Menu (Sprint 12.2) —
    same permission check and the same CreateTournamentStates wizard as
    the Admin's own tourn:create (admin/tournaments.py); every step
    after this one is state-gated and already shared."""
    if not callback.from_user or not await TournamentService(session).can_create_tournament(callback.from_user.id):
        return
    lang = await lang_for(session, callback.from_user.id)
    await state.set_state(CreateTournamentStates.enter_name)
    await state.update_data(lang=lang, editing_id=None)
    await callback.message.answer(t("tournament_enter_name", lang), parse_mode="Markdown")  # type: ignore[union-attr]
    await callback.answer()


@router.callback_query(F.data == "tourn_p:mine")
async def tourn_p_mine(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    if not callback.from_user or not await TournamentService(session).can_create_tournament(callback.from_user.id):
        return
    lang = await lang_for(session, callback.from_user.id)
    await _show_my_tournaments(callback.message, session, state, lang, callback.from_user.id, page=1)  # type: ignore[arg-type]
    await callback.answer()


@router.callback_query(MyTournamentsStates.browsing, F.data.regexp(r"^tourn:page:\d+$"))
async def tourn_p_mine_page(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    if not callback.from_user or not await TournamentService(session).can_create_tournament(callback.from_user.id):
        return
    page = int(callback.data.split(":")[2])  # type: ignore[union-attr]
    lang = await lang_for(session, callback.from_user.id)
    await _show_my_tournaments(callback.message, session, state, lang, callback.from_user.id, page=page)  # type: ignore[arg-type]
    await callback.answer()


@router.callback_query(TournamentBrowseStates.browsing, F.data.regexp(r"^tourn:page:\d+$"))
async def tournament_page(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    if not callback.data or not callback.message:
        await callback.answer()
        return
    page = int(callback.data.split(":")[2])
    player = await PlayerService(session).get_by_telegram_id(callback.from_user.id)
    lang = get_player_lang(player)
    await callback.answer()
    await _show_browse(callback.message, session, state, lang, page=page)


@router.callback_query(F.data == "tourn_p:menu")
async def tournament_back_to_menu(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    if not callback.message:
        await callback.answer()
        return
    await state.clear()
    player = await PlayerService(session).get_by_telegram_id(callback.from_user.id)
    lang = get_player_lang(player)
    await callback.answer()
    await send_main_menu(callback.message, lang)


@router.callback_query(F.data == "tourn_p:browse")
async def tournament_back_to_browse(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    if not callback.message:
        await callback.answer()
        return
    player = await PlayerService(session).get_by_telegram_id(callback.from_user.id)
    lang = get_player_lang(player)
    await callback.answer()
    await _show_browse(callback.message, session, state, lang, page=1)


# ── Register / Withdraw ───────────────────────────────────────────────────────
# Reached only from the one unified Tournament Details screen
# (tournament_details_keyboard, bot/keyboards/keyboards.py) — same
# callback namespace as Details itself (tourn:*), open to any player.

@router.callback_query(F.data.regexp(r"^tourn:register:\d+$"))
async def tournament_register(callback: CallbackQuery, session: AsyncSession, bot: Bot) -> None:
    if not callback.data or not callback.message:
        await callback.answer()
        return
    tournament_id = int(callback.data.split(":")[2])
    user = callback.from_user
    player = await PlayerService(session).get_by_telegram_id(user.id)
    lang = get_player_lang(player)

    service = TournamentService(session)
    registered, just_closed = await service.register_player(tournament_id, user.id)
    tournament = await service.get_tournament(tournament_id)

    if registered:
        await callback.message.answer(
            t("tournament_register_success", lang, name=_md(tournament.name) if tournament else ""),
            parse_mode="Markdown",
        )
        if just_closed:
            await notify_tournament_registration_closed(bot, session, tournament_id)
    else:
        await callback.message.answer(t("tournament_register_closed", lang), parse_mode="Markdown")

    await callback.answer()
    await show_tournament_details(callback.message, session, bot, lang, user.id, tournament_id)


@router.callback_query(F.data.regexp(r"^tourn:withdraw:\d+$"))
async def tournament_withdraw(callback: CallbackQuery, session: AsyncSession, bot: Bot) -> None:
    if not callback.data or not callback.message:
        await callback.answer()
        return
    tournament_id = int(callback.data.split(":")[2])
    user = callback.from_user
    player = await PlayerService(session).get_by_telegram_id(user.id)
    lang = get_player_lang(player)

    service = TournamentService(session)
    tournament = await service.get_tournament(tournament_id)
    withdrawn = await service.withdraw_player(tournament_id, user.id)

    if withdrawn:
        await callback.message.answer(
            t("tournament_withdraw_success", lang, name=_md(tournament.name) if tournament else ""),
            parse_mode="Markdown",
        )
    else:
        await callback.message.answer(t("tournament_withdraw_failed", lang), parse_mode="Markdown")

    await callback.answer()
    await show_tournament_details(callback.message, session, bot, lang, user.id, tournament_id)
