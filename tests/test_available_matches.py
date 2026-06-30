"""Tests for Sprint 7.0 — Available Matches (repository, service, race condition)."""
from datetime import date, time, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from aiogram.fsm.storage.memory import MemoryStorage

from backend.app.bot.handlers.available_matches import (
    _render_available_matches,
    available_confirm_callback,
    available_filter_set_callback,
    available_filters_back_callback,
    available_filters_callback,
    available_filters_open_category_callback,
)
from backend.app.bot.states.states import AvailableMatchesStates
from backend.app.bot.texts import t
from backend.app.database.models.game import Game, GamePlayer, GamePlayerStatus, GameStatus, MatchType
from backend.app.database.models.player import Player
from backend.app.database.repositories.game_repository import GamePlayerRepository, GameRepository
from backend.app.database.repositories.player_repository import PlayerRepository
from backend.app.schemas.game import GameCreate
from backend.app.schemas.player import PlayerCreate, PlayerUpdate
from backend.app.services.game_service import GameService
from backend.app.services.invitation_service import InvitationService
from backend.app.services.match_lifecycle_service import MatchLifecycleService
from backend.app.services.player_service import PlayerService

_FUTURE = date(2026, 12, 1)
_LATER = date(2026, 12, 2)


def _make_state(user_id: int) -> FSMContext:
    return FSMContext(storage=MemoryStorage(), key=StorageKey(bot_id=1, chat_id=user_id, user_id=user_id))


class _FakeMessage:
    """Minimal stand-in for aiogram's Message — records every .answer() call."""

    def __init__(self) -> None:
        self.sent: list[tuple[str, object]] = []

    async def answer(self, text, reply_markup=None, parse_mode=None):
        self.sent.append((text, reply_markup))
        return self


class _FakeCallback:
    """Minimal stand-in for aiogram's CallbackQuery — enough for handler functions
    that only touch .data, .message, .from_user.id, .answer(), .bot.send_message()."""

    def __init__(self, data: str, user_id: int) -> None:
        self.data = data
        self.from_user = SimpleNamespace(id=user_id)
        self.message = AsyncMock()
        self.message.edit_text = AsyncMock()
        self.bot = AsyncMock()
        self.bot.send_message = AsyncMock()
        self.answer = AsyncMock()


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _make_player(
    session, telegram_id: int, first_name: str = "Player", area: str = "Downtown", level: float = 3.0
) -> int:
    svc = PlayerService(session)
    player, _ = await svc.get_or_create(PlayerCreate(telegram_id=telegram_id, first_name=first_name))
    await svc.update_profile(
        telegram_id,
        PlayerUpdate(language="en", skill_level=level, home_area=area, preferred_courts=["High Park"]),
    )
    return player.id


async def _make_open_game(
    session,
    organizer_tid: int,
    *,
    match_type: MatchType = MatchType.SINGLES,
    area: str = "Downtown",
    match_date: date = _FUTURE,
    required_level: float | None = 3.0,
) -> int:
    game = await GameService(session).create_game(
        creator_telegram_id=organizer_tid,
        data=GameCreate(
            court="High Park Court 3",
            area=area,
            date=match_date,
            time=time(18, 0),
            match_type=match_type,
            required_level=required_level,
        ),
    )
    assert game is not None
    await MatchLifecycleService(session).transition(game.id, GameStatus.OPEN)
    return game.id


async def _accept_invitation(session, game_id: int, invitee_tid: int) -> None:
    invitee = await PlayerService(session).get_by_telegram_id(invitee_tid)
    assert invitee is not None
    inv = await InvitationService(session).create_invitation(game_id, invitee.id)
    assert inv is not None
    await InvitationService(session).accept(inv.id, invitee_tid)


async def _raw_player(session, tid: int, area: str = "Downtown", level: float = 3.0) -> Player:
    repo = PlayerRepository(session)
    p = Player(telegram_id=tid, first_name=f"P{tid}", language="en", home_area=area, skill_level=level)
    await repo.add(p)
    return p


async def _raw_game(session, creator_id: int, **kwargs) -> Game:
    defaults = dict(
        creator_id=creator_id,
        court="Court",
        area="Downtown",
        date=_FUTURE,
        time=time(9, 0),
        match_type=MatchType.SINGLES,
        required_level=3.0,
    )
    defaults.update(kwargs)
    game = Game(**defaults)
    repo = GameRepository(session)
    await repo.add(game)
    return game


