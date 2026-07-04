"""Tests for the Organize Match wizard handler flow (Sprint 11 Phase 1 —
Match Discovery Refactor). No handler-level coverage of this wizard
existed before this phase; test_organize_match.py only exercises
GameService directly via GameCreate.

Covers: the new mandatory Area step (Use My Area / Change Area), the
merged Favourite+Registry Court list (starred, no duplication), and the
core regression — game.area now reflects the explicitly chosen Area,
not silently the organizer's home_area.
"""
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from aiogram.fsm.storage.memory import MemoryStorage
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.bot.handlers.organize_match import (
    om_area_change,
    om_area_use_mine,
    om_area_zone_pick,
    om_court_preset,
    om_date_today,
    om_do_confirm,
    om_level_use_mine,
    om_players,
    om_time_preset,
)
from backend.app.bot.states.states import OrganizeMatchStates
from backend.app.bot.texts import t
from backend.app.database.repositories.game_repository import GameRepository
from backend.app.schemas.player import PlayerCreate, PlayerUpdate
from backend.app.services.player_service import PlayerService


def _make_state(user_id: int) -> FSMContext:
    return FSMContext(storage=MemoryStorage(), key=StorageKey(bot_id=1, chat_id=user_id, user_id=user_id))


def _buttons(markup) -> list[tuple[str, str]]:
    return [(b.text, b.callback_data) for row in markup.inline_keyboard for b in row]


class _FakeMessage:
    def __init__(self) -> None:
        self.sent: list[tuple[str, object]] = []

    async def answer(self, text, reply_markup=None, parse_mode=None):
        self.sent.append((text, reply_markup))
        return self


class _FakeCallback:
    def __init__(self, data: str, user_id: int) -> None:
        self.data = data
        self.from_user = SimpleNamespace(id=user_id)
        self.message = _FakeMessage()
        self.answer = AsyncMock()


async def _make_player(
    session: AsyncSession, telegram_id: int, area: str = "Downtown", courts: list[str] | None = None
) -> None:
    svc = PlayerService(session)
    await svc.get_or_create(PlayerCreate(telegram_id=telegram_id, first_name="Player"))
    await svc.update_profile(
        telegram_id,
        PlayerUpdate(language="en", skill_level=3.5, home_area=area, preferred_courts=courts or []),
    )
    await session.commit()


async def _reach_area_step(state: FSMContext, telegram_id: int) -> None:
    """Fast-forward state to just past Date+Time, as the real wizard does."""
    await state.set_state(OrganizeMatchStates.choose_time)
    await state.update_data(lang="en", date_label="Today", date_iso="2026-09-15")


# ---------------------------------------------------------------------------
# Area step
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_time_preset_advances_to_area_step_not_court(session: AsyncSession) -> None:
    """The wizard must ask for Area before Court now."""
    await _make_player(session, 800001, area="Downtown")
    state = _make_state(800001)
    await _reach_area_step(state, 800001)

    callback = _FakeCallback(data="om_time:18:00", user_id=800001)
    await om_time_preset(callback, state, session)

    assert await state.get_state() == OrganizeMatchStates.choose_area.state
    text, markup = callback.message.sent[0]
    assert text == t("om_choose_area", "en")
    callbacks = {cb for _, cb in _buttons(markup)}
    assert callbacks == {"om_area:use_mine", "om_area:change"}


@pytest.mark.asyncio
async def test_area_use_mine_sets_game_area_to_home_area(session: AsyncSession) -> None:
    await _make_player(session, 800101, area="Downtown", courts=["Ramsden Park"])
    state = _make_state(800101)
    await state.set_state(OrganizeMatchStates.choose_area)
    await state.update_data(lang="en")

    callback = _FakeCallback(data="om_area:use_mine", user_id=800101)
    await om_area_use_mine(callback, state, session)

    assert await state.get_state() == OrganizeMatchStates.choose_court.state
    assert (await state.get_data())["area"] == "Downtown"


@pytest.mark.asyncio
async def test_area_change_shows_full_zone_list(session: AsyncSession) -> None:
    await _make_player(session, 800201, area="Downtown")
    state = _make_state(800201)
    await state.set_state(OrganizeMatchStates.choose_area)
    await state.update_data(lang="en")

    callback = _FakeCallback(data="om_area:change", user_id=800201)
    await om_area_change(callback, state)

    text, markup = callback.message.sent[0]
    assert text == t("choose_area", "en")
    callbacks = {cb for _, cb in _buttons(markup)}
    assert "om_area_zone:North York" in callbacks
    assert "om_area_zone:Downtown" in callbacks


