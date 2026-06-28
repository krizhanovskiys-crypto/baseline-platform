"""Invitation-specific database queries."""
from datetime import datetime

from sqlalchemy import select, update

from backend.app.database.models.invitation import Invitation, InvitationStatus
from backend.app.database.repositories.base import BaseRepository


class InvitationRepository(BaseRepository[Invitation]):
    """Async repository for Invitation entities."""

    model = Invitation

    async def get_by_game_and_player(self, game_id: int, player_id: int) -> Invitation | None:
        """Return the invitation for this (game, player) pair, or None."""
        return await self._first(
            Invitation.game_id == game_id,
            Invitation.player_id == player_id,
        )

    async def create(self, game_id: int, player_id: int) -> Invitation:
        """Create a new PENDING invitation."""
        inv = Invitation(game_id=game_id, player_id=player_id)
        return await self.add(inv)

    async def update_status(
        self, invitation_id: int, status: InvitationStatus, responded_at: datetime
    ) -> Invitation | None:
        """Set invitation status and responded_at timestamp. Returns updated object."""
        stmt = (
            update(Invitation)
            .where(Invitation.id == invitation_id)
            .values(status=status, responded_at=responded_at)
        )
        await self._session.execute(stmt)
        await self._session.flush()
        return await self.get_by_id(invitation_id)
