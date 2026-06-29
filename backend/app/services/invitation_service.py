"""Invitation service — business logic for match invitations."""
import logging
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.exceptions import InvalidTransitionError
from backend.app.database.models.game import GamePlayerStatus, GameStatus
from backend.app.database.models.invitation import Invitation, InvitationStatus
from backend.app.database.repositories.game_repository import GamePlayerRepository, GameRepository
from backend.app.database.repositories.invitation_repository import InvitationRepository
from backend.app.database.repositories.player_repository import PlayerRepository
from backend.app.services.match_lifecycle_service import MatchLifecycleService

logger = logging.getLogger(__name__)


class InvitationService:
    """Handles invitation creation, acceptance, and decline."""

    def __init__(self, session: AsyncSession) -> None:
        self._repo = InvitationRepository(session)
        self._game_repo = GameRepository(session)
        self._gp_repo = GamePlayerRepository(session)
        self._player_repo = PlayerRepository(session)
        self._lifecycle = MatchLifecycleService(session)

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
    ) -> tuple[Invitation | None, str, GameStatus | None]:
        """Accept an invitation and advance match lifecycle.

        Returns (invitation, error_key, new_game_status).
        - error_key is "" on success, or a text key if something is wrong.
        - new_game_status is GameStatus.FULL when the match just became full, else None.
        - For already-responded invitations, returns (invitation, error_key, None) without
          re-processing to prevent duplicate transitions or notifications.
        """
        inv = await self._repo.get_by_id(invitation_id)
        if not inv:
            return None, "inv_not_found", None
        player = await self._player_repo.get_by_telegram_id(player_telegram_id)
        if not player or player.id != inv.player_id:
            return None, "inv_not_yours", None
        if inv.status != InvitationStatus.PENDING:
            return inv, "inv_already_responded", None

        updated = await self._repo.update_status(
            invitation_id, InvitationStatus.ACCEPTED, datetime.now(UTC)
        )
        existing_gp = await self._gp_repo.get_participation(inv.game_id, inv.player_id)
        if not existing_gp:
            await self._gp_repo.add_player_to_game(
                inv.game_id, inv.player_id, GamePlayerStatus.ACCEPTED
            )

        new_game_status = await self._try_advance_lifecycle(inv.game_id)
        logger.info("Invitation %s accepted by telegram_id=%s", invitation_id, player_telegram_id)
        return updated, "", new_game_status

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

    async def _try_advance_lifecycle(self, game_id: int) -> GameStatus | None:
        """Evaluate fill state after an acceptance and advance the match lifecycle if warranted.

        Attempts up to two sequential transitions:
          OPEN → PARTIALLY_FILLED  (on any acceptance)
          PARTIALLY_FILLED → FULL  (when committed count reaches required_players)

        Side effects: may call MatchLifecycleService.transition() which writes Game.status.
        Source of truth for player count: GamePlayer rows with ACCEPTED or CONFIRMED status,
        not Invitation records.

        Returns GameStatus.FULL if the match just became full, None in all other cases.

        InvalidTransitionError from MatchLifecycleService is caught silently. It means another
        concurrent request already performed the same transition — the game is already in the
        correct state, there is nothing to recover, and no notification should be sent.
        """
        game = await self._game_repo.get_by_id(game_id)
        if not game:
            return None

        current = game.status

        # OPEN → PARTIALLY_FILLED: triggered by the first accepted invitation
        if current == GameStatus.OPEN:
            try:
                await self._lifecycle.transition(game_id, GameStatus.PARTIALLY_FILLED)
                current = GameStatus.PARTIALLY_FILLED
            except InvalidTransitionError:
                pass

        # PARTIALLY_FILLED → FULL: when committed count reaches required_players
        if current == GameStatus.PARTIALLY_FILLED:
            committed = await self._gp_repo.count_committed_players(game_id)
            if committed >= game.required_players:
                try:
                    await self._lifecycle.transition(game_id, GameStatus.FULL)
                    logger.info("Game %s is now FULL (%s/%s players)", game_id, committed, game.required_players)
                    return GameStatus.FULL
                except InvalidTransitionError:
                    pass

        return None
