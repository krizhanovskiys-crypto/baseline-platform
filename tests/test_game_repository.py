"""Tests for GameRepository."""
import pytest
from datetime import date, time

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database.models.game import Game, GameStatus, MatchType
from backend.app.database.models.player import Player
from backend.app.database.repositories.game_repository import GamePlayerRepository, GameRepository
from backend.app.database.repositories.player_repository import PlayerRepository


async def _create_player(session: AsyncSession, tid: int, name: str) -> Player:
    repo = PlayerRepository(session)
    p = Player(telegram_id=tid, first_name=name)
    await repo.add(p)
    await session.commit()
    return p


@pytest.mark.asyncio
async def test_create_and_get_game(session: AsyncSession) -> None:
    player = await _create_player(session, 100, "Alice")
    repo = GameRepository(session)

    game = Game(
        creator_id=player.id,
        court="Ramsden Park",
        area="Downtown",
        date=date(2025, 8, 1),
        time=time(10, 0),
        match_type=MatchType.SINGLES,
    )
    await repo.add(game)
    await session.commit()

    fetched = await repo.get_by_id(game.id)
    assert fetched is not None
    assert fetched.court == "Ramsden Park"
    assert fetched.status == GameStatus.OPEN


@pytest.mark.asyncio
async def test_get_open_games_filtered_by_area(session: AsyncSession) -> None:
    player = await _create_player(session, 200, "Bob")
    repo = GameRepository(session)

    g1 = Game(creator_id=player.id, court="A", area="Downtown", date=date(2025, 8, 1), time=time(9, 0), match_type=MatchType.SINGLES)
    g2 = Game(creator_id=player.id, court="B", area="North York", date=date(2025, 8, 2), time=time(9, 0), match_type=MatchType.SINGLES)
    for g in [g1, g2]:
        await repo.add(g)
    await session.commit()

    downtown = await repo.get_open_games(area="Downtown")
    assert len(downtown) == 1
    assert downtown[0].area == "Downtown"

    all_games = await repo.get_open_games()
    assert len(all_games) == 2


@pytest.mark.asyncio
async def test_game_player_participation(session: AsyncSession) -> None:
    player = await _create_player(session, 300, "Carol")
    game_repo = GameRepository(session)
    gp_repo = GamePlayerRepository(session)

    game = Game(creator_id=player.id, court="X", area="Etobicoke", date=date(2025, 9, 1), time=time(14, 0), match_type=MatchType.DOUBLES)
    await game_repo.add(game)
    await session.commit()

    gp = await gp_repo.add_player_to_game(game.id, player.id)
    await session.commit()

    fetched = await gp_repo.get_participation(game.id, player.id)
    assert fetched is not None
    assert fetched.player_id == player.id


@pytest.mark.asyncio
async def test_game_round_and_winner_player_id_default_to_none(session: AsyncSession) -> None:
    player = await _create_player(session, 400, "Dave")
    repo = GameRepository(session)

    game = Game(
        creator_id=player.id,
        court="Y",
        area="Downtown",
        date=date(2025, 9, 5),
        time=time(11, 0),
        match_type=MatchType.SINGLES,
    )
    await repo.add(game)
    await session.commit()

    fetched = await repo.get_by_id(game.id)
    assert fetched is not None
    assert fetched.round is None
    assert fetched.winner_player_id is None


@pytest.mark.asyncio
async def test_game_round_and_winner_player_id_persist(session: AsyncSession) -> None:
    organizer = await _create_player(session, 401, "Eve")
    winner = await _create_player(session, 402, "Frank")
    repo = GameRepository(session)

    game = Game(
        creator_id=organizer.id,
        court="Z",
        area="Downtown",
        date=date(2025, 9, 6),
        time=time(12, 0),
        match_type=MatchType.SINGLES,
        round=1,
    )
    await repo.add(game)
    await session.commit()

    game.winner_player_id = winner.id
    game.status = GameStatus.COMPLETED
    await session.commit()

    fetched = await repo.get_by_id(game.id)
    assert fetched is not None
    assert fetched.round == 1
    assert fetched.winner_player_id == winner.id
    assert fetched.status == GameStatus.COMPLETED
