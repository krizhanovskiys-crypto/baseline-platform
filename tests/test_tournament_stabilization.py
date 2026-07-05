"""Regression tests for Sprint 11.1 — Tournament Stabilization, Phase 1.

Covers the three real bugs found during Repository Reality Check +
investigation:

1. Verified Coach couldn't create tournaments — root cause was a schema
   drift (TECH-010: create_all_tables() created new tables but never
   altered players.is_verified_coach onto the existing table). No code
   bug existed; this test proves the handler-level flow is correct
   against a properly-migrated schema, for both a pure Coach and a
   regular Player, so the two are not conflated with an Admin/Owner
   account the way the real dev database's only real account is.

2 & 3. Registration Deadline didn't auto-close, and the Registration
   Closed Notification never fired for it — because
   admin/tournaments.py's own _show_details() never called
   check_and_auto_close() at all (only the player-facing Details did).
   Fixed by wiring the same lazy check + notification into the Admin/
   Coach Details screen — both handlers now call the exact same
   TournamentService.check_and_auto_close() rather than maintaining two
   independent implementations. Also covers: the player-facing path
   still works unchanged, and re-opening Details on an already-closed
   tournament does not re-transition it or send a second notification
   (check_and_auto_close()'s own status guard is the single idempotency
   authority both handlers rely on — neither handler re-implements it).
"""
from datetime import date, time, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from aiogram.fsm.storage.memory import MemoryStorage
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.bot.handlers.admin.auth import cmd_dev
from backend.app.bot.handlers.admin.tournaments import tourn_close_registration, tourn_create_start, tourn_open
from backend.app.bot.handlers.tournament import tournament_open_details
from backend.app.bot.states.states import CreateTournamentStates
from backend.app.database.models.operator_permission import OperatorRole
from backend.app.database.models.tournament import TournamentStatus
from backend.app.database.repositories.tournament_repository import TournamentRepository
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
        self.from_user = SimpleNamespace(id=user_id) if user_id is not None else None

    async def answer(self, text, reply_markup=None, parse_mode=None):
        self.sent.append(text)
        return self


class _FakeCallback:
    def __init__(self, data: str, user_id: int) -> None:
        self.data = data
        self.from_user = SimpleNamespace(id=user_id)
        self.message = _FakeMessage()
        self.answer = AsyncMock()


class _FakeBot:
    def __init__(self) -> None:
        self.sent_to: list[int] = []

    async def send_message(self, chat_id, text, parse_mode=None) -> None:
        self.sent_to.append(chat_id)


async def _make_player(session: AsyncSession, telegram_id: int, name: str = "Player") -> int:
    svc = PlayerService(session)
    player, _ = await svc.get_or_create(PlayerCreate(telegram_id=telegram_id, first_name=name))
    await svc.update_profile(
        telegram_id, PlayerUpdate(language="en", skill_level=3.5, home_area="Downtown", preferred_courts=[])
    )
    await session.commit()
    return player.id


async def _make_tournament(
    session: AsyncSession, organizer_telegram_id: int, max_players: int = 4, deadline_days: int = 7
) -> int:
    tournament = await TournamentService(session).create_tournament(
        organizer_telegram_id,
        TournamentCreate(
            name="Cup", area="Downtown", court="High Park",
            start_date=date.today() + timedelta(days=14), start_time=time(10, 0),
            registration_deadline=date.today() + timedelta(days=deadline_days), max_players=max_players,
        ),
    )
    await session.commit()
    return tournament.id


