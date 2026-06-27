"""Player CRUD API endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database.session import get_db_session
from backend.app.schemas.player import PlayerCreate, PlayerRead, PlayerUpdate
from backend.app.services.player_service import PlayerService

router = APIRouter(prefix="/players", tags=["players"])


def _get_service(session: AsyncSession = Depends(get_db_session)) -> PlayerService:
    return PlayerService(session)


@router.get("/", response_model=list[PlayerRead])
async def list_players(service: PlayerService = Depends(_get_service)) -> list[PlayerRead]:
    """Return all players."""
    return await service.list_all()


@router.post("/", response_model=PlayerRead, status_code=status.HTTP_201_CREATED)
async def create_player(
    body: PlayerCreate, service: PlayerService = Depends(_get_service)
) -> PlayerRead:
    """Create a new player (idempotent — returns existing if telegram_id already exists)."""
    player, _ = await service.get_or_create(body)
    return player


@router.get("/{player_id}", response_model=PlayerRead)
async def get_player(
    player_id: int, service: PlayerService = Depends(_get_service)
) -> PlayerRead:
    """Return a player by internal ID."""
    player = await service.get_by_id(player_id)
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    return player


@router.patch("/{telegram_id}", response_model=PlayerRead)
async def update_player(
    telegram_id: int,
    body: PlayerUpdate,
    service: PlayerService = Depends(_get_service),
) -> PlayerRead:
    """Update player profile fields by Telegram ID."""
    player = await service.update_profile(telegram_id, body)
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    return player


@router.get("/{telegram_id}/partners", response_model=list[PlayerRead])
async def find_partners(
    telegram_id: int,
    service: PlayerService = Depends(_get_service),
) -> list[PlayerRead]:
    """Find matching partners for a player."""
    player = await service.get_by_telegram_id(telegram_id)
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    if not player.skill_level or not player.home_area:
        raise HTTPException(status_code=400, detail="Player profile incomplete")
    return await service.find_partners(
        telegram_id=telegram_id,
        area=player.home_area,
        skill_level=player.skill_level,
    )
