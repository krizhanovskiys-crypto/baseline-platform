"""ORM models package.

Importing this package registers all models with SQLAlchemy's metadata.
"""
from backend.app.database.models.admin_audit_log import AdminAuditLog, AuditAction
from backend.app.database.models.analytics_event import AnalyticsEvent
from backend.app.database.models.game import Game, GamePlayer, GamePlayerStatus, GameStatus, MatchType
from backend.app.database.models.invitation import Invitation, InvitationStatus
from backend.app.database.models.operator_permission import OperatorPermission, OperatorRole
from backend.app.database.models.player import Player
from backend.app.database.models.tournament import (
    Tournament,
    TournamentPlayer,
    TournamentPlayerStatus,
    TournamentStatus,
)

__all__ = [
    "Player",
    "Game",
    "GamePlayer",
    "GameStatus",
    "GamePlayerStatus",
    "MatchType",
    "Invitation",
    "InvitationStatus",
    "AnalyticsEvent",
    "OperatorPermission",
    "OperatorRole",
    "AdminAuditLog",
    "AuditAction",
    "Tournament",
    "TournamentPlayer",
    "TournamentStatus",
    "TournamentPlayerStatus",
]
