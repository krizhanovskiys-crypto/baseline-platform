"""Tournament Platform v1, Phase 1 (Sprint 12) — player-facing Browse /
Details / Register / Withdraw. Tournament creation and management are
deliberately NOT here — they live under /dev only
(bot/handlers/admin/tournaments.py), reached by Admins and Verified
Coaches, never from the Main Menu.
"""
from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.markdown import markdown_decoration
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.bot.handlers.helpers import get_player_lang, notify_tournament_registration_closed, send_main_menu
from backend.app.bot.keyboards.keyboards import tournament_browse_keyboard, tournament_player_details_keyboard
from backend.app.bot.states.states import TournamentBrowseStates
from backend.app.bot.texts import t
from backend.app.services.player_service import PlayerService
from backend.app.services.tournament_service import PAGE_SIZE, TournamentService

router = Router(name="tournament")


def _md(value: str) -> str:
    """Escape a free-text, organizer-entered value (tournament name)
    before it goes into parse_mode="Markdown" text — same rule as
    Player Details' own escaping (docs/PRODUCT_DECISIONS.md)."""
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
            open_prefix="tourn_p:open", back_callback="tourn_p:menu",
        ),
        parse_mode="Markdown",
    )


async def _show_details(
    message: Message, session: AsyncSession, bot: Bot, lang: str, telegram_id: int, tournament_id: int
) -> None:
    service = TournamentService(session)

    just_closed = await service.check_and_auto_close(tournament_id)
    if just_closed:
        await notify_tournament_registration_closed(bot, session, tournament_id)

    tournament = await service.get_tournament(tournament_id)
    if tournament is None:
        await message.answer(t("tournament_browse_empty", lang), parse_mode="Markdown")
        return

    registered_count = await service.count_registered(tournament_id)
    registrations = await service.get_registered_players(tournament_id)
    is_registered = any(r.telegram_id == telegram_id for r in registrations)

    from backend.app.database.models.tournament import TournamentStatus

    note_key = (
        "tournament_registration_open_note"
        if tournament.status == TournamentStatus.REGISTRATION_OPEN
        else "tournament_registration_closed_note"
    )
    note = t(note_key, lang, deadline=tournament.registration_deadline.strftime("%d.%m.%Y"))

    await message.answer(
        t(
            "tournament_details_player",
            lang,
            name=_md(tournament.name),
            area=tournament.area,
            court=tournament.court,
            start_date=tournament.start_date.strftime("%d.%m.%Y"),
            start_time=tournament.start_time.strftime("%H:%M"),
            registered=registered_count,
            max_players=tournament.max_players,
            registration_note=note,
        ),
        reply_markup=tournament_player_details_keyboard(lang, tournament_id, is_registered),
        parse_mode="Markdown",
    )


# ── Entry / navigation ────────────────────────────────────────────────────────

@router.message(F.text.in_(_TRIGGER_TEXTS))
async def tournament_browse_entry(message: Message, state: FSMContext, session: AsyncSession) -> None:
    user = message.from_user
    if not user:
        return
    player = await PlayerService(session).get_by_telegram_id(user.id)
    lang = get_player_lang(player)
    await _show_browse(message, session, state, lang, page=1)


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


@router.callback_query(F.data.regexp(r"^tourn_p:open:\d+$"))
async def tournament_open_details(callback: CallbackQuery, session: AsyncSession, bot: Bot) -> None:
    if not callback.data or not callback.message:
        await callback.answer()
        return
    tournament_id = int(callback.data.split(":")[2])
    user = callback.from_user
    player = await PlayerService(session).get_by_telegram_id(user.id)
    lang = get_player_lang(player)
    await callback.answer()
    await _show_details(callback.message, session, bot, lang, user.id, tournament_id)


# ── Register / Withdraw ───────────────────────────────────────────────────────

@router.callback_query(F.data.regexp(r"^tourn_p:register:\d+$"))
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
    await _show_details(callback.message, session, bot, lang, user.id, tournament_id)


@router.callback_query(F.data.regexp(r"^tourn_p:withdraw:\d+$"))
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
    await _show_details(callback.message, session, bot, lang, user.id, tournament_id)