# ---------------------------------------------------------------------------
# Task 1 — Verified Coach can create tournaments; Regular Player cannot
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_verified_coach_reaches_tournament_center_via_dev_and_can_create(session: AsyncSession) -> None:
    """End-to-end through the actual handlers (not just the service
    check) for a Coach who holds no operator role at all — the exact
    scenario the real dev database couldn't exercise, since its only
    real account was also an Owner."""
    player_id = await _make_player(session, 6001, "CoachOnly")
    await PlayersService(session).set_verified_coach(player_id, True)
    await session.commit()

    dev_message = _FakeMessage(user_id=6001)
    await cmd_dev(dev_message, session, _make_state(6001))
    assert dev_message.sent == ["🏆 *My Tournaments*"]

    create_callback = _FakeCallback(data="tourn:create", user_id=6001)
    state = _make_state(6001)
    await tourn_create_start(create_callback, session, state)

    assert await state.get_state() == CreateTournamentStates.enter_name.state
    assert create_callback.message.sent  # the "enter tournament name" prompt was sent


@pytest.mark.asyncio
async def test_regular_player_gets_no_dev_access_and_cannot_create(session: AsyncSession) -> None:
    await _make_player(session, 6002, "RegularPlayer")

    dev_message = _FakeMessage(user_id=6002)
    await cmd_dev(dev_message, session, _make_state(6002))
    assert dev_message.sent == []  # silent, exactly as if /dev doesn't exist

    create_callback = _FakeCallback(data="tourn:create", user_id=6002)
    state = _make_state(6002)
    await tourn_create_start(create_callback, session, state)

    assert create_callback.message.sent == []  # blocked — no wizard prompt sent
    assert await state.get_state() is None  # never entered the create wizard


# ---------------------------------------------------------------------------
# Task 2 & 3 — Admin/Coach Details now auto-closes past-deadline
# registrations and fires the notification (previously it did neither)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_admin_opening_details_past_deadline_auto_closes_and_notifies(session: AsyncSession) -> None:
    """The exact bug: admin/tournaments.py's own Details screen never
    called check_and_auto_close() at all, so a tournament whose
    deadline had passed stayed REGISTRATION_OPEN forever from the
    Admin/Coach's own point of view, and no notification ever fired."""
    await PermissionService(session).seed_owners([6101])
    await session.commit()
    with _with_pin() as mock:
        mock.return_value.admin_pin = TEST_PIN
        await AdminSessionService(session).attempt_login(6101, OperatorRole.OWNER, TEST_PIN)
        await session.commit()

    organizer_id = await _make_player(session, 6102, "Organizer")
    # Deadline still in the future at creation/registration time — the
    # player registers normally, tournament stays open.
    tournament_id = await _make_tournament(session, 6102, max_players=10, deadline_days=7)
    await TournamentLifecycleService(session).transition(tournament_id, TournamentStatus.REGISTRATION_OPEN)

    registrant_id = await _make_player(session, 6103, "Registrant")
    registered, just_closed_at_registration = await TournamentService(session).register_player(tournament_id, 6103)
    assert registered is True
    assert just_closed_at_registration is False
    await session.commit()

    # Time passes — the deadline elapses with nobody having looked at
    # the tournament since. This is the real-world sequence the bug
    # affected: registration happened while still open; the deadline
    # only later became "reached".
    from backend.app.database.repositories.tournament_repository import TournamentRepository

    await TournamentRepository(session).update_fields(
        tournament_id, {"registration_deadline": date.today() - timedelta(days=1)}
    )
    await session.commit()

    bot = _FakeBot()
    callback = _FakeCallback(data=f"tourn:open:{tournament_id}", user_id=6101)
    await tourn_open(callback, session, bot)

    tournament = await TournamentService(session).get_tournament(tournament_id)
    assert tournament.status == TournamentStatus.REGISTRATION_CLOSED
    assert bot.sent_to == [6103]  # exactly one notification, to the one registered player


