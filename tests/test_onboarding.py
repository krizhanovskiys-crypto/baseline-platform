"""Tests for onboarding's Court Registry integration (Sprint 10.3 Phase 2).

Covers: Area step now selects a Tennis Zone, the Courts step is scoped to
that zone, and "Add my own court" lets a new user add a custom court during
first-time setup (not just via Edit Profile later).
"""
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from aiogram.fsm.storage.memory import MemoryStorage

from backend.app.bot.handlers.start import (
    onboarding_area,
    onboarding_court_add_custom,
    onboarding_court_toggle,
    onboarding_courts_done,
    onboarding_custom_court_submit,
)
from backend.app.bot.states.states import OnboardingStates
from backend.app.bot.texts import t
from backend.app.schemas.player import PlayerCreate
from backend.app.services.player_service import PlayerService


def _make_state(user_id: int) -> FSMContext:
    return FSMContext(storage=MemoryStorage(), key=StorageKey(bot_id=1, chat_id=user_id, user_id=user_id))


def _buttons(markup) -> list[tuple[str, str]]:
    return [(b.text, b.callback_data) for row in markup.inline_keyboard for b in row]


class _FakeMessage:
    def __init__(self, text: str | None = None, from_user_id: int | None = None) -> None:
        self.text = text
        self.from_user = SimpleNamespace(id=from_user_id) if from_user_id else None
        self.sent: list[tuple[str, object]] = []
        self.edit_reply_markup = AsyncMock()

    async def answer(self, text, reply_markup=None, parse_mode=None):
        self.sent.append((text, reply_markup))
        return self


class _FakeCallback:
    def __init__(self, data: str, user_id: int) -> None:
        self.data = data
        self.from_user = SimpleNamespace(id=user_id)
        self.message = _FakeMessage()
        self.answer = AsyncMock()


async def _seed_player(session, telegram_id: int) -> None:
    await PlayerService(session).get_or_create(PlayerCreate(telegram_id=telegram_id, first_name="Newbie"))


async def test_area_selection_moves_to_zone_scoped_courts_step(session):
    """Picking a Tennis Zone in step 3 immediately shows only that zone's
    registry courts in step 4 — no separate re-selection needed here."""
    await _seed_player(session, 700001)
    state = _make_state(700001)
    await state.set_state(OnboardingStates.choose_area)
    await state.update_data(language="en", skill_level=3.5)

    callback = _FakeCallback(data="area:Mississauga", user_id=700001)
    await onboarding_area(callback, state, session)

    assert await state.get_state() == OnboardingStates.choose_courts.state
    assert (await state.get_data())["home_area"] == "Mississauga"
    text, markup = callback.message.sent[0]
    assert text == t("choose_courts", "en", zone="Mississauga")
    buttons = _buttons(markup)
    assert ("Mississauga Valley Park", "court_toggle:Mississauga Valley Park") in buttons
    # A Downtown-only court must not leak into the Mississauga screen.
    assert not any(cb == "court_toggle:Ramsden Park" for _, cb in buttons)
    assert ("➕ Add my own court", "court_add_custom") in buttons


async def test_court_toggle_multiselect(session):
    state = _make_state(700101)
    await state.set_state(OnboardingStates.choose_courts)
    await state.update_data(language="en", home_area="Downtown", selected_courts=[])

    callback = _FakeCallback(data="court_toggle:Ramsden Park", user_id=700101)
    await onboarding_court_toggle(callback, state)

    assert (await state.get_data())["selected_courts"] == ["Ramsden Park"]
    callback.message.edit_reply_markup.assert_awaited_once()


