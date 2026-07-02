"""Tests for Sprint 7.1 — Profile UX Redesign (Edit Profile + spoken Languages)."""
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from aiogram.fsm.storage.memory import MemoryStorage

from backend.app.bot.handlers.profile import (
    edit_profile,
    edit_profile_language_toggle,
    edit_profile_languages_done,
    edit_profile_languages_start,
    edit_profile_name_save,
    edit_profile_name_start,
    settings_change_area,
    settings_change_courts,
    settings_choose_courts_zone,
    settings_court_add_custom,
    settings_court_toggle,
    settings_courts_done,
    settings_custom_court_submit,
    settings_save_area,
    settings_save_level,
)
from backend.app.bot.keyboards.keyboards import profile_keyboard, settings_keyboard
from backend.app.bot.states.states import SettingsStates
from backend.app.bot.texts import t
from backend.app.schemas.player import PlayerCreate, PlayerUpdate
from backend.app.services.player_service import PlayerService


def _make_state(user_id: int) -> FSMContext:
    return FSMContext(storage=MemoryStorage(), key=StorageKey(bot_id=1, chat_id=user_id, user_id=user_id))


def _buttons(markup) -> list[tuple[str, str]]:
    return [(b.text, b.callback_data) for row in markup.inline_keyboard for b in row]


class _FakeMessage:
    """Minimal stand-in for aiogram's Message — records .answer()/.edit_text() calls."""

    def __init__(self, text: str | None = None, from_user_id: int | None = None) -> None:
        self.text = text
        self.from_user = SimpleNamespace(id=from_user_id) if from_user_id else None
        self.answer = AsyncMock(side_effect=self._record_answer)
        self.edit_text = AsyncMock()
        self.edit_reply_markup = AsyncMock()
        self.sent: list[tuple[str, object]] = []

    async def _record_answer(self, text, reply_markup=None, parse_mode=None):
        self.sent.append((text, reply_markup))


class _FakeCallback:
    """Minimal stand-in for aiogram's CallbackQuery."""

    def __init__(self, data: str, user_id: int) -> None:
        self.data = data
        self.from_user = SimpleNamespace(id=user_id)
        self.message = _FakeMessage()
        self.answer = AsyncMock()


async def _make_player(session, telegram_id: int, first_name: str = "Player") -> None:
    service = PlayerService(session)
    await service.get_or_create(PlayerCreate(telegram_id=telegram_id, first_name=first_name))
    await service.update_profile(
        telegram_id,
        PlayerUpdate(
            language="en",
            skill_level=3.0,
            home_area="Downtown",
            preferred_courts=["High Park"],
            spoken_languages=["ENG"],
        ),
    )


# ── Service: spoken_languages round-trip ─────────────────────────────────────

async def test_update_profile_spoken_languages(session):
    service = PlayerService(session)
    await service.get_or_create(PlayerCreate(telegram_id=9001, first_name="Zoe"))
    await session.commit()

    updated = await service.update_profile(9001, PlayerUpdate(spoken_languages=["UKR", "ENG"]))
    await session.commit()

    assert updated is not None
    assert updated.spoken_languages == ["UKR", "ENG"]

    fetched = await service.get_by_telegram_id(9001)
    assert fetched.spoken_languages == ["UKR", "ENG"]


async def test_update_profile_spoken_languages_defaults_empty(session):
    service = PlayerService(session)
    await service.get_or_create(PlayerCreate(telegram_id=9002, first_name="Noah"))
    await session.commit()
    player = await service.get_by_telegram_id(9002)
    assert player.spoken_languages == []


# ── Keyboards ────────────────────────────────────────────────────────────────

def test_profile_keyboard_has_edit_and_menu_buttons():
    buttons = _buttons(profile_keyboard("en"))
    callbacks = {cb for _, cb in buttons}
    assert "profile:edit" in callbacks
    assert "menu:main" in callbacks


def test_settings_keyboard_only_has_language():
    buttons = _buttons(settings_keyboard("en"))
    callbacks = {cb for _, cb in buttons}
    assert callbacks == {"settings:language"}


