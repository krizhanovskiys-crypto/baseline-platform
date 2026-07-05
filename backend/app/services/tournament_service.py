"""Tournament service — business logic for Tournament Platform v1
(Sprint 12, Phase 1).

Transport-agnostic like every other service: it never touches Bot or
sends Telegram messages itself. The Registration Closed Notification is
sent by a handler-layer helper (bot/handlers/tournament_helpers.py)
right after any of the three triggers below successfully closes
registration — this method only ever returns whether a close just
happened, so the caller can decide to notify.

Tournament matches are NOT a new entity — generate_matches() creates
ordinary Game rows via the existing GameService.create_game(), tagged
with tournament_id. No new match or invitation architecture.
"""
import logging
import random
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.exceptions import InvalidTournamentTransitionError
from backend.app.database.models.game import GamePlayerStatus
from backend.app.database.models.tournament import Tournament, TournamentPlayerStatus, TournamentStatus
from backend.app.database.repositories.game_repository import GamePlayerRepository, GameRepository
from backend.app.database.repositories.player_repository import PlayerRepository
from backend.app.database.repositories.tournament_repository import (
    TournamentPlayerRepository,
    TournamentRepository,
)
from backend.app.schemas.game import GameCreate
from backend.app.schemas.tournament import TournamentCreate, TournamentPlayerRead, TournamentRead, TournamentUpdate
from backend.app.services.admin_session_service import AdminSessionService
from backend.app.services.game_service import GameService
from backend.app.services.tournament_lifecycle_service import TournamentLifecycleService

logger = logging.getLogger(__name__)

PAGE_SIZE = 20


def _tournament_to_schema(tournament) -> TournamentRead:
    return TournamentRead.model_validate(tournament)


def _registration_to_schema(tp, player) -> TournamentPlayerRead:
    return TournamentPlayerRead(
        player_id=player.id,
        first_name=player.first_name,
        telegram_id=player.telegram_id,
        language=player.language,
        status=tp.status,
        registered_at=tp.registered_at,
    )


