"""Tests for Find Players for a Match's empty state (Sprint 11 Phase 3.1A)
— Invite a Friend, the same player-discovery empty state Find Partner uses.
"""
from datetime import date, time
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from aiogram.fsm.storage.memory import MemoryStorage

from backend.app.bot.handlers.find_players_for_match import fpm_start
from backend.app.bot.states.states import FindPlayersForMatchStates
from backend.app.bot.texts import t
from backend.app.database.models.game import MatchType
from backend.app.schemas.game import GameCreate
from backend.app.schemas.player import PlayerCreate, PlayerUpdate
from backend.app.services.game_service import GameService
from backend.app.services.player_service import PlayerService


def _make_state(user_id: int) -> FSMContext:
    return FSMContext(storage=MemoryStorage(), key=StorageKey(bot_id=1, chat_id=user_id, user_id=user_id))


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


class _FakeBot:
    async def get_me(self):
        return SimpleNamespace(username="baseline_test_bot")


async def _make_player(session, telegram_id: int, area: str, level: float, first_name: str = "Player") -> None:
    svc = PlayerService(session)
    await svc.get_or_create(PlayerCreate(telegram_id=telegram_id, first_name=first_name))
    await svc.update_profile(
        telegram_id,
        PlayerUpdate(language="en", skill_level=level, home_area=area, preferred_courts=["High Park"]),
    )


async def _make_game(session, organizer_id: int, area: str, level: float) -> int:
    game = await GameService(session).create_game(
        creator_telegram_id=organizer_id,
        data=GameCreate(
            court="High Park",
            area=area,
            date=date(2026, 8, 1),
            time=time(18, 0),
            match_type=MatchType.SINGLES,
            required_level=level,
        ),
    )
    assert game is not None
    return game.id


async def test_fpm_start_empty_state_offers_invite_a_friend(session):
    """No matching candidates in this player's area/level — the empty
    state must offer a real next action instead of a dead end."""
    await _make_player(session, 910001, "Downtown", 3.0, "Owner")
    game_id = await _make_game(session, 910001, "Downtown", 3.0)
    await session.commit()

    state = _make_state(910001)
    callback = _FakeCallback(data=f"fpm:start:{game_id}", user_id=910001)
    await fpm_start(callback, state, session, _FakeBot())

    assert await state.get_state() is None  # state.clear() on the empty path
    text, markup = callback.message.sent[0]
    assert text == t("player_discovery_no_results", "en")

    buttons = [(b.text, b.callback_data, b.url) for row in markup.inline_keyboard for b in row]
    invite = next(b for b in buttons if b[0] == t("btn_invite_friend", "en"))
    assert invite[2] is not None
    assert invite[2].startswith("https://t.me/share/url?")
    assert "baseline_test_bot" in invite[2]

    back = next(b for b in buttons if b[0] == t("btn_back", "en"))
    assert back[1] == "fpm:menu"
    callback.answer.assert_awaited_once()
