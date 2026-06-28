"""Pydantic schemas for Invitation."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from backend.app.database.models.invitation import InvitationStatus


class InvitationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    game_id: int
    player_id: int
    status: InvitationStatus
    created_at: datetime
    responded_at: datetime | None
