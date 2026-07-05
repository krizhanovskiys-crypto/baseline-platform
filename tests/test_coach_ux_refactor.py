"""Regression tests for Sprint 12.2 — Coach UX Refactor.

Removes the dependency between Verified Coach and /dev. A Coach is a
business role, not an administrator: Tournament features are now
reached from the normal Main Menu's role-aware 🏆 Tournaments button
(bot/handlers/tournament.py's Role Resolver), never /dev. /dev remains
Admin/Owner only — Tournament Administration through Dashboard is
completely unchanged.

Permission logic itself is untouched (TournamentService.
can_create_tournament / can_manage_tournament, both reused exactly as
before) — only navigation changed, per the approved architecture.
"""
from datetime import date, time
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from aiogram.fsm.storage.memory import MemoryStorage
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.bot.handlers.admin.auth import cmd_dev
from backend.app.bot.handlers.admin.dashboard import dashboard_open_tournaments
from backend.app.bot.handlers.admin.tournaments import tourn_do_cancel, tourn_delete, tourn_open
from backend.app.bot.handlers.profile import show_profile
from backend.app.bot.handlers.tournament import tourn_p_create_start, tourn_p_mine, tournament_menu_entry
from backend.app.bot.states.states import CreateTournamentStates
from backend.app.database.models.operator_permission import OperatorRole
from backend.app.database.models.tournament import TournamentStatus
from backend.app.schemas.player import PlayerCreate, PlayerUpdate
from backend.app.schemas.tournament import TournamentCreate
from backend.app.services import admin_session_service as svc_module
from backend.app.services.admin_session_service import AdminSessionService
from backend.app.services.permission_service import PermissionService
from backend.app.services.player_service import PlayerService
from backend.app.services.players_service import PlayersService
from backend.app.services.tournament_lifecycle_service import TournamentLifecycleService
from backend.app.services.tournament_service import TournamentService

TEST_PIN = "4242"


@pytest.fixture(autouse=True)
def _clear_process_global_state():
    svc_module._sessions.clear()
    svc_module._attempts.clear()
    yield
    svc_module._sessions.clear()
    svc_module._attempts.clear()


def _with_pin():
    return patch("backend.app.services.admin_session_service.get_settings")


def _make_state(user_id: int) -> FSMContext:
    return FSMContext(storage=MemoryStorage(), key=StorageKey(bot_id=1, chat_id=user_id, user_id=user_id))


class _FakeMessage:
    def __init__(self, user_id: int | None = None) -> None:
        self.sent: list[str] = []
        self.markups: list = []
        self.from_user = SimpleNamespace(id=user_id) if user_id is not None else None

    async def answer(self, text, reply_markup=None, parse_mode=None):
        self.sent.append(text)
        self.markups.append(reply_markup)
        return self


class _FakeCallback:
    def __init__(self, data: str, user_id: int) -> None:
        self.data = data
        self.from_user = SimpleNamespace(id=user_id)
        self.message = _FakeMessage()
        self.answer = AsyncMock()


class _FakeBot:
    async def send_message(self, *args, **kwargs) -> None:
        return None


def _callback_data_set(markup) -> set[str]:
    if markup is None:
        return set()
    return {btn.callback_data for row in markup.inline_keyboard for btn in row}


def _back_button_target(markup) -> str:
    """The Back button is always the last row on Tournament Details."""
    return markup.inline_keyboard[-1][0].callback_data


async def _make_player(session: AsyncSession, telegram_id: int, name: str = "Player") -> int:
    svc = PlayerService(session)
    player, _ = await svc.get_or_create(PlayerCreate(telegram_id=telegram_id, first_name=name))
    await svc.update_profile(
        telegram_id, PlayerUpdate(language="en", skill_level=3.5, home_area="Downtown", preferred_courts=[])
    )
    await session.commit()
    return player.id


