"""Tournament Platform v1 (Sprint 12) — Admin Tournament Administration.

Reached via Dashboard's "Tournaments" button (PIN session already
active) — /dev is Admin/Owner only (Sprint 12.2 Coach UX Refactor
removed the Verified Coach's direct /dev path; a Coach now reaches
tournament features from the Main Menu's own role-aware 🏆 Tournaments
menu, bot/handlers/tournament.py). Create Tournament's wizard here
still serves both an Admin acting from Dashboard and a Coach who
started the same wizard from the Main Menu — the permission checks
below are unchanged and decide per-account, not per-entry-point. Never
authorized_role(), which strictly requires a PIN session a coach never
has.

Tournament Details is one unified screen, not a separate Player/Admin
variant — show_tournament_details() (bot/handlers/helpers.py) decides
which buttons appear per-tournament via can_manage_tournament(); this
module never renders Details itself. Sprint 12.2 also removed every
remaining path that sent a Coach back to this module's own Tournament
Center screen (tourn_do_cancel, tourn_delete) — a Coach now returns to
the role-aware Tournament Menu instead (show_tournament_menu()); only
an Admin still sees this screen, via Dashboard.

Two separate, centralized permission checks, deliberately not merged
(they answer different questions and will diverge further once a
Tournament Organizer permission exists):
- can_create_tournament() — blanket: gates Tournament Center access,
  Create Tournament, and (this module's own) Browse.
- can_manage_tournament() — ownership-aware: gates every action on one
  specific, existing tournament (Edit, Open/Close Registration,
  View/Add/Remove Players, Generate Matches, Delete). Admin manages any
  tournament; Verified Coach manages only tournaments they organized.

Tournament matches are NOT a new entity — Generate Matches creates
ordinary Games via the existing GameService, tagged with tournament_id,
always owned by the Tournament Organizer. No new match or invitation
architecture.
"""
import logging
from datetime import date, datetime, time

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.markdown import markdown_decoration
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.bot.handlers.admin.common import lang_for
from backend.app.bot.handlers.helpers import (
    notify_tournament_registration_closed,
    show_tournament_details,
    show_tournament_menu,
)
from backend.app.bot.keyboards.keyboards import (
    area_keyboard,
    player_picker_menu_keyboard,
    tournament_add_player_results_keyboard,
    tournament_browse_keyboard,
    tournament_center_keyboard,
    tournament_confirm_keyboard,
    tournament_court_keyboard,
    tournament_registered_players_keyboard,
)
from backend.app.bot.states.states import AdminTournamentsStates, CreateTournamentStates, PlayerPickerStates
from backend.app.bot.texts import t
from backend.app.data.courts import get_courts_for_zone
from backend.app.schemas.tournament import TournamentCreate, TournamentUpdate
from backend.app.services.permission_service import PermissionService
from backend.app.services.players_service import PlayersService
from backend.app.services.tournament_service import PAGE_SIZE, TournamentService, is_power_of_two

logger = logging.getLogger(__name__)
router = Router(name="admin_tournaments")


def _md(value: str) -> str:
    """Escape a free-text, organizer-entered value (tournament name)
    before it goes into parse_mode="Markdown" text — same rule and same
    aiogram helper as Player Details' own escaping (docs/PRODUCT_DECISIONS.md)."""
    return markdown_decoration.quote(value)


async def _can_create(session: AsyncSession, telegram_id: int) -> bool:
    """Blanket check — Tournament Center access, Create, Browse."""
    return await TournamentService(session).can_create_tournament(telegram_id)


async def _can_manage_specific(session: AsyncSession, telegram_id: int, tournament) -> bool:
    """Ownership-aware check for a specific, already-fetched tournament."""
    if tournament is None:
        return False
    return await TournamentService(session).can_manage_tournament(telegram_id, tournament.organizer_player_id)


async def _is_operator(session: AsyncSession, telegram_id: int) -> bool:
    return await PermissionService(session).is_operator(telegram_id)