# ── Repository: GameRepository.get_available_matches ───────────────────────────

async def test_repo_excludes_non_joinable_statuses(session):
    organizer = await _raw_player(session, 100001)
    viewer = await _raw_player(session, 100002)

    statuses = [
        GameStatus.DRAFT,
        GameStatus.OPEN,
        GameStatus.PARTIALLY_FILLED,
        GameStatus.FULL,
        GameStatus.CONFIRMED,
        GameStatus.IN_PROGRESS,
        GameStatus.COMPLETED,
        GameStatus.CANCELLED,
        GameStatus.EXPIRED,
    ]
    for i, status in enumerate(statuses):
        await _raw_game(session, organizer.id, court=f"Court{i}", status=status)
    await session.commit()

    repo = GameRepository(session)
    games, total = await repo.get_available_matches(viewer.id, viewer.home_area, viewer.skill_level)

    assert total == 2
    assert {g.status for g in games} == {GameStatus.OPEN, GameStatus.PARTIALLY_FILLED}


async def test_repo_excludes_organizer_own_games(session):
    organizer = await _raw_player(session, 100101)
    await _raw_game(session, organizer.id)
    await session.commit()

    repo = GameRepository(session)
    games, total = await repo.get_available_matches(organizer.id, organizer.home_area, organizer.skill_level)
    assert total == 0
    assert games == []


async def test_repo_excludes_already_accepted_but_not_invited(session):
    organizer = await _raw_player(session, 100201)
    viewer = await _raw_player(session, 100202)
    game = await _raw_game(session, organizer.id)
    await session.commit()

    gp_repo = GamePlayerRepository(session)
    await gp_repo.add_player_to_game(game.id, viewer.id, GamePlayerStatus.ACCEPTED)
    await session.commit()

    repo = GameRepository(session)
    games, total = await repo.get_available_matches(viewer.id, viewer.home_area, viewer.skill_level)
    assert total == 0

    # An INVITED (not yet accepted) row should NOT exclude the game.
    gp = await gp_repo.get_participation(game.id, viewer.id)
    gp.status = GamePlayerStatus.INVITED
    await session.flush()

    games, total = await repo.get_available_matches(viewer.id, viewer.home_area, viewer.skill_level)
    assert total == 1


async def test_repo_area_filter(session):
    organizer = await _raw_player(session, 100301)
    viewer = await _raw_player(session, 100302)
    await _raw_game(session, organizer.id, court="A", area="Downtown")
    await _raw_game(session, organizer.id, court="B", area="North York")
    await session.commit()

    repo = GameRepository(session)
    games, total = await repo.get_available_matches(
        viewer.id, viewer.home_area, viewer.skill_level, area="North York"
    )
    assert total == 1
    assert games[0].area == "North York"


async def test_repo_date_filter(session):
    organizer = await _raw_player(session, 100401)
    viewer = await _raw_player(session, 100402)
    await _raw_game(session, organizer.id, court="A", date=_FUTURE)
    await _raw_game(session, organizer.id, court="B", date=_LATER)
    await session.commit()

    repo = GameRepository(session)
    games, total = await repo.get_available_matches(
        viewer.id, viewer.home_area, viewer.skill_level, on_date=_LATER
    )
    assert total == 1
    assert games[0].date == _LATER


async def test_repo_match_type_filter(session):
    organizer = await _raw_player(session, 100501)
    viewer = await _raw_player(session, 100502)
    await _raw_game(session, organizer.id, court="A", match_type=MatchType.SINGLES)
    await _raw_game(session, organizer.id, court="B", match_type=MatchType.DOUBLES)
    await session.commit()

    repo = GameRepository(session)
    games, total = await repo.get_available_matches(
        viewer.id, viewer.home_area, viewer.skill_level, match_type=MatchType.DOUBLES
    )
    assert total == 1
    assert games[0].match_type == MatchType.DOUBLES


async def test_repo_level_filter(session):
    organizer = await _raw_player(session, 100601)
    viewer = await _raw_player(session, 100602, level=3.0)
    await _raw_game(session, organizer.id, court="A", required_level=3.0)   # within ±0.5
    await _raw_game(session, organizer.id, court="B", required_level=4.5)   # outside ±0.5
    await session.commit()

    repo = GameRepository(session)
    games, total = await repo.get_available_matches(
        viewer.id, viewer.home_area, viewer.skill_level, level=viewer.skill_level, level_tolerance=0.5
    )
    assert total == 1
    assert games[0].required_level == 3.0


