"""Player-specific database queries."""
from datetime import datetime

from sqlalchemy import and_, select, update

from backend.app.database.models.player import Player
from backend.app.database.repositories.base import BaseRepository


class PlayerRepository(BaseRepository[Player]):
    """Async repository for Player entities."""

    model = Player

    async def get_by_telegram_id(self, telegram_id: int) -> Player | None:
        """Return the player with the given Telegram user-id, or None."""
        return await self._first(Player.telegram_id == telegram_id)

    async def find_partners(
        self,
        area: str,
        skill_level: float,
        exclude_telegram_id: int,
        level_tolerance: float = 0.5,
    ) -> list[Player]:
        """Return complete-profile players in the same area within ±level_tolerance.

        Completeness is enforced here to keep service-layer sorting cheap.
        Final ranking (shared courts, skill diff, recency) is done in the service.
        """
        stmt = (
            select(Player)
            .where(
                and_(
                    Player.home_area == area,
                    Player.skill_level >= skill_level - level_tolerance,
                    Player.skill_level <= skill_level + level_tolerance,
                    Player.telegram_id != exclude_telegram_id,
                    Player.language.is_not(None),
                    Player.preferred_courts.is_not(None),
                )
            )
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_available_now(self) -> list[Player]:
        """Return players who have marked themselves available right now."""
        now = datetime.utcnow()
        stmt = (
            select(Player)
            .where(
                and_(
                    Player.available_now == True,  # noqa: E712
                    Player.available_until > now,
                )
            )
            .order_by(Player.rating.desc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def set_available(self, player_id: int, available_until: datetime) -> None:
        """Mark player as available until the given datetime."""
        stmt = (
            update(Player)
            .where(Player.id == player_id)
            .values(available_now=True, available_until=available_until)
        )
        await self._session.execute(stmt)
        await self._session.flush()
