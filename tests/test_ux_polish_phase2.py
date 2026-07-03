"""Tests for Sprint 10.4 Phase 2 (UX Polish) — MVP Required items only.

UX-04: 🎾 no longer shared between two main-menu buttons.
UX-22: cancelling a match notifies every participant, not just the organizer.
UX-23: Cancel Match requires a confirmation step before anything is cancelled.
UX-24: View Roster's "Back" returns to Match Details, not the Main Menu.
UX-27: the "profile incomplete" message matches actual behaviour.
"""
from datetime import date, time
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from backend.app.bot.handlers.confirm_match import view_roster
from backend.app.bot.handlers.my_matches import (
    match_cancel_ask_handler,
    match_cancel_confirm_handler,
)
from backend.app.bot.handlers.profile import show_profile
from backend.app.bot.texts import t
from backend.app.database.models.game import GameStatus, MatchType
from backend.app.schemas.game import GameCreate
from backend.app.schemas.player import PlayerCreate, PlayerUpdate
from backend.app.services.game_service import GameService
from backend.app.services.player_service import PlayerService


def _buttons(markup) -> list[tuple[str, str]]:
    return [(b.text, b.callback_data) for row in markup.inline_keyboard for b in row]


class _FakeMessage:
    def __init__(self, text: str | None = None, from_user_id: int | None = None) -> None:
        self.text = text
        self.from_user = SimpleNamespace(id=from_user_id) if from_user_id else None
        self.sent: list[tuple[str, object]] = []

    async def answer(self, text, reply_markup=None, parse_mode=None):
        self.sent.append((text, reply_markup))
        return self


class _FakeCallback:
    """Enough for handler functions that only touch .data, .message,
    .from_user.id, .answer(), .bot.send_message()."""

    def __init__(self, data: str, user_id: int) -> None:
        self.data = data
        self.from_user = SimpleNamespace(id=user_id)
        self.message = AsyncMock()
        self.message.edit_text = AsyncMock()
        self.bot = AsyncMock()
        self.bot.send_message = AsyncMock()
        self.answer = AsyncMock()


async def _make_player(session, telegram_id: int, first_name: str = "Player") -> None:
    svc = PlayerService(session)
    await svc.get_or_create(PlayerCreate(telegram_id=telegram_id, first_name=first_name))
    await svc.update_profile(
        telegram_id,
        PlayerUpdate(language="en", skill_level=3.0, home_area="Downtown", preferred_courts=["Ramsden Park"]),
    )


async def _make_match_with_participant(
    session, organizer_tid: int, participant_tid: int
) -> int:
    await _make_player(session, organizer_tid, "Organizer")
    await _make_player(session, participant_tid, "Participant")
    game = await GameService(session).create_game(
        creator_telegram_id=organizer_tid,
        data=GameCreate(
            court="Ramsden Park",
            area="Downtown",
            date=date(2026, 9, 1),
            time=time(18, 0),
            match_type=MatchType.SINGLES,
        ),
    )
    assert game is not None
    _, err = await GameService(session).join_match(game.id, participant_tid)
    assert err == ""
    return game.id


# ── UX-04: no duplicate emoji on the main menu ──────────────────────────────────

def test_available_matches_button_no_longer_shares_emoji_with_organize_match():
    for lang in ["en", "uk", "ru"]:
        organize = t("btn_organize_match", lang)
        available = t("btn_available_matches", lang)
        organize_emoji = organize.split()[0]
        available_emoji = available.split()[0]
        assert organize_emoji != available_emoji, f"{lang}: both buttons use {organize_emoji}"
        assert "🎾" not in available


def test_available_matches_header_matches_its_menu_button_emoji():
    for lang in ["en", "uk", "ru"]:
        header = t("available_matches_header", lang, count=0)
        button = t("btn_available_matches", lang)
        assert header.split()[0] == button.split()[0]


# ── UX-27: profile-incomplete message matches actual behaviour ─────────────────

@pytest.mark.asyncio
async def test_show_profile_incomplete_uses_the_honest_message(session):
    await PlayerService(session).get_or_create(PlayerCreate(telegram_id=600001, first_name="Nora"))
    await session.commit()

    message = _FakeMessage(from_user_id=600001)
    await show_profile(message, session)

    text, _ = message.sent[0]
    assert text == t("profile_not_complete_action", "en")


@pytest.mark.asyncio
async def test_show_profile_incomplete_no_longer_promises_onboarding(session):
    """The old copy claimed onboarding would start automatically — it never
    did. Confirm the misleading text is gone, not just replaced elsewhere."""
    await PlayerService(session).get_or_create(PlayerCreate(telegram_id=600002, first_name="Omar"))
    await session.commit()

    message = _FakeMessage(from_user_id=600002)
    await show_profile(message, session)

    text, _ = message.sent[0]
    assert "onboarding" not in text.lower()
    assert "starting" not in text.lower()