# ── Edit Profile screen ──────────────────────────────────────────────────────

async def test_edit_profile_shows_fields_and_menu(session):
    await _make_player(session, 800001, "Alice")
    await session.commit()

    callback = _FakeCallback(data="profile:edit", user_id=800001)
    await edit_profile(callback, session)

    callback.answer.assert_awaited_once()
    callback.message.answer.assert_awaited_once()
    text, markup = callback.message.sent[0]
    assert text == t("edit_profile_header", "en")
    buttons = _buttons(markup)
    texts = dict(buttons)
    assert any("Alice" in label and cb == "editprofile:name" for label, cb in buttons)
    assert any("Downtown" in label and cb == "settings:area" for label, cb in buttons)
    assert any("High Park" in label and cb == "settings:courts" for label, cb in buttons)
    assert any("ENG" in label and cb == "editprofile:languages" for label, cb in buttons)
    assert "menu:main" in texts.values()
    assert "available:start" not in texts.values()


# ── Reused selectors now return to Edit Profile, not Main Menu ─────────────────

async def test_settings_save_area_returns_to_edit_profile(session):
    await _make_player(session, 800101, "Bob")
    state = _make_state(800101)
    await state.set_state(SettingsStates.change_area)

    callback = _FakeCallback(data="settings_area:North York", user_id=800101)
    await settings_save_area(callback, state, session)

    callback.answer.assert_awaited_once()
    callback.message.edit_text.assert_awaited_once()
    args, kwargs = callback.message.edit_text.call_args
    assert args[0] == t("edit_profile_header", "en")
    buttons = _buttons(kwargs["reply_markup"])
    assert any("North York" in label and cb == "settings:area" for label, cb in buttons)
    assert await state.get_state() is None  # state cleared, not left mid-flow


async def test_settings_save_level_returns_to_edit_profile(session):
    await _make_player(session, 800201, "Cleo")
    state = _make_state(800201)
    await state.set_state(SettingsStates.change_level)

    callback = _FakeCallback(data="level:4.0", user_id=800201)
    await settings_save_level(callback, state, session)

    args, kwargs = callback.message.edit_text.call_args
    assert args[0] == t("edit_profile_header", "en")
    buttons = _buttons(kwargs["reply_markup"])
    assert any("4.0" in label and cb == "settings:level" for label, cb in buttons)


async def test_settings_courts_done_returns_to_edit_profile(session):
    await _make_player(session, 800301, "Dan")
    state = _make_state(800301)
    await state.set_state(SettingsStates.change_courts)
    await state.update_data(selected_courts=["Stanley Park"], lang="en")

    callback = _FakeCallback(data="courts_done", user_id=800301)
    await settings_courts_done(callback, state, session)

    args, kwargs = callback.message.edit_text.call_args
    assert args[0] == t("edit_profile_header", "en")
    buttons = _buttons(kwargs["reply_markup"])
    assert any("Stanley Park" in label and cb == "settings:courts" for label, cb in buttons)


# ── Name field (free-text) ───────────────────────────────────────────────────

async def test_edit_profile_name_start_prompts_for_text(session):
    await _make_player(session, 800401, "Eve")
    state = _make_state(800401)

    callback = _FakeCallback(data="editprofile:name", user_id=800401)
    await edit_profile_name_start(callback, state, session)

    callback.answer.assert_awaited_once()
    assert await state.get_state() == SettingsStates.change_name.state
    callback.message.answer.assert_awaited_once()
    text, _ = callback.message.sent[0]
    assert text == t("edit_profile_enter_name", "en")


async def test_edit_profile_name_save_updates_and_returns(session):
    await _make_player(session, 800501, "Frank")
    state = _make_state(800501)
    await state.set_state(SettingsStates.change_name)

    message = _FakeMessage(text="Franky", from_user_id=800501)
    await edit_profile_name_save(message, state, session)

    assert await state.get_state() is None
    text, markup = message.sent[0]
    assert text == t("edit_profile_header", "en")
    buttons = _buttons(markup)
    assert any("Franky" in label and cb == "editprofile:name" for label, cb in buttons)

    player = await PlayerService(session).get_by_telegram_id(800501)
    assert player.first_name == "Franky"