class TournamentService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = TournamentRepository(session)
        self._tp_repo = TournamentPlayerRepository(session)
        self._player_repo = PlayerRepository(session)
        self._game_repo = GameRepository(session)
        self._gp_repo = GamePlayerRepository(session)
        self._lifecycle = TournamentLifecycleService(session)

    # ── Permission ────────────────────────────────────────────────────────
    # Two separate, centralized methods — kept apart deliberately, not
    # merged, since they answer different questions and will diverge
    # further once a Tournament Organizer permission exists: creating a
    # tournament vs. managing one you don't necessarily own are not the
    # same check.

    async def can_create_tournament(self, telegram_id: int) -> bool:
        """Gates Tournament Center access, Create Tournament, and
        Browse (browsing lists every tournament regardless of
        ownership). Admin (active PIN session) or Verified Coach today.
        Adding a future Tournament Organizer permission means editing
        only this method's body."""
        if await AdminSessionService(self._session).validate_session(telegram_id) is not None:
            return True
        player = await self._player_repo.get_by_telegram_id(telegram_id)
        return bool(player and player.is_verified_coach)

    async def can_manage_tournament(self, telegram_id: int, organizer_player_id: int) -> bool:
        """Ownership-aware — gates every action on one specific,
        existing tournament (Edit, Open/Close Registration, View/Add/
        Remove Players, Generate Matches, Delete). Admin manages any
        tournament; Verified Coach manages only tournaments they
        organized themselves."""
        if await AdminSessionService(self._session).validate_session(telegram_id) is not None:
            return True
        player = await self._player_repo.get_by_telegram_id(telegram_id)
        if not player or not player.is_verified_coach:
            return False
        return player.id == organizer_player_id

    # ── Create / Edit ─────────────────────────────────────────────────────

    async def create_tournament(
        self, organizer_telegram_id: int, data: TournamentCreate
    ) -> TournamentRead | None:
        """Returns None if the organizer has no Player row — mirrors
        GameService.create_game()'s existing defensive behaviour."""
        organizer = await self._player_repo.get_by_telegram_id(organizer_telegram_id)
        if not organizer:
            logger.warning("create_tournament called for unknown telegram_id=%s", organizer_telegram_id)
            return None

        tournament = Tournament(
            name=data.name,
            description=data.description,
            organizer_player_id=organizer.id,
            area=data.area,
            court=data.court,
            start_date=data.start_date,
            start_time=data.start_time,
            registration_deadline=data.registration_deadline,
            max_players=data.max_players,
            status=TournamentStatus.DRAFT,
        )
        tournament = await self._repo.add(tournament)
        return _tournament_to_schema(tournament)

    async def edit_tournament(self, tournament_id: int, data: TournamentUpdate) -> TournamentRead | None:
        values = data.model_dump(exclude_unset=True, exclude_none=True)
        updated = await self._repo.update_fields(tournament_id, values)
        return _tournament_to_schema(updated) if updated else None

    async def get_tournament(self, tournament_id: int) -> TournamentRead | None:
        tournament = await self._repo.get_by_id(tournament_id)
        return _tournament_to_schema(tournament) if tournament else None

    async def list_tournaments(self, page: int) -> tuple[list[TournamentRead], int]:
        total = await self._repo.count_all()
        offset = (page - 1) * PAGE_SIZE
        tournaments = await self._repo.get_paginated(offset, PAGE_SIZE)
        return [_tournament_to_schema(t) for t in tournaments], total

    async def list_my_tournaments(self, organizer_telegram_id: int, page: int) -> tuple[list[TournamentRead], int]:
        """My Tournaments (Sprint 12.2) — only tournaments organized by
        this specific account, unlike list_tournaments() which lists
        every visible tournament regardless of ownership."""
        organizer = await self._player_repo.get_by_telegram_id(organizer_telegram_id)
        if not organizer:
            return [], 0
        total = await self._repo.count_by_organizer(organizer.id)
        offset = (page - 1) * PAGE_SIZE
        tournaments = await self._repo.get_paginated_by_organizer(organizer.id, offset, PAGE_SIZE)
        return [_tournament_to_schema(t) for t in tournaments], total

    async def delete_tournament(self, tournament_id: int) -> bool:
        tournament = await self._repo.get_by_id(tournament_id)
        if tournament is None:
            return False
        await self._repo.delete(tournament)
        return True

    # ── Lifecycle ─────────────────────────────────────────────────────────

    async def open_registration(self, tournament_id: int) -> TournamentRead:
        return await self._lifecycle.transition(tournament_id, TournamentStatus.REGISTRATION_OPEN)

    async def close_registration(self, tournament_id: int) -> TournamentRead:
        """Pure status transition — no notification here. The caller
        (handler layer) sends the Registration Closed Notification right
        after this succeeds."""
        return await self._lifecycle.transition(tournament_id, TournamentStatus.REGISTRATION_CLOSED)

    async def check_and_auto_close(self, tournament_id: int) -> bool:
        """Lazy check mirroring GameService._expire_stale's read-time
        pattern: closes registration if the deadline has passed or
        max_players is reached. Call before displaying/registering.
        Returns True if this call just closed registration (so the
        caller knows to send the Registration Closed Notification)."""
        tournament = await self._repo.get_by_id(tournament_id)
        if tournament is None or tournament.status != TournamentStatus.REGISTRATION_OPEN:
            return False

        deadline_passed = date.today() > tournament.registration_deadline
        count = await self._tp_repo.count_registered(tournament_id)
        max_reached = count >= tournament.max_players

        if not (deadline_passed or max_reached):
            return False

        try:
            await self.close_registration(tournament_id)
        except InvalidTournamentTransitionError:
            return False
        return True

    # ── Registration ──────────────────────────────────────────────────────

    async def register_player(self, tournament_id: int, telegram_id: int) -> tuple[bool, bool]:
        """Returns (registered, just_closed). registered is False if the
        tournament isn't open for registration or the player is already
        registered. just_closed is True if this registration pushed the
        tournament to max_players and auto-closed it."""
        tournament = await self._repo.get_by_id(tournament_id)
        if tournament is None or tournament.status != TournamentStatus.REGISTRATION_OPEN:
            return False, False

        player = await self._player_repo.get_by_telegram_id(telegram_id)
        if not player:
            return False, False

        existing = await self._tp_repo.get_registration(tournament_id, player.id)
        if existing and existing.status == TournamentPlayerStatus.REGISTERED:
            return False, False

        if existing:
            await self._tp_repo.set_status(tournament_id, player.id, TournamentPlayerStatus.REGISTERED)
        else:
            await self._tp_repo.add_registration(tournament_id, player.id)

        just_closed = await self.check_and_auto_close(tournament_id)
        return True, just_closed

    async def withdraw_player(self, tournament_id: int, telegram_id: int) -> bool:
        tournament = await self._repo.get_by_id(tournament_id)
        if tournament is None or tournament.status != TournamentStatus.REGISTRATION_OPEN:
            return False
        player = await self._player_repo.get_by_telegram_id(telegram_id)
        if not player:
            return False
        registration = await self._tp_repo.get_registration(tournament_id, player.id)
        if not registration or registration.status != TournamentPlayerStatus.REGISTERED:
            return False
        await self._tp_repo.set_status(tournament_id, player.id, TournamentPlayerStatus.WITHDRAWN)
        return True

    async def get_registered_players(self, tournament_id: int) -> list[TournamentPlayerRead]:
        registrations = await self._tp_repo.get_registrations_with_players(tournament_id)
        return [_registration_to_schema(tp, tp.player) for tp in registrations]

    async def count_registered(self, tournament_id: int) -> int:
        return await self._tp_repo.count_registered(tournament_id)

    # ── Admin Player Management (Add/Remove — reuses register/withdraw) ──

    async def admin_add_player(self, tournament_id: int, player_telegram_id: int) -> bool:
        registered, _ = await self.register_player(tournament_id, player_telegram_id)
        return registered

    async def admin_remove_player(self, tournament_id: int, player_telegram_id: int) -> bool:
        return await self.withdraw_player(tournament_id, player_telegram_id)

    # ── Generate Matches ──────────────────────────────────────────────────

    async def generate_matches(self, tournament_id: int) -> tuple[bool, str]:
        """Shuffle registered players, pair sequentially, create ordinary
        Games via GameService.create_game() tagged with tournament_id.
        Every generated Game belongs to the Tournament Organizer
        (tournament.organizer_player_id), never to either pair player.

        Returns (success, error_key). error_key is one of:
        "tournament_generate_wrong_status", "tournament_generate_odd_players",
        "tournament_generate_already_done", or "" on success.
        """
        tournament = await self._repo.get_by_id(tournament_id)
        if tournament is None or tournament.status != TournamentStatus.REGISTRATION_CLOSED:
            return False, "tournament_generate_wrong_status"

        existing_games = await self._game_repo.get_games_by_tournament(tournament_id)
        if existing_games:
            return False, "tournament_generate_already_done"

        players = await self._tp_repo.get_registered_players(tournament_id)
        if len(players) % 2 != 0 or len(players) == 0:
            return False, "tournament_generate_odd_players"

        shuffled = list(players)
        random.shuffle(shuffled)

        organizer = await self._player_repo.get_by_id(tournament.organizer_player_id)
        if not organizer:
            return False, "tournament_generate_wrong_status"

        game_service = GameService(self._session)
        for i in range(0, len(shuffled), 2):
            player_a, player_b = shuffled[i], shuffled[i + 1]
            # The Game always belongs to the Tournament Organizer, never
            # to either pair player — auto_join_creator=False so the
            # organizer (who may not be playing this specific match)
            # isn't added as a participant; both pair players are added
            # explicitly below instead.
            game = await game_service.create_game(
                creator_telegram_id=organizer.telegram_id,
                data=GameCreate(
                    court=tournament.court,
                    area=tournament.area,
                    date=tournament.start_date,
                    time=tournament.start_time,
                    tournament_id=tournament.id,
                ),
                auto_join_creator=False,
            )
            if game:
                await self._gp_repo.add_player_to_game(
                    game_id=game.id, player_id=player_a.id, status=GamePlayerStatus.CONFIRMED
                )
                await self._gp_repo.add_player_to_game(
                    game_id=game.id, player_id=player_b.id, status=GamePlayerStatus.CONFIRMED
                )

        await self._lifecycle.transition(tournament_id, TournamentStatus.IN_PROGRESS)
        logger.info("Generated matches for tournament_id=%s (%d players)", tournament_id, len(players))
        return True, ""

    async def mark_completed(self, tournament_id: int) -> TournamentRead:
        return await self._lifecycle.transition(tournament_id, TournamentStatus.COMPLETED)
