"""Game-specific database queries."""
from sqlalchemy import and_, select, update

from backend.app.database.models.game import Game, GamePlayer, GamePlayerStatus, GameStatus
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