async def test_custom_court_flow_adds_court_and_confirms(session):
    """➕ Add my own court -> "Enter the court name:" -> confirmation ->
    the court is included when the wizard finishes (Court Registry v1.0,
    section 5)."""
    await _seed_player(session, 700201)
    state = _make_state(700201)
    await state.set_state(OnboardingStates.choose_courts)
    await state.update_data(language="en", skill_level=3.0, home_area="Downtown", selected_courts=[])

    add_cb = _FakeCallback(data="court_add_custom", user_id=700201)
    await onboarding_court_add_custom(add_cb, state)
    assert await state.get_state() == OnboardingStates.enter_custom_court.state
    prompt, _ = add_cb.message.sent[0]
    assert prompt == t("custom_court_prompt", "en")

    message = _FakeMessage(text="High Park Bubble", from_user_id=700201)
    await onboarding_custom_court_submit(message, state)

    assert await state.get_state() == OnboardingStates.choose_courts.state
    assert (await state.get_data())["selected_courts"] == ["High Park Bubble"]
    confirmation, _ = message.sent[0]
    assert confirmation == t("custom_court_added", "en")

    # Immediately visible and already checked — not just a confirmation text.
    screen_text, screen_markup = message.sent[1]
    assert screen_text == t("choose_courts", "en", zone="Downtown")
    buttons = _buttons(screen_markup)
    assert (t("custom_courts_divider", "en"), "noop") in buttons
    assert ("✅ High Park Bubble", "court_toggle:High Park Bubble") in buttons

    done_cb = _FakeCallback(data="courts_done", user_id=700201)
    await onboarding_courts_done(done_cb, state, session)

    player = await PlayerService(session).get_by_telegram_id(700201)
    assert player.preferred_courts == ["High Park Bubble"]
    assert player.is_profile_complete is True


async def test_custom_court_toggled_off_by_tapping_again(session):
    """The custom court's button in "Custom Courts" toggles exactly like a
    registry court — reusing onboarding_court_toggle, no separate handler."""
    state = _make_state(700251)
    await state.set_state(OnboardingStates.choose_courts)
    await state.update_data(language="en", home_area="Downtown", selected_courts=["High Park Bubble"])

    callback = _FakeCallback(data="court_toggle:High Park Bubble", user_id=700251)
    await onboarding_court_toggle(callback, state)

    assert (await state.get_data())["selected_courts"] == []
    buttons = _buttons(callback.message.edit_reply_markup.call_args[1]["reply_markup"])
    assert not any(cb == "court_toggle:High Park Bubble" for _, cb in buttons)


async def test_courts_screen_mixes_registry_and_custom_courts(session):
    state = _make_state(700261)
    await state.set_state(OnboardingStates.choose_courts)
    await state.update_data(
        language="en", home_area="Downtown", selected_courts=["Ramsden Park", "High Park Bubble"]
    )

    callback = _FakeCallback(data="court_toggle:Withrow Park", user_id=700261)
    await onboarding_court_toggle(callback, state)  # re-render without changing the mix under test

    buttons = _buttons(callback.message.edit_reply_markup.call_args[1]["reply_markup"])
    assert ("✅ Ramsden Park", "court_toggle:Ramsden Park") in buttons
    assert ("✅ High Park Bubble", "court_toggle:High Park Bubble") in buttons
    assert (t("custom_courts_divider", "en"), "noop") in buttons


async def test_custom_court_rejects_empty_input(session):
    state = _make_state(700301)
    await state.set_state(OnboardingStates.enter_custom_court)
    await state.update_data(language="en", home_area="Downtown", selected_courts=[])

    message = _FakeMessage(text="   ", from_user_id=700301)
    await onboarding_custom_court_submit(message, state)

    text, _ = message.sent[0]
    assert text == t("custom_court_empty_error", "en")
    assert await state.get_state() == OnboardingStates.enter_custom_court.state


async def test_onboarding_completes_with_no_courts_selected(session):
    """Finishing with zero courts selected is allowed — an empty list is a
    valid, complete profile (no forced 'Other' fallback anymore)."""
    await _seed_player(session, 700401)
    state = _make_state(700401)
    await state.set_state(OnboardingStates.choose_courts)
    await state.update_data(language="en", skill_level=3.0, home_area="Downtown", selected_courts=[])

    done_cb = _FakeCallback(data="courts_done", user_id=700401)
    await onboarding_courts_done(done_cb, state, session)

    player = await PlayerService(session).get_by_telegram_id(700401)
    assert player.preferred_courts == []
    assert player.is_profile_complete is True
