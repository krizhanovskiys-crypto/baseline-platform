"""Pydantic schemas for Player — used by API and service layer."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PlayerCreate(BaseModel):
    """Data required to create a new player."""

    telegram_id: int
    username: str | None = None
    first_name: str


class PlayerUpdate(BaseModel):
    """Fields that can be updated after creation."""

    username: str | None = None
    first_name: str | None = None
    language: str | None = None
    skill_level: float | None = Field(default=None, ge=2.0, le=7.0)
    level_source: str | None = None
    home_area: str | None = None
    preferred_courts: list[str] | None = None


class PlayerRead(BaseModel):
    """Full player representation returned to clients."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    telegram_id: int
    username: str | None
    first_name: str
    language: str | None
    skill_level: float | None
    level_source: str | None = None
    home_area: str | None
    preferred_courts: list[str] | None = None
    available_now: bool
    available_until: datetime | None
    rating: float
    matches_played: int
    is_profile_complete: bool
    created_at: datetime
    updated_at: datetime
