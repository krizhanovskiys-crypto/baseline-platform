"""Player service — business logic for player management.

This layer is transport-agnostic: usable from Telegram bot, REST API, CLI, etc.
"""
import json
import logging
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database.models.player import Player
from backend.app.database.repositories.player_repository import PlayerRepository
from backend.app.schemas.player import PlayerCreate, PlayerRead, PlayerUpdate

logger = logging.getLogger(__name__)

AVAILABLE_NOW_DURATION_HOURS = 2


def _parse_courts(player: Player) -> list[str]:
    if not player.preferred_courts:
        return []
    try:
        return json.loads(player.preferred_courts)
    except (json.JSONDecodeError, TypeError):
        return []


def _player_to_schema(player: Player) -> PlayerRead:
    data = {
        "id": player.id,
        "telegram_id": player.telegram_id,
        "username": player.username,
        "first_name": player.first_name,
        "language": player.language,
        "skill_level": player.skill_level,
        "level_source": player.level_source,
        "home_area": player.home_area,
        "preferred_courts": _parse_courts(player),
        "available_now": player.available_now,
        "available_until": player.available_until,
        "rating": player.rating,
        "matches_played": player.matches_played,
        "is_profile_complete": player.is_profile_complete,
        "created_at": player.created_at,
        "updated_at": player.updated_at,
    }
    return PlayerRead.model_validate(data)


class PlayerService:
    """Handles all player-related use cases."""

    def __init__(self, session: AsyncSession) -> None:
        self._repo = PlayerRepository(session)

    async def get_or_create(self, data: PlayerCreate) -> tuple[PlayerRead, bool]:
        """Return (player, created) — creates player if telegram_id is new."""
        player = await self._repo.get_by_telegram_id(data.telegram_id)
        if player:
            return _player_to_schema(player), False

        player = Player(
            telegram_id=data.telegram_id,
            username=data.username,
            first_name=data.first_name,
        )
        player = await self._repo.add(player)
        logger.info("Created new player telegram_id=%s", data.telegram_id)
        return _player_to_schema(player), True

    async def get_by_telegram_id(self, telegram_id: int) -> PlayerRead | None:
        """Return player schema or None."""
        player = await self._repo.get_by_telegram_id(telegram_id)
        return _player_to_schema(player) if player else None

    async def get_by_id(self, player_id: int) -> PlayerRead | None:
        player = await self._repo.get_by_id(player_id)
        return _player_to_schema(player) if player else None

    async def update_profile(self, telegram_id: int, data: PlayerUpdate) -> PlayerRead | None:
        """Update player profile fields.  Returns updated schema or None if not found."""
        player = await self._repo.get_by_telegram_id(telegram_id)
        if not player:
            return None

        update_dict = data.model_dump(exclude_unset=True)
        if "preferred_courts" in update_dict and update_dict["preferred_courts"] is not None:
            update_dict["preferred_courts"] = json.dumps(update_dict["preferred_courts"])
        if "skill_level" in update_dict and update_dict["skill_level"] is not None:
            if not update_dict.get("level_source") and player.level_source is None:
                update_dict["level_source"] = "self_rated"

        for field, value in update_dict.items():
            setattr(player, field, value)

        await self._repo._session.flush()
        await self._repo._session.refresh(player)
        logger.info("Updated profile for telegram_id=%s fields=%s", telegram_id, list(update_dict))
        return _player_to_schema(player)

    async def find_partners(
        self,
        telegram_id: int,
        area: str,
        skill_level: float,
        my_courts: list[str] | None = None,
        level_tolerance: float = 0.5,
    ) -> list[PlayerRead]:
        """Find and rank compatible partners.

        Sort order:
          1. Shared favourite courts (descending)
          2. Absolute skill difference (ascending)
          3. Most recently active (descending)
        """
        players = await self._repo.find_partners(
            area=area,
            skill_level=skill_level,
            exclude_telegram_id=telegram_id,
            level_tolerance=level_tolerance,
        )
        partners = [_player_to_schema(p) for p in players]

        my_courts_set = set(my_courts or [])
        partners.sort(
            key=lambda p: (
                -len(my_courts_set & set(p.preferred_courts or [])),
                abs((p.skill_level or 0.0) - skill_level),
                -(p.updated_at.timestamp() if p.updated_at else 0),
            )
        )
        return partners

    async def set_available_now(self, telegram_id: int) -> PlayerRead | None:
        """Mark player as available for the next 2 hours."""
        player = await self._repo.get_by_telegram_id(telegram_id)
        if not player:
            return None
        available_until = datetime.utcnow() + timedelta(hours=AVAILABLE_NOW_DURATION_HOURS)
        await self._repo.set_available(player.id, available_until)
        await self._repo._session.refresh(player)
        logger.info("Player telegram_id=%s set available until %s", telegram_id, available_until)
        return _player_to_schema(player)

    async def get_available_now(self) -> list[PlayerRead]:
        """Return all currently-available players."""
        players = await self._repo.get_available_now()
        return [_player_to_schema(p) for p in players]

    async def list_all(self) -> list[PlayerRead]:
        players = await self._repo.get_all()
        return [_player_to_schema(p) for p in players]
