"""Tests for the Tournament Dashboard (Sprint 16, Step 1) — the
organizer/admin-only view rendered by show_tournament_details() when
can_manage is True. A Player must keep seeing the existing, unchanged
simplified Tournament Details screen (bot/presenters/tournament_details.py,
untouched by this sprint) — covered explicitly below, not assumed.

Presentation-only: no business logic under test here beyond what
already exists in TournamentService/GameService (start_match,
complete_match, generate_matches, get_standings — all pre-existing,
reused as-is to build realistic fixtures for the dashboard to render).
"""
from datetime import date, time
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.bot.handlers.admin.tournaments import tourn_open
from backend.app.bot.presenters.tournament_dashboard import (
    build_dashboard_header_text,
    build_empty_state_text,
    current_round,
    group_matches_by_round,
)
from backend.app.database.models.tournament import TournamentStatus
from backend.app.database.repositories.game_repository import GamePlayerRepository, GameRepository
from backend.app.schemas.player import PlayerCreate, PlayerUpdate
from backend.app.schemas.tournament import TournamentCreate
from backend.app.services.player_service import PlayerService
from backend.app.services.players_service import PlayersService
from backend.app.services.tournament_lifecycle_service import TournamentLifecycleService
from backend.app.services.tournament_service import TournamentService


class _FakeMessage:
    def __init__(self) -> None:
        self.sent: list[str] = []
        self.markups: list = []

    async def answer(self, text, reply_markup=None, parse_mode=None):
        self.sent.append(text)
        self.markups.append(reply_markup)
        return self


class _FakeCallback:
    def __init__(self, data: str, user_id: int) -> None:
        self.data = data
        self.from_user = SimpleNamespace(id=user_id)
        self.message = _FakeMessage()
        self.answer = AsyncMock()


class _FakeBot:
    async def send_message(self, *args, **kwargs) -> None:
        return None


async def _make_player(session: AsyncSession, telegram_id: int, name: str = "Player") -> int:
    svc = PlayerService(session)
    player, _ = await svc.get_or_create(PlayerCreate(telegram_id=telegram_id, first_name=name))
    await svc.update_profile(
        telegram_id,
        PlayerUpdate(language="en", skill_level=3.5, home_area="Downtown", preferred_courts=["High Park"]),
    )
    await session.commit()
    return player.id


async def _make_tournament(session: AsyncSession, organizer_telegram_id: int, max_players: int = 14) -> int:
    organizer_id = await _make_player(session, organizer_telegram_id, "Organizer")
    await PlayersService(session).set_verified_coach(organizer_id, True)
    await session.commit()
    tournament = await TournamentService(session).create_tournament(
        organizer_telegram_id,
        TournamentCreate(
            name="Dashboard Cup",
            area="Downtown",
            court="High Park",
            start_date=date(2026, 8, 1),
            start_time=time(10, 0),
            registration_deadline=date(2026, 7, 20),
            max_players=max_players,
        ),
    )
    await session.commit()
    return tournament.id


# ---------------------------------------------------------------------------
# Organizer sees the dashboard; a Player never does
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_organizer_receives_dashboard_with_multiple_messages(session: AsyncSession) -> None:
    organizer_telegram_id = 12001
    tournament_id = await _make_tournament(session, organizer_telegram_id)
    await TournamentLifecycleService(session).transition(tournament_id, TournamentStatus.REGISTRATION_OPEN)

    callback = _FakeCallback(data=f"tourn:open:{tournament_id}", user_id=organizer_telegram_id)
    await tourn_open(callback, session, _FakeBot())

    # Header + one empty-state message for a still-open registration.
    assert len(callback.message.sent) == 2
    assert "Dashboard Cup" in callback.message.sent[0]
    assert "Registration is open" in callback.message.sent[1]


@pytest.mark.asyncio
async def test_player_still_sees_simplified_single_message_view(session: AsyncSession) -> None:
    organizer_telegram_id = 12101
    tournament_id = await _make_tournament(session, organizer_telegram_id)
    await TournamentLifecycleService(session).transition(tournament_id, TournamentStatus.REGISTRATION_OPEN)
    await _make_player(session, 12102, "RegularPlayer")

    callback = _FakeCallback(data=f"tourn:open:{tournament_id}", user_id=12102)
    await tourn_open(callback, session, _FakeBot())

    assert len(callback.message.sent) == 1
    assert "Current Round" not in callback.message.sent[0]
    callbacks = {btn.callback_data for row in callback.message.markups[0].inline_keyboard for btn in row}
    assert f"tourn:edit:{tournament_id}" not in callbacks  # no management buttons for a Player


