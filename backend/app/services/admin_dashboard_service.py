"""Admin Center Dashboard — read-only aggregate stats.

Every figure is computed from the current database at request time, no
caching, no hardcoded values. Deliberately separate from DevService,
which is explicitly scoped to test/seed data, not the permanent
dashboard: see docs/PRODUCT_DECISIONS.md's "Admin Center Architecture"
decision — administrative functionality must not duplicate business
logic, so this reuses PlayerRepository rather than re-querying Player
directly wherever an existing repository method already does the job.
"""
import json

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database.models.game import Game, GameStatus
from backend.app.database.models.player import Player
from backend.app.database.repositories.player_repository import PlayerRepository

_ACTIVE_STATUSES = (
    GameStatus.OPEN,
    GameStatus.PARTIALLY_FILLED,
    GameStatus.FULL,
    GameStatus.CONFIRMED,
    GameStatus.IN_PROGRESS,
)


class AdminDashboardService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._player_repo = PlayerRepository(session)

    async def get_stats(self) -> dict[str, int]:
        users = await self._session.scalar(
            select(func.count()).select_from(Player)
        ) or 0

        active_matches = await self._session.scalar(
            select(func.count()).select_from(Game).where(Game.status.in_(_ACTIVE_STATUSES))
        ) or 0

        available_now = len(await self._player_repo.get_available_now())

        courts = await self._count_distinct_courts()

        return {
            "users": int(users),
            "active_matches": int(active_matches),
            "available_now": available_now,
            "courts": courts,
        }

    async def _count_distinct_courts(self) -> int:
        """Distinct courts currently favourited by any player — registry
        and custom courts counted identically, matching how
        PlayerService.find_partners already treats preferred_courts with
        no awareness of the Court Registry (ARCHITECTURE.md §6)."""
        all_players = await self._player_repo.get_all()
        distinct: set[str] = set()
        for player in all_players:
            if player.preferred_courts:
                distinct.update(json.loads(player.preferred_courts))
        return len(distinct)