# ── UX-24: View Roster returns to Match Details, not the Main Menu ─────────────

@pytest.mark.asyncio
async def test_view_roster_back_button_returns_to_match_details(session):
    game_id = await _make_match_with_participant(session, 600101, 600102)
    await session.commit()

    callback = _FakeCallback(data=f"view_game:{game_id}", user_id=600101)
    await view_roster(callback, session)

    args, kwargs = callback.message.answer.call_args
    buttons = _buttons(kwargs["reply_markup"])
    assert (t("btn_back_to_match_details", "en"), f"match:open:{game_id}") in buttons
    assert not any(cb == "menu:main" and label == t("match_details_btn_back", "en") for label, cb in buttons)


# ── UX-23: Cancel Match requires confirmation ───────────────────────────────────

@pytest.mark.asyncio
async def test_cancel_match_ask_shows_confirmation_without_cancelling(session):
    game_id = await _make_match_with_participant(session, 600201, 600202)
    await session.commit()

    callback = _FakeCallback(data=f"match:cancel:{game_id}", user_id=600201)
    await match_cancel_ask_handler(callback, session)

    args, kwargs = callback.message.edit_text.call_args
    assert args[0] == t("cancel_match_confirm_ask", "en")
    buttons = _buttons(kwargs["reply_markup"])
    assert (t("cancel_match_confirm_yes", "en"), f"match:cancel_confirm:{game_id}") in buttons
    assert (t("cancel_match_confirm_no", "en"), f"match:open:{game_id}") in buttons

    game = await GameService(session).get_game(game_id)
    assert game.status != GameStatus.CANCELLED  # nothing happened yet


# ── UX-22: cancelling notifies every participant ────────────────────────────────

@pytest.mark.asyncio
async def test_cancel_match_confirm_notifies_participant_not_organizer(session):
    game_id = await _make_match_with_participant(session, 600301, 600302)
    await session.commit()

    callback = _FakeCallback(data=f"match:cancel_confirm:{game_id}", user_id=600301)
    await match_cancel_confirm_handler(callback, session)

    game = await GameService(session).get_game(game_id)
    assert game.status == GameStatus.CANCELLED

    # Organizer gets the confirmation via edit_text, not a push notification.
    callback.bot.send_message.assert_awaited_once()
    notified_tid = callback.bot.send_message.call_args[0][0]
    assert notified_tid == 600302  # the participant, not the organizer (600301)

    notified_text = callback.bot.send_message.call_args[0][1]
    assert "cancelled" in notified_text.lower() or "скасовано" in notified_text.lower()


@pytest.mark.asyncio
async def test_cancel_match_confirm_notifies_all_participants_in_doubles(session):
    await _make_player(session, 600401, "Organizer")
    await _make_player(session, 600402, "P2")
    await _make_player(session, 600403, "P3")
    game = await GameService(session).create_game(
        creator_telegram_id=600401,
        data=GameCreate(
            court="Ramsden Park", area="Downtown", date=date(2026, 9, 1), time=time(18, 0),
            match_type=MatchType.DOUBLES,
        ),
    )
    assert game is not None
    for tid in (600402, 600403):
        _, err = await GameService(session).join_match(game.id, tid)
        assert err == ""
    await session.commit()

    callback = _FakeCallback(data=f"match:cancel_confirm:{game.id}", user_id=600401)
    await match_cancel_confirm_handler(callback, session)

    assert callback.bot.send_message.await_count == 2
    notified_ids = {call.args[0] for call in callback.bot.send_message.await_args_list}
    assert notified_ids == {600402, 600403}


@pytest.mark.asyncio
async def test_cancel_match_confirm_rejects_non_organizer(session):
    game_id = await _make_match_with_participant(session, 600501, 600502)
    await session.commit()

    callback = _FakeCallback(data=f"match:cancel_confirm:{game_id}", user_id=600502)
    await match_cancel_confirm_handler(callback, session)

    callback.answer.assert_awaited_once_with(t("cancel_match_not_yours", "en"), show_alert=True)
    callback.bot.send_message.assert_not_awaited()

    game = await GameService(session).get_game(game_id)
    assert game.status != GameStatus.CANCELLED


# ── Cancel Match is now a single flow, reachable from Match Details AND the
#    game-full notification (game_full_keyboard) ────────────────────────────────

def test_game_full_keyboard_cancel_button_uses_the_unified_cancel_flow():
    from backend.app.bot.keyboards.keyboards import game_full_keyboard

    markup = game_full_keyboard("en", game_id=42)
    buttons = _buttons(markup)
    assert ("❌ Cancel Match", "match:cancel:42") in buttons
    assert not any(cb == "cancel_match:42" for _, cb in buttons)