async def test_repo_sorting_same_area_and_today_first(session):
    organizer = await _raw_player(session, 100701)
    viewer = await _raw_player(session, 100702, area="Downtown")
    today = date.today() + timedelta(days=10)  # any fixed weekday far enough to avoid expiry
    far = today + timedelta(days=5)

    await _raw_game(session, organizer.id, court="Far-OtherArea", area="North York", date=far)
    await _raw_game(session, organizer.id, court="Near-SameArea", area="Downtown", date=far)
    await _raw_game(session, organizer.id, court="Today-OtherArea", area="North York", date=today)
    await session.commit()

    repo = GameRepository(session)
    games, total = await repo.get_available_matches(viewer.id, viewer.home_area, viewer.skill_level)
    assert total == 3
    # Same-area match floats to the top regardless of date.
    assert games[0].court == "Near-SameArea"


async def test_repo_pagination(session):
    organizer = await _raw_player(session, 100801)
    viewer = await _raw_player(session, 100802)
    for i in range(7):
        await _raw_game(session, organizer.id, court=f"Court{i}", time=time(9 + i, 0))
    await session.commit()

    repo = GameRepository(session)
    page1, total = await repo.get_available_matches(
        viewer.id, viewer.home_area, viewer.skill_level, page=1, page_size=5
    )
    page2, _ = await repo.get_available_matches(
        viewer.id, viewer.home_area, viewer.skill_level, page=2, page_size=5
    )
    assert total == 7
    assert len(page1) == 5
    assert len(page2) == 2
    assert {g.id for g in page1}.isdisjoint({g.id for g in page2})


# ── Service: GameService.get_available_matches ──────────────────────────────────

async def test_service_get_available_matches_pass_through(session):
    await _make_player(session, 200001, "Organizer")
    await _make_player(session, 200002, "Viewer")
    await _make_open_game(session, 200001)
    await session.commit()

    matches, total = await GameService(session).get_available_matches(200002)
    assert total == 1
    assert len(matches) == 1
    game, committed_count = matches[0]
    assert committed_count == 1  # organizer auto-joins as CONFIRMED


async def test_service_get_available_matches_unknown_player(session):
    matches, total = await GameService(session).get_available_matches(999999)
    assert matches == []
    assert total == 0


# ── Service: GameService.join_match — error cases ───────────────────────────────

async def test_join_match_not_found(session):
    await _make_player(session, 300001)
    _, err = await GameService(session).join_match(99999, 300001)
    assert err == "match_not_found"


async def test_join_match_organizer_cannot_join_own_match(session):
    await _make_player(session, 300101, "Organizer")
    game_id = await _make_open_game(session, 300101)

    _, err = await GameService(session).join_match(game_id, 300101)
    assert err == "join_match_organizer"


async def test_join_match_already_joined(session):
    await _make_player(session, 300201, "Organizer")
    await _make_player(session, 300202, "Participant")
    game_id = await _make_open_game(session, 300201, match_type=MatchType.DOUBLES)
    await _accept_invitation(session, game_id, 300202)

    _, err = await GameService(session).join_match(game_id, 300202)
    assert err == "join_match_already_joined"


@pytest.mark.parametrize(
    "target_status",
    [GameStatus.FULL, GameStatus.CONFIRMED, GameStatus.CANCELLED, GameStatus.EXPIRED],
)
async def test_join_match_forbidden_statuses(session, target_status):
    organizer_tid = 300301 + hash(target_status.value) % 1000
    await _make_player(session, organizer_tid, "Organizer")
    game_id = await _make_open_game(session, organizer_tid, match_type=MatchType.DOUBLES)

    lifecycle = MatchLifecycleService(session)
    if target_status in (GameStatus.FULL, GameStatus.CONFIRMED):
        await lifecycle.transition(game_id, GameStatus.PARTIALLY_FILLED)
        await lifecycle.transition(game_id, GameStatus.FULL)
        if target_status == GameStatus.CONFIRMED:
            await lifecycle.transition(game_id, GameStatus.CONFIRMED)
    else:
        await lifecycle.transition(game_id, target_status)

    await _make_player(session, 300999, "Joiner")
    _, err = await GameService(session).join_match(game_id, 300999)
    assert err == "join_match_not_allowed"


