"""Release Announcement service (Sprint 13.1) — business logic for
"has this player seen the current version's announcement yet."

Transport-agnostic like every other service: no Bot, no message
rendering. This is the one place that decides whether to show the
announcement — bot/handlers/release_announcement.py and the
middleware both call into this, never re-implementing the comparison
themselves.
"""
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.version import APP_VERSION
from backend.app.data.release_announcements import Release, get_current_release
from backend.app.database.repositories.player_repository import PlayerRepository


class ReleaseAnnouncementService:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = PlayerRepository(session)

    async def should_show_announcement(self, telegram_id: int) -> bool:
        """The one comparison in the whole system: has this player
        already seen APP_VERSION's announcement? A player who doesn't
        exist yet, hasn't completed onboarding, or has already seen
        this exact version never sees it (again)."""
        player = await self._repo.get_by_telegram_id(telegram_id)
        if player is None or not player.is_profile_complete:
            return False
        if get_current_release() is None:
            # APP_VERSION was bumped without a matching Release entry —
            # nothing to announce, not an error.
            return False
        return player.last_seen_version != APP_VERSION

    async def mark_seen(self, telegram_id: int) -> None:
        await self._repo.set_last_seen_version(telegram_id, APP_VERSION)

    def get_current_release(self) -> Release | None:
        return get_current_release()