async def _make_admin_with_active_session(session: AsyncSession, telegram_id: int) -> None:
    await PermissionService(session).seed_owners([telegram_id])
    await session.commit()
    with _with_pin() as mock:
        mock.return_value.admin_pin = TEST_PIN
        await AdminSessionService(session).attempt_login(telegram_id, OperatorRole.OWNER, TEST_PIN)
        await session.commit()


# ---------------------------------------------------------------------------
# Role-aware Tournament Menu — the single Role Resolver
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_player_tournament_menu_shows_browse_only(session: AsyncSession) -> None:
    await _make_player(session, 7001, "RegularPlayer")

    message = _FakeMessage(user_id=7001)
    await tournament_menu_entry(message, session)

    assert message.sent == ["🏆 *Tournaments*"]
    callbacks = _callback_data_set(message.markups[0])
    assert callbacks == {"tourn_p:browse", "menu:main"}
    assert "tourn_p:create" not in callbacks
    assert "tourn_p:mine" not in callbacks


@pytest.mark.asyncio
async def test_coach_tournament_menu_shows_create_and_my_tournaments(session: AsyncSession) -> None:
    player_id = await _make_player(session, 7002, "CoachOnly")
    await PlayersService(session).set_verified_coach(player_id, True)
    await session.commit()

    message = _FakeMessage(user_id=7002)
    await tournament_menu_entry(message, session)

    callbacks = _callback_data_set(message.markups[0])
    assert "tourn_p:create" in callbacks
    assert "tourn_p:mine" in callbacks
    assert "tourn_p:browse" in callbacks


# ---------------------------------------------------------------------------
# Create Tournament — reached from the Main Menu, not /dev
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_player_cannot_start_create_tournament(session: AsyncSession) -> None:
    await _make_player(session, 7003, "RegularPlayer")

    callback = _FakeCallback(data="tourn_p:create", user_id=7003)
    state = _make_state(7003)
    await tourn_p_create_start(callback, session, state)

    assert callback.message.sent == []
    assert await state.get_state() is None


@pytest.mark.asyncio
async def test_coach_can_start_create_tournament_from_main_menu(session: AsyncSession) -> None:
    from backend.app.bot.states.states import CreateTournamentStates

    player_id = await _make_player(session, 7004, "CoachOnly")
    await PlayersService(session).set_verified_coach(player_id, True)
    await session.commit()

    callback = _FakeCallback(data="tourn_p:create", user_id=7004)
    state = _make_state(7004)
    await tourn_p_create_start(callback, session, state)

    assert await state.get_state() == CreateTournamentStates.enter_name.state
    assert callback.message.sent  # "enter tournament name" prompt was sent


# ---------------------------------------------------------------------------
# My Tournaments — only tournaments this Coach organized
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_my_tournaments_shows_only_own_tournaments(session: AsyncSession) -> None:
    coach_id = await _make_player(session, 7005, "CoachA")
    await PlayersService(session).set_verified_coach(coach_id, True)
    other_organizer_id = await _make_player(session, 7006, "CoachB")
    await PlayersService(session).set_verified_coach(other_organizer_id, True)
    await session.commit()

    service = TournamentService(session)
    mine = await service.create_tournament(
        7005,
        TournamentCreate(
            name="My Cup", area="Downtown", court="High Park",
            start_date=date(2026, 8, 1), start_time=time(10, 0),
            registration_deadline=date(2026, 7, 20), max_players=4,
        ),
    )
    await service.create_tournament(
        7006,
        TournamentCreate(
            name="Their Cup", area="Downtown", court="High Park",
            start_date=date(2026, 8, 2), start_time=time(10, 0),
            registration_deadline=date(2026, 7, 21), max_players=4,
        ),
    )
    await session.commit()

    tournaments, total = await service.list_my_tournaments(7005, page=1)
    assert total == 1
    assert [t.id for t in tournaments] == [mine.id]

    # Browse (unfiltered) still lists both — reused, untouched.
    browse_tournaments, browse_total = await service.list_tournaments(page=1)
    assert browse_total == 2


