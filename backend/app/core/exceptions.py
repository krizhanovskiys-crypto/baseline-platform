"""Domain exceptions for the Baseline platform."""
from backend.app.database.models.game import GameStatus


class InvalidTransitionError(Exception):
    """Raised when a requested game status transition is not permitted."""

    def __init__(self, from_status: GameStatus, to_status: GameStatus) -> None:
        super().__init__(
            f"Invalid transition: {from_status.value} → {to_status.value}"
        )
        self.from_status = from_status
        self.to_status = to_status
