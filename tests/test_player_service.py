"""Tests for PlayerService."""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.schemas.player import PlayerCreate, PlayerUpdate
from backend.app.services.player_service import PlayerService


@pytest.mark.asyncio
async def test_get_or_create_new_player(session: AsyncSession) -> None:
    service = PlayerService(session)
    player, created = await service.get_or_create(
        PlayerCreate(telegram_id=1001, username="alice", first_name="Alice")
    )
    await session.commit()

    assert created is True
    assert player.telegram_id == 1001
    assert player.first_name == "Alice"
    assert player.is_profile_complete is False


@pytest.mark.asyncio
async def test_get_or_create_existing_player(session: AsyncSession) -> None:
    service = PlayerService(session)
    create_data = PlayerCreate(telegram_id=1002, first_name="Bob")

    p1, created1 = await service.get_or_create(create_data)
    await session.commit()
    p2, created2 = await service.get_or_create(create_data)
    await session.commit()

    assert created1 is True
    assert created2 is False
    assert p1.id == p2.id


@pytest.mark.asyncio
async def test_update_profile(session: AsyncSession) -> None:
    service = PlayerService(session)
    await service.get_or_create(PlayerCreate(telegram_id=1003, first_name="Carol"))
    await session.commit()

    updated = await service.update_profile(
        1003,
        PlayerUpdate(
            language="en",
            skill_level=3.5,
            home_area="Downtown",
            preferred_courts=["Ramsden Park", "High Park"],
        ),
    )
    await session.commit()

    assert updated is not None
    assert updated.skill_level == 3.5
    assert updated.home_area == "Downtown"
    assert updated.is_profile_complete is True
    assert "Ramsden Park" in (updated.preferred_courts or [])


@pytest.mark.asyncio
async def test_find_partners(session: AsyncSession) -> None:
    service = PlayerService(session)

    for tid, name, level, area in [
        (2001, "Alice", 3.0, "Downtown"),
        (2002, "Bob", 3.5, "Downtown"),
        (2003, "Carol", 5.0, "Downtown"),
        (2004, "Dave", 3.0, "North York"),
    ]:
        p, _ = await service.get_or_create(PlayerCreate(telegram_id=tid, first_name=name))
        await service.update_profile(
            tid, PlayerUpdate(language="en", skill_level=level, home_area=area, preferred_courts=["Other"])
        )
    await session.commit()

    partners = await service.find_partners(
        telegram_id=2001, area="Downtown", skill_level=3.0
    )
    names = {p.first_name for p in partners}
    assert "Bob" in names
    assert "Alice" not in names  # self excluded
    assert "Carol" not in names
    assert "Dave" not in names


@pytest.mark.asyncio
async def test_set_available_now(session: AsyncSession) -> None:
    service = PlayerService(session)
    await service.get_or_create(PlayerCreate(telegram_id=3001, first_name="Eve"))
    await session.commit()

    result = await service.set_available_now(3001)
    await session.commit()

    assert result is not None
    assert result.available_now is True
    assert result.available_until is not None


@pytest.mark.asyncio
async def test_profile_complete_flag(session: AsyncSession) -> None:
    service = PlayerService(session)
    player, _ = await service.get_or_create(PlayerCreate(telegram_id=4001, first_name="Frank"))
    await session.commit()
    assert player.is_profile_complete is False

    await service.update_profile(
        4001,
        PlayerUpdate(language="uk", skill_level=4.0, home_area="Markham", preferred_courts=["High Park"]),
    )
    await session.commit()

    player = await service.get_by_telegram_id(4001)
    assert player is not None
    assert player.is_profile_complete is True
