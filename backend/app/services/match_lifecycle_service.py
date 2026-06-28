"""Match lifecycle service — the sole authority over game status transitions."""
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.exceptions import InvalidTransitionError
from backend.app.database.models.game import GameStatus
from backend.app.database.repositories.game_repository import GameRepository
from backend.app.schemas.game import GameRead

logger = logging.getLogger(__name__)

# Maps each status to the set of statuses it may transition into.
_VALID_TRANSITIONS: dict[GameStatus, frozenset[GameStatus]] = {
    GameStatus.DRAFT:            frozenset({GameStatus.OPEN, GameStatus.CANCELLED}),
    GameStatus.OPEN:             frozenset({GameStatus.PARTIALLY_FILLED, GameStatus.CANCELLED, GameStatus.EXPIRED}),
    GameStatus.PARTIALLY_FILLED: frozenset({GameStatus.FULL, GameStatus.CANCELLED, GameStatus.EXPIRED}),
    GameStatus.FULL:             frozenset({GameStatus.CONFIRMED, GameStatus.CANCELLED}),
    GameStatus.CONFIRMED:        frozenset({GameStatus.IN_PROGRESS, GameStatus.CANCELLED}),
    GameStatus.IN_PROGRESS:      frozenset({GameStatus.COMPLETED}),
    # Terminal states — no outgoing transitions.
    GameStatus.COMPLETED:        frozenset(),
    GameStatus.CANCELLED:        frozenset(),
    GameStatus.EXPIRED:          frozenset(),
}


def _game_to_schema(game) -> GameRead:
    return GameRead.model_validate(game)


class MatchLifecycleService:
    """Owns all game status transitions.

    Only this service may change a game's status.
    Handlers must never modify status directly.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._repo = GameRepository(session)

    async def transition(self, game_id: int, new_status: GameStatus) -> GameRead:
        """Transition a game to a new status.

        Raises:
            ValueError: if the game does not exist.
            InvalidTransitionError: if the transition is not permitted.
        """
        game = await self._repo.get_by_id(game_id)
        if game is None:
            raise ValueError(f"Game {game_id} not found")

        current = game.status
        allowed = _VALID_TRANSITIONS.get(current, frozenset())

        if new_status not in allowed:
            raise InvalidTransitionError(current, new_status)

        updated = await self._repo.update_status(game_id, new_status)
        logger.info("Game %s transitioned %s → %s", game_id, current.value, new_status.value)
        return _game_to_schema(updated)
