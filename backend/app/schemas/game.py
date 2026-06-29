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
