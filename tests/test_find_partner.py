"""Tests for Sprint 7.2 — Find Partner Search Mode + Smart Filter."""
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from aiogram.fsm.storage.memory import MemoryStorage

from backend.app.bot.handlers.find_partner import (
    find_partner,
    fp_mode_all,
    fp_mode_smart,
    fp_smartfilter_apply,
    fp_smartfilter_court_add_custom,
    fp_smartfilter_court_toggle,
    fp_smartfilter_courts_done,
    fp_smartfilter_custom_court_submit,
    fp_smartfilter_open_courts,
    fp_smartfilter_save_area,
    fp_smartfilter_save_level,
)
from backend.app.bot.states.states import FindPartnerStates
from backend.app.bot.texts import t
from backend.app.schemas.player import PlayerCreate, PlayerUpdate
from backend.app.services.player_service import PlayerService


def _make_state(user_id: int) -> FSMContext:
    return FSMContext(storage=MemoryStorage(), key=StorageKey(bot_id=1, chat_id=user_id, user_id=user_id))


def _buttons(markup) -> list[tuple[str, str]]:
    return [(b.text, b.callback_data) for row in markup.inline_keyboard for b in row]


class _FakeMessage:
    def __init__(self) -> None:
        self.sent: list[tuple[str, object]] = []
        self.edit_text = AsyncMock()

    async def answer(self, text, reply_markup=None, parse_mode=None):
        self.sent.append((text, reply_markup))
        return self


class _FakeCallback:
    def __init__(self, data: str, user_id: int) -> None:
        self.data = data
        self.from_user = SimpleNamespace(id=user_id)
        self.message = _FakeMessage()
        self.answer = AsyncMock()


class _FakeBot:
    """Stands in for aiogram's injected `bot: Bot` — only get_me() is
    exercised, by build_invite_share_url() in the empty-state path."""

    async def get_me(self):
        return SimpleNamespace(username="baseline_test_bot")


async def _make_player(session, telegram_id: int, first_name: str = "Player", area: str = "Downtown") -> None:
    service = PlayerService(session)
    await service.get_or_create(PlayerCreate(telegram_id=telegram_id, first_name=first_name))
    await service.update_profile(
        telegram_id,
        # Ramsden Park is a real Downtown-zone Court Registry entry (see
        # backend/app/data/courts.py) so it renders as a ✅ button on the
        # Downtown zone's court screen, matching the player's own home_area.
        PlayerUpdate(language="en", skill_level=3.0, home_area=area, preferred_courts=["Ramsden Park"]),
    )


async def _make_candidate(session, telegram_id: int, name: str, level: float, area: str, courts: list[str]) -> None:
    service = PlayerService(session)
    await service.get_or_create(PlayerCreate(telegram_id=telegram_id, first_name=name))
    await service.update_profile(
        telegram_id,
        PlayerUpdate(language="en", skill_level=level, home_area=area, preferred_courts=courts),
    )


# ── Entry point now shows Search Mode, not an immediate search ─────────────────

async def test_find_partner_shows_search_mode_screen(session):
    await _make_player(session, 900001, "Alice")
    await session.commit()

    message = _FakeMessage()
    message.from_user = SimpleNamespace(id=900001)
    await find_partner(message, session)

    assert len(message.sent) == 1
    text, markup = message.sent[0]
    assert text == t("fp_search_mode_header", "en")
    buttons = _buttons(markup)
    callbacks = {cb for _, cb in buttons}
    assert callbacks == {"fp:mode:all", "fp:mode:smart", "menu:main"}


# ── All Players — unchanged search behaviour ────────────────────────────────────

async def test_fp_mode_all_runs_existing_search(session):
    await _make_player(session, 900101, "Bob", area="Downtown")
    await _make_candidate(session, 900102, "Carol", 3.0, "Downtown", ["High Park"])
    await session.commit()

    state = _make_state(900101)
    callback = _FakeCallback(data="fp:mode:all", user_id=900101)
    await fp_mode_all(callback, state, session, _FakeBot())

    callback.answer.assert_awaited_once()
    assert await state.get_state() == FindPartnerStates.browsing.state
    text, _ = callback.message.sent[0]
    assert "Carol" in text


