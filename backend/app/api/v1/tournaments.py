"""Tournament Read API endpoints (Sprint 15, Step 1).

Read-only: list, detail, standings. No create/update/result-entry
endpoints here — those are separate, not-yet-built steps
(docs/Sprint14_Tournament_Engine_Plan.md's Step 2 continues; PATCH
/games/{id}/result per PD-001 is a later step of that same plan).

No business logic in this router, same rule as games.py/players.py:
every read goes straight through the existing TournamentService.
Standings are never recomputed here — always
TournamentService.get_standings(), which is itself always computed
from Game rows, never stored.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database.session import get_db_session
from backend.app.schemas.tournament import TournamentRead, TournamentStandingEntry
from backend.app.services.tournament_service import TournamentService

router = APIRouter(prefix="/tournaments", tags=["tournaments"])


def _get_service(session: AsyncSession = Depends(get_db_session)) -> TournamentService:
    return TournamentService(session)


@router.get("/", response_model=list[TournamentRead])
async def list_tournaments(
    page: int = Query(default=1, ge=1),
    service: TournamentService = Depends(_get_service),
) -> list[TournamentRead]:
    """Return one page of tournaments, in TournamentService's own Browse
    ordering (grouped by status, then date)."""
    tournaments, _ = await service.list_tournaments(page=page)
    return tournaments


@router.get("/{tournament_id}", response_model=TournamentRead)
async def get_tournament(
    tournament_id: int, service: TournamentService = Depends(_get_service)
) -> TournamentRead:
    """Return a tournament by ID."""
    tournament = await service.get_tournament(tournament_id)
    if not tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")
    return tournament


@router.get("/{tournament_id}/standings", response_model=list[TournamentStandingEntry])
async def get_tournament_standings(
    tournament_id: int, service: TournamentService = Depends(_get_service)
) -> list[TournamentStandingEntry]:
    """Return computed standings for a tournament. Empty list is a valid
    response (no registrations/completed matches yet) — 404 is reserved
    for a tournament_id that doesn't exist at all."""
    tournament = await service.get_tournament(tournament_id)
    if not tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")
    return await service.get_standings(tournament_id)
