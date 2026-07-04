"""Tests for the Admin Center Players module handler flow
(Sprint 11 Phase 3.0) — Dashboard entry, root screen, Browse pagination,
Search (single/multiple/no match), Player Details, and navigation."""
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from aiogram.fsm.storage.memory import MemoryStorage
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.bot.handlers.admin.players import (
    players_back_to_dashboard,
    players_back_to_root,
    players_browse,
    players_open_details,
    players_open_from_dashboard,
    players_page,
    players_search_prompt,
    players_search_submit,
)
from backend.app.bot.states.states import AdminPlayersStates
from backend.app.database.models.operator_permission import OperatorPermission, OperatorRole
from backend.app.database.models.player import Player
from backend.app.database.repositories.operator_permission_repository import (
    OperatorPermissionRepository,
)
from backend.app.database.repositories.player_repository import PlayerRepository
from backend.app.services import admin_session_service as svc_module
from backend.app.services.admin_session_service import AdminSessionService


@pytest.fixture(autouse=True)
def _clear_process_global_state():
    svc_module._sessions.clear()
    svc_module._attempts.clear()
    yield
    svc_module._sessions.clear()
    svc_module._attempts.clear()


def _make_state(user_id: int) -> FSMContext:
    return FSMContext(storage=MemoryStorage(), key=StorageKey(bot_id=1, chat_id=user_id, user_id=user_id))


class _FakeMessage:
    def __init__(self, text: str | None = None) -> None:
        self.text = text
        self.sent: list[tuple[str, object]] = []
        self.from_user = None

    async def answer(self, text, reply_markup=None, parse_mode=None):
        self.sent.append((text, reply_markup))
        return self


class _FakeCallback:
    def __init__(self, user_id: int, data: str = "") -> None:
        self.from_user = SimpleNamespace(id=user_id)
        self.data = data
        self.message = _FakeMessage()
        self.answer = AsyncMock()


async def _seed_and_login(session: AsyncSession, telegram_id: int) -> None:
    await OperatorPermissionRepository(session).add(
        OperatorPermission(telegram_id=telegram_id, role=OperatorRole.ADMIN)
    )
    await session.commit()
    await AdminSessionService(session).create_session(telegram_id, OperatorRole.ADMIN)


async def _seed_players(session: AsyncSession, count: int) -> None:
    repo = PlayerRepository(session)
    for i in range(count):
        await repo.add(
            Player(
                telegram_id=2000 + i,
                first_name=f"Player{i}",
                username=f"player{i}",
                home_area="Downtown",
                skill_level=3.0,
            )
        )
    await session.commit()


# ---------------------------------------------------------------------------
# Authorization gate — every handler requires an active session
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_players_open_from_dashboard_requires_active_session(session: AsyncSession) -> None:
    callback = _FakeCallback(user_id=111)
    state = _make_state(111)

    await players_open_from_dashboard(callback, session, state)

    assert callback.message.sent == []
    callback.answer.assert_not_called()


# ---------------------------------------------------------------------------
# Players root screen
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_players_root_shows_total_count(session: AsyncSession) -> None:
    await _seed_and_login(session, 111)
    await _seed_players(session, 3)
    callback = _FakeCallback(user_id=111)
    state = _make_state(111)

    await players_open_from_dashboard(callback, session, state)

    assert len(callback.message.sent) == 1
    text, markup = callback.message.sent[0]
    assert "Players" in text
    assert "Total Players: 3" in text
    assert markup is not None


@pytest.mark.asyncio
async def test_players_root_clears_fsm_state(session: AsyncSession) -> None:
    await _seed_and_login(session, 111)
    callback = _FakeCallback(user_id=111)
    state = _make_state(111)
    await state.set_state(AdminPlayersStates.browsing)

    await players_back_to_root(callback, session, state)

    assert await state.get_state() is None


