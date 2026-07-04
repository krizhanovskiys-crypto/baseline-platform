"""Data access for OperatorPermission."""
from backend.app.database.models.operator_permission import OperatorPermission
from backend.app.database.repositories.base import BaseRepository


class OperatorPermissionRepository(BaseRepository[OperatorPermission]):
    model = OperatorPermission

    async def get_by_telegram_id(self, telegram_id: int) -> OperatorPermission | None:
        return await self._first(OperatorPermission.telegram_id == telegram_id)
