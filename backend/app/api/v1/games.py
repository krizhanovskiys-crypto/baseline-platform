"""Game CRUD API endpoints."""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database.session import get_db_session
from backend.app.schemas.game import GameCreate, GameRead
from backend.app.services.game_service import GameService
from backend.app.services.tournament_service import TournamentService

router = APIRouter(prefix="/games", tags=["games"])


def _get_service(session: AsyncSession = Depends(get_db_session)) -> GameService:
    return GameService(session)


def _get_tournament_service(session: AsyncSession = Depends(get_db_session)) -> TournamentService:
    return TournamentService(session)


# Tournament match lifecycle (Sprint 15, Step 2) — result entry per
# PD-001: Tournament Organizer (Verified Coach or Admin) only, never a
# Player. No authorization logic here — TournamentService.start_match()/
# complete_match() already re-check can_manage_tournament() themselves;
# this router only maps their (game, error_key) result onto HTTP.
_ERROR_STATUS: dict[str, int] = {
    "tournament_match_not_found": status.HTTP_404_NOT_FOUND,
    "tournament_match_forbidden": status.HTTP_403_FORBIDDEN,
    "tournament_match_invalid_transition": status.HTTP_409_CONFLICT,
    "tournament_match_wrong_status": status.HTTP_409_CONFLICT,
    "tournament_match_winner_not_participant": status.HTTP_400_BAD_REQUEST,
}


def _raise_for_error(error_key: str) -> None:
    raise HTTPException(status_code=_ERROR_STATUS.get(error_key, 400), detail=error_key)


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


@router.post("/{game_id}/start", response_model=GameRead)
async def start_tournament_match(
    game_id: int,
    organizer_telegram_id: int,
    service: TournamentService = Depends(_get_tournament_service),
) -> GameRead:
    """Start a tournament match (OPEN -> IN_PROGRESS). Tournament
    Organizer (Verified Coach or Admin) only — never a Player, per
    PD-001. Delegates entirely to TournamentService.start_match()."""
    updated, error_key = await service.start_match(game_id, organizer_telegram_id)
    if error_key:
        _raise_for_error(error_key)
    return updated


@router.post("/{game_id}/complete", response_model=GameRead)
async def complete_tournament_match(
    game_id: int,
    winner_player_id: int,
    organizer_telegram_id: int,
    service: TournamentService = Depends(_get_tournament_service),
) -> GameRead:
    """Report a tournament match's Winner (IN_PROGRESS -> COMPLETED).
    Tournament Organizer (Verified Coach or Admin) only — never a
    Player, per PD-001. Winner-only, no score. Delegates entirely to
    TournamentService.complete_match(), which also advances the bracket
    (next round or tournament completion) — no duplicated logic here."""
    updated, error_key = await service.complete_match(game_id, winner_player_id, organizer_telegram_id)
    if error_key:
        _raise_for_error(error_key)
    return updated
