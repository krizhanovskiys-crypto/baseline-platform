"""Game-specific database queries."""
from datetime import date as date_

from sqlalchemy import and_, case, func, select, update

from backend.app.database.models.game import Game, GamePlayer, GamePlayerStatus, GameStatus, MatchType
from backend.app.database.models.player import Player
from backend.app.database.repositories.base import BaseRepository


class GameRepository(BaseRepository[Game]):
    """Async repository for Game entities."""

    model = Game

    async def get_open_games(self, area: str | None = None) -> list[Game]:
        """Return open games, optionally filtered by area."""
        conditions = [Game.status == GameStatus.OPEN]
        if area:
            conditions.append(Game.area == area)
        stmt = select(Game).where(and_(*conditions)).order_by(Game.date, Game.time)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_games_by_creator(self, creator_id: int) -> list[Game]:
        """Return all games created by this player."""
        return await self._all(Game.creator_id == creator_id)

    async def update_status(self, game_id: int, status: GameStatus) -> Game | None:
        """Persist a new status for the given game. Returns the updated Game or None."""
        stmt = update(Game).where(Game.id == game_id).values(status=status)
        await self._session.execute(stmt)
        await self._session.flush()
        return await self.get_by_id(game_id)

    async def get_expirable_matches(self) -> list[Game]:
        """Return all games currently in a pre-start status.

        The caller (MatchLifecycleService.expire_if_stale) applies the datetime
        filter in Python so no SQLite datetime arithmetic is needed here.
        """
        stmt = select(Game).where(
            Game.status.in_([
                GameStatus.OPEN,
                GameStatus.PARTIALLY_FILLED,
                GameStatus.FULL,
                GameStatus.CONFIRMED,
            ])
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_upcoming_matches_for_player(self, player_id: int) -> list[Game]:
        """Return upcoming games where the player has committed participation (ACCEPTED or CONFIRMED).

        Excludes COMPLETED, CANCELLED, EXPIRED, DRAFT, and IN_PROGRESS games.
        Sorted by date and time ascending so the soonest match appears first.
        INVITED-only rows are excluded — the player must have accepted.
        """
        stmt = (
            select(Game)
            .join(GamePlayer, GamePlayer.game_id == Game.id)
            .where(
                and_(
                    GamePlayer.player_id == player_id,
                    GamePlayer.status.in_([GamePlayerStatus.ACCEPTED, GamePlayerStatus.CONFIRMED]),
                    Game.status.in_([
                        GameStatus.OPEN,
                        GameStatus.PARTIALLY_FILLED,
                        GameStatus.FULL,
                        GameStatus.CONFIRMED,
                    ]),
                )
            )
            .order_by(Game.date, Game.time)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_available_matches(
        self,
        player_id: int,
        home_area: str,
        skill_level: float,
        *,
        area: str | None = None,
        on_date: date_ | None = None,
        match_type: MatchType | None = None,
        level: float | None = None,
        level_tolerance: float = 0.5,
        page: int = 1,
        page_size: int = 5,
    ) -> tuple[list[Game], int]:
        """Return joinable games for this player, filtered, sorted, and paginated.

        Joinable = status OPEN or PARTIALLY_FILLED, not created by this player,
        and this player has no ACCEPTED/CONFIRMED participation row already.

        Sort priority: same area as home_area, today, earliest date, earliest
        time, closest required_level to skill_level. Distance sorting is
        reserved for a future release.

        Returns (games_for_page, total_matching_count).
        """
        joined_subq = select(GamePlayer.game_id).where(
            GamePlayer.player_id == player_id,
            GamePlayer.status.in_([GamePlayerStatus.ACCEPTED, GamePlayerStatus.CONFIRMED]),
        )
        conditions = [
            Game.status.in_([GameStatus.OPEN, GameStatus.PARTIALLY_FILLED]),
            Game.creator_id != player_id,
            Game.id.notin_(joined_subq),
        ]
        if area:
            conditions.append(Game.area == area)
        if on_date:
            conditions.append(Game.date == on_date)
        if match_type:
            conditions.append(Game.match_type == match_type)
        effective_level = func.coalesce(Game.required_level, 3.0)
        if level is not None:
            conditions.append(effective_level >= level - level_tolerance)
            conditions.append(effective_level <= level + level_tolerance)

        where_clause = and_(*conditions)

        count_stmt = select(func.count()).select_from(Game).where(where_clause)
        total = (await self._session.execute(count_stmt)).scalar_one()

        same_area_rank = case((Game.area == home_area, 0), else_=1)
        today_rank = case((Game.date == date_.today(), 0), else_=1)
        level_diff = func.abs(effective_level - skill_level)

        stmt = (
            select(Game)
            .where(where_clause)
            .order_by(same_area_rank, today_rank, Game.date, Game.time, level_diff)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all()), total


class GamePlayerRepository(BaseRepository[GamePlayer]):
    """Async repository for GamePlayer (game-participation) entities."""

    model = GamePlayer

    async def get_participant_player_ids(self, game_id: int) -> list[int]:
        """Return the player IDs of all participants in the given game."""
        stmt = select(GamePlayer.player_id).where(GamePlayer.game_id == game_id)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_participation(self, game_id: int, player_id: int) -> GamePlayer | None:
        """Return participation record or None."""
        return await self._first(
            GamePlayer.game_id == game_id,
            GamePlayer.player_id == player_id,
        )

    async def add_player_to_game(
        self, game_id: int, player_id: int, status: GamePlayerStatus = GamePlayerStatus.INVITED
    ) -> GamePlayer:
        """Create a new participation record."""
        gp = GamePlayer(game_id=game_id, player_id=player_id, status=status)
        return await self.add(gp)

    async def get_committed_players(self, game_id: int) -> list[Player]:
        """Return Player objects for all committed participants (ACCEPTED or CONFIRMED status).

        Used to build roster displays and dispatch confirmation notifications.
        """
        stmt = (
            select(Player)
            .join(GamePlayer, GamePlayer.player_id == Player.id)
            .where(
                and_(
                    GamePlayer.game_id == game_id,
                    GamePlayer.status.in_([GamePlayerStatus.ACCEPTED, GamePlayerStatus.CONFIRMED]),
                )
            )
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def count_committed_players(self, game_id: int) -> int:
        """Count players who have committed to this game (status ACCEPTED or CONFIRMED).

        Used by InvitationService to decide whether the game has reached required_players.
        INVITED and DECLINED rows are excluded — only active participants count.
        """
        stmt = (
            select(func.count())
            .select_from(GamePlayer)
            .where(
                and_(
                    GamePlayer.game_id == game_id,
                    GamePlayer.status.in_([GamePlayerStatus.ACCEPTED, GamePlayerStatus.CONFIRMED]),
                )
            )
        )
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def remove_player_from_game(self, game_id: int, player_id: int) -> bool:
        """Delete the participation row for a player. Returns True if a row was found and deleted."""
        gp = await self.get_participation(game_id, player_id)
        if gp is None:
            return False
        await self.delete(gp)
        return True
