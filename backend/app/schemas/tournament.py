"""Pydantic schemas for Tournament."""
from datetime import date, datetime, time

from pydantic import BaseModel, ConfigDict

from backend.app.database.models.tournament import TournamentPlayerStatus, TournamentStatus


class TournamentCreate(BaseModel):
    """Data required to create a new tournament."""

    name: str
    description: str | None = None
    area: str
    court: str
    start_date: date
    start_time: time
    registration_deadline: date
    max_players: int


class TournamentUpdate(BaseModel):
    """Partial update — only fields the organizer can still change."""

    name: str | None = None
    description: str | None = None
    area: str | None = None
    court: str | None = None
    start_date: date | None = None
    start_time: time | None = None
    registration_deadline: date | None = None
    max_players: int | None = None


class TournamentRead(BaseModel):
    """Full tournament representation."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    organizer_player_id: int
    area: str
    court: str
    start_date: date
    start_time: time
    registration_deadline: date
    max_players: int
    status: TournamentStatus
    created_at: datetime


class TournamentPlayerRead(BaseModel):
    """A single registration row, joined with the player's identity for display."""

    model_config = ConfigDict(from_attributes=True)

    player_id: int
    first_name: str
    telegram_id: int
    language: str | None = None
    status: TournamentPlayerStatus
    registered_at: datetime