# ── Empty state — Invite a Friend (Sprint 11 Phase 3.1A) ────────────────────────

async def test_fp_mode_all_empty_state_offers_invite_a_friend(session):
    """No candidates at all — the empty state must offer a real,
    working next action, not just a dead-end message."""
    await _make_player(session, 900103, "Owen", area="Downtown")
    await session.commit()

    state = _make_state(900103)
    callback = _FakeCallback(data="fp:mode:all", user_id=900103)
    await fp_mode_all(callback, state, session, _FakeBot())

    text, markup = callback.message.sent[0]
    assert text == t("player_discovery_no_results", "en")
    buttons = _buttons(markup)
    assert len(buttons) == 2
    invite_button = next(b for b in markup.inline_keyboard[0])
    assert invite_button.text == t("btn_invite_friend", "en")
    assert invite_button.url is not None
    assert invite_button.url.startswith("https://t.me/share/url?")
    assert "baseline_test_bot" in invite_button.url
    back_texts_callbacks = {(b.text, b.callback_data) for row in markup.inline_keyboard for b in row}
    assert (t("btn_back", "en"), "menu:main") in back_texts_callbacks


async def test_fp_smartfilter_apply_empty_state_offers_invite_a_friend(session):
    await _make_player(session, 900803, "Nora", area="Downtown")
    await session.commit()

    state = _make_state(900803)
    await state.set_state(FindPartnerStates.smart_filter)
    await state.update_data(filters={"area": "home", "courts": None, "level": "default"})

    callback = _FakeCallback(data="fp:smartfilter:apply", user_id=900803)
    await fp_smartfilter_apply(callback, state, session, _FakeBot())

    text, markup = callback.message.sent[0]
    assert text == t("player_discovery_no_results", "en")
    callbacks = {b.callback_data for row in markup.inline_keyboard for b in row}
    assert "menu:main" in callbacks


# ── Smart Filter — defaults ──────────────────────────────────────────────────

async def test_fp_mode_smart_shows_defaults(session):
    await _make_player(session, 900201, "Dan", area="Downtown")
    await session.commit()

    state = _make_state(900201)
    callback = _FakeCallback(data="fp:mode:smart", user_id=900201)
    await fp_mode_smart(callback, state, session)

    callback.answer.assert_awaited_once()
    assert await state.get_state() == FindPartnerStates.smart_filter.state
    text, markup = callback.message.sent[0]
    assert text == t("smart_filter_header", "en")
    buttons = _buttons(markup)
    assert any("Downtown" in label and cb == "fp:smartfilter:open:area" for label, cb in buttons)
    assert any("Ramsden Park" in label and cb == "fp:smartfilter:open:courts" for label, cb in buttons)
    assert any("±0.5" in label and cb == "fp:smartfilter:open:level" for label, cb in buttons)
    assert "fp:smartfilter:apply" in {cb for _, cb in buttons}
    assert "menu:main" in {cb for _, cb in buttons}


# ── Smart Filter — Area selection round-trip ─────────────────────────────────

async def test_fp_smartfilter_save_area_updates_screen(session):
    await _make_player(session, 900301, "Eve", area="Downtown")
    state = _make_state(900301)
    await state.set_state(FindPartnerStates.smart_filter)
    await state.update_data(filters={"area": "home", "courts": ["High Park"], "level": "default"})

    callback = _FakeCallback(data="fp_smartfilter_area:North York", user_id=900301)
    await fp_smartfilter_save_area(callback, state, session)

    assert (await state.get_data())["filters"]["area"] == "North York"
    args, kwargs = callback.message.edit_text.call_args
    assert args[0] == t("smart_filter_header", "en")
    buttons = _buttons(kwargs["reply_markup"])
    assert any("North York" in label and cb == "fp:smartfilter:open:area" for label, cb in buttons)