# ---------------------------------------------------------------------------
# /dev — Admin/Owner only
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_dev_no_longer_routes_coach_into_tournament_center(session: AsyncSession) -> None:
    player_id = await _make_player(session, 7007, "CoachOnly")
    await PlayersService(session).set_verified_coach(player_id, True)
    await session.commit()

    message = _FakeMessage(user_id=7007)
    await cmd_dev(message, session, _make_state(7007))

    assert message.sent == []  # silent, exactly as if /dev doesn't exist for a Coach


@pytest.mark.asyncio
async def test_admin_still_reaches_tournament_administration_via_dev(session: AsyncSession) -> None:
    await _make_admin_with_active_session(session, 7008)

    dashboard_message = _FakeMessage(user_id=7008)
    await cmd_dev(dashboard_message, session, _make_state(7008))
    assert dashboard_message.sent  # PIN session active -> straight to Dashboard

    tournaments_callback = _FakeCallback(data="dashboard:tournaments", user_id=7008)
    await dashboard_open_tournaments(tournaments_callback, session)
    assert tournaments_callback.message.sent == ["🏆 *Tournament Center*"]


# ---------------------------------------------------------------------------
# Existing permissions unchanged — only navigation changed
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_permission_logic_unchanged_admin_and_coach_and_player(session: AsyncSession) -> None:
    await _make_admin_with_active_session(session, 7009)
    coach_id = await _make_player(session, 7010, "CoachOnly")
    await PlayersService(session).set_verified_coach(coach_id, True)
    await _make_player(session, 7011, "RegularPlayer")
    await session.commit()

    service = TournamentService(session)
    assert await service.can_create_tournament(7009) is True   # Admin
    assert await service.can_create_tournament(7010) is True   # Verified Coach
    assert await service.can_create_tournament(7011) is False  # Regular Player


# ---------------------------------------------------------------------------
# Profile — Verified Coach badge
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_profile_shows_verified_coach_badge(session: AsyncSession) -> None:
    coach_id = await _make_player(session, 7012, "CoachOnly")
    await PlayersService(session).set_verified_coach(coach_id, True)
    await session.commit()

    message = _FakeMessage(user_id=7012)
    await show_profile(message, session)

    assert message.sent and "🏅" in message.sent[0]


@pytest.mark.asyncio
async def test_profile_shows_no_coach_badge_for_regular_player(session: AsyncSession) -> None:
    await _make_player(session, 7013, "RegularPlayer")

    message = _FakeMessage(user_id=7013)
    await show_profile(message, session)

    assert message.sent and "🏅" not in message.sent[0]


# ---------------------------------------------------------------------------
# No remaining path sends a Coach back to the old Tournament Center
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_coach_cancelling_create_returns_to_tournament_menu_not_old_center(session: AsyncSession) -> None:
    coach_id = await _make_player(session, 7014, "CoachOnly")
    await PlayersService(session).set_verified_coach(coach_id, True)
    await session.commit()

    state = _make_state(7014)
    await state.set_state(CreateTournamentStates.confirm)
    await state.update_data(lang="en", editing_id=None, name="X")

    callback = _FakeCallback(data="tourn:cancel", user_id=7014)
    await tourn_do_cancel(callback, session, state)

    headers = callback.message.sent
    assert "🏆 *Tournaments*" in headers  # the new role-aware Tournament Menu
    assert "🏆 *My Tournaments*" not in headers  # never the old Coach Tournament Center
    assert "🏆 *Tournament Center*" not in headers