@pytest.mark.asyncio
async def test_manual_close_notifies_every_registered_player_exactly_once(session: AsyncSession) -> None:
    await PermissionService(session).seed_owners([6201])
    await session.commit()
    with _with_pin() as mock:
        mock.return_value.admin_pin = TEST_PIN
        await AdminSessionService(session).attempt_login(6201, OperatorRole.OWNER, TEST_PIN)
        await session.commit()

    organizer_id = await _make_player(session, 6202, "Organizer")
    tournament_id = await _make_tournament(session, 6202, max_players=10)
    await TournamentLifecycleService(session).transition(tournament_id, TournamentStatus.REGISTRATION_OPEN)

    service = TournamentService(session)
    await _make_player(session, 6203, "P1")
    await _make_player(session, 6204, "P2")
    await service.register_player(tournament_id, 6203)
    await service.register_player(tournament_id, 6204)
    await session.commit()

    bot = _FakeBot()
    callback = _FakeCallback(data=f"tourn:close_reg:{tournament_id}", user_id=6201)
    await tourn_close_registration(callback, session, bot)

    tournament = await service.get_tournament(tournament_id)
    assert tournament.status == TournamentStatus.REGISTRATION_CLOSED
    assert sorted(bot.sent_to) == [6203, 6204]  # each registrant notified exactly once


@pytest.mark.asyncio
async def test_player_opening_details_past_deadline_still_auto_closes_and_notifies(session: AsyncSession) -> None:
    """Regression: the Admin-side fix must not have disturbed the
    player-facing Details screen, which already called
    check_and_auto_close() correctly before this sprint."""
    organizer_id = await _make_player(session, 6301, "Organizer")
    tournament_id = await _make_tournament(session, 6301, max_players=10, deadline_days=7)
    await TournamentLifecycleService(session).transition(tournament_id, TournamentStatus.REGISTRATION_OPEN)

    await _make_player(session, 6302, "Registrant")
    registered, just_closed_at_registration = await TournamentService(session).register_player(tournament_id, 6302)
    assert registered is True
    assert just_closed_at_registration is False
    await session.commit()

    await TournamentRepository(session).update_fields(
        tournament_id, {"registration_deadline": date.today() - timedelta(days=1)}
    )
    await session.commit()

    bot = _FakeBot()
    callback = _FakeCallback(data=f"tourn_p:open:{tournament_id}", user_id=6302)
    await tournament_open_details(callback, session, bot)

    tournament = await TournamentService(session).get_tournament(tournament_id)
    assert tournament.status == TournamentStatus.REGISTRATION_CLOSED
    assert bot.sent_to == [6302]


@pytest.mark.asyncio
async def test_reopening_details_on_already_closed_tournament_does_not_renotify(session: AsyncSession) -> None:
    """Neither handler re-implements the idempotency guard — both defer
    to check_and_auto_close()'s own status check. Opening Details a
    second time after the tournament has already auto-closed must not
    re-transition it and must not send a second notification."""
    await PermissionService(session).seed_owners([6401])
    await session.commit()
    with _with_pin() as mock:
        mock.return_value.admin_pin = TEST_PIN
        await AdminSessionService(session).attempt_login(6401, OperatorRole.OWNER, TEST_PIN)
        await session.commit()

    organizer_id = await _make_player(session, 6402, "Organizer")
    tournament_id = await _make_tournament(session, 6402, max_players=10, deadline_days=7)
    await TournamentLifecycleService(session).transition(tournament_id, TournamentStatus.REGISTRATION_OPEN)

    await _make_player(session, 6403, "Registrant")
    await TournamentService(session).register_player(tournament_id, 6403)
    await session.commit()

    await TournamentRepository(session).update_fields(
        tournament_id, {"registration_deadline": date.today() - timedelta(days=1)}
    )
    await session.commit()

    bot = _FakeBot()

    # First open: auto-closes and notifies.
    first_callback = _FakeCallback(data=f"tourn:open:{tournament_id}", user_id=6401)
    await tourn_open(first_callback, session, bot)
    assert bot.sent_to == [6403]

    # Second open on the now-already-closed tournament: must not
    # re-transition (check_and_auto_close's status guard returns False
    # immediately) and must not send a second notification.
    second_callback = _FakeCallback(data=f"tourn:open:{tournament_id}", user_id=6401)
    await tourn_open(second_callback, session, bot)

    tournament = await TournamentService(session).get_tournament(tournament_id)
    assert tournament.status == TournamentStatus.REGISTRATION_CLOSED
    assert bot.sent_to == [6403]  # unchanged — no second notification
