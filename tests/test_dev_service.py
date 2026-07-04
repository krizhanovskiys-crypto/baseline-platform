"""Tests for DevService.

The old flat DEVELOPER_IDS access guard (_is_developer) was replaced in
Sprint 11 Phase 2.1 by PermissionService + AdminSessionService — see
test_permission_service.py, test_admin_session_service.py, and
test_admin_center_auth.py for the new access-flow coverage.
"""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.services.dev_service import DevService, _TEST_PLAYERS, _TEST_TELEGRAM_ID_BASE


# ---------------------------------------------------------------------------
# DevService
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_test_players(session: AsyncSession) -> None:
    svc = DevService(session)
    count = await svc.create_test_players()
    await session.commit()

    assert count == len(_TEST_PLAYERS)


@pytest.mark.asyncio
async def test_create_test_players_idempotent(session: AsyncSession) -> None:
    """Running create twice should not duplicate players."""
    svc = DevService(session)
    await svc.create_test_players()
    await session.commit()
    second = await svc.create_test_players()
    await session.commit()

    assert second == 0


@pytest.mark.asyncio
async def test_reset_test_data(session: AsyncSession) -> None:
    svc = DevService(session)
    await svc.create_test_players()
    await session.commit()

    deleted = await svc.reset_test_data()
    await session.commit()

    assert deleted == len(_TEST_PLAYERS)


@pytest.mark.asyncio
async def test_reset_test_data_nothing_to_delete(session: AsyncSession) -> None:
    svc = DevService(session)
    deleted = await svc.reset_test_data()
    assert deleted == 0


@pytest.mark.asyncio
async def test_get_stats_empty(session: AsyncSession) -> None:
    svc = DevService(session)
    stats = await svc.get_stats()

    assert stats["players"] == 0
    assert stats["complete"] == 0
    assert stats["games"] == 0
    assert stats["available"] == 0


@pytest.mark.asyncio
async def test_get_stats_after_seeding(session: AsyncSession) -> None:
    svc = DevService(session)
    await svc.create_test_players()
    await session.commit()

    stats = await svc.get_stats()

    assert stats["players"] == len(_TEST_PLAYERS)
    # All test players have complete profiles
    assert stats["complete"] == len(_TEST_PLAYERS)
