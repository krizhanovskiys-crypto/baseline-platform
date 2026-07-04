"""Tests for PermissionService — Admin Center authorization.

Covers the single entry point for "is this Telegram ID an operator" and
"does their role meet the bar for this action", and the OWNER_IDS
bootstrap seeding path. Session/PIN lifecycle is a separate concern,
covered in test_admin_session_service.py.
"""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database.models.operator_permission import OperatorRole
from backend.app.services.permission_service import PermissionService


@pytest.mark.asyncio
async def test_unknown_telegram_id_is_not_an_operator(session: AsyncSession) -> None:
    svc = PermissionService(session)
    assert await svc.is_operator(999) is False
    assert await svc.get_role(999) is None


@pytest.mark.asyncio
async def test_seed_owners_grants_owner_role(session: AsyncSession) -> None:
    svc = PermissionService(session)
    granted = await svc.seed_owners([111, 222])
    await session.commit()

    assert granted == 2
    assert await svc.is_operator(111) is True
    assert await svc.get_role(111) == OperatorRole.OWNER
    assert await svc.get_role(222) == OperatorRole.OWNER


@pytest.mark.asyncio
async def test_seed_owners_is_idempotent(session: AsyncSession) -> None:
    """Re-running the bootstrap seed must not duplicate or error."""
    svc = PermissionService(session)
    await svc.seed_owners([111])
    await session.commit()

    granted_again = await svc.seed_owners([111])
    await session.commit()

    assert granted_again == 0


@pytest.mark.asyncio
async def test_seed_owners_does_not_touch_existing_operator(session: AsyncSession) -> None:
    """Seeding must never overwrite an already-granted role (e.g. someone
    demoted from Owner to Admin must not be silently re-promoted)."""
    from backend.app.database.models.operator_permission import OperatorPermission
    from backend.app.database.repositories.operator_permission_repository import (
        OperatorPermissionRepository,
    )

    repo = OperatorPermissionRepository(session)
    await repo.add(OperatorPermission(telegram_id=111, role=OperatorRole.ADMIN))
    await session.commit()

    svc = PermissionService(session)
    granted = await svc.seed_owners([111])
    await session.commit()

    assert granted == 0
    assert await svc.get_role(111) == OperatorRole.ADMIN


@pytest.mark.asyncio
async def test_has_role_exact_match_only(session: AsyncSession) -> None:
    svc = PermissionService(session)
    await svc.seed_owners([111])
    await session.commit()

    assert await svc.has_role(111, OperatorRole.OWNER) is True
    assert await svc.has_role(111, OperatorRole.ADMIN) is False


@pytest.mark.asyncio
async def test_has_permission_uses_moderator_admin_owner_hierarchy(session: AsyncSession) -> None:
    from backend.app.database.models.operator_permission import OperatorPermission
    from backend.app.database.repositories.operator_permission_repository import (
        OperatorPermissionRepository,
    )

    repo = OperatorPermissionRepository(session)
    await repo.add(OperatorPermission(telegram_id=1, role=OperatorRole.MODERATOR))
    await repo.add(OperatorPermission(telegram_id=2, role=OperatorRole.ADMIN))
    await repo.add(OperatorPermission(telegram_id=3, role=OperatorRole.OWNER))
    await session.commit()

    svc = PermissionService(session)

    # Owner satisfies every minimum bar.
    assert await svc.has_permission(3, OperatorRole.MODERATOR) is True
    assert await svc.has_permission(3, OperatorRole.ADMIN) is True
    assert await svc.has_permission(3, OperatorRole.OWNER) is True

    # Admin satisfies Moderator/Admin but not Owner.
    assert await svc.has_permission(2, OperatorRole.MODERATOR) is True
    assert await svc.has_permission(2, OperatorRole.ADMIN) is True
    assert await svc.has_permission(2, OperatorRole.OWNER) is False

    # Moderator satisfies only Moderator.
    assert await svc.has_permission(1, OperatorRole.MODERATOR) is True
    assert await svc.has_permission(1, OperatorRole.ADMIN) is False


@pytest.mark.asyncio
async def test_has_permission_false_for_non_operator(session: AsyncSession) -> None:
    svc = PermissionService(session)
    assert await svc.has_permission(999, OperatorRole.MODERATOR) is False