async def test_edit_profile_name_save_rejects_empty(session):
    await _make_player(session, 800601, "Grace")
    state = _make_state(800601)
    await state.set_state(SettingsStates.change_name)

    message = _FakeMessage(text="   ", from_user_id=800601)
    await edit_profile_name_save(message, state, session)

    text, _ = message.sent[0]
    assert text == t("edit_profile_name_error", "en")
    assert await state.get_state() == SettingsStates.change_name.state  # stays in the flow

    player = await PlayerService(session).get_by_telegram_id(800601)
    assert player.first_name == "Grace"  # unchanged


# ── Languages field (new, multi-select) ──────────────────────────────────────

async def test_edit_profile_languages_start_shows_current_selection(session):
    await _make_player(session, 800701, "Hank")
    state = _make_state(800701)

    callback = _FakeCallback(data="editprofile:languages", user_id=800701)
    await edit_profile_languages_start(callback, state, session)

    assert await state.get_state() == SettingsStates.change_languages.state
    assert (await state.get_data())["selected_languages"] == ["ENG"]
    args, kwargs = callback.message.edit_text.call_args
    assert args[0] == t("edit_profile_languages_header", "en")
    buttons = _buttons(kwargs["reply_markup"])
    assert ("✅ ENG", "language_toggle:ENG") in buttons
    assert ("UKR", "language_toggle:UKR") in buttons


async def test_edit_profile_language_toggle_updates_selection(session):
    state = _make_state(800801)
    await state.set_state(SettingsStates.change_languages)
    await state.update_data(selected_languages=["ENG"], lang="en")

    callback = _FakeCallback(data="language_toggle:UKR", user_id=800801)
    await edit_profile_language_toggle(callback, state)

    callback.answer.assert_awaited_once()
    assert sorted((await state.get_data())["selected_languages"]) == ["ENG", "UKR"]
    callback.message.edit_reply_markup.assert_awaited_once()


async def test_edit_profile_languages_done_saves_and_returns(session):
    await _make_player(session, 800901, "Ivy")
    state = _make_state(800901)
    await state.set_state(SettingsStates.change_languages)
    await state.update_data(selected_languages=["UKR", "RUS"], lang="en")

    callback = _FakeCallback(data="languages_done", user_id=800901)
    await edit_profile_languages_done(callback, state, session)

    assert await state.get_state() is None
    args, kwargs = callback.message.edit_text.call_args
    assert args[0] == t("edit_profile_header", "en")
    buttons = _buttons(kwargs["reply_markup"])
    assert any("UKR, RUS" in label and cb == "editprofile:languages" for label, cb in buttons)

    player = await PlayerService(session).get_by_telegram_id(800901)
    assert sorted(player.spoken_languages) == ["RUS", "UKR"]


# ── Courts field (Sprint 10.3 Phase 2 — Court Registry) ─────────────────────
# New flow: Select Tennis Zone -> that zone's courts -> optional custom court.

async def test_settings_change_courts_opens_zone_selection_first(session):
    """Tapping the Courts field no longer jumps straight to a court list —
    it opens the Tennis Zone picker first (Select Tennis Zone -> zone's courts)."""
    await _make_player(session, 801001, "Jill")
    state = _make_state(801001)

    callback = _FakeCallback(data="settings:courts", user_id=801001)
    await settings_change_courts(callback, state, session)

    assert await state.get_state() == SettingsStates.choose_courts_zone.state
    args, kwargs = callback.message.edit_text.call_args
    assert args[0] == t("choose_area", "en")
    buttons = _buttons(kwargs["reply_markup"])
    assert ("Downtown", "settings_courts_zone:Downtown") in buttons
    assert ("Mississauga", "settings_courts_zone:Mississauga") in buttons


