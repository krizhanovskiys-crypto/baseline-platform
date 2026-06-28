"""Invitation service — business logic for match invitations."""
import logging
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database.models.game import GamePlayerStatus
from backend.app.database.models.invitation import Invitation, InvitationStatus
from backend.app.database.repositories.game_repository import GamePlayerRepository, GameRepository
from backend.app.database.repositories.invitation_repository import InvitationRepository
from backend.app.database.repositories.player_repository import PlayerRepository

logger = logging.getLogger(__name__)


class InvitationService:
    """Handles invitation creation, acceptance, and decline."""

    def __init__(self, session: AsyncSession) -> None:
        self._repo = InvitationRepository(session)
        self._game_repo = GameRepository(session)
        self._gp_repo = GamePlayerRepository(session)
        self._player_repo = PlayerRepository(session)

    async def create_invitation(
        self, game_id: int, invitee_player_id: int
    ) -> Invitation | None:
        """Create a PENDING invitation.

        Returns None if the player is already invited or already in the game.
        """
        existing = await self._repo.get_by_game_and_player(game_id, invitee_player_id)
        if existing:
            logger.debug("Duplicate invitation game=%s player=%s", game_id, invitee_player_id)
            return None
        participant_ids = await self._gp_repo.get_participant_player_ids(game_id)
        if invitee_player_id in participant_ids:
            logger.debug("Player %s already in game %s", invitee_player_id, game_id)
            return None
        invitation = await self._repo.create(game_id, invitee_player_id)
        logger.info("Invitation created id=%s game=%s player=%s", invitation.id, game_id, invitee_player_id)
        return invitation

    async def accept(
        self, invitation_id: int, player_telegram_id: int
    ) -> tuple[Invitation | None, str]:
        """Accept an invitation.

        Returns (invitation, "") on success, (None, error_key) on failure.
        """
        inv = await self._repo.get_by_id(invitation_id)
        if not inv:
            return None, "inv_not_found"
        player = await self._player_repo.get_by_telegram_id(player_telegram_id)
        if not player or player.id != inv.player_id:
            return None, "inv_not_yours"
        if inv.status != InvitationStatus.PENDING:
            return None, "inv_already_responded"

        updated = await self._repo.update_status(
            invitation_id, InvitationStatus.ACCEPTED, datetime.now(UTC)
        )
        existing_gp = await self._gp_repo.get_participation(inv.game_id, inv.player_id)
        if not existing_gp:
            await self._gp_repo.add_player_to_game(
                inv.game_id, inv.player_id, GamePlayerStatus.ACCEPTED
            )
        logger.info("Invitation %s accepted by telegram_id=%s", invitation_id, player_telegram_id)
        return updated, ""

    async def decline(
        self, invitation_id: int, player_telegram_id: int
    ) -> tuple[Invitation | None, str]:
        """Decline an invitation.

        Returns (invitation, "") on success, (None, error_key) on failure.
        """
        inv = await self._repo.get_by_id(invitation_id)
        if not inv:
            return None, "inv_not_found"
        player = await self._player_repo.get_by_telegram_id(player_telegram_id)
        if not player or player.id != inv.player_id:
            return None, "inv_not_yours"
        if inv.status != InvitationStatus.PENDING:
            return None, "inv_already_responded"

        updated = await self._repo.update_status(
            invitation_id, InvitationStatus.DECLINED, datetime.now(UTC)
        )
        logger.info("Invitation %s declined by telegram_id=%s", invitation_id, player_telegram_id)
        return updated, ""