@pytest.mark.asyncio
async def test_coach_deleting_tournament_returns_to_tournament_menu_not_old_center(session: AsyncSession) -> None:
    coach_id = await _make_player(session, 7015, "CoachOnly")
    await PlayersService(session).set_verified_coach(coach_id, True)
    await session.commit()

    tournament = await TournamentService(session).create_tournament(
        7015,
        TournamentCreate(
            name="ToDelete", area="Downtown", court="High Park",
            start_date=date(2026, 8, 1), start_time=time(10, 0),
            registration_deadline=date(2026, 7, 20), max_players=4,
        ),
    )
    await session.commit()

    callback = _FakeCallback(data=f"tourn:delete:{tournament.id}", user_id=7015)
    await tourn_delete(callback, session)

    headers = callback.message.sent
    assert "🏆 *Tournaments*" in headers
    assert "🏆 *My Tournaments*" not in headers
    assert "🏆 *Tournament Center*" not in headers


@pytest.mark.asyncio
async def test_admin_cancelling_create_still_returns_to_tournament_center(session: AsyncSession) -> None:
    """The Admin path is unaffected — only a Coach's return screen changed."""
    await _make_admin_with_active_session(session, 7016)

    state = _make_state(7016)
    await state.set_state(CreateTournamentStates.confirm)
    await state.update_data(lang="en", editing_id=None, name="X")

    callback = _FakeCallback(data="tourn:cancel", user_id=7016)
    await tourn_do_cancel(callback, session, state)

    assert "🏆 *Tournament Center*" in callback.message.sent


# ---------------------------------------------------------------------------
# One unified Tournament Details — no separate Player/Admin variant
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_unified_details_shows_management_and_registration_for_organizer(session: AsyncSession) -> None:
    """The organizer of a tournament sees BOTH management actions and
    Register — a single screen, not two."""
    coach_id = await _make_player(session, 7017, "CoachOnly")
    await PlayersService(session).set_verified_coach(coach_id, True)
    await session.commit()

    tournament = await TournamentService(session).create_tournament(
        7017,
        TournamentCreate(
            name="Organizer's Cup", area="Downtown", court="High Park",
            start_date=date(2026, 8, 1), start_time=time(10, 0),
            registration_deadline=date(2026, 7, 20), max_players=4,
        ),
    )
    await session.commit()

    callback = _FakeCallback(data=f"tourn:open:{tournament.id}", user_id=7017)
    await tourn_open(callback, session, _FakeBot())

    callbacks = _callback_data_set(callback.message.markups[0])
    assert f"tourn:edit:{tournament.id}" in callbacks       # management
    assert f"tourn:delete:{tournament.id}" in callbacks     # management
    assert f"tourn:register:{tournament.id}" in callbacks   # registration — same screen


@pytest.mark.asyncio
async def test_unified_details_shows_only_registration_for_non_managing_player(session: AsyncSession) -> None:
    """A Regular Player opening someone else's tournament sees no
    management buttons at all — same screen, fewer buttons, not a
    separate template."""
    coach_id = await _make_player(session, 7018, "CoachOnly")
    await PlayersService(session).set_verified_coach(coach_id, True)
    await _make_player(session, 7019, "RegularPlayer")
    await session.commit()

    tournament = await TournamentService(session).create_tournament(
        7018,
        TournamentCreate(
            name="Someone Else's Cup", area="Downtown", court="High Park",
            start_date=date(2026, 8, 1), start_time=time(10, 0),
            registration_deadline=date(2026, 7, 20), max_players=4,
        ),
    )
    await session.commit()
    await TournamentLifecycleService(session).transition(tournament.id, TournamentStatus.REGISTRATION_OPEN)

    callback = _FakeCallback(data=f"tourn:open:{tournament.id}", user_id=7019)
    await tourn_open(callback, session, _FakeBot())

    callbacks = _callback_data_set(callback.message.markups[0])
    assert f"tourn:edit:{tournament.id}" not in callbacks
    assert f"tourn:delete:{tournament.id}" not in callbacks
    assert f"tourn:register:{tournament.id}" in callbacks