async def test_settings_choose_courts_zone_shows_only_that_zones_courts(session):
    await _make_player(session, 801101, "Kim")
    state = _make_state(801101)
    await state.set_state(SettingsStates.choose_courts_zone)
    await state.update_data(selected_courts=["High Park"], lang="en")

    callback = _FakeCallback(data="settings_courts_zone:West Toronto / Etobicoke", user_id=801101)
    await settings_choose_courts_zone(callback, state)

    assert await state.get_state() == SettingsStates.change_courts.state
    assert (await state.get_data())["courts_zone"] == "West Toronto / Etobicoke"
    args, kwargs = callback.message.edit_text.call_args
    assert args[0] == t("choose_courts", "en", zone="West Toronto / Etobicoke")
    buttons = _buttons(kwargs["reply_markup"])
    assert ("✅ High Park", "court_toggle:High Park") in buttons
    assert ("Colonel Samuel Smith Park", "court_toggle:Colonel Samuel Smith Park") in buttons
    # Downtown-only courts must not appear on the Etobicoke zone screen.
    assert not any(cb == "court_toggle:Ramsden Park" for _, cb in buttons)
    assert ("➕ Add my own court", "court_add_custom") in buttons


async def test_settings_court_toggle_then_done_saves_to_profile(session):
    await _make_player(session, 801201, "Leo")
    state = _make_state(801201)
    await state.set_state(SettingsStates.change_courts)
    await state.update_data(selected_courts=[], lang="en", courts_zone="Downtown")

    toggle_cb = _FakeCallback(data="court_toggle:Withrow Park", user_id=801201)
    await settings_court_toggle(toggle_cb, state)
    assert (await state.get_data())["selected_courts"] == ["Withrow Park"]

    done_cb = _FakeCallback(data="courts_done", user_id=801201)
    await settings_courts_done(done_cb, state, session)

    player = await PlayerService(session).get_by_telegram_id(801201)
    assert player.preferred_courts == ["Withrow Park"]


async def test_settings_custom_court_flow_adds_and_confirms(session):
    """➕ Add my own court -> free-text prompt -> confirmation -> the same
    zone screen re-renders with the new court immediately visible and
    already checked in a "Custom Courts" section (not just a text message),
    then Done persists it."""
    await _make_player(session, 801301, "Mia")
    state = _make_state(801301)
    await state.set_state(SettingsStates.change_courts)
    await state.update_data(selected_courts=[], lang="en", courts_zone="Downtown")

    add_cb = _FakeCallback(data="court_add_custom", user_id=801301)
    await settings_court_add_custom(add_cb, state)
    assert await state.get_state() == SettingsStates.enter_custom_court.state
    prompt_text, _ = add_cb.message.sent[0]
    assert prompt_text == t("custom_court_prompt", "en")

    message = _FakeMessage(text="High Park Bubble", from_user_id=801301)
    await settings_custom_court_submit(message, state)

    assert await state.get_state() == SettingsStates.change_courts.state
    assert (await state.get_data())["selected_courts"] == ["High Park Bubble"]
    confirmation, _ = message.sent[0]
    assert confirmation == t("custom_court_added", "en")
    screen_text, screen_markup = message.sent[1]
    assert screen_text == t("choose_courts", "en", zone="Downtown")
    buttons = _buttons(screen_markup)
    assert (t("custom_courts_divider", "en"), "noop") in buttons
    assert ("✅ High Park Bubble", "court_toggle:High Park Bubble") in buttons

    done_cb = _FakeCallback(data="courts_done", user_id=801301)
    await settings_courts_done(done_cb, state, session)
    player = await PlayerService(session).get_by_telegram_id(801301)
    assert player.preferred_courts == ["High Park Bubble"]


