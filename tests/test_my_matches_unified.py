"""Tests for Sprint 10.3 Phase 1 — unified My Matches / Match Details flow.

Before this fix there were two parallel "My Matches" screens: the real one
(backend/app/bot/handlers/my_matches.py, with a proper Match Details screen
and Edit/Invite/Cancel/Back actions) and a legacy duplicate wired to the
Organize Match success screen's "My Matches" button
(backend/app/bot/handlers/organize_match.py: om_my_matches), which used a
different service method, a different card format, and hardcoded the
player count. These tests verify only one screen remains reachable.
"""
from datetime import date, time
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

import backend.app.bot.handlers.organize_match as organize_match
from backend.app.bot.handlers.my_matches import my_matches_back_handler
from backend.app.bot.keyboards.keyboards import om_success_keyboard
from backend.app.database.models.game import MatchType
from backend.app.schemas.game import GameCreate
from backend.app.schemas.player import PlayerCreate, PlayerUpdate
from backend.app.services.game_service import GameService
from backend.app.services.player_service import PlayerService


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


async def _make_player(session, telegram_id: int, first_name: str = "Player") -> None:
    svc = PlayerService(session)
    await svc.get_or_create(PlayerCreate(telegram_id=telegram_id, first_name=first_name))
    await svc.update_profile(
        telegram_id,
        PlayerUpdate(language="en", skill_level=3.0, home_area="Downtown", preferred_courts=["High Park"]),
    )


# ── Only one screen is wired up ─────────────────────────────────────────────────

def test_success_screen_my_matches_button_uses_unified_callback():
    """The post-creation success screen's 'My Matches' button must route to
    the same callback as the main-menu My Matches flow (my_matches:back),
    not the old, separate 'om:my_matches' duplicate."""
    markup = om_success_keyboard("en", game_id=42)
    buttons = [b for row in markup.inline_keyboard for b in row]
    my_matches_buttons = [b for b in buttons if "my_matches" in (b.callback_data or "")]

    assert len(my_matches_buttons) == 1
    assert my_matches_buttons[0].callback_data == "my_matches:back"


def test_duplicate_my_matches_handler_removed():
    """The legacy duplicate handler (om_my_matches) must no longer exist —
    there must be only one Match Details / My Matches implementation."""
    assert not hasattr(organize_match, "om_my_matches")


# ── End-to-end: whichever entry point, the same screen renders the match ───────

@pytest.mark.asyncio
async def test_success_screen_button_and_main_menu_show_the_same_match(session):
    """Regardless of entry point, tapping through to My Matches renders the
    same freshly created match via the same handler."""
    await _make_player(session, 40001, "Organizer")
    game = await GameService(session).create_game(
        creator_telegram_id=40001,
        data=GameCreate(
            court="High Park Court 3",
            area="Downtown",
            date=date(2026, 9, 1),
            time=time(18, 0),
            match_type=MatchType.SINGLES,
        ),
    )
    assert game is not None

    # This is the exact handler the success screen's "My Matches" button
    # (callback_data="my_matches:back") now invokes — the same one used by
    # the main-menu "📋 My Matches" trigger and by "Back" from Match Details.
    callback = _FakeCallback(data="my_matches:back", user_id=40001)
    await my_matches_back_handler(callback, session)

    sent_texts = [text for text, _ in callback.message.sent]
    assert any("High Park Court 3" in text for text in sent_texts)