@pytest.mark.asyncio
async def test_organizer_first_message_keeps_existing_management_keyboard(session: AsyncSession) -> None:
    """The dashboard must not drop any existing, working management
    action — Edit/Delete/etc. stay exactly where they were."""
    organizer_telegram_id = 12201
    tournament_id = await _make_tournament(session, organizer_telegram_id)

    callback = _FakeCallback(data=f"tourn:open:{tournament_id}", user_id=organizer_telegram_id)
    await tourn_open(callback, session, _FakeBot())

    callbacks = {btn.callback_data for row in callback.message.markups[0].inline_keyboard for btn in row}
    assert f"tourn:edit:{tournament_id}" in callbacks
    assert f"tourn:delete:{tournament_id}" in callbacks


# ---------------------------------------------------------------------------
# Empty states — one per reason, per the task's explicit list
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_empty_state_draft(session: AsyncSession) -> None:
    organizer_telegram_id = 12301
    tournament_id = await _make_tournament(session, organizer_telegram_id)  # still DRAFT

    callback = _FakeCallback(data=f"tourn:open:{tournament_id}", user_id=organizer_telegram_id)
    await tourn_open(callback, session, _FakeBot())

    assert "Draft" in callback.message.sent[1]


@pytest.mark.asyncio
async def test_empty_state_awaiting_bracket_generation(session: AsyncSession) -> None:
    organizer_telegram_id = 12401
    tournament_id = await _make_tournament(session, organizer_telegram_id)
    lifecycle = TournamentLifecycleService(session)
    await lifecycle.transition(tournament_id, TournamentStatus.REGISTRATION_OPEN)
    await lifecycle.transition(tournament_id, TournamentStatus.REGISTRATION_CLOSED)

    callback = _FakeCallback(data=f"tourn:open:{tournament_id}", user_id=organizer_telegram_id)
    await tourn_open(callback, session, _FakeBot())

    assert "Generate Matches" in callback.message.sent[1]


@pytest.mark.asyncio
async def test_empty_state_cancelled(session: AsyncSession) -> None:
    organizer_telegram_id = 12501
    tournament_id = await _make_tournament(session, organizer_telegram_id)
    await TournamentLifecycleService(session).transition(tournament_id, TournamentStatus.CANCELLED)

    callback = _FakeCallback(data=f"tourn:open:{tournament_id}", user_id=organizer_telegram_id)
    await tourn_open(callback, session, _FakeBot())

    assert "cancelled" in callback.message.sent[1]


# ---------------------------------------------------------------------------
# Round-grouped match cards
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_dashboard_shows_round_grouped_match_cards_with_start_button(session: AsyncSession) -> None:
    organizer_telegram_id = 12601
    tournament_id = await _make_tournament(session, organizer_telegram_id)
    lifecycle = TournamentLifecycleService(session)
    await lifecycle.transition(tournament_id, TournamentStatus.REGISTRATION_OPEN)

    service = TournamentService(session)
    for i in range(4):
        tid = 12700 + i
        await _make_player(session, tid, f"Player{i}")
        await service.register_player(tournament_id, tid)

    await lifecycle.transition(tournament_id, TournamentStatus.REGISTRATION_CLOSED)
    success, error_key = await service.generate_matches(tournament_id)
    assert success is True, error_key

    callback = _FakeCallback(data=f"tourn:open:{tournament_id}", user_id=organizer_telegram_id)
    await tourn_open(callback, session, _FakeBot())

    # Header, "Round 1" label, 2 match cards.
    assert len(callback.message.sent) == 4
    assert "Round 1" in callback.message.sent[1]
    assert "vs" in callback.message.sent[2]
    assert "Scheduled" in callback.message.sent[2]
    start_buttons = {btn.callback_data for row in callback.message.markups[2].inline_keyboard for btn in row}
    assert any(cb.startswith("tourn:start_match:") for cb in start_buttons)


@pytest.mark.asyncio
async def test_dashboard_match_card_shows_in_progress_and_result_button(session: AsyncSession) -> None:
    organizer_telegram_id = 12801
    tournament_id = await _make_tournament(session, organizer_telegram_id)
    lifecycle = TournamentLifecycleService(session)
    await lifecycle.transition(tournament_id, TournamentStatus.REGISTRATION_OPEN)

    service = TournamentService(session)
    for i in range(2):
        tid = 12900 + i
        await _make_player(session, tid, f"Player{i}")
        await service.register_player(tournament_id, tid)
    await lifecycle.transition(tournament_id, TournamentStatus.REGISTRATION_CLOSED)
    await service.generate_matches(tournament_id)

    round_1 = await GameRepository(session).get_games_by_tournament_round(tournament_id, 1)
    await service.start_match(round_1[0].id, organizer_telegram_id)

    callback = _FakeCallback(data=f"tourn:open:{tournament_id}", user_id=organizer_telegram_id)
    await tourn_open(callback, session, _FakeBot())

    card_text = callback.message.sent[2]
    assert "In Progress" in card_text
    buttons = {btn.callback_data for row in callback.message.markups[2].inline_keyboard for btn in row}
    assert any(cb.startswith("tourn:enter_result:") for cb in buttons)


