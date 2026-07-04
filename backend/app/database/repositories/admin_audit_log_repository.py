"""Data access for AdminAuditLog."""
from backend.app.database.models.admin_audit_log import AdminAuditLog
from backend.app.database.repositories.base import BaseRepository


class AdminAuditLogRepository(BaseRepository[AdminAuditLog]):
    model = AdminAuditLog

    async def log(self, telegram_id: int, action: str) -> AdminAuditLog:
        return await self.add(AdminAuditLog(telegram_id=telegram_id, action=action))