async def show_tournament_center(message: Message, session: AsyncSession, lang: str, is_operator: bool) -> None:
    """The shared Tournament Center root — reached from /dev (coach, no
    PIN, "My Tournaments") or Dashboard (admin, PIN already active,
    "Tournaments" — manages every tournament, not just their own)."""
    header_key = "tournament_center_header" if is_operator else "tournament_my_tournaments_header"
    await message.answer(
        t(header_key, lang),
        reply_markup=tournament_center_keyboard(lang, is_operator),
        parse_mode="Markdown",
    )


async def _show_browse(message: Message, session: AsyncSession, state: FSMContext, lang: str, page: int) -> None:
    service = TournamentService(session)
    tournaments, total = await service.list_tournaments(page)
    total_pages = max(1, -(-total // PAGE_SIZE))

    await state.set_state(AdminTournamentsStates.browsing)
    await state.update_data(current_page=page)

    await message.answer(t("tournament_browse_header", lang, total=total), parse_mode="Markdown")
    if not tournaments:
        await message.answer(t("tournament_browse_empty", lang))
        return

    await message.answer(
        t("tournament_browse_header", lang, total=total),
        reply_markup=tournament_browse_keyboard(
            lang, tournaments, page, has_prev=page > 1, has_next=page < total_pages,
            open_prefix="tourn:open", back_callback="tourn:menu",
        ),
        parse_mode="Markdown",
    )


# ── Entry / navigation ────────────────────────────────────────────────────────

@router.callback_query(F.data == "tourn:browse")
async def tourn_browse(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    if not callback.from_user or not await _can_create(session, callback.from_user.id):
        return
    lang = await lang_for(session, callback.from_user.id)
    await _show_browse(callback.message, session, state, lang, page=1)  # type: ignore[arg-type]
    await callback.answer()


@router.callback_query(AdminTournamentsStates.browsing, F.data.regexp(r"^tourn:page:\d+$"))
async def tourn_page(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    if not callback.from_user or not await _can_create(session, callback.from_user.id):
        return
    page = int(callback.data.split(":")[2])  # type: ignore[union-attr]
    lang = await lang_for(session, callback.from_user.id)
    await _show_browse(callback.message, session, state, lang, page=page)  # type: ignore[arg-type]
    await callback.answer()


@router.callback_query(F.data == "tourn:menu")
async def tourn_menu(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    if not callback.from_user or not await _can_create(session, callback.from_user.id):
        return
    await state.clear()
    lang = await lang_for(session, callback.from_user.id)
    is_operator = await _is_operator(session, callback.from_user.id)
    await show_tournament_center(callback.message, session, lang, is_operator)  # type: ignore[arg-type]
    await callback.answer()


@router.callback_query(F.data.regexp(r"^tourn:open:\d+$"))
async def tourn_open(callback: CallbackQuery, session: AsyncSession, bot: Bot) -> None:
    """Opens the one Tournament Details screen (Sprint 12.2) — never
    gated by can_create_tournament(): viewing/registering is open to
    any player, not just Admin/Coach. show_tournament_details() decides
    which management buttons appear, per-tournament, via
    can_manage_tournament()."""
    if not callback.from_user:
        return
    tournament_id = int(callback.data.split(":")[2])  # type: ignore[union-attr]
    lang = await lang_for(session, callback.from_user.id)
    await show_tournament_details(callback.message, session, bot, lang, callback.from_user.id, tournament_id)  # type: ignore[arg-type]
    await callback.answer()


# ── Create Tournament wizard ─────────────────────────────────────────────────

@router.callback_query(F.data == "tourn:create")
async def tourn_create_start(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    if not callback.from_user or not await _can_create(session, callback.from_user.id):
        return
    lang = await lang_for(session, callback.from_user.id)
    await state.set_state(CreateTournamentStates.enter_name)
    await state.update_data(lang=lang, editing_id=None)
    await callback.message.answer(t("tournament_enter_name", lang), parse_mode="Markdown")  # type: ignore[union-attr]
    await callback.answer()


@router.message(CreateTournamentStates.enter_name)
async def tourn_enter_name(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data.get("lang", "en")
    name = (message.text or "").strip()
    if not name:
        return
    await state.update_data(name=name)
    await state.set_state(CreateTournamentStates.choose_area)
    await message.answer(
        t("choose_area", lang), reply_markup=area_keyboard(lang, callback_prefix="tourn_area"), parse_mode="Markdown"
    )


@router.callback_query(CreateTournamentStates.choose_area, F.data.startswith("tourn_area:"))
async def tourn_choose_area(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data.get("lang", "en")
    zone = callback.data.split(":", 1)[1]  # type: ignore[union-attr]
    await state.update_data(area=zone)
    await state.set_state(CreateTournamentStates.choose_court)
    courts = get_courts_for_zone(zone)
    await state.update_data(courts_shown=courts)
    await callback.message.answer(  # type: ignore[union-attr]
        t("tournament_choose_court", lang), reply_markup=tournament_court_keyboard(lang, courts), parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query(CreateTournamentStates.choose_court, F.data == "tourn:court_custom")
async def tourn_court_custom_prompt(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data.get("lang", "en")
    await state.set_state(CreateTournamentStates.enter_custom_court)
    await callback.message.answer(t("tournament_enter_court", lang), parse_mode="Markdown")  # type: ignore[union-attr]
    await callback.answer()


@router.callback_query(CreateTournamentStates.choose_court, F.data.startswith("tourn_court:"))
async def tourn_choose_court(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data.get("lang", "en")
    idx = int(callback.data.split(":")[1])  # type: ignore[union-attr]
    courts_shown: list[str] = data.get("courts_shown", [])
    if idx < 0 or idx >= len(courts_shown):
        await callback.answer()
        return
    await state.update_data(court=courts_shown[idx])
    await state.set_state(CreateTournamentStates.enter_date)
    await callback.message.answer(t("tournament_enter_date", lang), parse_mode="Markdown")  # type: ignore[union-attr]
    await callback.answer()


@router.message(CreateTournamentStates.enter_custom_court)
async def tourn_custom_court_submit(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data.get("lang", "en")
    court = (message.text or "").strip()
    if not court:
        return
    await state.update_data(court=court)
    await state.set_state(CreateTournamentStates.enter_date)
    await message.answer(t("tournament_enter_date", lang), parse_mode="Markdown")


@router.message(CreateTournamentStates.enter_date)
async def tourn_enter_date(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data.get("lang", "en")
    text = (message.text or "").strip()
    try:
        parsed = datetime.strptime(text, "%d.%m.%Y").date()
    except ValueError:
        await message.answer(t("tournament_error_date", lang), parse_mode="Markdown")
        return
    await state.update_data(start_date=parsed.isoformat())
    await state.set_state(CreateTournamentStates.enter_time)
    await message.answer(t("tournament_enter_time", lang), parse_mode="Markdown")


@router.message(CreateTournamentStates.enter_time)
async def tourn_enter_time(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data.get("lang", "en")
    text = (message.text or "").strip()
    try:
        datetime.strptime(text, "%H:%M")
    except ValueError:
        await message.answer(t("tournament_error_time", lang), parse_mode="Markdown")
        return
    await state.update_data(start_time=text)
    await state.set_state(CreateTournamentStates.enter_deadline)
    await message.answer(t("tournament_enter_deadline", lang), parse_mode="Markdown")


@router.message(CreateTournamentStates.enter_deadline)
async def tourn_enter_deadline(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data.get("lang", "en")
    text = (message.text or "").strip()
    try:
        deadline = datetime.strptime(text, "%d.%m.%Y").date()
    except ValueError:
        await message.answer(t("tournament_error_deadline", lang), parse_mode="Markdown")
        return
    start_date = date.fromisoformat(data["start_date"])
    if deadline > start_date:
        await message.answer(t("tournament_error_deadline", lang), parse_mode="Markdown")
        return
    await state.update_data(registration_deadline=deadline.isoformat())
    await state.set_state(CreateTournamentStates.enter_max_players)
    await message.answer(t("tournament_enter_max_players", lang), parse_mode="Markdown")


@router.message(CreateTournamentStates.enter_max_players)
async def tourn_enter_max_players(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data.get("lang", "en")
    text = (message.text or "").strip()
    if not text.isdigit() or not is_power_of_two(int(text)):
        await message.answer(t("tournament_error_max_players", lang), parse_mode="Markdown")
        return
    await state.update_data(max_players=int(text))
    await state.set_state(CreateTournamentStates.confirm)
    data = await state.get_data()
    await message.answer(
        t(
            "tournament_confirm",
            lang,
            name=_md(data["name"]),
            area=data["area"],
            court=data["court"],
            start_date=data["start_date"],
            start_time=data["start_time"],
            deadline=data["registration_deadline"],
            max_players=data["max_players"],
        ),
        reply_markup=tournament_confirm_keyboard(lang),
        parse_mode="Markdown",
    )


@router.callback_query(CreateTournamentStates.confirm, F.data == "tourn:confirm")
async def tourn_do_confirm(callback: CallbackQuery, session: AsyncSession, state: FSMContext, bot: Bot) -> None:
    data = await state.get_data()
    lang = data.get("lang", "en")
    user = callback.from_user
    if not user:
        await callback.answer()
        return

    service = TournamentService(session)
    tournament_data = TournamentCreate(
        name=data["name"],
        area=data["area"],
        court=data["court"],
        start_date=date.fromisoformat(data["start_date"]),
        start_time=time.fromisoformat(data["start_time"] + ":00"),
        registration_deadline=date.fromisoformat(data["registration_deadline"]),
        max_players=data["max_players"],
    )

    editing_id = data.get("editing_id")
    if editing_id:
        await service.edit_tournament(
            editing_id,
            TournamentUpdate(
                name=tournament_data.name,
                area=tournament_data.area,
                court=tournament_data.court,
                start_date=tournament_data.start_date,
                start_time=tournament_data.start_time,
                registration_deadline=tournament_data.registration_deadline,
                max_players=tournament_data.max_players,
            ),
        )
        await state.clear()
        await callback.message.answer(t("tournament_created", lang), parse_mode="Markdown")  # type: ignore[union-attr]
        await show_tournament_details(callback.message, session, bot, lang, user.id, editing_id)  # type: ignore[arg-type]
        await callback.answer()
        return

    tournament = await service.create_tournament(user.id, tournament_data)
    await state.clear()
    if not tournament:
        await callback.message.answer(t("error_generic", lang), parse_mode="Markdown")  # type: ignore[union-attr]
        await callback.answer()
        return

    await callback.message.answer(t("tournament_created", lang), parse_mode="Markdown")  # type: ignore[union-attr]
    await show_tournament_details(callback.message, session, bot, lang, user.id, tournament.id)  # type: ignore[arg-type]
    await callback.answer()


@router.callback_query(CreateTournamentStates.confirm, F.data == "tourn:cancel")
async def tourn_do_cancel(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data.get("lang", "en")
    await state.clear()
    await callback.message.answer(t("cancelled", lang), parse_mode="Markdown")  # type: ignore[union-attr]
    # Sprint 12.2: a Verified Coach must never land back on the old
    # Tournament Center — only an Admin does. Everyone else returns to
    # the role-aware Tournament Menu instead.
    is_operator = await _is_operator(session, callback.from_user.id)
    if is_operator:
        await show_tournament_center(callback.message, session, lang, is_operator)  # type: ignore[arg-type]
    else:
        await show_tournament_menu(callback.message, session, lang, callback.from_user.id)  # type: ignore[arg-type]
    await callback.answer()


# ── Edit Tournament (reuses the create wizard, branching at confirm) ─────────

@router.callback_query(F.data.regexp(r"^tourn:edit:\d+$"))
async def tourn_edit_start(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    if not callback.from_user:
        return
    tournament_id = int(callback.data.split(":")[2])  # type: ignore[union-attr]
    lang = await lang_for(session, callback.from_user.id)
    tournament = await TournamentService(session).get_tournament(tournament_id)
    if tournament is None or not await _can_manage_specific(session, callback.from_user.id, tournament):
        await callback.answer()
        return
    await state.set_state(CreateTournamentStates.enter_name)
    await state.update_data(lang=lang, editing_id=tournament_id)
    await callback.message.answer(  # type: ignore[union-attr]
        t("tournament_enter_name", lang) + f"\n\n_{_md(tournament.name)}_", parse_mode="Markdown"
    )
    await callback.answer()


# ── Lifecycle actions ─────────────────────────────────────────────────────────

@router.callback_query(F.data.regexp(r"^tourn:open_reg:\d+$"))
async def tourn_open_registration(callback: CallbackQuery, session: AsyncSession, bot: Bot) -> None:
    if not callback.from_user:
        return
    tournament_id = int(callback.data.split(":")[2])  # type: ignore[union-attr]
    service = TournamentService(session)
    tournament = await service.get_tournament(tournament_id)
    if not await _can_manage_specific(session, callback.from_user.id, tournament):
        await callback.answer()
        return
    lang = await lang_for(session, callback.from_user.id)
    await service.open_registration(tournament_id)
    await show_tournament_details(callback.message, session, bot, lang, callback.from_user.id, tournament_id)  # type: ignore[arg-type]
    await callback.answer()


@router.callback_query(F.data.regexp(r"^tourn:close_reg:\d+$"))
async def tourn_close_registration(callback: CallbackQuery, session: AsyncSession, bot: Bot) -> None:
    if not callback.from_user:
        return
    tournament_id = int(callback.data.split(":")[2])  # type: ignore[union-attr]
    service = TournamentService(session)
    tournament = await service.get_tournament(tournament_id)
    if not await _can_manage_specific(session, callback.from_user.id, tournament):
        await callback.answer()
        return
    lang = await lang_for(session, callback.from_user.id)
    await service.close_registration(tournament_id)
    await notify_tournament_registration_closed(bot, session, tournament_id)
    await show_tournament_details(callback.message, session, bot, lang, callback.from_user.id, tournament_id)  # type: ignore[arg-type]
    await callback.answer()


@router.callback_query(F.data.regexp(r"^tourn:generate:\d+$"))
async def tourn_generate_matches(callback: CallbackQuery, session: AsyncSession, bot: Bot) -> None:
    if not callback.from_user:
        return
    tournament_id = int(callback.data.split(":")[2])  # type: ignore[union-attr]
    service = TournamentService(session)
    tournament = await service.get_tournament(tournament_id)
    if not await _can_manage_specific(session, callback.from_user.id, tournament):
        await callback.answer()
        return
    lang = await lang_for(session, callback.from_user.id)
    success, error_key = await service.generate_matches(tournament_id)
    if success:
        await callback.message.answer(t("tournament_generate_success", lang), parse_mode="Markdown")  # type: ignore[union-attr]
    else:
        await callback.message.answer(t(error_key, lang), parse_mode="Markdown")  # type: ignore[union-attr]
    await show_tournament_details(callback.message, session, bot, lang, callback.from_user.id, tournament_id)  # type: ignore[arg-type]
    await callback.answer()


@router.callback_query(F.data.regexp(r"^tourn:complete:\d+$"))
async def tourn_mark_completed(callback: CallbackQuery, session: AsyncSession, bot: Bot) -> None:
    if not callback.from_user:
        return
    tournament_id = int(callback.data.split(":")[2])  # type: ignore[union-attr]
    service = TournamentService(session)
    tournament = await service.get_tournament(tournament_id)
    if not await _can_manage_specific(session, callback.from_user.id, tournament):
        await callback.answer()
        return
    lang = await lang_for(session, callback.from_user.id)
    await service.mark_completed(tournament_id)
    await show_tournament_details(callback.message, session, bot, lang, callback.from_user.id, tournament_id)  # type: ignore[arg-type]
    await callback.answer()


@router.callback_query(F.data.regexp(r"^tourn:delete:\d+$"))
async def tourn_delete(callback: CallbackQuery, session: AsyncSession) -> None:
    if not callback.from_user:
        return
    tournament_id = int(callback.data.split(":")[2])  # type: ignore[union-attr]
    service = TournamentService(session)
    tournament = await service.get_tournament(tournament_id)
    if not await _can_manage_specific(session, callback.from_user.id, tournament):
        await callback.answer()
        return
    lang = await lang_for(session, callback.from_user.id)
    await service.delete_tournament(tournament_id)
    await callback.message.answer(t("tournament_deleted", lang), parse_mode="Markdown")  # type: ignore[union-attr]
    # Sprint 12.2: same rule as tourn_do_cancel — a Coach never returns
    # to the old Tournament Center, only an Admin does.
    is_operator = await _is_operator(session, callback.from_user.id)
    if is_operator:
        await show_tournament_center(callback.message, session, lang, is_operator)  # type: ignore[arg-type]
    else:
        await show_tournament_menu(callback.message, session, lang, callback.from_user.id)  # type: ignore[arg-type]
    await callback.answer()


# ── View / Add / Remove Registered Players ───────────────────────────────────

@router.callback_query(F.data.regexp(r"^tourn:players:\d+$"))
async def tourn_view_players(callback: CallbackQuery, session: AsyncSession) -> None:
    if not callback.from_user:
        return
    tournament_id = int(callback.data.split(":")[2])  # type: ignore[union-attr]
    service = TournamentService(session)
    tournament = await service.get_tournament(tournament_id)
    if not await _can_manage_specific(session, callback.from_user.id, tournament):
        await callback.answer()
        return
    lang = await lang_for(session, callback.from_user.id)
    registrations = await service.get_registered_players(tournament_id)
    if not registrations:
        await callback.message.answer(t("tournament_players_empty", lang), parse_mode="Markdown")  # type: ignore[union-attr]
    else:
        await callback.message.answer(  # type: ignore[union-attr]
            t("tournament_players_header", lang, count=len(registrations)),
            reply_markup=tournament_registered_players_keyboard(lang, registrations, tournament_id),
            parse_mode="Markdown",
        )
    await callback.answer()


@router.callback_query(F.data.regexp(r"^tourn:remove_player:\d+:\d+$"))
async def tourn_remove_player(callback: CallbackQuery, session: AsyncSession) -> None:
    if not callback.from_user:
        return
    _, _, tournament_id_s, player_id_s = callback.data.split(":")  # type: ignore[union-attr]
    tournament_id, player_id = int(tournament_id_s), int(player_id_s)
    service = TournamentService(session)
    tournament = await service.get_tournament(tournament_id)
    if not await _can_manage_specific(session, callback.from_user.id, tournament):
        await callback.answer()
        return
    lang = await lang_for(session, callback.from_user.id)

    player = await PlayersService(session).get_by_id(player_id)
    if player:
        removed = await service.admin_remove_player(tournament_id, player.telegram_id)
        if removed:
            await callback.message.answer(  # type: ignore[union-attr]
                t("tournament_remove_player_success", lang, name=_md(player.first_name)), parse_mode="Markdown"
            )
    registrations = await service.get_registered_players(tournament_id)
    if registrations:
        await callback.message.answer(  # type: ignore[union-attr]
            t("tournament_players_header", lang, count=len(registrations)),
            reply_markup=tournament_registered_players_keyboard(lang, registrations, tournament_id),
            parse_mode="Markdown",
        )
    else:
        await callback.message.answer(t("tournament_players_empty", lang), parse_mode="Markdown")  # type: ignore[union-attr]
    await callback.answer()


@router.callback_query(F.data.regexp(r"^tourn:add_player:\d+$"))
async def tourn_add_player_prompt(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    """Add Player now opens the Universal Player Picker's menu (Sprint
    12.3) — Search or All Players — instead of jumping straight to a
    text prompt. This handler's only job is to set the Picker's context
    (which tournament, where "back" returns to); the menu itself and
    everything past it lives in bot/handlers/player_picker.py."""
    if not callback.from_user:
        return
    tournament_id = int(callback.data.split(":")[2])  # type: ignore[union-attr]
    tournament = await TournamentService(session).get_tournament(tournament_id)
    if not await _can_manage_specific(session, callback.from_user.id, tournament):
        await callback.answer()
        return
    lang = await lang_for(session, callback.from_user.id)
    await state.update_data(
        lang=lang,
        picker_context_type="tournament_add_player",
        picker_tournament_id=tournament_id,
        picker_menu_callback=f"tourn:open:{tournament_id}",
    )
    await callback.message.answer(  # type: ignore[union-attr]
        t("picker_menu_header", lang),
        reply_markup=player_picker_menu_keyboard(lang, back_callback=f"tourn:open:{tournament_id}"),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(F.data == "pp:search")
async def tourn_add_player_search_start(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    """The Picker's "🔍 Search" option — same prompt and same
    PlayersService.search() flow (tourn_add_player_submit below) that
    already existed before Sprint 12.3, just reached from the menu."""
    if not callback.from_user or not callback.message:
        await callback.answer()
        return
    lang = await lang_for(session, callback.from_user.id)
    await state.set_state(PlayerPickerStates.enter_search)
    await callback.message.answer(t("tournament_add_player_prompt", lang), parse_mode="Markdown")
    await callback.answer()


async def _add_player_to_tournament(
    message: Message, session: AsyncSession, bot: Bot, lang: str, acting_telegram_id: int, tournament_id: int, player
) -> None:
    added = await TournamentService(session).admin_add_player(tournament_id, player.telegram_id)
    key = "tournament_add_player_success" if added else "tournament_add_player_not_registered"
    await message.answer(t(key, lang, name=_md(player.first_name)), parse_mode="Markdown")
    await show_tournament_details(message, session, bot, lang, acting_telegram_id, tournament_id)


@router.message(PlayerPickerStates.enter_search)
async def tourn_add_player_submit(message: Message, session: AsyncSession, state: FSMContext, bot: Bot) -> None:
    """Reuses PlayersService.search() (the existing Admin Center Player
    Search — not a new one-off flow) and the same three-way branch every
    Admin Center search already follows: one match adds directly,
    several show a selectable list, none shows not-found. Reached from
    the Universal Player Picker's "🔍 Search" option (Sprint 12.3)."""
    user = message.from_user
    if not user:
        return
    data = await state.get_data()
    lang = data.get("lang", "en")
    tournament_id = data.get("picker_tournament_id")
    query = (message.text or "").strip()
    if not query or not tournament_id:
        return

    results = await PlayersService(session).search(query)
    await state.clear()

    if not results:
        await message.answer(t("tournament_add_player_not_registered", lang), parse_mode="Markdown")
        return

    if len(results) == 1:
        await _add_player_to_tournament(message, session, bot, lang, user.id, tournament_id, results[0])
        return

    await message.answer(
        t("players_search_results_header", lang, count=len(results)),
        reply_markup=tournament_add_player_results_keyboard(lang, results, tournament_id),
        parse_mode="Markdown",
    )


@router.callback_query(F.data.regexp(r"^tourn:add_player_pick:\d+:\d+$"))
async def tourn_add_player_pick(callback: CallbackQuery, session: AsyncSession, bot: Bot) -> None:
    if not callback.from_user:
        return
    _, _, tournament_id_s, player_id_s = callback.data.split(":")  # type: ignore[union-attr]
    tournament_id, player_id = int(tournament_id_s), int(player_id_s)
    tournament = await TournamentService(session).get_tournament(tournament_id)
    if not await _can_manage_specific(session, callback.from_user.id, tournament):
        await callback.answer()
        return
    lang = await lang_for(session, callback.from_user.id)
    player = await PlayersService(session).get_by_id(player_id)
    if player:
        await _add_player_to_tournament(callback.message, session, bot, lang, callback.from_user.id, tournament_id, player)  # type: ignore[arg-type]
    await callback.answer()