@pytest.mark.asyncio
async def test_dashboard_shows_champion_banner_and_winner_on_completed_tournament(session: AsyncSession) -> None:
    organizer_telegram_id = 13001
    tournament_id = await _make_tournament(session, organizer_telegram_id)
    lifecycle = TournamentLifecycleService(session)
    await lifecycle.transition(tournament_id, TournamentStatus.REGISTRATION_OPEN)

    service = TournamentService(session)
    for i in range(2):
        tid = 13100 + i
        await _make_player(session, tid, f"Player{i}")
        await service.register_player(tournament_id, tid)
    await lifecycle.transition(tournament_id, TournamentStatus.REGISTRATION_CLOSED)
    await service.generate_matches(tournament_id)

    game_repo = GameRepository(session)
    gp_repo = GamePlayerRepository(session)
    round_1 = await game_repo.get_games_by_tournament_round(tournament_id, 1)
    game = round_1[0]
    participants = await gp_repo.get_participant_player_ids(game.id)
    await service.start_match(game.id, organizer_telegram_id)
    await service.complete_match(game.id, participants[0], organizer_telegram_id)

    tournament = await service.get_tournament(tournament_id)
    assert tournament.status == TournamentStatus.COMPLETED  # 2-player bracket: one match is the whole tournament

    callback = _FakeCallback(data=f"tourn:open:{tournament_id}", user_id=organizer_telegram_id)
    await tourn_open(callback, session, _FakeBot())

    assert "Champion" in callback.message.sent[1]
    assert "Winner" in callback.message.sent[3]
    assert "Completed" in callback.message.sent[3]


# ---------------------------------------------------------------------------
# Pure presenter unit tests — no database, per established convention
# ---------------------------------------------------------------------------


def test_group_matches_by_round_pure() -> None:
    from datetime import datetime

    from backend.app.database.models.game import GameStatus, MatchType
    from backend.app.schemas.game import GameRead, MatchDetails

    def _match(game_id: int, round_: int, status: GameStatus) -> MatchDetails:
        return MatchDetails(
            game=GameRead(
                id=game_id, creator_id=1, tournament_id=1, court="Court", area="Downtown",
                date=date(2026, 8, 1), time=time(10, 0), match_type=MatchType.SINGLES,
                required_level=None, status=status, round=round_, winner_player_id=None,
                created_at=datetime(2026, 1, 1), required_players=2,
            ),
            organizer_name="—", players=[], committed_count=2,
        )

    matches = [_match(1, 1, GameStatus.COMPLETED), _match(2, 1, GameStatus.OPEN), _match(3, 2, GameStatus.OPEN)]
    grouped = group_matches_by_round(matches)
    assert set(grouped.keys()) == {1, 2}
    assert [m.game.id for m in grouped[1]] == [1, 2]

    assert current_round(matches) == 1  # round 1 still has an OPEN match


def test_build_empty_state_text_distinguishes_each_reason() -> None:
    texts = {
        status: build_empty_state_text("en", status)
        for status in (
            TournamentStatus.DRAFT,
            TournamentStatus.REGISTRATION_OPEN,
            TournamentStatus.REGISTRATION_CLOSED,
            TournamentStatus.CANCELLED,
        )
    }
    assert len(set(texts.values())) == 4  # every reason gets distinct wording


def test_build_dashboard_header_text_includes_round_only_when_present() -> None:
    from datetime import datetime as datetime_

    from backend.app.schemas.tournament import TournamentRead

    tournament = TournamentRead(
        id=1, name="Header Cup", description=None, organizer_player_id=1,
        area="Downtown", court="High Park", start_date=date(2026, 8, 1), start_time=time(10, 0),
        registration_deadline=date(2026, 7, 20), max_players=8,
        status=TournamentStatus.IN_PROGRESS, created_at=datetime_(2026, 1, 1),
    )

    with_round = build_dashboard_header_text("en", tournament, registered_count=8, round_now=2)
    without_round = build_dashboard_header_text("en", tournament, registered_count=8, round_now=None)

    assert "Current Round: 2" in with_round
    assert "Current Round" not in without_round
