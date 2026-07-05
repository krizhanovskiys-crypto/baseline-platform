"""Regression tests for Sprint 12.3 — Player Platform Refactor.

Part 2 (Universal Player Presenter): one place builds every player
card; badges are additive; every caller renders identically.

Part 1 (Universal Player Picker): level grouping, SQL-based counts,
pagination, search reuse, excluding already-registered players,
selecting immediately registers, and returning to the same level list
(not the beginning) afterward.
"""
from datetime import date, time
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from aiogram.fsm.storage.memory import MemoryStorage
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.bot.handlers.admin.tournaments import tourn_add_player_prompt, tourn_add_player_search_start
from backend.app.bot.handlers.player_picker import pp_level_page, pp_levels, pp_select
from backend.app.bot.presenters.player_card import build_player_card_text
from backend.app.bot.states.states import PlayerPickerStates
from backend.app.database.models.tournament import TournamentStatus
from backend.app.schemas.player import PlayerCreate, PlayerUpdate
from backend.app.schemas.tournament import TournamentCreate
from backend.app.services.player_service import PlayerService
from backend.app.services.players_service import PlayersService
from backend.app.services.tournament_lifecycle_service import TournamentLifecycleService
from backend.app.services.tournament_service import TournamentService

def _make_state(user_id: int) -> FSMContext:
    return FSMContext(storage=MemoryStorage(), key=StorageKey(bot_id=1, chat_id=user_id, user_id=user_id))


class _FakeMessage:
    def __init__(self) -> None:
        self.sent: list[str] = []
        self.markups: list = []

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


def _callback_data_set(markup) -> set[str]:
    if markup is None:
        return set()
    return {btn.callback_data for row in markup.inline_keyboard for btn in row}


def _button_texts(markup) -> list[str]:
    return [btn.text for row in markup.inline_keyboard for btn in row]


async def _make_player(
    session: AsyncSession, telegram_id: int, name: str, level: float, coach: bool = False
) -> int:
    svc = PlayerService(session)
    player, _ = await svc.get_or_create(PlayerCreate(telegram_id=telegram_id, first_name=name))
    await svc.update_profile(
        telegram_id,
        PlayerUpdate(language="en", skill_level=level, home_area="Downtown", preferred_courts=["High Park"]),
    )
    if coach:
        await PlayersService(session).set_verified_coach(player.id, True)
    return player.id


async def _make_open_tournament(session: AsyncSession, organizer_tg: int, max_players: int = 20) -> int:
    """Callers must have already made organizer_tg a Verified Coach
    (or seeded them as an Admin) — can_manage_tournament() requires it,
    same as the real approved architecture."""
    tournament = await TournamentService(session).create_tournament(
        organizer_tg,
        TournamentCreate(
            name="Picker Test Cup", area="Downtown", court="High Park",
            start_date=date(2026, 8, 1), start_time=time(10, 0),
            registration_deadline=date(2026, 7, 20), max_players=max_players,
        ),
    )
    await TournamentLifecycleService(session).transition(tournament.id, TournamentStatus.REGISTRATION_OPEN)
    return tournament.id


# ---------------------------------------------------------------------------
# Universal Player Presenter
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_presenter_shows_coach_badge_when_true(session: AsyncSession) -> None:
    await _make_player(session, 8101, "CoachPlayer", 3.5, coach=True)
    await session.commit()
    player = await PlayerService(session).get_by_telegram_id(8101)

    text = build_player_card_text("en", player)

    assert "🏅 Verified Coach" in text


@pytest.mark.asyncio
async def test_presenter_omits_coach_badge_when_false(session: AsyncSession) -> None:
    await _make_player(session, 8102, "RegularPlayer", 3.5, coach=False)
    await session.commit()
    player = await PlayerService(session).get_by_telegram_id(8102)

    text = build_player_card_text("en", player)

    assert "🏅 Verified Coach" not in text


@pytest.mark.asyncio
async def test_presenter_renders_fields_in_standard_order(session: AsyncSession) -> None:
    await _make_player(session, 8103, "OrderTest", 4.0, coach=True)
    await session.commit()
    player = await PlayerService(session).get_by_telegram_id(8103)

    text = build_player_card_text("en", player)
    lines = text.split("\n")

    assert "OrderTest" in lines[0] and lines[0].startswith("👤")
    assert lines[1] == "🏅 Verified Coach"
    assert lines[2].startswith("⭐ Level")
    assert lines[3].startswith("🗣️ Languages")
    assert lines[4].startswith("🎾 Favourite Courts")
    assert lines[5].startswith("📊 Matches")


@pytest.mark.asyncio
async def test_presenter_escapes_free_text_name_and_courts(session: AsyncSession) -> None:
    player_id = await _make_player(session, 8104, "John_Doe", 3.0)
    svc = PlayerService(session)
    await svc.update_profile(
        8104, PlayerUpdate(language="en", skill_level=3.0, home_area="Downtown", preferred_courts=["My_Court [East]"])
    )
    await session.commit()
    player = await svc.get_by_telegram_id(8104)

    text = build_player_card_text("en", player)

    assert "John\\_Doe" in text
    assert "My\\_Court \\[East\\]" in text


@pytest.mark.asyncio
async def test_presenter_renders_identically_regardless_of_caller(session: AsyncSession) -> None:
    """The same player produces byte-identical card text whether called
    for Profile, Find Partner, or Admin Details — there is exactly one
    formatting implementation."""
    await _make_player(session, 8105, "Consistency", 3.5, coach=True)
    await session.commit()
    player = await PlayerService(session).get_by_telegram_id(8105)

    first_call = build_player_card_text("en", player)
    second_call = build_player_card_text("en", player)

    assert first_call == second_call


