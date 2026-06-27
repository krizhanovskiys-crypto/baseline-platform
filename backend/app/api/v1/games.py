"""Game CRUD API endpoints."""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database.session import get_db_session
from backend.app.schemas.game import GameCreate, GameRead
from backend.app.services.game_service import GameService

router = APIRouter(prefix="/games", tags=["games"])


def _get_service(session: AsyncSession = Depends(get_db_session)) -> GameService:
    return GameService(session)


@router.get("/", response_model=list[GameRead])
async def list_games(
    area: str | None = Query(default=None),
    service: GameService = Depends(_get_service),
) -> list[GameRead]:
    """Return open games, optionally filtered by area."""
    return await service.get_open_games(area=area)


@router.post("/", response_model=GameRead, status_code=status.HTTP_201_CREATED)
async def create_game(
    creator_telegram_id: int,
    body: GameCreate,
    service: GameService = Depends(_get_service),
) -> GameRead:
    """Create a new game."""
    game = await service.create_game(creator_telegram_id=creator_telegram_id, data=body)
    if not game:
        raise HTTPException(status_code=404, detail="Creator player not found")
    return game


@router.get("/{game_id}", response_model=GameRead)
async def get_game(
    game_id: int, service: GameService = Depends(_get_service)
) -> GameRead:
    """Return a game by ID."""
    game = await service.get_game(game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    return game