# ── Smart Filter — Courts: temporary only, never saved to profile ──────────────

async def test_fp_smartfilter_courts_default_to_favourites(session):
    await _make_player(session, 900401, "Finn")
    state = _make_state(900401)

    callback = _FakeCallback(data="fp:smartfilter:open:courts", user_id=900401)
    await fp_smartfilter_open_courts(callback, state, session)

    args, kwargs = callback.message.edit_text.call_args
    buttons = _buttons(kwargs["reply_markup"])
    assert ("✅ Ramsden Park", "court_toggle:Ramsden Park") in buttons


async def test_fp_smartfilter_court_toggle_does_not_touch_profile(session):
    await _make_player(session, 900501, "Gina")
    state = _make_state(900501)
    await state.set_state(FindPartnerStates.smart_filter)
    await state.update_data(filters={"area": "home", "courts": ["High Park"], "level": "default"})

    callback = _FakeCallback(data="court_toggle:Stanley Park", user_id=900501)
    await fp_smartfilter_court_toggle(callback, state, session)

    filters = (await state.get_data())["filters"]
    assert sorted(filters["courts"]) == ["High Park", "Stanley Park"]

    # The player's actual saved profile must be untouched.
    player = await PlayerService(session).get_by_telegram_id(900501)
    assert player.preferred_courts == ["Ramsden Park"]


async def test_fp_smartfilter_courts_done_does_not_save_to_profile(session):
    await _make_player(session, 900601, "Hugo")
    state = _make_state(900601)
    await state.set_state(FindPartnerStates.smart_filter)
    await state.update_data(filters={"area": "home", "courts": ["High Park", "Stanley Park"], "level": "default"})

    callback = _FakeCallback(data="courts_done", user_id=900601)
    await fp_smartfilter_courts_done(callback, state, session)

    args, kwargs = callback.message.edit_text.call_args
    assert args[0] == t("smart_filter_header", "en")
    buttons = _buttons(kwargs["reply_markup"])
    assert any("High Park, Stanley Park" in label and cb == "fp:smartfilter:open:courts" for label, cb in buttons)

    player = await PlayerService(session).get_by_telegram_id(900601)
    assert player.preferred_courts == ["Ramsden Park"]  # unchanged


# ── Smart Filter — Custom court ("Custom Courts" section) ──────────────────────
# Same UX as onboarding and Edit Profile: a custom court is visible and
# already checked immediately, not just confirmed via text.

async def test_fp_smartfilter_custom_court_shown_immediately(session):
    await _make_player(session, 900651, "Kelly", area="Downtown")
    state = _make_state(900651)
    await state.set_state(FindPartnerStates.smart_filter)
    await state.update_data(filters={"area": "home", "courts": [], "level": "default"})

    add_cb = _FakeCallback(data="court_add_custom", user_id=900651)
    await fp_smartfilter_court_add_custom(add_cb, state, session)
    assert await state.get_state() == FindPartnerStates.enter_custom_court.state
    prompt, _ = add_cb.message.sent[0]
    assert prompt == t("custom_court_prompt", "en")

    message = _FakeMessage()
    message.from_user = SimpleNamespace(id=900651)
    message.text = "High Park Bubble"
    await fp_smartfilter_custom_court_submit(message, state, session)

    assert await state.get_state() == FindPartnerStates.smart_filter.state
    assert (await state.get_data())["filters"]["courts"] == ["High Park Bubble"]
    confirmation, _ = message.sent[0]
    assert confirmation == t("custom_court_added", "en")
    screen_text, screen_markup = message.sent[1]
    assert screen_text == t("choose_courts", "en", zone="Downtown")
    buttons = _buttons(screen_markup)
    assert (t("custom_courts_divider", "en"), "noop") in buttons
    assert ("✅ High Park Bubble", "court_toggle:High Park Bubble") in buttons

    # This selection is temporary (Smart Filter never writes to the profile).
    player = await PlayerService(session).get_by_telegram_id(900651)
    assert player.preferred_courts == ["Ramsden Park"]


