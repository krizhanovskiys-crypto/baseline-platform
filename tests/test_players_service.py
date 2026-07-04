"""Tests for PlayersService — Admin Center's Players module business logic."""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database.models.player import Player
from backend.app.database.repositories.player_repository import PlayerRepository
from backend.app.services.players_service import PAGE_SIZE, PlayersService


async def _seed(session: AsyncSession, count: int) -> None:
    repo = PlayerRepository(session)
    for i in range(count):
        await repo.add(
            Player(
                telegram_id=1000 + i,
                first_name=f"Player{i}",
                username=f"player{i}",
                home_area="Downtown",
                skill_level=3.0 + i * 0.1,
            )
        )
    await session.commit()


@pytest.mark.asyncio
async def test_count_all(session: AsyncSession) -> None:
    await _seed(session, 3)
    assert await PlayersService(session).count_all() == 3


@pytest.mark.asyncio
async def test_get_page_returns_players_and_total(session: AsyncSession) -> None:
    await _seed(session, 25)
    svc = PlayersService(session)

    page_1, total = await svc.get_page(1)
    page_2, total_again = await svc.get_page(2)

    assert total == 25 == total_again
    assert len(page_1) == PAGE_SIZE
    assert len(page_2) == 5
    assert page_1[0].first_name == "Player0"
    assert page_2[0].first_name == "Player20"


@pytest.mark.asyncio
async def test_get_by_id_returns_full_schema(session: AsyncSession) -> None:
    await _seed(session, 1)
    svc = PlayersService(session)
    page, _ = await svc.get_page(1)
    player_id = page[0].id

    fetched = await svc.get_by_id(player_id)
    assert fetched is not None
    assert fetched.first_name == "Player0"


@pytest.mark.asyncio
async def test_get_by_id_returns_none_for_unknown_id(session: AsyncSession) -> None:
    svc = PlayersService(session)
    assert await svc.get_by_id(999) is None


# ---------------------------------------------------------------------------
# search()
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_search_by_telegram_id_is_an_exact_match(session: AsyncSession) -> None:
    await _seed(session, 3)
    svc = PlayersService(session)

    results = await svc.search("1001")
    assert len(results) == 1
    assert results[0].telegram_id == 1001


@pytest.mark.asyncio
async def test_search_by_telegram_id_not_found_returns_empty(session: AsyncSession) -> None:
    svc = PlayersService(session)
    assert await svc.search("9999999") == []


@pytest.mark.asyncio
async def test_search_by_name_returns_multiple_matches(session: AsyncSession) -> None:
    await _seed(session, 15)  # Player0..Player14 — "Player1" substring matches Player1, 10-14
    svc = PlayersService(session)

    results = await svc.search("Player1")
    names = {p.first_name for p in results}
    assert "Player1" in names
    assert "Player10" in names
    assert "Player0" not in names


@pytest.mark.asyncio
async def test_search_strips_leading_at_from_username(session: AsyncSession) -> None:
    await _seed(session, 3)
    svc = PlayersService(session)

    results = await svc.search("@player1")
    assert len(results) == 1
    assert results[0].username == "player1"


@pytest.mark.asyncio
async def test_search_no_match_returns_empty(session: AsyncSession) -> None:
    await _seed(session, 3)
    svc = PlayersService(session)
    assert await svc.search("nobody") == []


@pytest.mark.asyncio
async def test_search_blank_query_returns_empty(session: AsyncSession) -> None:
    svc = PlayersService(session)
    assert await svc.search("   ") == []