async def test_join_match_draft_not_allowed(session):
    await _make_player(session, 300401, "Organizer")
    draft_game = await GameService(session).create_game(
        creator_telegram_id=300401,
        data=GameCreate(court="X", area="Downtown", date=_FUTURE, time=time(9, 0)),
    )
    await session.commit()
    assert draft_game.status == GameStatus.DRAFT

    await _make_player(session, 300402, "Joiner")
    _, err = await GameService(session).join_match(draft_game.id, 300402)
    assert err == "join_match_not_allowed"


# ── Service: GameService.join_match — success + lifecycle ──────────────────────

async def test_join_match_open_to_partially_filled(session):
    await _make_player(session, 400001, "Organizer")
    await _make_player(session, 400002, "Joiner")
    game_id = await _make_open_game(session, 400001, match_type=MatchType.DOUBLES)

    updated, err = await GameService(session).join_match(game_id, 400002)
    assert err == ""
    assert updated is not None
    assert updated.status == GameStatus.PARTIALLY_FILLED

    gp_repo = GamePlayerRepository(session)
    assert await gp_repo.count_committed_players(game_id) == 2


async def test_join_match_fills_singles_to_full(session):
    await _make_player(session, 400101, "Organizer")
    await _make_player(session, 400102, "Joiner")
    game_id = await _make_open_game(session, 400101, match_type=MatchType.SINGLES)

    updated, err = await GameService(session).join_match(game_id, 400102)
    assert err == ""
    assert updated.status == GameStatus.FULL


async def test_join_match_reactivates_invited_row(session):
    """A player with a pending INVITED row can still join directly; no duplicate row, no crash."""
    await _make_player(session, 400201, "Organizer")
    await _make_player(session, 400202, "Invitee")
    game_id = await _make_open_game(session, 400201, match_type=MatchType.DOUBLES)

    invitee = await PlayerService(session).get_by_telegram_id(400202)
    assert await GameService(session).invite_player(game_id, 400202)
    await session.commit()

    gp_repo = GamePlayerRepository(session)
    gp = await gp_repo.get_participation(game_id, invitee.id)
    assert gp.status == GamePlayerStatus.INVITED

    updated, err = await GameService(session).join_match(game_id, 400202)
    assert err == ""
    assert updated.status == GameStatus.PARTIALLY_FILLED
    gp = await gp_repo.get_participation(game_id, invitee.id)
    assert gp.status == GamePlayerStatus.ACCEPTED
    assert await gp_repo.count_committed_players(game_id) == 2


# ── Race condition: last slot taken by two joins ────────────────────────────────

async def test_join_match_race_for_last_slot(session):
    """Two requests race for the last slot of a singles match (organizer + 1 open
    spot). A real concurrent interleaving can't be expressed with one sequential
    asyncio session/connection (the first call always fully completes, including
    its lifecycle transition, before the second begins) — so Racer A's write is
    simulated directly, as it would land mid-flight in a real race: its
    GamePlayer row is inserted but the lifecycle has not yet advanced past OPEN.
    Racer B's join_match then runs as the "losing" concurrent request: it still
    sees status=OPEN, proceeds to insert, and must detect the overfill via
    count_committed_players on its own re-check and roll back."""
    await _make_player(session, 500001, "Organizer")
    await _make_player(session, 500002, "Racer A")
    await _make_player(session, 500003, "Racer B")
    game_id = await _make_open_game(session, 500001, match_type=MatchType.SINGLES)

    racer_a = await PlayerService(session).get_by_telegram_id(500002)
    gp_repo = GamePlayerRepository(session)
    await gp_repo.add_player_to_game(game_id, racer_a.id, GamePlayerStatus.ACCEPTED)
    await session.flush()  # visible to the next query, lifecycle not yet advanced

    updated_b, err_b = await GameService(session).join_match(game_id, 500003)

    assert err_b == "match_already_full"
    assert updated_b is None
    assert await gp_repo.count_committed_players(game_id) == 2  # organizer + Racer A only

    racer_b = await PlayerService(session).get_by_telegram_id(500003)
    assert await gp_repo.get_participation(game_id, racer_b.id) is None  # rolled back, not stuck


