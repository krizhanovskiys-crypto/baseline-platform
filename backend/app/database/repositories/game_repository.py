"""Game-specific database queries."""
from sqlalchemy import and_, func, select, update

from backend.app.database.models.game import Game, GamePlayer, GamePlayerStatus, GameStatus
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