# ---------------------------------------------------------------------------
# Back returns to the list this tournament actually belongs to
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_back_returns_organizer_to_my_tournaments(session: AsyncSession) -> None:
    coach_id = await _make_player(session, 7020, "CoachOnly")
    await PlayersService(session).set_verified_coach(coach_id, True)
    await session.commit()

    tournament = await TournamentService(session).create_tournament(
        7020,
        TournamentCreate(
            name="Back Test Cup A", area="Downtown", court="High Park",
            start_date=date(2026, 8, 1), start_time=time(10, 0),
            registration_deadline=date(2026, 7, 20), max_players=4,
        ),
    )
    await session.commit()

    callback = _FakeCallback(data=f"tourn:open:{tournament.id}", user_id=7020)
    await tourn_open(callback, session, _FakeBot())

    assert _back_button_target(callback.message.markups[0]) == "tourn_p:mine"


@pytest.mark.asyncio
async def test_back_returns_admin_to_admin_browse_for_someone_elses_tournament(session: AsyncSession) -> None:
    await _make_admin_with_active_session(session, 7021)
    coach_id = await _make_player(session, 7022, "CoachOnly")
    await PlayersService(session).set_verified_coach(coach_id, True)
    await session.commit()

    tournament = await TournamentService(session).create_tournament(
        7022,
        TournamentCreate(
            name="Back Test Cup B", area="Downtown", court="High Park",
            start_date=date(2026, 8, 1), start_time=time(10, 0),
            registration_deadline=date(2026, 7, 20), max_players=4,
        ),
    )
    await session.commit()

    callback = _FakeCallback(data=f"tourn:open:{tournament.id}", user_id=7021)
    await tourn_open(callback, session, _FakeBot())

    assert _back_button_target(callback.message.markups[0]) == "tourn:browse"


@pytest.mark.asyncio
async def test_back_returns_regular_player_to_browse(session: AsyncSession) -> None:
    coach_id = await _make_player(session, 7023, "CoachOnly")
    await PlayersService(session).set_verified_coach(coach_id, True)
    await _make_player(session, 7024, "RegularPlayer")
    await session.commit()

    tournament = await TournamentService(session).create_tournament(
        7023,
        TournamentCreate(
            name="Back Test Cup C", area="Downtown", court="High Park",
            start_date=date(2026, 8, 1), start_time=time(10, 0),
            registration_deadline=date(2026, 7, 20), max_players=4,
        ),
    )
    await session.commit()

    callback = _FakeCallback(data=f"tourn:open:{tournament.id}", user_id=7024)
    await tourn_open(callback, session, _FakeBot())

    assert _back_button_target(callback.message.markups[0]) == "tourn_p:browse"


# ---------------------------------------------------------------------------
# The presenter itself — pure, no session, testable in isolation
# ---------------------------------------------------------------------------

def test_presenter_builds_view_from_plain_data_with_no_database() -> None:
    from datetime import date as date_, datetime as datetime_, time as time_

    from backend.app.bot.presenters.tournament_details import build_tournament_details_view
    from backend.app.database.models.tournament import TournamentStatus
    from backend.app.schemas.tournament import TournamentRead

    tournament = TournamentRead(
        id=42, name="Pure Presenter Cup", description=None, organizer_player_id=1,
        area="Downtown", court="High Park", start_date=date_(2026, 8, 1), start_time=time_(10, 0),
        registration_deadline=date_(2026, 7, 20), max_players=8,
        status=TournamentStatus.REGISTRATION_OPEN, created_at=datetime_(2026, 1, 1),
    )

    view = build_tournament_details_view(
        "en", tournament, registered_count=3, can_manage=False, is_registered=False, back_callback="tourn_p:browse"
    )

    assert "Pure Presenter Cup" in view.text
    assert "3/8" in view.text
    callbacks = {btn.callback_data for row in view.keyboard.inline_keyboard for btn in row}
    assert callbacks == {"tourn:register:42", "tourn_p:browse"}
