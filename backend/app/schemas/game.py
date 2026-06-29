"""Pydantic schemas for Game."""
from datetime import date, datetime, time

from pydantic import BaseModel, ConfigDict

from backend.app.database.models.game import GameStatus, MatchType


class GameCreate(BaseModel):
    """Data required to create a new game."""

    court: str
    area: str
    date: date
    time: time
    match_type: MatchType = MatchType.SINGLES
    required_level: float | None = None


class GameRead(BaseModel):
    """Full game representation."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    creator_id: int
    court: str
    area: str
    date: date
    time: time
    match_type: MatchType
    required_level: float | None
    status: GameStatus
    created_at: datetime
    required_players: int


class PlayerSummary(BaseModel):
    """Minimal player identity needed for match display and future extensions."""

    name: str
    telegram_id: int
    is_organizer: bool


class MatchDetails(BaseModel):
    """Assembled view of a match for display — not tied to ORM structure."""

    game: GameRead
    organizer_name: str      # convenience: name of the player where is_organizer=True
    players: list[PlayerSummary]
    committed_count: int