@pytest.mark.asyncio
async def test_area_zone_pick_overrides_home_area(session: AsyncSession) -> None:
    """Core regression: organizer's home_area is Downtown, but they pick
    a different zone for this specific match — that choice must win."""
    await _make_player(session, 800301, area="Downtown")
    state = _make_state(800301)
    await state.set_state(OrganizeMatchStates.choose_area)
    await state.update_data(lang="en")

    callback = _FakeCallback(data="om_area_zone:North York", user_id=800301)
    await om_area_zone_pick(callback, state, session)

    assert await state.get_state() == OrganizeMatchStates.choose_court.state
    assert (await state.get_data())["area"] == "North York"


# ---------------------------------------------------------------------------
# Court step — merged Favourite + Registry list, starred, no duplication
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_court_step_stars_favourites_and_lists_them_first(session: AsyncSession) -> None:
    await _make_player(session, 800401, area="Downtown", courts=["Stanley Park", "Withrow Park"])
    state = _make_state(800401)
    await state.set_state(OrganizeMatchStates.choose_area)
    await state.update_data(lang="en")

    await om_area_use_mine(_FakeCallback(data="om_area:use_mine", user_id=800401), state, session)

    data = await state.get_data()
    courts_shown = data["courts_shown"]
    # Favourites first (in the zone's own registry order — Withrow precedes
    # Stanley in Downtown's registry, regardless of preference-list order),
    # then the rest of Downtown's registry.
    assert courts_shown[0] == "Withrow Park"
    assert courts_shown[1] == "Stanley Park"
    assert set(courts_shown) == {
        "Ramsden Park", "Trinity Bellwoods Park", "Withrow Park", "Christie Pits Park",
        "Stanley Park", "Riverdale Park", "Moss Park",
    }
    # No duplication — each court appears exactly once.
    assert len(courts_shown) == len(set(courts_shown))


@pytest.mark.asyncio
async def test_court_step_favourite_outside_chosen_zone_is_not_shown(session: AsyncSession) -> None:
    """A favourite court from a different zone than the one picked for
    this match must not appear (starred or otherwise) — favourites are a
    shortcut within the selected Area, not a global list."""
    await _make_player(session, 800501, area="Downtown", courts=["Oriole Park"])  # North York court
    state = _make_state(800501)
    await state.set_state(OrganizeMatchStates.choose_area)
    await state.update_data(lang="en")

    await om_area_use_mine(_FakeCallback(data="om_area:use_mine", user_id=800501), state, session)

    courts_shown = (await state.get_data())["courts_shown"]
    assert "Oriole Park" not in courts_shown


# ---------------------------------------------------------------------------
# Full happy path — confirms game.area reflects the chosen Area
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_full_wizard_creates_game_with_explicitly_chosen_area(session: AsyncSession) -> None:
    await _make_player(session, 800601, area="Downtown", courts=["Ramsden Park"])
    state = _make_state(800601)

    # Date
    await state.set_state(OrganizeMatchStates.choose_date)
    await state.update_data(lang="en")
    await om_date_today(_FakeCallback(data="om_date:today", user_id=800601), state)

    # Time -> Area prompt
    await om_time_preset(_FakeCallback(data="om_time:18:00", user_id=800601), state, session)

    # Area: explicitly change away from home_area (Downtown -> North York)
    await om_area_zone_pick(_FakeCallback(data="om_area_zone:North York", user_id=800601), state, session)

    # Court: pick the first shown (North York's registry, no favourites there)
    data = await state.get_data()
    await om_court_preset(_FakeCallback(data="om_court:0", user_id=800601), state, session)

    # Level: use mine
    await om_level_use_mine(_FakeCallback(data="om_level:use_mine", user_id=800601), state)

    # Players
    await om_players(_FakeCallback(data="om_players:2", user_id=800601), state)

    # Confirm
    callback = _FakeCallback(data="om:confirm", user_id=800601)
    await om_do_confirm(callback, state, session)
    await session.commit()

    games = await GameRepository(session).get_games_by_creator(
        (await PlayerService(session).get_by_telegram_id(800601)).id
    )
    assert len(games) == 1
    assert games[0].area == "North York"  # not "Downtown", the organizer's home_area
