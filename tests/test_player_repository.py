"""Tests for PlayerRepository."""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database.models.player import Player
from backend.app.database.repositories.player_repository import PlayerRepository


@pytest.mark.asyncio
async def test_add_and_get_by_telegram_id(session: AsyncSession) -> None:
    repo = PlayerRepository(session)
    player = Player(telegram_id=111, first_name="Alice")
    await repo.add(player)
    await session.commit()

    result = await repo.get_by_telegram_id(111)
    assert result is not None
    assert result.first_name == "Alice"
    assert result.telegram_id == 111


@pytest.mark.asyncio
async def test_get_by_telegram_id_not_found(session: AsyncSession) -> None:
    repo = PlayerRepository(session)
    result = await repo.get_by_telegram_id(999999)
    assert result is None


@pytest.mark.asyncio
async def test_find_partners(session: AsyncSession) -> None:
    repo = PlayerRepository(session)

    _courts = '["High Park"]'
    alice = Player(telegram_id=1, first_name="Alice", skill_level=3.0, home_area="Downtown", language="en", preferred_courts=_courts)
    bob = Player(telegram_id=2, first_name="Bob", skill_level=3.5, home_area="Downtown", language="en", preferred_courts=_courts)
    carol = Player(telegram_id=3, first_name="Carol", skill_level=5.0, home_area="Downtown", language="en", preferred_courts=_courts)
    dave = Player(telegram_id=4, first_name="Dave", skill_level=3.0, home_area="North York", language="en", preferred_courts=_courts)

    for p in [alice, bob, carol, dave]:
        await repo.add(p)
    await session.commit()

    # Alice (3.0, Downtown) — partners within ±0.5 in Downtown: Bob (3.5) only
    partners = await repo.find_partners(
        area="Downtown", skill_level=3.0, exclude_telegram_id=1, level_tolerance=0.5
    )
    names = {p.first_name for p in partners}
    assert "Bob" in names
    assert "Carol" not in names  # level too high
    assert "Dave" not in names  # wrong area
    assert "Alice" not in names  # excluded


@pytest.mark.asyncio
async def test_set_available(session: AsyncSession) -> None:
    from datetime import datetime, timedelta

    repo = PlayerRepository(session)
    player = Player(telegram_id=10, first_name="Eve")
    await repo.add(player)
    await session.commit()

    available_until = datetime.utcnow() + timedelta(hours=2)
    await repo.set_available(player.id, available_until)
    await session.commit()

    updated = await repo.get_by_telegram_id(10)
    assert updated is not None
    assert updated.available_now is True
    assert updated.available_until is not None


# ---------------------------------------------------------------------------
# Admin Center Players module additions
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_count_all(session: AsyncSession) -> None:
    repo = PlayerRepository(session)
    assert await repo.count_all() == 0

    await repo.add(Player(telegram_id=1, first_name="Alice"))
    await repo.add(Player(telegram_id=2, first_name="Bob"))
    await session.commit()

    assert await repo.count_all() == 2


@pytest.mark.asyncio
async def test_get_paginated_orders_by_id_and_respects_offset_limit(session: AsyncSession) -> None:
    repo = PlayerRepository(session)
    for i in range(5):
        await repo.add(Player(telegram_id=i, first_name=f"Player{i}"))
    await session.commit()

    first_page = await repo.get_paginated(offset=0, limit=2)
    second_page = await repo.get_paginated(offset=2, limit=2)

    assert [p.first_name for p in first_page] == ["Player0", "Player1"]
    assert [p.first_name for p in second_page] == ["Player2", "Player3"]


@pytest.mark.asyncio
async def test_search_by_name_or_username_is_case_insensitive_substring(session: AsyncSession) -> None:
    repo = PlayerRepository(session)
    await repo.add(Player(telegram_id=1, first_name="Alice Johnson", username="alicej"))
    await repo.add(Player(telegram_id=2, first_name="Bob", username="bobby"))
    await session.commit()

    by_name = await repo.search_by_name_or_username("ALICE")
    assert [p.first_name for p in by_name] == ["Alice Johnson"]

    by_username = await repo.search_by_name_or_username("BOBBY")
    assert [p.first_name for p in by_username] == ["Bob"]

    no_match = await repo.search_by_name_or_username("zzz")
    assert no_match == []