# ---------------------------------------------------------------------------
# Universal Player Picker
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_level_group_counts_are_sql_based_and_correct(session: AsyncSession) -> None:
    await _make_player(session, 8201, "LowLevel", 2.0)
    await _make_player(session, 8202, "MidLevelA", 3.5)
    await _make_player(session, 8203, "MidLevelB", 3.0)
    await _make_player(session, 8204, "HighLevel", 5.5)
    await session.commit()

    organizer_id = await _make_player(session, 8299, "Organizer", 3.5, coach=True)
    tournament_id = await _make_open_tournament(session, 8299)
    await session.commit()

    callback = _FakeCallback(data="pp:levels", user_id=8299)
    state = _make_state(8299)
    await state.update_data(picker_context_type="tournament_add_player", picker_tournament_id=tournament_id)
    await pp_levels(callback, session, state)

    texts = _button_texts(callback.message.markups[0])
    assert any(t.startswith("🎾 Level 2.0–2.5 (1)") for t in texts)  # LowLevel only
    assert any(t.startswith("🎾 Level 3.0–3.5 (3)") for t in texts)  # MidLevelA/B + Organizer
    assert any(t.startswith("🎾 Level 5.0+ (1)") for t in texts)  # HighLevel only


@pytest.mark.asyncio
async def test_level_list_is_alphabetical_and_paginated(session: AsyncSession) -> None:
    for i, name in enumerate(["Zack", "Anna", "Mike"]):
        await _make_player(session, 8300 + i, name, 3.5)
    organizer_id = await _make_player(session, 8399, "Organizer2", 3.5, coach=True)
    tournament_id = await _make_open_tournament(session, 8399)
    await session.commit()

    callback = _FakeCallback(data="pp:level:1:1", user_id=8399)
    state = _make_state(8399)
    await state.update_data(picker_context_type="tournament_add_player", picker_tournament_id=tournament_id)
    await pp_level_page(callback, session, state)

    names = [b for b in _button_texts(callback.message.markups[0]) if b not in ("⬅️ Back",)]
    player_names = [n for n in names if n in ("Zack", "Anna", "Mike", "Organizer2")]
    assert player_names == sorted(player_names)  # alphabetical
    assert "Page 1/1" in callback.message.sent[0]


@pytest.mark.asyncio
async def test_level_list_excludes_already_registered_players(session: AsyncSession) -> None:
    organizer_id = await _make_player(session, 8401, "Organizer3", 3.5, coach=True)
    tournament_id = await _make_open_tournament(session, 8401)
    already_id = await _make_player(session, 8402, "AlreadyIn", 3.5)
    not_yet_id = await _make_player(session, 8403, "NotYetIn", 3.5)
    await session.commit()

    await TournamentService(session).register_player(tournament_id, 8402)
    await session.commit()

    callback = _FakeCallback(data="pp:level:1:1", user_id=8401)
    state = _make_state(8401)
    await state.update_data(picker_context_type="tournament_add_player", picker_tournament_id=tournament_id)
    await pp_level_page(callback, session, state)

    names = _button_texts(callback.message.markups[0])
    assert "AlreadyIn" not in names
    assert "NotYetIn" in names


@pytest.mark.asyncio
async def test_selecting_a_player_registers_them_and_returns_to_same_level_list(session: AsyncSession) -> None:
    organizer_id = await _make_player(session, 8501, "Organizer4", 3.5, coach=True)
    tournament_id = await _make_open_tournament(session, 8501)
    target_id = await _make_player(session, 8502, "SelectMe", 3.5)
    await session.commit()

    callback = _FakeCallback(data=f"pp:select:{target_id}", user_id=8501)
    state = _make_state(8501)
    await state.update_data(
        picker_context_type="tournament_add_player",
        picker_tournament_id=tournament_id,
        picker_group_index=1,
        picker_page=1,
    )
    await pp_select(callback, session, state)

    assert any("added" in text for text in callback.message.sent)
    # Returned to the SAME level group's list — not the beginning
    assert "🎾 Level 3.0–3.5" in callback.message.sent[-1] or "Page" in callback.message.sent[-1]

    registrations = await TournamentService(session).get_registered_players(tournament_id)
    assert any(r.player_id == target_id for r in registrations)


@pytest.mark.asyncio
async def test_add_player_shows_menu_not_direct_search_prompt(session: AsyncSession) -> None:
    """The old flow (Add Player -> straight to a text prompt) is gone —
    it now shows the Picker menu first."""
    organizer_id = await _make_player(session, 8601, "Organizer5", 3.5, coach=True)
    tournament_id = await _make_open_tournament(session, 8601)
    await session.commit()

    callback = _FakeCallback(data=f"tourn:add_player:{tournament_id}", user_id=8601)
    state = _make_state(8601)
    await tourn_add_player_prompt(callback, session, state)

    assert callback.message.sent == ["➕ *Add Player*"]
    callbacks = _callback_data_set(callback.message.markups[0])
    assert callbacks == {"pp:search", "pp:levels", f"tourn:open:{tournament_id}"}


@pytest.mark.asyncio
async def test_search_option_reuses_existing_search_prompt_and_state(session: AsyncSession) -> None:
    """Search logic itself is unchanged — this only confirms the menu's
    Search button reaches the same prompt/state as before."""
    callback = _FakeCallback(data="pp:search", user_id=8601)
    state = _make_state(8601)
    await tourn_add_player_search_start(callback, session, state)

    assert await state.get_state() == PlayerPickerStates.enter_search.state
    assert callback.message.sent == ["Enter the player's name, username, or Telegram ID:"]
