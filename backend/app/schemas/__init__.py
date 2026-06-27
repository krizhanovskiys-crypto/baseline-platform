"""Pydantic schema package."""
from backend.app.schemas.game import GameCreate, GameRead
from backend.app.schemas.player import PlayerCreate, PlayerRead, PlayerUpdate

__all__ = [
    "PlayerCreate",
    "PlayerRead",
    "PlayerUpdate",
    "GameCreate",
    "GameRead",
]