async def test_custom_court_toggled_off_by_tapping_again(session):
    """A custom court's "Custom Courts" button behaves exactly like a registry
    button — tapping it again removes it from the selection, using the same
    court_toggle handler and no separate code path."""
    state = _make_state(801351)
    await state.set_state(SettingsStates.change_courts)
    await state.update_data(selected_courts=["High Park Bubble"], lang="en", courts_zone="Downtown")

    toggle_cb = _FakeCallback(data="court_toggle:High Park Bubble", user_id=801351)
    await settings_court_toggle(toggle_cb, state)

    assert (await state.get_data())["selected_courts"] == []
    buttons = _buttons(toggle_cb.message.edit_reply_markup.call_args[1]["reply_markup"])
    assert not any(cb == "court_toggle:High Park Bubble" for _, cb in buttons)
    assert (t("custom_courts_divider", "en"), "noop") not in buttons  # section disappears once empty


async def test_courts_screen_mixes_registry_and_custom_selections(session):
    """A registry court and a custom court, both selected, render together —
    the registry court checked in its normal spot, the custom court checked
    in the separate 'Custom Courts' section."""
    state = _make_state(801361)
    await state.set_state(SettingsStates.change_courts)
    await state.update_data(
        selected_courts=["Ramsden Park", "High Park Bubble"], lang="en", courts_zone="Downtown"
    )

    toggle_cb = _FakeCallback(data="court_toggle:Withrow Park", user_id=801361)
    await settings_court_toggle(toggle_cb, state)  # re-render without changing the mix under test

    buttons = _buttons(toggle_cb.message.edit_reply_markup.call_args[1]["reply_markup"])
    assert ("✅ Ramsden Park", "court_toggle:Ramsden Park") in buttons
    assert ("✅ High Park Bubble", "court_toggle:High Park Bubble") in buttons
    assert (t("custom_courts_divider", "en"), "noop") in buttons


async def test_settings_custom_court_rejects_empty_input(session):
    await _make_player(session, 801401, "Nia")
    state = _make_state(801401)
    await state.set_state(SettingsStates.enter_custom_court)
    await state.update_data(selected_courts=[], lang="en", courts_zone="Downtown")

    message = _FakeMessage(text="   ", from_user_id=801401)
    await settings_custom_court_submit(message, state)

    text, _ = message.sent[0]
    assert text == t("custom_court_empty_error", "en")
    assert await state.get_state() == SettingsStates.enter_custom_court.state  # stays in the flow
    assert (await state.get_data())["selected_courts"] == []


# ── Backward compatibility: pre-Sprint-10.3 profiles keep working ───────────

async def test_pre_sprint_court_selection_survives_a_zone_screen_visit(session):
    """A player whose preferred_courts predate the Court Registry (e.g. the
    literal 'Other' sentinel from the old flow) must not lose that selection
    just by opening a different zone's court screen — no migration is
    required for old profiles to keep working. It now also shows up in the
    "Custom Courts" section (same mechanism as a freshly-added custom court),
    which is a UX improvement over being silently invisible."""
    service = PlayerService(session)
    await service.get_or_create(PlayerCreate(telegram_id=801501, first_name="Omar"))
    await service.update_profile(
        801501,
        PlayerUpdate(language="en", skill_level=3.0, home_area="Downtown", preferred_courts=["Other"]),
    )
    await session.commit()

    state = _make_state(801501)
    await state.set_state(SettingsStates.choose_courts_zone)
    await state.update_data(selected_courts=["Other"], lang="en")

    # Open an unrelated zone screen — "Other" isn't a Scarborough registry
    # court, but it still surfaces (checked) in the Custom Courts section.
    zone_cb = _FakeCallback(data="settings_courts_zone:Scarborough", user_id=801501)
    await settings_choose_courts_zone(zone_cb, state)
    buttons = _buttons(zone_cb.message.edit_text.call_args[1]["reply_markup"])
    assert ("✅ Other", "court_toggle:Other") in buttons

    # ...then hit Done without touching anything — the old value must survive.
    done_cb = _FakeCallback(data="courts_done", user_id=801501)
    await settings_courts_done(done_cb, state, session)

    player = await service.get_by_telegram_id(801501)
    assert player.preferred_courts == ["Other"]
    assert player.is_profile_complete is True