# ── Integration: browse then join end-to-end ────────────────────────────────────

async def test_browse_then_join_end_to_end(session):
    await _make_player(session, 600001, "Organizer")
    await _make_player(session, 600002, "Joiner")
    game_id = await _make_open_game(session, 600001, match_type=MatchType.DOUBLES)
    await session.commit()

    matches, total = await GameService(session).get_available_matches(600002)
    assert total == 1
    assert matches[0][0].id == game_id

    updated, err = await GameService(session).join_match(game_id, 600002)
    assert err == ""
    assert updated.status == GameStatus.PARTIALLY_FILLED

    # The joined match no longer appears in the joiner's Available Matches.
    matches_after, total_after = await GameService(session).get_available_matches(600002)
    assert total_after == 0


# ── Regression: FSM cleanup after successful join ───────────────────────────────

async def test_join_confirm_clears_fsm_state_on_success(session):
    await _make_player(session, 700001, "Organizer")
    await _make_player(session, 700002, "Joiner")
    game_id = await _make_open_game(session, 700001, match_type=MatchType.DOUBLES)
    await session.commit()

    state = _make_state(700002)
    await state.set_state(AvailableMatchesStates.browsing)
    await state.update_data(filters={"area": "any"}, current_page=2)

    callback = _FakeCallback(data=f"available:confirm:{game_id}", user_id=700002)
    await available_confirm_callback(callback, state, session)

    assert await state.get_state() is None
    assert await state.get_data() == {}
    callback.answer.assert_awaited_once()


async def test_join_confirm_does_not_clear_fsm_state_on_failure(session):
    """A failed join (e.g. match_already_full) should not wipe the player's
    browsing context — they may still want to keep paginating/filtering."""
    await _make_player(session, 700101, "Organizer")
    await _make_player(session, 700102, "Joiner")
    game_id = await _make_open_game(session, 700101, match_type=MatchType.SINGLES)
    await MatchLifecycleService(session).transition(game_id, GameStatus.CANCELLED)
    await session.commit()

    state = _make_state(700102)
    await state.set_state(AvailableMatchesStates.browsing)
    await state.update_data(filters={"area": "any"}, current_page=2)

    callback = _FakeCallback(data=f"available:confirm:{game_id}", user_id=700102)
    await available_confirm_callback(callback, state, session)

    assert await state.get_state() == AvailableMatchesStates.browsing.state
    assert (await state.get_data())["current_page"] == 2


# ── Regression: pagination self-heals when a page becomes invalid ──────────────

async def test_render_clamps_page_beyond_last_page(session):
    """Requesting a page number past the last valid page lands on the last page
    instead of rendering empty with no way back."""
    await _make_player(session, 700201, "Organizer")
    await _make_player(session, 700202, "Viewer")
    for i in range(3):  # 3 matches, page_size=5 -> last_page == 1
        await _make_open_game(session, 700201, area="Downtown", match_date=_FUTURE)
    await session.commit()

    state = _make_state(700202)
    await state.update_data(filters={"area": "any", "date": "any", "match_type": None, "level": "any"})
    message = _FakeMessage()
    await _render_available_matches(message, session, state, 700202, "en", page=3)

    assert (await state.get_data())["current_page"] == 1
    texts = [text for text, _ in message.sent]
    assert any("3 matches found" in text or "3" in text for text in texts[:1])
    assert any(text == t("available_matches_page_indicator", "en", page=1, total_pages=1) for text in texts)
    # The clamped page actually rendered real cards, not the empty state.
    assert not any(text == t("available_matches_empty", "en") for text in texts)


async def test_render_clamps_to_page_one_when_current_page_becomes_empty(session):
    """Simulates the player having joined every match on the last page: a
    previously valid page (2) now has zero results, but the overall list
    isn't empty — they should land on page 1, not a dead end."""
    await _make_player(session, 700301, "Organizer")
    await _make_player(session, 700302, "Viewer")
    await _make_open_game(session, 700301, area="Downtown", match_date=_FUTURE)  # only 1 match left
    await session.commit()

    state = _make_state(700302)
    await state.update_data(
        filters={"area": "any", "date": "any", "match_type": None, "level": "any"}, current_page=2
    )
    message = _FakeMessage()

    # Player's stale nav button still says "page 2" even though only 1 match remains.
    await _render_available_matches(message, session, state, 700302, "en", page=2)

    assert (await state.get_data())["current_page"] == 1
    texts = [text for text, _ in message.sent]
    assert not any(text == t("available_matches_empty", "en") for text in texts)
    assert any(text == t("available_matches_page_indicator", "en", page=1, total_pages=1) for text in texts)


