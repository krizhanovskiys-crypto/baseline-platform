"""Player-specific database queries."""
from datetime import datetime

from sqlalchemy import and_, func, or_, select, update

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

    async def find_players_for_match(
        self,
        area: str,
        level: float,
        exclude_player_ids: set[int],
        level_tolerance: float = 0.5,
    ) -> list[Player]:
        """Return complete-profile players matching area and level ±tolerance.

        Excludes players whose IDs are in exclude_player_ids.
        """
        conditions = [
            Player.home_area == area,
            Player.skill_level >= level - level_tolerance,
            Player.skill_level <= level + level_tolerance,
            Player.language.is_not(None),
            Player.preferred_courts.is_not(None),
        ]
        if exclude_player_ids:
            conditions.append(Player.id.not_in(list(exclude_player_ids)))
        stmt = select(Player).where(and_(*conditions)).order_by(Player.rating.desc())
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

    async def count_all(self) -> int:
        """Total registered players — used by Admin Center's Players module."""
        result = await self._session.execute(select(func.count()).select_from(Player))
        return result.scalar() or 0

    async def get_paginated(self, offset: int, limit: int) -> list[Player]:
        """A stable, ordered page of players (Admin Center Browse Players)."""
        stmt = select(Player).order_by(Player.id).offset(offset).limit(limit)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def search_by_name_or_username(self, query: str) -> list[Player]:
        """Case-insensitive substring match against first_name or username
        (Admin Center Search Player). `.ilike()` rather than `.like()` so
        this stays correct on Postgres too, where LIKE is case-sensitive."""
        pattern = f"%{query}%"
        stmt = (
            select(Player)
            .where(or_(Player.first_name.ilike(pattern), Player.username.ilike(pattern)))
            .order_by(Player.first_name)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
