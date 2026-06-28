"""ORM models package.

Importing this package registers all models with SQLAlchemy's metadata.
"""
from backend.app.database.models.game import Game, GamePlayer, GamePlayerStatus, GameStatus, MatchType
from backend.app.database.models.invitation import Invitation, InvitationStatus
from backend.app.database.models.player import Player

__all__ = [
    "Player",
    "Game",
    "GamePlayer",
    "GameStatus",
    "GamePlayerStatus",
    "MatchType",
    "Invitation",
    "InvitationStatus",
]