# ---------------------------------------------------------------------------
# Browse Players pagination
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_browse_first_page_shows_twenty_and_next_only(session: AsyncSession) -> None:
    await _seed_and_login(session, 111)
    await _seed_players(session, 25)
    callback = _FakeCallback(user_id=111)
    state = _make_state(111)

    await players_browse(callback, session, state)

    text, markup = callback.message.sent[0]
    assert "Page 1/2" in text
    assert "Player0" in text
    assert "Player19" in text
    assert "Player20" not in text
    assert await state.get_data() == {"current_page": 1}


@pytest.mark.asyncio
async def test_browse_second_page_shows_remaining_five(session: AsyncSession) -> None:
    await _seed_and_login(session, 111)
    await _seed_players(session, 25)
    state = _make_state(111)
    callback = _FakeCallback(user_id=111, data="players:page:2")

    await players_page(callback, session, state)

    text, _ = callback.message.sent[0]
    assert "Page 2/2" in text
    assert "Player20" in text
    assert "Player24" in text


@pytest.mark.asyncio
async def test_browse_empty_database_shows_page_one_of_one(session: AsyncSession) -> None:
    await _seed_and_login(session, 111)
    callback = _FakeCallback(user_id=111)
    state = _make_state(111)

    await players_browse(callback, session, state)

    text, _ = callback.message.sent[0]
    assert "Page 1/1" in text


# ---------------------------------------------------------------------------
# Search Player
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_search_prompt_sets_state(session: AsyncSession) -> None:
    await _seed_and_login(session, 111)
    callback = _FakeCallback(user_id=111)
    state = _make_state(111)

    await players_search_prompt(callback, session, state)

    assert await state.get_state() == AdminPlayersStates.enter_search
    assert len(callback.message.sent) == 1


@pytest.mark.asyncio
async def test_search_single_match_opens_player_details(session: AsyncSession) -> None:
    await _seed_and_login(session, 111)
    await _seed_players(session, 3)
    state = _make_state(111)
    await state.set_state(AdminPlayersStates.enter_search)
    message = _FakeMessage(text="2000")
    message.from_user = SimpleNamespace(id=111)

    await players_search_submit(message, session, state)

    assert await state.get_state() is None
    text, markup = message.sent[0]
    assert "Player Details" in text
    assert "2000" in text
    assert "Player0" in text


@pytest.mark.asyncio
async def test_search_multiple_matches_shows_selectable_list(session: AsyncSession) -> None:
    await _seed_and_login(session, 111)
    await _seed_players(session, 3)
    state = _make_state(111)
    await state.set_state(AdminPlayersStates.enter_search)
    message = _FakeMessage(text="Player")
    message.from_user = SimpleNamespace(id=111)

    await players_search_submit(message, session, state)

    text, markup = message.sent[0]
    assert "Search Results" in text
    assert "(3)" in text
    assert markup is not None


@pytest.mark.asyncio
async def test_search_no_match_shows_no_players_found(session: AsyncSession) -> None:
    await _seed_and_login(session, 111)
    state = _make_state(111)
    await state.set_state(AdminPlayersStates.enter_search)
    message = _FakeMessage(text="nobody")
    message.from_user = SimpleNamespace(id=111)

    await players_search_submit(message, session, state)

    text, _ = message.sent[0]
    assert "No players found" in text


# ---------------------------------------------------------------------------
# Player Details
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_open_details_shows_every_required_field(session: AsyncSession) -> None:
    await _seed_and_login(session, 111)
    repo = PlayerRepository(session)
    player = await repo.add(
        Player(
            telegram_id=3000,
            first_name="Alice",
            username="alicej",
            language="en",
            skill_level=4.5,
            home_area="Downtown",
            preferred_courts='["Ramsden Park"]',
            spoken_languages='["UKR", "ENG"]',
            available_now=True,
        )
    )
    await session.commit()

    callback = _FakeCallback(user_id=111, data=f"players:open:{player.id}")
    await players_open_details(callback, session)

    text, markup = callback.message.sent[0]
    assert "3000" in text
    assert "Alice" in text
    assert "@alicej" in text
    assert "UKR • ENG" in text
    assert "4.5" in text
    assert "Downtown" in text
    assert "Ramsden Park" in text
    assert "Yes" in text  # Available Now
    assert markup is not None


