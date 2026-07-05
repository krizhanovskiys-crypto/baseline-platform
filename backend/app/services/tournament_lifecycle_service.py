"""Tournament lifecycle service — the sole authority over tournament
status transitions. Mirrors MatchLifecycleService's shape exactly."""
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.exceptions import InvalidTournamentTransitionError
from backend.app.database.models.tournament import TournamentStatus
from backend.app.database.repositories.tournament_repository import TournamentRepository
from backend.app.schemas.tournament import TournamentRead

logger = logging.getLogger(__name__)

# Strictly forward, per the approved status diagram — no backward
# transitions (unlike GameStatus, which allows re-opening a full match).
_VALID_TRANSITIONS: dict[TournamentStatus, frozenset[TournamentStatus]] = {
    TournamentStatus.DRAFT: frozenset({TournamentStatus.REGISTRATION_OPEN, TournamentStatus.CANCELLED}),
    TournamentStatus.REGISTRATION_OPEN: frozenset(
        {TournamentStatus.REGISTRATION_CLOSED, TournamentStatus.CANCELLED}
    ),
    TournamentStatus.REGISTRATION_CLOSED: frozenset(
        {TournamentStatus.IN_PROGRESS, TournamentStatus.CANCELLED}
    ),
    TournamentStatus.IN_PROGRESS: frozenset({TournamentStatus.COMPLETED, TournamentStatus.CANCELLED}),
    # Terminal states — no outgoing transitions.
    TournamentStatus.COMPLETED: frozenset(),
    TournamentStatus.CANCELLED: frozenset(),
}


def _tournament_to_schema(tournament) -> TournamentRead:
    return TournamentRead.model_validate(tournament)


class TournamentLifecycleService:
    """Owns all tournament status transitions. Only this service may
    change a tournament's status."""

    def __init__(self, session: AsyncSession) -> None:
        self._repo = TournamentRepository(session)

    async def transition(self, tournament_id: int, new_status: TournamentStatus) -> TournamentRead:
        """Transition a tournament to a new status and return the updated read model.

        Raises:
            ValueError: if the tournament does not exist.
            InvalidTournamentTransitionError: if the transition is not permitted.
        """
        tournament = await self._repo.get_by_id(tournament_id)
        if tournament is None:
            raise ValueError(f"Tournament {tournament_id} not found")

        current = tournament.status
        allowed = _VALID_TRANSITIONS.get(current, frozenset())

        if new_status not in allowed:
            raise InvalidTournamentTransitionError(current, new_status)

        updated = await self._repo.update_status(tournament_id, new_status)
        logger.info("Tournament %s transitioned %s → %s", tournament_id, current.value, new_status.value)
        return _tournament_to_schema(updated)
