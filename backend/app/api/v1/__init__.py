"""API v1 router — aggregates all endpoint modules."""
from fastapi import APIRouter

from backend.app.api.v1 import games, players

router = APIRouter(prefix="/api/v1")
router.include_router(players.router)
router.include_router(games.router)
