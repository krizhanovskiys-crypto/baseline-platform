"""Game service — business logic for game management."""
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.exceptions import InvalidTransitionError
from backend.app.database.models.game import Game, GamePlayerStatus, GameStatus
from backend.app.database.repositories.game_repository import GamePlayerRepository, GameRepository
from backend.app.database.repositories.player_repository import PlayerRepository
from backend.app.schemas.game import GameCreate, GameRead
from backend.app.schemas.player import PlayerRead
from backend.app.services.player_service import _player_to_schema as _player_to_read

logger = logging.getLogger(__name__)


def _game_to_schema(game: Game) -> GameRead:
    return GameRead.model_validate(game)


class GameService:
    """Handles all game-related use cases."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
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
            status=GameStatus.DRAFT,
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

    async def find_players_for_match(
        self, game_id: int, organizer_telegram_id: int
    ) -> list[PlayerRead]:
        """Return candidate players who qualify for this match.

        Excludes the organizer and any existing participants.
        Filters by same area and skill level ±0.5.
        """
        game = await self._game_repo.get_by_id(game_id)
        if not game:
            return []
        organizer = await self._player_repo.get_by_telegram_id(organizer_telegram_id)
        if not organizer:
            return []
        participant_ids = await self._gp_repo.get_participant_player_ids(game_id)
        exclude_ids = set(participant_ids) | {organizer.id}
        level = float(game.required_level) if game.required_level is not None else 3.0
        candidates = await self._player_repo.find_players_for_match(
            area=game.area,
            level=level,
            exclude_player_ids=exclude_ids,
        )
        return [_player_to_read(p) for p in candidates]

    async def get_my_upcoming_matches(
        self, telegram_id: int
    ) -> list[tuple[GameRead, int]]:
        """Return (game, committed_player_count) for all upcoming matches the player participates in.

        Includes matches where the player is organizer (CONFIRMED GamePlayer status) or
        accepted invitee (ACCEPTED GamePlayer status). Sorted by date/time ascending.
        """
        player = await self._player_repo.get_by_telegram_id(telegram_id)
        if not player:
            return []
        games = await self._game_repo.get_upcoming_matches_for_player(player.id)
        result = []
        for game in games:
            count = await self._gp_repo.count_committed_players(game.id)
            result.append((_game_to_schema(game), count))
        return result

    async def confirm_match(
        self, game_id: int, organizer_telegram_id: int
    ) -> tuple[GameRead | None, list[PlayerRead], str]:
        """Transition a FULL match to CONFIRMED and return the committed player roster.

        Returns (updated_game, all_committed_players, error_key).
        all_committed_players includes the organizer — the handler decides who to notify.
        error_key is "" on success.
        """
        from backend.app.services.match_lifecycle_service import MatchLifecycleService

        game = await self._game_repo.get_by_id(game_id)
        if not game:
            return None, [], "confirm_match_not_found"

        organizer = await self._player_repo.get_by_telegram_id(organizer_telegram_id)
        if not organizer or organizer.id != game.creator_id:
            return None, [], "confirm_match_not_yours"

        if game.status != GameStatus.FULL:
            return None, [], "confirm_match_wrong_status"

        try:
            updated = await MatchLifecycleService(self._session).transition(game_id, GameStatus.CONFIRMED)
        except InvalidTransitionError:
            return None, [], "confirm_match_wrong_status"

        committed = await self._gp_repo.get_committed_players(game_id)
        return updated, [_player_to_read(p) for p in committed], ""

    async def cancel_match(
        self, game_id: int, organizer_telegram_id: int
    ) -> tuple[GameRead | None, str]:
        """Cancel a match at any cancellable status.

        Returns (updated_game, "") on success, (None, error_key) on failure.
        """
        from backend.app.services.match_lifecycle_service import MatchLifecycleService

        game = await self._game_repo.get_by_id(game_id)
        if not game:
            return None, "cancel_match_not_found"

        organizer = await self._player_repo.get_by_telegram_id(organizer_telegram_id)
        if not organizer or organizer.id != game.creator_id:
            return None, "cancel_match_not_yours"

        try:
            updated = await MatchLifecycleService(self._session).transition(game_id, GameStatus.CANCELLED)
        except InvalidTransitionError:
            return None, "cancel_match_not_cancellable"

        return updated, ""

    async def get_roster(self, game_id: int) -> tuple[GameRead | None, list[PlayerRead]]:
        """Return game details and committed player roster for display."""
        game = await self._game_repo.get_by_id(game_id)
        if not game:
            return None, []
        committed = await self._gp_repo.get_committed_players(game_id)
        return _game_to_schema(game), [_player_to_read(p) for p in committed]

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
