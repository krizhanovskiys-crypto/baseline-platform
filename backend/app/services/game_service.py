"""Game service — business logic for game management."""
import logging
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.exceptions import InvalidTransitionError
from backend.app.database.models.game import Game, GamePlayerStatus, GameStatus, MatchType
from backend.app.database.repositories.game_repository import GamePlayerRepository, GameRepository
from backend.app.database.repositories.player_repository import PlayerRepository
from backend.app.insights.service import AnalyticsService
from backend.app.schemas.game import GameCreate, GameRead, MatchDetails, PlayerSummary
from backend.app.schemas.player import PlayerRead
from backend.app.services.player_service import _player_to_schema as _player_to_read

logger = logging.getLogger(__name__)


def _game_to_schema(game: Game) -> GameRead:
    return GameRead.model_validate(game)


class GameService:
    """Handles all game-related use cases."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._game_repo = GameRepository(session)
        self._gp_repo = GamePlayerRepository(session)
        self._player_repo = PlayerRepository(session)
        self._analytics = AnalyticsService(session)

    async def create_game(
        self, creator_telegram_id: int, data: GameCreate, auto_join_creator: bool = True
    ) -> GameRead | None:
        """Create a new game.  Returns None if creator player not found.

        auto_join_creator=False skips adding the creator as a CONFIRMED
        participant — used by TournamentService.generate_matches(),
        where the Game's creator_id must be the Tournament Organizer
        (ownership), but the organizer isn't necessarily one of the two
        players actually playing that specific match.
        """
        creator = await self._player_repo.get_by_telegram_id(creator_telegram_id)
        if not creator:
            logger.warning("create_game called for unknown telegram_id=%s", creator_telegram_id)
            return None

        game = Game(
            creator_id=creator.id,
            tournament_id=data.tournament_id,
            court=data.court,
            area=data.area,
            date=data.date,
            time=data.time,
            match_type=data.match_type,
            required_level=data.required_level,
            status=GameStatus.DRAFT,
        )
        game = await self._game_repo.add(game)

        if auto_join_creator:
            await self._gp_repo.add_player_to_game(
                game_id=game.id,
                player_id=creator.id,
                status=GamePlayerStatus.CONFIRMED,
            )

        # A created match must be immediately visible/joinable — DRAFT is a
        # construction-only state. This is the single point that opens every
        # match regardless of caller (bot wizard, REST API, future callers),
        # so no caller can forget the transition and leave a match invisible.
        from backend.app.services.match_lifecycle_service import MatchLifecycleService

        opened = await MatchLifecycleService(self._session).transition(game.id, GameStatus.OPEN)

        logger.info(
            "Game created id=%s by telegram_id=%s area=%s", game.id, creator_telegram_id, game.area
        )
        await self._analytics.track_event(creator.id, "game_created", {"game_id": game.id})
        return opened

    async def get_open_games(self, area: str | None = None) -> list[GameRead]:
        """Return all open games, optionally filtered by area."""
        games = await self._game_repo.get_open_games(area=area)
        return [_game_to_schema(g) for g in games]

    async def get_available_matches(
        self,
        player_telegram_id: int,
        *,
        area: str | None = None,
        on_date: date | None = None,
        match_type: MatchType | None = None,
        apply_level_filter: bool = True,
        page: int = 1,
        page_size: int = 5,
    ) -> tuple[list[tuple[GameRead, int]], int]:
        """Return (game, committed_player_count) pairs the player can join, plus total count.

        area/on_date/match_type are optional hard filters (None = no restriction).
        apply_level_filter toggles the default skill_level ±0.5 NTRP filter.
        Excludes games created by the player and games they already joined.
        """
        await self._expire_stale()
        player = await self._player_repo.get_by_telegram_id(player_telegram_id)
        if not player:
            return [], 0

        games, total = await self._game_repo.get_available_matches(
            player_id=player.id,
            home_area=player.home_area,
            skill_level=player.skill_level,
            area=area,
            on_date=on_date,
            match_type=match_type,
            level=player.skill_level if apply_level_filter else None,
            page=page,
            page_size=page_size,
        )
        result = []
        for game in games:
            count = await self._gp_repo.count_committed_players(game.id)
            result.append((_game_to_schema(game), count))
        return result, total

    async def join_match(
        self, game_id: int, player_telegram_id: int
    ) -> tuple[GameRead | None, str]:
        """Join an OPEN/PARTIALLY_FILLED match as a committed participant.

        Returns (updated_game, "") on success, (None, error_key) on failure.

        Error keys:
          match_not_found            — game or player does not exist
          join_match_not_allowed     — game status does not allow joining
          join_match_organizer       — organizer cannot join their own match
          join_match_already_joined  — player already has a committed row
          match_already_full         — race lost: another join filled the last slot first
        """
        from backend.app.services.match_lifecycle_service import MatchLifecycleService

        _joinable = {GameStatus.OPEN, GameStatus.PARTIALLY_FILLED}

        await self._expire_stale(game_id)
        game = await self._game_repo.get_by_id(game_id)
        if not game:
            return None, "match_not_found"
        if game.status not in _joinable:
            return None, "join_match_not_allowed"

        player = await self._player_repo.get_by_telegram_id(player_telegram_id)
        if not player:
            return None, "match_not_found"
        if player.id == game.creator_id:
            return None, "join_match_organizer"

        existing = await self._gp_repo.get_participation(game_id, player.id)
        if existing and existing.status in (GamePlayerStatus.ACCEPTED, GamePlayerStatus.CONFIRMED):
            return None, "join_match_already_joined"

        previous_status = existing.status if existing else None
        if existing:
            existing.status = GamePlayerStatus.ACCEPTED
        else:
            await self._gp_repo.add_player_to_game(game_id, player.id, GamePlayerStatus.ACCEPTED)

        # Race-condition check: re-validate after the write. If this join pushed
        # the match over capacity, another concurrent join got there first — undo.
        committed = await self._gp_repo.count_committed_players(game_id)
        if committed > game.required_players:
            if previous_status is not None:
                existing.status = previous_status
            else:
                await self._gp_repo.remove_player_from_game(game_id, player.id)
            return None, "match_already_full"

        # Sequential advancement, mirroring InvitationService._try_advance_lifecycle:
        # OPEN -> PARTIALLY_FILLED first, then PARTIALLY_FILLED -> FULL if capacity is reached.
        # A single join can cross both steps (e.g. singles filling on the first join).
        lifecycle = MatchLifecycleService(self._session)
        current_status = game.status
        updated = _game_to_schema(game)
        if current_status == GameStatus.OPEN:
            try:
                updated = await lifecycle.transition(game_id, GameStatus.PARTIALLY_FILLED)
                current_status = GameStatus.PARTIALLY_FILLED
            except InvalidTransitionError:
                pass
        if current_status == GameStatus.PARTIALLY_FILLED and committed >= game.required_players:
            try:
                updated = await lifecycle.transition(game_id, GameStatus.FULL)
            except InvalidTransitionError:
                pass

        logger.info("Player telegram_id=%s joined game %s", player_telegram_id, game_id)
        return updated, ""

    async def get_game(self, game_id: int) -> GameRead | None:
        game = await self._game_repo.get_by_id(game_id)
        return _game_to_schema(game) if game else None

    async def list_all(self) -> list[GameRead]:
        games = await self._game_repo.get_all()
        return [_game_to_schema(g) for g in games]

    async def get_my_matches(self, telegram_id: int) -> list[GameRead]:
        """Return all games created by this player, ordered by creation time."""
        player = await self._player_repo.get_by_telegram_id(telegram_id)
        if not player:
            return []
        games = await self._game_repo.get_games_by_creator(player.id)
        return [_game_to_schema(g) for g in games]

    async def get_games_by_tournament(self, tournament_id: int) -> list[GameRead]:
        """Return every Game generated for this tournament. Read-only
        pass-through — TournamentService already owns tournament
        orchestration; this exposes the existing repository query
        through GameService for callers (the Telegram Tournament
        Dashboard, Sprint 16) that only need Game data, not tournament
        business logic."""
        games = await self._game_repo.get_games_by_tournament(tournament_id)
        return [_game_to_schema(g) for g in games]

    async def _expire_stale(self, game_id: int | None = None) -> None:
        """Lazily expire pre-start matches whose scheduled datetime has passed.

        If game_id is given, checks only that game. Otherwise checks all pre-start games.
        Called at the entry point of any service method that reads or acts on match state.
        """
        from backend.app.services.match_lifecycle_service import MatchLifecycleService

        lc = MatchLifecycleService(self._session)
        if game_id is not None:
            await lc.expire_if_stale(game_id)
            return
        for game in await self._game_repo.get_expirable_matches():
            await lc.expire_if_stale(game.id)

    async def find_players_for_match(
        self, game_id: int, organizer_telegram_id: int
    ) -> list[PlayerRead]:
        """Return candidate players who qualify for this match.

        Excludes the organizer and any existing participants.
        Filters by same area and skill level ±0.5.
        """
        await self._expire_stale(game_id)
        game = await self._game_repo.get_by_id(game_id)
        if not game or game.status not in {GameStatus.OPEN, GameStatus.PARTIALLY_FILLED}:
            return []
        organizer = await self._player_repo.get_by_telegram_id(organizer_telegram_id)
        if not organizer:
            return []
        participant_ids = await self._gp_repo.get_participant_player_ids(game_id)
        exclude_ids = set(participant_ids) | {organizer.id}
        level = float(game.required_level) if game.required_level is not None else 3.0
        candidates = await self._player_repo.find_players_for_match(
            area=game.area,
            level=level,
            exclude_player_ids=exclude_ids,
        )
        return [_player_to_read(p) for p in candidates]

    async def get_match_details(self, game_id: int) -> MatchDetails | None:
        """Return assembled match details for rendering. None if the game does not exist.

        The organizer is always present in committed players (joined with CONFIRMED status
        on game creation), so organizer_name is derived from the player list — no extra query.
        """
        await self._expire_stale(game_id)
        game = await self._game_repo.get_by_id(game_id)
        if not game:
            return None
        committed = await self._gp_repo.get_committed_players(game.id)
        players = [
            PlayerSummary(
                player_id=p.id,
                name=p.first_name,
                telegram_id=p.telegram_id,
                is_organizer=(p.id == game.creator_id),
            )
            for p in committed
        ]
        organizer_name = next((p.name for p in players if p.is_organizer), "—")
        return MatchDetails(
            game=_game_to_schema(game),
            organizer_name=organizer_name,
            players=players,
            committed_count=len(players),
        )

    async def get_my_upcoming_matches(
        self, telegram_id: int
    ) -> list[tuple[GameRead, int]]:
        """Return (game, committed_player_count) for all upcoming matches the player participates in.

        Includes matches where the player is organizer (CONFIRMED GamePlayer status) or
        accepted invitee (ACCEPTED GamePlayer status). Sorted by date/time ascending.
        """
        player = await self._player_repo.get_by_telegram_id(telegram_id)
        if not player:
            return []
        await self._expire_stale()
        games = await self._game_repo.get_upcoming_matches_for_player(player.id)
        result = []
        for game in games:
            count = await self._gp_repo.count_committed_players(game.id)
            result.append((_game_to_schema(game), count))
        return result

    async def confirm_match(
        self, game_id: int, organizer_telegram_id: int
    ) -> tuple[GameRead | None, list[PlayerRead], str]:
        """Transition a FULL match to CONFIRMED and return the committed player roster.

        Returns (updated_game, all_committed_players, error_key).
        all_committed_players includes the organizer — the handler decides who to notify.
        error_key is "" on success.
        """
        from backend.app.services.match_lifecycle_service import MatchLifecycleService

        await self._expire_stale(game_id)
        game = await self._game_repo.get_by_id(game_id)
        if not game:
            return None, [], "confirm_match_not_found"

        organizer = await self._player_repo.get_by_telegram_id(organizer_telegram_id)
        if not organizer or organizer.id != game.creator_id:
            return None, [], "confirm_match_not_yours"

        if game.status != GameStatus.FULL:
            return None, [], "confirm_match_wrong_status"

        try:
            updated = await MatchLifecycleService(self._session).transition(game_id, GameStatus.CONFIRMED)
        except InvalidTransitionError:
            return None, [], "confirm_match_wrong_status"

        committed = await self._gp_repo.get_committed_players(game_id)
        return updated, [_player_to_read(p) for p in committed], ""

    async def cancel_match(
        self, game_id: int, organizer_telegram_id: int
    ) -> tuple[GameRead | None, str]:
        """Cancel a match at any cancellable status.

        Returns (updated_game, "") on success, (None, error_key) on failure.
        """
        from backend.app.services.match_lifecycle_service import MatchLifecycleService

        await self._expire_stale(game_id)
        game = await self._game_repo.get_by_id(game_id)
        if not game:
            return None, "cancel_match_not_found"

        organizer = await self._player_repo.get_by_telegram_id(organizer_telegram_id)
        if not organizer or organizer.id != game.creator_id:
            return None, "cancel_match_not_yours"

        try:
            updated = await MatchLifecycleService(self._session).transition(game_id, GameStatus.CANCELLED)
        except InvalidTransitionError:
            return None, "cancel_match_not_cancellable"

        return updated, ""

    async def leave_match(
        self, game_id: int, player_telegram_id: int
    ) -> tuple[GameRead | None, str]:
        """Remove a committed participant from a match and apply the reverse lifecycle transition.

        Returns (updated_game, "") on success, (None, error_key) on failure.

        Error keys:
          leave_match_not_allowed      — game not found or status does not allow leaving
          leave_match_organizer        — organizer cannot leave; must cancel instead
          leave_match_not_participant  — player has no committed row in this game
        """
        from backend.app.services.match_lifecycle_service import MatchLifecycleService

        _leavable = {GameStatus.OPEN, GameStatus.PARTIALLY_FILLED, GameStatus.FULL, GameStatus.CONFIRMED}

        game = await self._game_repo.get_by_id(game_id)
        if not game or game.status not in _leavable:
            return None, "leave_match_not_allowed"

        player = await self._player_repo.get_by_telegram_id(player_telegram_id)
        if not player:
            return None, "leave_match_not_participant"

        if player.id == game.creator_id:
            return None, "leave_match_organizer"

        gp = await self._gp_repo.get_participation(game_id, player.id)
        if gp is None or gp.status != GamePlayerStatus.ACCEPTED:
            return None, "leave_match_not_participant"

        await self._gp_repo.remove_player_from_game(game_id, player.id)

        new_count = await self._gp_repo.count_committed_players(game_id)
        target = GameStatus.OPEN if new_count <= 1 else GameStatus.PARTIALLY_FILLED

        try:
            updated = await MatchLifecycleService(self._session).transition(game_id, target)
        except InvalidTransitionError:
            updated = _game_to_schema(game)

        return updated, ""

    async def get_roster(self, game_id: int) -> tuple[GameRead | None, list[PlayerRead]]:
        """Return game details and committed player roster for display."""
        game = await self._game_repo.get_by_id(game_id)
        if not game:
            return None, []
        committed = await self._gp_repo.get_committed_players(game_id)
        return _game_to_schema(game), [_player_to_read(p) for p in committed]

    async def invite_player(
        self, game_id: int, invitee_telegram_id: int
    ) -> bool:
        """Invite a player to a game.  Returns False if already participating."""
        invitee = await self._player_repo.get_by_telegram_id(invitee_telegram_id)
        if not invitee:
            return False
        existing = await self._gp_repo.get_participation(game_id, invitee.id)
        if existing:
            return False
        await self._gp_repo.add_player_to_game(
            game_id=game_id,
            player_id=invitee.id,
            status=GamePlayerStatus.INVITED,
        )
        return True
