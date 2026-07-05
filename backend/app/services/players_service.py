"""Admin Center — Players business logic.

Handlers never query PlayerRepository directly; every Players-module
lookup, page, or search goes through this service. Reuses
PlayerRepository (no duplicated queries) and `_player_to_schema()` from
player_service.py — the only sanctioned way to turn a Player ORM row
into a PlayerRead (ARCHITECTURE.md's own convention; game_service.py
already imports the same function for the same reason).
"""
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database.repositories.player_repository import PlayerRepository
from backend.app.schemas.player import PlayerRead
from backend.app.services.player_service import _player_to_schema

PAGE_SIZE = 20


class PlayersService:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = PlayerRepository(session)

    async def count_all(self) -> int:
        return await self._repo.count_all()

    async def get_page(self, page: int) -> tuple[list[PlayerRead], int]:
        """1-indexed page of players, ordered by id. Returns (players, total)."""
        total = await self._repo.count_all()
        offset = (page - 1) * PAGE_SIZE
        players = await self._repo.get_paginated(offset, PAGE_SIZE)
        return [_player_to_schema(p) for p in players], total

    async def get_by_id(self, player_id: int) -> PlayerRead | None:
        player = await self._repo.get_by_id(player_id)
        return _player_to_schema(player) if player else None

    async def search(self, query: str) -> list[PlayerRead]:
        """Search by Telegram ID (exact), or first name / username
        (case-insensitive substring). A leading '@' on the query is
        stripped, matching how usernames are entered without one."""
        query = query.strip()
        if not query:
            return []

        if query.lstrip("-").isdigit():
            player = await self._repo.get_by_telegram_id(int(query))
            return [_player_to_schema(player)] if player else []

        players = await self._repo.search_by_name_or_username(query.lstrip("@"))
        return [_player_to_schema(p) for p in players]

    async def set_verified_coach(self, player_id: int, value: bool) -> PlayerRead | None:
        """Grant (True) or revoke (False) the Verified Coach badge."""
        await self._repo.set_verified_coach(player_id, value)
        return await self.get_by_id(player_id)
