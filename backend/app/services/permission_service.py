"""Single entry point for Admin Center authorization.

Every admin handler must go through this service to answer "is this
person an operator" and "does their role meet the bar for this action" —
never an inline, per-handler check. A permission check duplicated across
handlers is the same failure mode as TECH-001's duplicated
`_TRIGGER_TEXTS` sets, except the failure mode here is a security gap
instead of a dead button.
"""
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database.models.operator_permission import OperatorPermission, OperatorRole
from backend.app.database.repositories.operator_permission_repository import (
    OperatorPermissionRepository,
)

_ROLE_RANK = {
    OperatorRole.MODERATOR: 1,
    OperatorRole.ADMIN: 2,
    OperatorRole.OWNER: 3,
}


class PermissionService:
    """Authorization only. Session/PIN lifecycle lives in AdminSessionService."""

    def __init__(self, session: AsyncSession) -> None:
        self._repo = OperatorPermissionRepository(session)

    async def get_role(self, telegram_id: int) -> OperatorRole | None:
        """Return this Telegram ID's role, or None if they are not an operator."""
        record = await self._repo.get_by_telegram_id(telegram_id)
        return record.role if record else None

    async def is_operator(self, telegram_id: int) -> bool:
        """Whether this Telegram ID holds any Admin Center role at all."""
        return await self.get_role(telegram_id) is not None

    async def has_role(self, telegram_id: int, role: OperatorRole) -> bool:
        """Whether this Telegram ID holds exactly this role."""
        return await self.get_role(telegram_id) == role

    async def has_permission(self, telegram_id: int, minimum_role: OperatorRole) -> bool:
        """Whether this Telegram ID's role satisfies at least `minimum_role`,
        using the Moderator < Admin < Owner hierarchy."""
        current = await self.get_role(telegram_id)
        if current is None:
            return False
        return _ROLE_RANK[current] >= _ROLE_RANK[minimum_role]

    async def seed_owners(self, owner_ids: list[int]) -> int:
        """Grant Owner to any of these Telegram IDs that hold no role yet.
        Bootstrap only — every grant after this happens in-app once an
        Owner exists. Returns the number of new grants made."""
        granted = 0
        for telegram_id in owner_ids:
            if await self._repo.get_by_telegram_id(telegram_id) is not None:
                continue
            await self._repo.add(
                OperatorPermission(telegram_id=telegram_id, role=OperatorRole.OWNER)
            )
            granted += 1
        return granted
