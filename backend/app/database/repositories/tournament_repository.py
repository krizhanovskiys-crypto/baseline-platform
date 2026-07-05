"""Tournament-specific database queries."""
from sqlalchemy import and_, case, func, select, update
from sqlalchemy.orm import selectinload

from backend.app.database.models.player import Player
from backend.app.database.models.tournament import Tournament, TournamentPlayer, TournamentPlayerStatus, TournamentStatus
from backend.app.database.repositories.base import BaseRepository

# Browse order for both "My Tournaments" (Admin/Coach) and the
# player-facing Browse Tournaments: what needs attention or is still
# relevant sorts first, purely a display concern — no status is ever
# filtered out of the query itself. This is intentional: a future
# archive view for COMPLETED tournaments must not require touching this
# query, only how (or whether) its results are paginated/filtered by a
# caller — the repository never assumes completed tournaments aren't
# shown.
#
# Built as condition/value tuples (same shape as GameRepository.
# get_available_matches()'s same_area_rank/today_rank), not a
# value-keyed case() dict — binding a raw Enum member as a case() WHEN
# value doesn't go through the column's Enum type adapter and silently
# never matches; comparing Tournament.status == <member> does.
_STATUS_ORDER: list[tuple[TournamentStatus, int]] = [
    (TournamentStatus.DRAFT, 0),
    (TournamentStatus.REGISTRATION_OPEN, 1),
    (TournamentStatus.REGISTRATION_CLOSED, 2),
    (TournamentStatus.IN_PROGRESS, 3),
    (TournamentStatus.COMPLETED, 4),
    (TournamentStatus.CANCELLED, 5),
]


class TournamentRepository(BaseRepository[Tournament]):
    """Async repository for Tournament entities."""

    model = Tournament

    async def count_all(self) -> int:
        result = await self._session.execute(select(func.count()).select_from(Tournament))
        return result.scalar() or 0

    async def get_paginated(self, offset: int, limit: int) -> list[Tournament]:
        """A stable, ordered page of tournaments (Browse Tournaments /
        My Tournaments): grouped by status in _STATUS_ORDER, then by
        start_date within each group."""
        status_rank = case(
            *[(Tournament.status == status, rank) for status, rank in _STATUS_ORDER],
            else_=len(_STATUS_ORDER),
        )
        stmt = (
            select(Tournament)
            .order_by(status_rank, Tournament.start_date, Tournament.id)
            .offset(offset)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def count_by_organizer(self, organizer_player_id: int) -> int:
        result = await self._session.execute(
            select(func.count())
            .select_from(Tournament)
            .where(Tournament.organizer_player_id == organizer_player_id)
        )
        return result.scalar() or 0

    async def get_paginated_by_organizer(
        self, organizer_player_id: int, offset: int, limit: int
    ) -> list[Tournament]:
        """My Tournaments (Sprint 12.2) — same ordering as
        get_paginated(), scoped to one organizer."""
        status_rank = case(
            *[(Tournament.status == status, rank) for status, rank in _STATUS_ORDER],
            else_=len(_STATUS_ORDER),
        )
        stmt = (
            select(Tournament)
            .where(Tournament.organizer_player_id == organizer_player_id)
            .order_by(status_rank, Tournament.start_date, Tournament.id)
            .offset(offset)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def update_status(self, tournament_id: int, status: TournamentStatus) -> Tournament | None:
        """Persist a new status. The only method that may change Tournament.status."""
        stmt = update(Tournament).where(Tournament.id == tournament_id).values(status=status)
        await self._session.execute(stmt)
        await self._session.flush()
        return await self.get_by_id(tournament_id)

    async def update_fields(self, tournament_id: int, values: dict) -> Tournament | None:
        """Persist a partial field update (Edit Tournament)."""
        if values:
            stmt = update(Tournament).where(Tournament.id == tournament_id).values(**values)
            await self._session.execute(stmt)
            await self._session.flush()
        return await self.get_by_id(tournament_id)


class TournamentPlayerRepository(BaseRepository[TournamentPlayer]):
    """Async repository for TournamentPlayer (registration) entities —
    structural mirror of GamePlayerRepository."""

    model = TournamentPlayer

    async def get_registration(self, tournament_id: int, player_id: int) -> TournamentPlayer | None:
        return await self._first(
            TournamentPlayer.tournament_id == tournament_id,
            TournamentPlayer.player_id == player_id,
        )

    async def add_registration(
        self, tournament_id: int, player_id: int, status: TournamentPlayerStatus = TournamentPlayerStatus.REGISTERED
    ) -> TournamentPlayer:
        tp = TournamentPlayer(tournament_id=tournament_id, player_id=player_id, status=status)
        return await self.add(tp)

    async def set_status(
        self, tournament_id: int, player_id: int, status: TournamentPlayerStatus
    ) -> TournamentPlayer | None:
        stmt = (
            update(TournamentPlayer)
            .where(
                and_(
                    TournamentPlayer.tournament_id == tournament_id,
                    TournamentPlayer.player_id == player_id,
                )
            )
            .values(status=status)
        )
        await self._session.execute(stmt)
        await self._session.flush()
        return await self.get_registration(tournament_id, player_id)

    async def get_registered_players(self, tournament_id: int) -> list[Player]:
        """Player rows for every REGISTERED registration — used by View
        Registered Players and Generate Matches."""
        stmt = (
            select(Player)
            .join(TournamentPlayer, TournamentPlayer.player_id == Player.id)
            .where(
                and_(
                    TournamentPlayer.tournament_id == tournament_id,
                    TournamentPlayer.status == TournamentPlayerStatus.REGISTERED,
                )
            )
            .order_by(TournamentPlayer.registered_at)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_registrations_with_players(self, tournament_id: int) -> list[TournamentPlayer]:
        """REGISTERED registration rows with .player eager-loaded — used
        by View Registered Players, which needs registered_at alongside
        each player's identity."""
        stmt = (
            select(TournamentPlayer)
            .options(selectinload(TournamentPlayer.player))
            .where(
                and_(
                    TournamentPlayer.tournament_id == tournament_id,
                    TournamentPlayer.status == TournamentPlayerStatus.REGISTERED,
                )
            )
            .order_by(TournamentPlayer.registered_at)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def count_registered(self, tournament_id: int) -> int:
        stmt = (
            select(func.count())
            .select_from(TournamentPlayer)
            .where(
                and_(
                    TournamentPlayer.tournament_id == tournament_id,
                    TournamentPlayer.status == TournamentPlayerStatus.REGISTERED,
                )
            )
        )
        result = await self._session.execute(stmt)
        return result.scalar_one()