async def test_render_shows_empty_state_when_truly_zero_matches(session):
    """When there are genuinely zero matches, clamping lands on page 1 and the
    empty-state message is shown (no nav keyboard claiming a page exists)."""
    await _make_player(session, 700401, "Viewer")
    state = _make_state(700401)
    message = _FakeMessage()

    await _render_available_matches(message, session, state, 700401, "en", page=5)

    assert (await state.get_data())["current_page"] == 1
    texts = [text for text, _ in message.sent]
    assert any(text == t("available_matches_empty", "en") for text in texts)


# ── Regression: two-level Filters UX (main screen + per-category screens) ──────

def _buttons(markup) -> list[tuple[str, str]]:
    return [(b.text, b.callback_data) for row in markup.inline_keyboard for b in row]


async def test_filters_main_screen_shows_categories_with_current_values(session):
    await _make_player(session, 800001, "Viewer", area="Downtown", level=3.0)
    state = _make_state(800001)

    callback = _FakeCallback(data="available:filters", user_id=800001)
    await available_filters_callback(callback, state, session)

    callback.answer.assert_awaited_once()
    callback.message.answer.assert_awaited_once()
    _, kwargs = callback.message.answer.call_args
    buttons = _buttons(kwargs["reply_markup"])
    texts = dict(buttons)
    assert any("Downtown" in label and cb == "available:filters:open:area" for label, cb in buttons)
    assert any("±0.5" in label and cb == "available:filters:open:level" for label, cb in buttons)
    assert any("Today" in label and cb == "available:filters:open:date" for label, cb in buttons)
    assert any("Any" in label and cb == "available:filters:open:type" for label, cb in buttons)
    assert "available:filters:apply" in texts.values()
    assert "menu:main" in texts.values()  # "🏠 Menu" — project's standard return-to-main-menu pattern


async def test_filters_open_category_shows_single_column_with_selection_marked(session):
    await _make_player(session, 800101, "Viewer", area="Downtown")
    state = _make_state(800101)

    callback = _FakeCallback(data="available:filters:open:area", user_id=800101)
    await available_filters_open_category_callback(callback, state, session)

    callback.answer.assert_awaited_once()
    args, kwargs = callback.message.edit_text.call_args
    assert args[0] == t("available_matches_choose_area", "en")
    buttons = _buttons(kwargs["reply_markup"])
    assert ("✅ Downtown", "available:filter:area:Downtown") in buttons
    assert ("North York", "available:filter:area:North York") in buttons
    assert (t("available_matches_btn_back_to_filters", "en"), "available:filters:back") in buttons


async def test_filter_set_saves_value_and_returns_to_main_screen(session):
    await _make_player(session, 800201, "Viewer", area="Downtown")
    state = _make_state(800201)

    callback = _FakeCallback(data="available:filter:area:North York", user_id=800201)
    await available_filter_set_callback(callback, state, session)

    callback.answer.assert_awaited_once()
    assert (await state.get_data())["filters"]["area"] == "North York"

    args, kwargs = callback.message.edit_text.call_args
    assert args[0] == t("available_matches_filters_header", "en")
    buttons = _buttons(kwargs["reply_markup"])
    assert any("North York" in label and cb == "available:filters:open:area" for label, cb in buttons)


async def test_filters_back_returns_to_main_screen_without_changing_value(session):
    await _make_player(session, 800301, "Viewer", area="Downtown")
    state = _make_state(800301)
    await state.update_data(filters={"area": "any", "date": "today", "match_type": None, "level": "default"})

    callback = _FakeCallback(data="available:filters:back", user_id=800301)
    await available_filters_back_callback(callback, state, session)

    callback.answer.assert_awaited_once()
    assert (await state.get_data())["filters"]["area"] == "any"  # unchanged

    args, kwargs = callback.message.edit_text.call_args
    assert args[0] == t("available_matches_filters_header", "en")
    buttons = _buttons(kwargs["reply_markup"])
    assert any("Any" in label and cb == "available:filters:open:area" for label, cb in buttons)
