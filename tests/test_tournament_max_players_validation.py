"""Regression test for Sprint 14, Step 2's UX finish: Create
Tournament's max_players input now enforces "power of two" immediately,
at input time — not only later, at Generate Matches time. Before this,
a value like 6 was silently accepted at creation and only rejected
after players had already registered. Same rule
(TournamentService.is_power_of_two), checked in two places by design
(defense in depth) — never duplicated logic.
"""
from types import SimpleNamespace

import pytest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from aiogram.fsm.storage.memory import MemoryStorage

from backend.app.bot.handlers.admin.tournaments import tourn_enter_max_players
from backend.app.bot.states.states import CreateTournamentStates


class _FakeMessage:
    def __init__(self, text: str) -> None:
        self.text = text
        self.sent: list[str] = []
        self.from_user = SimpleNamespace(id=1)

    async def answer(self, text, reply_markup=None, parse_mode=None):
        self.sent.append(text)
        return self


def _make_state() -> FSMContext:
    return FSMContext(storage=MemoryStorage(), key=StorageKey(bot_id=1, chat_id=1, user_id=1))


@pytest.mark.asyncio
@pytest.mark.parametrize("invalid_value", ["6", "10", "12", "14", "18", "0", "-4", "abc"])
async def test_enter_max_players_rejects_non_power_of_two(invalid_value: str) -> None:
    state = _make_state()
    await state.set_state(CreateTournamentStates.enter_max_players)
    await state.update_data(lang="en")

    message = _FakeMessage(invalid_value)
    await tourn_enter_max_players(message, state)

    assert message.sent == ["❌ Enter a number that is a power of two (4, 8, 16, 32...)."]
    data = await state.get_data()
    assert "max_players" not in data
    # Stays on the same input step — the wizard doesn't advance on a rejected value.
    assert await state.get_state() == CreateTournamentStates.enter_max_players.state


@pytest.mark.asyncio
@pytest.mark.parametrize("valid_value", ["4", "8", "16", "32"])
async def test_enter_max_players_accepts_power_of_two(valid_value: str) -> None:
    state = _make_state()
    await state.set_state(CreateTournamentStates.enter_max_players)
    await state.update_data(
        lang="en",
        name="Summer Cup",
        area="Downtown",
        court="High Park",
        start_date="2026-08-01",
        start_time="10:00",
        registration_deadline="2026-07-20",
    )

    message = _FakeMessage(valid_value)
    await tourn_enter_max_players(message, state)

    data = await state.get_data()
    assert data["max_players"] == int(valid_value)
    assert await state.get_state() == CreateTournamentStates.confirm.state