@pytest.mark.asyncio
async def test_open_details_handles_missing_optional_fields(session: AsyncSession) -> None:
    await _seed_and_login(session, 111)
    repo = PlayerRepository(session)
    player = await repo.add(Player(telegram_id=3001, first_name="Bob"))
    await session.commit()

    callback = _FakeCallback(user_id=111, data=f"players:open:{player.id}")
    await players_open_details(callback, session)

    text, _ = callback.message.sent[0]
    assert "—" in text  # blank username/languages/level/area/courts render as em dash
    assert "⚠️" in text  # incomplete profile


# ---------------------------------------------------------------------------
# Regression: Markdown special characters in free-text fields must never
# reach Telegram unescaped (TelegramBadRequest: "can't parse entities").
# Telegram usernames routinely contain underscores; first_name and custom
# court names are unrestricted free text. Assertions check for the exact
# escaped substring aiogram's markdown_decoration.quote() produces,
# rather than a generic "no unescaped specials" scan — this file's own
# messages deliberately (and correctly) use unescaped `*`/backtick
# markup for the header and the Telegram ID code span, so a generic scan
# would flag those as false positives.
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_player_details_escapes_underscore_in_username_and_name(session: AsyncSession) -> None:
    """The exact crash from the bug report: a single unpaired '_' in
    first_name/username read as an unterminated italic span."""
    await _seed_and_login(session, 111)
    repo = PlayerRepository(session)
    player = await repo.add(
        Player(telegram_id=4000, first_name="John_Doe", username="john_doe")
    )
    await session.commit()

    callback = _FakeCallback(user_id=111, data=f"players:open:{player.id}")
    await players_open_details(callback, session)

    text, _ = callback.message.sent[0]
    # The literal name/username still reach the operator, just escaped —
    # never the raw, unpaired-underscore form that crashed Telegram.
    assert "John\\_Doe" in text
    assert "John_Doe" not in text
    assert "@john\\_doe" in text
    assert "@john_doe" not in text


@pytest.mark.asyncio
async def test_player_details_escapes_full_markdown_special_set(session: AsyncSession) -> None:
    """Brackets, asterisks, and backticks are just as unbalanced-prone as
    underscores and must be escaped the same way."""
    await _seed_and_login(session, 111)
    repo = PlayerRepository(session)
    player = await repo.add(
        Player(
            telegram_id=4001,
            first_name="*Bold* [link](x) `code`",
            preferred_courts='["My_Court [East]"]',
        )
    )
    await session.commit()

    callback = _FakeCallback(user_id=111, data=f"players:open:{player.id}")
    await players_open_details(callback, session)

    text, _ = callback.message.sent[0]
    assert "\\*Bold\\* \\[link\\]\\(x\\) \\`code\\`" in text
    assert "My\\_Court \\[East\\]" in text


@pytest.mark.asyncio
async def test_browse_row_escapes_underscore_in_name(session: AsyncSession) -> None:
    """Browse Players interpolates first_name too — same bug class."""
    await _seed_and_login(session, 111)
    repo = PlayerRepository(session)
    await repo.add(Player(telegram_id=4002, first_name="Jane_Smith", home_area="Downtown"))
    await session.commit()

    callback = _FakeCallback(user_id=111)
    state = _make_state(111)
    await players_browse(callback, session, state)

    text, _ = callback.message.sent[0]
    assert "Jane\\_Smith" in text
    assert "Jane_Smith" not in text


# ---------------------------------------------------------------------------
# Navigation back to Dashboard
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_back_to_dashboard_ends_up_on_dashboard_and_clears_state(session: AsyncSession) -> None:
    await _seed_and_login(session, 111)
    callback = _FakeCallback(user_id=111)
    state = _make_state(111)
    await state.set_state(AdminPlayersStates.browsing)

    await players_back_to_dashboard(callback, session, state)

    assert await state.get_state() is None
    text, _ = callback.message.sent[0]
    assert "Admin Center" in text
