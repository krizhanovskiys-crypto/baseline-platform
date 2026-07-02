"""Tests for find_partners sorting and completeness filter."""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.schemas.player import PlayerCreate, PlayerUpdate
from backend.app.services.player_service import PlayerService

_BASE_UPDATE = dict(language="en", home_area="Downtown", preferred_courts=["High Park"])


async def _make(session: AsyncSession, tid: int, name: str, level: float, courts: list[str]) -> None:
    svc = PlayerService(session)
    await svc.get_or_create(PlayerCreate(telegram_id=tid, first_name=name))
    await svc.update_profile(tid, PlayerUpdate(preferred_courts=courts, skill_level=level, **{k: v for k, v in _BASE_UPDATE.items() if k != "preferred_courts"}))  # type: ignore[arg-type]
    await session.commit()


@pytest.mark.asyncio
async def test_incomplete_profiles_excluded(session: AsyncSession) -> None:
    """Players without a complete profile must not appear in results."""
    svc = PlayerService(session)
    # Complete player
    await svc.get_or_create(PlayerCreate(telegram_id=7001, first_name="Alice"))
    await svc.update_profile(7001, PlayerUpdate(language="en", skill_level=3.0, home_area="Downtown", preferred_courts=["High Park"]))
    # Incomplete player (no language)
    await svc.get_or_create(PlayerCreate(telegram_id=7002, first_name="Bob"))
    await svc.update_profile(7002, PlayerUpdate(skill_level=3.0, home_area="Downtown", preferred_courts=["High Park"]))
    await session.commit()

    partners = await svc.find_partners(telegram_id=9999, area="Downtown", skill_level=3.0)
    names = {p.first_name for p in partners}
    assert "Alice" in names
    assert "Bob" not in names


@pytest.mark.asyncio
async def test_sorted_by_shared_courts(session: AsyncSession) -> None:
    """Partner sharing more courts should rank higher."""
    svc = PlayerService(session)
    await svc.get_or_create(PlayerCreate(telegram_id=8001, first_name="One"))
    await svc.update_profile(8001, PlayerUpdate(language="en", skill_level=3.5, home_area="Downtown", preferred_courts=["High Park"]))
    await svc.get_or_create(PlayerCreate(telegram_id=8002, first_name="Two"))
    await svc.update_profile(8002, PlayerUpdate(language="en", skill_level=3.5, home_area="Downtown", preferred_courts=["High Park", "Ramsden Park"]))
    await svc.get_or_create(PlayerCreate(telegram_id=8003, first_name="Three"))
    await svc.update_profile(8003, PlayerUpdate(language="en", skill_level=3.5, home_area="Downtown", preferred_courts=["Other"]))
    await session.commit()

    partners = await svc.find_partners(
        telegram_id=9999,
        area="Downtown",
        skill_level=3.5,
        my_courts=["High Park", "Ramsden Park"],
    )
    names = [p.first_name for p in partners]
    # Two shares 2 courts, One shares 1, Three shares 0
    assert names[0] == "Two"
    assert names[1] == "One"
    assert names[2] == "Three"


@pytest.mark.asyncio
async def test_sorted_by_skill_diff(session: AsyncSession) -> None:
    """When shared courts are equal, smallest skill difference ranks higher."""
    svc = PlayerService(session)
    # Both within ±0.5 of searcher's 3.0; neither shares courts with searcher
    await svc.get_or_create(PlayerCreate(telegram_id=8010, first_name="Close"))
    await svc.update_profile(8010, PlayerUpdate(language="en", skill_level=3.0, home_area="Downtown", preferred_courts=["Other"]))
    await svc.get_or_create(PlayerCreate(telegram_id=8011, first_name="Far"))
    await svc.update_profile(8011, PlayerUpdate(language="en", skill_level=3.5, home_area="Downtown", preferred_courts=["Other"]))
    await session.commit()

    partners = await svc.find_partners(
        telegram_id=9999,
        area="Downtown",
        skill_level=3.0,
        my_courts=[],
    )
    names = [p.first_name for p in partners]
    assert names[0] == "Close"   # diff=0.0
    assert names[1] == "Far"     # diff=0.5


@pytest.mark.asyncio
async def test_self_excluded(session: AsyncSession) -> None:
    """The requesting player must never appear in their own results."""
    svc = PlayerService(session)
    await svc.get_or_create(PlayerCreate(telegram_id=8020, first_name="Me"))
    await svc.update_profile(8020, PlayerUpdate(language="en", skill_level=3.0, home_area="Downtown", preferred_courts=["High Park"]))
    await session.commit()

    partners = await svc.find_partners(telegram_id=8020, area="Downtown", skill_level=3.0)
    assert all(p.telegram_id != 8020 for p in partners)


@pytest.mark.asyncio
async def test_empty_when_no_matches(session: AsyncSession) -> None:
    """Returns empty list when no one matches area + level criteria."""
    svc = PlayerService(session)
    partners = await svc.find_partners(telegram_id=9999, area="Nowhere", skill_level=3.0)
    assert partners == []


# ── Sprint 10.3 Phase 2 — Court Registry: matching is court-value agnostic ───

@pytest.mark.asyncio
async def test_matching_works_with_registry_and_custom_courts_mixed(session: AsyncSession) -> None:
    """find_partners() only ever does plain string set-intersection on
    preferred_courts — it has no knowledge of the Court Registry or Tennis
    Zones. Official registry courts and freeform custom courts (added via
    'Add my own court') must sort identically, with no regression."""
    svc = PlayerService(session)
    # Registry court, matches searcher exactly.
    await svc.get_or_create(PlayerCreate(telegram_id=8101, first_name="Registry"))
    await svc.update_profile(8101, PlayerUpdate(language="en", skill_level=3.5, home_area="Downtown", preferred_courts=["Ramsden Park"]))
    # Custom (non-registry) court, matches searcher exactly.
    await svc.get_or_create(PlayerCreate(telegram_id=8102, first_name="Custom"))
    await svc.update_profile(8102, PlayerUpdate(language="en", skill_level=3.5, home_area="Downtown", preferred_courts=["High Park Bubble"]))
    # No shared court at all.
    await svc.get_or_create(PlayerCreate(telegram_id=8103, first_name="NoMatch"))
    await svc.update_profile(8103, PlayerUpdate(language="en", skill_level=3.5, home_area="Downtown", preferred_courts=["Some Other Court"]))
    await session.commit()

    partners = await svc.find_partners(
        telegram_id=9999,
        area="Downtown",
        skill_level=3.5,
        my_courts=["Ramsden Park", "High Park Bubble"],
    )
    names = [p.first_name for p in partners]
    # Registry and Custom both share exactly 1 court with the searcher, so
    # they must rank ahead of NoMatch — the registry/custom distinction has
    # no effect on ranking.
    assert set(names[:2]) == {"Registry", "Custom"}
    assert names[2] == "NoMatch"
