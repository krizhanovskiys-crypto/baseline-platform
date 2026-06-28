"""Game service — business logic for game management."""
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database.models.game import Game, GamePlayerStatus
from backend.app.database.repositories.game_repository import GamePlayerRepository, GameRepository
from backend.app.database.repositories.player_repository import PlayerRepository
from backend.app.schemas.game import GameCreate, GameRead

logger = logging.getLogger(__name__)


def _game_to_schema(game: Game) -> GameRead:
    return GameRead.model_validate(game)


class GameService:
    """Handles all game-related use cases."""

    def __init__(self, session: AsyncSession) -> None:
        self._game_repo = GameRepository(session)
        self._gp_repo = GamePlayerRepository(session)
        self._player_repo = PlayerRepository(session)

    async def create_game(self, creator_telegram_id: int, data: GameCreate) -> GameRead | None:
        """Create a new game.  Returns None if creator player not found."""
        creator = await self._player_repo.get_by_telegram_id(creator_telegram_id)
        if not creator:
            logger.warning("create_game called for unknown telegram_id=%s", creator_telegram_id)
            return None

        game = Game(
            creator_id=creator.id,
            court=data.court,
            area=data.area,
            date=data.date,
            time=data.time,
            match_type=data.match_type,
            required_level=data.required_level,
        )
        game = await self._game_repo.add(game)

        # Creator automatically joins the game
        await self._gp_repo.add_player_to_game(
            game_id=game.id,
            player_id=creator.id,
            status=GamePlayerStatus.CONFIRMED,
        )

        logger.info(
            "Game created id=%s by telegram_id=%s area=%s", game.id, creator_telegram_id, game.area
        )
        return _game_to_schema(game)

    async def get_open_games(self, area: str | None = None) -> list[GameRead]:
        """Return all open games, optionally filtered by area."""
        games = await self._game_repo.get_open_games(area=area)
        return [_game_to_schema(g) for g in games]

    async def get_game(self, game_id: int) -> GameRead | None:
        game = await self._game_repo.get_by_id(game_id)
        return _game_to_schema(game) if game else None

    async def list_all(self) -> list[GameRead]:
        games = await self._game_repo.get_all()
        return [_game_to_schema(g) for g in games]

    async def get_my_matches(self, telegram_id: int) -> list[GameRead]:
        """Return all games created by this player, ordered by creation time."""
        player = await self._player_repo.get_by_telegram_id(telegram_id)
        if not player:
            return []
        games = await self._game_repo.get_games_by_creator(player.id)
        return [_game_to_schema(g) for g in games]

    async def invite_player(
        self, game_id: int, invitee_telegram_id: int
    ) -> bool:
        """Invite a player to a game.  Returns False if already participating."""
        invitee = await self._player_repo.get_by_telegram_id(invitee_telegram_id)
        if not invitee:
            return False
        existing = await self._gp_repo.get_participation(game_id, invitee.id)
        if existing:
            return False
        await self._gp_repo.add_player_to_game(
            game_id=game_id,
            player_id=invitee.id,
            status=GamePlayerStatus.INVITED,
        )
        return True