async def test_fp_smartfilter_custom_court_toggled_off(session):
    await _make_player(session, 900661, "Liam", area="Downtown")
    state = _make_state(900661)
    await state.set_state(FindPartnerStates.smart_filter)
    await state.update_data(filters={"area": "home", "courts": ["High Park Bubble"], "level": "default"})

    toggle_cb = _FakeCallback(data="court_toggle:High Park Bubble", user_id=900661)
    await fp_smartfilter_court_toggle(toggle_cb, state, session)

    assert (await state.get_data())["filters"]["courts"] == []
    args, kwargs = toggle_cb.message.edit_text.call_args
    buttons = _buttons(kwargs["reply_markup"])
    assert not any(cb == "court_toggle:High Park Bubble" for _, cb in buttons)


async def test_fp_smartfilter_courts_screen_mixes_registry_and_custom(session):
    await _make_player(session, 900671, "Mona", area="Downtown")
    state = _make_state(900671)
    await state.set_state(FindPartnerStates.smart_filter)
    await state.update_data(
        filters={"area": "home", "courts": ["Ramsden Park", "High Park Bubble"], "level": "default"}
    )

    toggle_cb = _FakeCallback(data="court_toggle:Withrow Park", user_id=900671)
    await fp_smartfilter_court_toggle(toggle_cb, state, session)  # re-render only

    args, kwargs = toggle_cb.message.edit_text.call_args
    buttons = _buttons(kwargs["reply_markup"])
    assert ("✅ Ramsden Park", "court_toggle:Ramsden Park") in buttons
    assert ("✅ High Park Bubble", "court_toggle:High Park Bubble") in buttons
    assert (t("custom_courts_divider", "en"), "noop") in buttons


# ── Smart Filter — Level tolerance ───────────────────────────────────────────

async def test_fp_smartfilter_save_level_any(session):
    await _make_player(session, 900701, "Ivy")
    state = _make_state(900701)
    await state.set_state(FindPartnerStates.smart_filter)
    await state.update_data(filters={"area": "home", "courts": ["High Park"], "level": "default"})

    callback = _FakeCallback(data="fp_smartfilter_level:any", user_id=900701)
    await fp_smartfilter_save_level(callback, state, session)

    assert (await state.get_data())["filters"]["level"] == "any"
    args, kwargs = callback.message.edit_text.call_args
    buttons = _buttons(kwargs["reply_markup"])
    assert any(
        t("available_matches_filter_any", "en") in label and cb == "fp:smartfilter:open:level"
        for label, cb in buttons
    )


# ── Find Players — applies filters then launches the existing browse flow ──────

async def test_fp_smartfilter_apply_uses_resolved_filters_and_starts_browsing(session):
    await _make_player(session, 900801, "Jack", area="Downtown")
    # Within tolerance and shares the temporarily-selected court.
    await _make_candidate(session, 900802, "Kara", 4.5, "North York", ["Stanley Park"])
    await session.commit()

    state = _make_state(900801)
    await state.set_state(FindPartnerStates.smart_filter)
    await state.update_data(filters={"area": "North York", "courts": ["Stanley Park"], "level": "any"})

    callback = _FakeCallback(data="fp:smartfilter:apply", user_id=900801)
    await fp_smartfilter_apply(callback, state, session, _FakeBot())

    assert await state.get_state() == FindPartnerStates.browsing.state
    text, _ = callback.message.sent[0]
    assert "Kara" in text  # found despite the wide level gap, thanks to area+level="any"

    # The organizer's own profile must remain untouched by the search filters.
    player = await PlayerService(session).get_by_telegram_id(900801)
    assert player.home_area == "Downtown"
    assert player.preferred_courts == ["Ramsden Park"]
