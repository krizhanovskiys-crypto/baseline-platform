"""Developer service — internal testing and inspection utilities."""
import json
import logging
from datetime import datetime

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database.models.game import Game
from backend.app.database.models.player import Player
from backend.app.database.repositories.player_repository import PlayerRepository

logger = logging.getLogger(__name__)

_TEST_PREFIX = "_test_"
_TEST_TELEGRAM_ID_BASE = 9_000_000_000

_TEST_PLAYERS = [
    {"first_name": "Test Alice", "username": "_test_alice", "skill_level": 3.0, "home_area": "Downtown",   "courts": ["Ramsden Park", "Withrow Park"]},
    {"first_name": "Test Bob",   "username": "_test_bob",   "skill_level": 3.5, "home_area": "Downtown",   "courts": ["Ramsden Park"]},
    {"first_name": "Test Carol", "username": "_test_carol", "skill_level": 4.0, "home_area": "North York", "courts": ["Oriole Park"]},
    {"first_name": "Test Dave",  "username": "_test_dave",  "skill_level": 3.5, "home_area": "West Toronto / Etobicoke", "courts": ["High Park Bubble"]},
    {"first_name": "Test Eve",   "username": "_test_eve",   "skill_level": 4.5, "home_area": "Mississauga","courts": ["Mississauga Valley Park"]},
]


class DevService:
    """Internal utilities for development and testing. Never expose to end-users."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._player_repo = PlayerRepository(session)

    async def get_stats(self) -> dict[str, int]:
        """Return basic counts from the live database."""
        total_players = await self._session.scalar(
            select(func.count()).select_from(Player)
        ) or 0

        complete_players = await self._session.scalar(
            select(func.count()).select_from(Player).where(
                and_(
                    Player.language.is_not(None),
                    Player.skill_level.is_not(None),
                    Player.home_area.is_not(None),
                    Player.preferred_courts.is_not(None),
                )
            )
        ) or 0

        total_games = await self._session.scalar(
            select(func.count()).select_from(Game)
        ) or 0

        available_now = await self._session.scalar(
            select(func.count()).select_from(Player).where(
                and_(
                    Player.available_now == True,  # noqa: E712
                    Player.available_until > datetime.utcnow(),
                )
            )
        ) or 0

        return {
            "players": int(total_players),
            "complete": int(complete_players),
            "games": int(total_games),
            "available": int(available_now),
        }

    async def create_test_players(self) -> int:
        """Seed test players. Skips entries that already exist. Returns count created."""
        created = 0
        for i, data in enumerate(_TEST_PLAYERS):
            tid = _TEST_TELEGRAM_ID_BASE + i
            if await self._player_repo.get_by_telegram_id(tid):
                continue
            player = Player(
                telegram_id=tid,
                first_name=data["first_name"],
                username=data["username"],
                language="en",
                skill_level=data["skill_level"],
                home_area=data["home_area"],
                preferred_courts=json.dumps(data["courts"]),
                level_source="self_rated",
            )
            await self._player_repo.add(player)
            created += 1
        logger.info("Dev: created %d test players", created)
        return created

    async def reset_test_data(self) -> int:
        """Delete all test players (username prefix '_test_'). Returns count deleted."""
        all_players = await self._player_repo.get_all()
        test_players = [p for p in all_players if p.username and p.username.startswith(_TEST_PREFIX)]
        for p in test_players:
            await self._session.delete(p)
        await self._session.flush()
        logger.info("Dev: deleted %d test players", len(test_players))
        return len(test_players)
