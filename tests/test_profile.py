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
    settings_courts_done,
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
