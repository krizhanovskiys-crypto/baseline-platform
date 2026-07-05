"""Regression tests for Sprint 13.1 — Release Announcements.

Covers the service (the one place that decides whether to show the
announcement), the presenter (both screens, all three languages), and
end-to-end middleware interception through the real dispatcher.
"""
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
from aiogram import Bot
from aiogram.types import CallbackQuery, Chat, Message, Update, User
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.bot.main import build_dispatcher
from backend.app.bot.presenters.release_announcement import build_announcement_view, build_whats_new_view
from backend.app.core.version import APP_VERSION
from backend.app.data.release_announcements import Release, ReleaseChange, display_version, get_current_release
from backend.app.schemas.player import PlayerCreate, PlayerUpdate
from backend.app.services.player_service import PlayerService
from backend.app.services.release_announcement_service import ReleaseAnnouncementService

_TEST_RELEASE = Release(
    version=APP_VERSION,
    title="Player Platform",
    changes=[
        ReleaseChange(emoji="🏆", label="Coach Tournament Management"),
        ReleaseChange(emoji="👥", label="Improved Player Cards"),
    ],
)


async def _make_complete_player(session: AsyncSession, telegram_id: int, name: str = "Player") -> None:
    svc = PlayerService(session)
    await svc.get_or_create(PlayerCreate(telegram_id=telegram_id, first_name=name))
    await svc.update_profile(
        telegram_id, PlayerUpdate(language="en", skill_level=3.5, home_area="Downtown", preferred_courts=[])
    )
    await session.commit()


# ---------------------------------------------------------------------------
# ReleaseAnnouncementService — the one comparison
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_current_release_registry_matches_app_version() -> None:
    """The registry must have an entry for whatever APP_VERSION actually
    is right now, or every test below is checking against nothing."""
    assert get_current_release() is not None
    assert get_current_release().version == APP_VERSION


@pytest.mark.asyncio
async def test_first_launch_after_update_shows_announcement(session: AsyncSession) -> None:
    """A player who exists, has a complete profile, and has an outdated
    (or NULL) last_seen_version sees the announcement."""
    await _make_complete_player(session, 13101)
    # Simulate an existing pre-migration player: NULL is already the
    # default from _make_complete_player's get_or_create, but an older
    # real version is the more realistic "just upgraded" case.
    from sqlalchemy import text as sql_text
    await session.execute(sql_text("UPDATE players SET last_seen_version = 'v0.1.0' WHERE telegram_id = :t"), {"t": 13101})
    await session.commit()

    assert await ReleaseAnnouncementService(session).should_show_announcement(13101) is True


@pytest.mark.asyncio
async def test_already_viewed_version_does_not_show_again(session: AsyncSession) -> None:
    await _make_complete_player(session, 13102)
    await ReleaseAnnouncementService(session).mark_seen(13102)
    await session.commit()

    assert await ReleaseAnnouncementService(session).should_show_announcement(13102) is False


@pytest.mark.asyncio
async def test_no_duplicate_announcements_across_repeated_checks(session: AsyncSession) -> None:
    await _make_complete_player(session, 13103)
    from sqlalchemy import text as sql_text
    await session.execute(sql_text("UPDATE players SET last_seen_version = 'v0.1.0' WHERE telegram_id = :t"), {"t": 13103})
    await session.commit()

    service = ReleaseAnnouncementService(session)
    assert await service.should_show_announcement(13103) is True
    await service.mark_seen(13103)
    await session.commit()

    # Checking again and again never re-shows it for the same version.
    assert await service.should_show_announcement(13103) is False
    assert await service.should_show_announcement(13103) is False


@pytest.mark.asyncio
async def test_version_persists_to_the_database(session: AsyncSession) -> None:
    await _make_complete_player(session, 13104)
    await ReleaseAnnouncementService(session).mark_seen(13104)
    await session.commit()

    player = await PlayerService(session).get_by_telegram_id(13104)
    # last_seen_version isn't on PlayerRead (an internal concern) —
    # confirm directly against the repository/ORM layer instead.
    from backend.app.database.repositories.player_repository import PlayerRepository
    raw = await PlayerRepository(session).get_by_telegram_id(13104)
    assert raw.last_seen_version == APP_VERSION


@pytest.mark.asyncio
async def test_new_player_never_sees_announcement_for_the_version_they_joined_on(session: AsyncSession) -> None:
    """Backward compatibility / correct default: a brand-new player is
    stamped with the current APP_VERSION at creation — nothing to
    announce to them."""
    await _make_complete_player(session, 13105)

    assert await ReleaseAnnouncementService(session).should_show_announcement(13105) is False


@pytest.mark.asyncio
async def test_incomplete_profile_never_shows_announcement(session: AsyncSession) -> None:
    """A player mid-onboarding must not be interrupted by the
    announcement — it only appears once they've reached the Main Menu
    for the first time."""
    svc = PlayerService(session)
    await svc.get_or_create(PlayerCreate(telegram_id=13106, first_name="Onboarding"))
    from sqlalchemy import text as sql_text
    await session.execute(sql_text("UPDATE players SET last_seen_version = 'v0.1.0' WHERE telegram_id = :t"), {"t": 13106})
    await session.commit()

    assert await ReleaseAnnouncementService(session).should_show_announcement(13106) is False


@pytest.mark.asyncio
async def test_nonexistent_player_never_shows_announcement(session: AsyncSession) -> None:
    assert await ReleaseAnnouncementService(session).should_show_announcement(999999999) is False


# ---------------------------------------------------------------------------
# Presenter — both screens, all three languages
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("lang", ["en", "uk", "ru"])
def test_announcement_view_renders_version_and_both_buttons(lang: str) -> None:
    view = build_announcement_view(lang, _TEST_RELEASE)

    assert display_version(_TEST_RELEASE.version) in view.text
    # The release title is deliberately not shown on this first screen
    # (kept on the Release model, surfaced only on What's New below).
    assert _TEST_RELEASE.title not in view.text
    callbacks = {btn.callback_data for row in view.keyboard.inline_keyboard for btn in row}
    assert callbacks == {"announce:continue", "announce:whats_new"}


@pytest.mark.parametrize("lang", ["en", "uk", "ru"])
def test_whats_new_view_renders_every_change_and_one_continue_button(lang: str) -> None:
    view = build_whats_new_view(lang, _TEST_RELEASE)

    assert display_version(_TEST_RELEASE.version) in view.text
    # The release title is never shown to the user — not on this
    # screen either — only what changed, not the internal release name.
    assert _TEST_RELEASE.title not in view.text
    for change in _TEST_RELEASE.changes:
        assert change.emoji in view.text
        assert change.label in view.text
    callbacks = {btn.callback_data for row in view.keyboard.inline_keyboard for btn in row}
    assert callbacks == {"announce:continue"}


def test_display_version_strips_leading_v() -> None:
    assert display_version("v0.13.0") == "0.13.0"
    assert display_version("0.13.0") == "0.13.0"


# ---------------------------------------------------------------------------
# End-to-end: real dispatcher, real middleware interception
#
# DatabaseMiddleware (and therefore ReleaseAnnouncementMiddleware) binds
# to backend.app.database.session's module-level engine/session
# factory — the real dev database, not the isolated in-memory `session`
# fixture every other test in this suite uses. There is no clean way to
# swap that engine per-test without monkeypatching the module-level
# singleton itself, so these two tests deliberately use the real
# get_session() instead, creating a clearly-marked temporary player and
# removing it in a finally block — the same pattern used throughout
# this project's manual runtime verifications, formalized as a
# permanent, repeatable test.
# ---------------------------------------------------------------------------

captured: list = []
_dp_holder: dict = {}

_E2E_TG_ID_1 = 99999013201
_E2E_TG_ID_2 = 99999013202


async def _fake_call(self, method, request_timeout=None):
    captured.append(method)
    return MagicMock()


def _shared_dispatcher():
    """aiogram Routers attach to exactly one Dispatcher for their
    lifetime — build_dispatcher() can only be called once per process,
    so every end-to-end test in this file shares one instance."""
    if "dp" not in _dp_holder:
        _dp_holder["dp"] = build_dispatcher()
    return _dp_holder["dp"]


async def _feed_text(dp, bot, tg_id, text):
    tg_user = User(id=tg_id, is_bot=False, first_name="X")
    chat = Chat(id=tg_id, type="private")
    msg = Message(message_id=1, date=datetime.now(timezone.utc), chat=chat, from_user=tg_user, text=text)
    await dp.feed_update(bot, Update(update_id=1, message=msg))


async def _feed_cbq(dp, bot, tg_id, data):
    tg_user = User(id=tg_id, is_bot=False, first_name="X")
    chat = Chat(id=tg_id, type="private")
    cbq_message = Message(message_id=2, date=datetime.now(timezone.utc), chat=chat, from_user=tg_user, text="x")
    cbq = CallbackQuery(id="c1", from_user=tg_user, chat_instance="i", data=data, message=cbq_message)
    await dp.feed_update(bot, Update(update_id=2, callback_query=cbq))


async def _make_real_complete_player_with_stale_version(telegram_id: int) -> None:
    from sqlalchemy import text as sql_text

    from backend.app.database.session import get_session

    async with get_session() as real_session:
        svc = PlayerService(real_session)
        await svc.get_or_create(PlayerCreate(telegram_id=telegram_id, first_name="E2EAnnouncementTest"))
        await svc.update_profile(
            telegram_id, PlayerUpdate(language="en", skill_level=3.5, home_area="Downtown", preferred_courts=[])
        )
        await real_session.commit()
        await real_session.execute(
            sql_text("UPDATE players SET last_seen_version = 'v0.1.0' WHERE telegram_id = :t"), {"t": telegram_id}
        )
        await real_session.commit()


async def _get_real_last_seen_version(telegram_id: int) -> str | None:
    from backend.app.database.repositories.player_repository import PlayerRepository
    from backend.app.database.session import get_session

    async with get_session() as real_session:
        player = await PlayerRepository(real_session).get_by_telegram_id(telegram_id)
        return player.last_seen_version if player else None


async def _delete_real_player(telegram_id: int) -> None:
    from sqlalchemy import text as sql_text

    from backend.app.database.session import get_session

    async with get_session() as real_session:
        await real_session.execute(sql_text("DELETE FROM players WHERE telegram_id = :t"), {"t": telegram_id})
        await real_session.commit()


@pytest.mark.asyncio
async def test_end_to_end_continue_flow_marks_seen_and_shows_main_menu(monkeypatch) -> None:
    await _make_real_complete_player_with_stale_version(_E2E_TG_ID_1)
    try:
        monkeypatch.setattr(Bot, "__call__", _fake_call)
        captured.clear()
        bot = Bot(token="123:FAKE")
        dp = _shared_dispatcher()

        # Any normal interaction — not /start — triggers the announcement.
        await _feed_text(dp, bot, _E2E_TG_ID_1, "👤 My Profile")
        texts = [getattr(m, "text", None) for m in captured]
        assert any(t and "Baseline updated" in t for t in texts)
        assert not any(t and "Your Profile" in t for t in texts)  # My Profile itself never ran

        # Press Continue.
        captured.clear()
        await _feed_cbq(dp, bot, _E2E_TG_ID_1, "announce:continue")
        assert await _get_real_last_seen_version(_E2E_TG_ID_1) == APP_VERSION

        # Now that it's been seen, the SAME interaction reaches the real handler.
        captured.clear()
        await _feed_text(dp, bot, _E2E_TG_ID_1, "👤 My Profile")
        texts = [getattr(m, "text", None) for m in captured]
        assert not any(t and "Baseline has been updated" in t for t in texts)
        assert any(t and "Your Profile" in t for t in texts)
    finally:
        await _delete_real_player(_E2E_TG_ID_1)


@pytest.mark.asyncio
async def test_end_to_end_whats_new_flow_then_continue(monkeypatch) -> None:
    await _make_real_complete_player_with_stale_version(_E2E_TG_ID_2)
    try:
        monkeypatch.setattr(Bot, "__call__", _fake_call)
        captured.clear()
        bot = Bot(token="123:FAKE")
        dp = _shared_dispatcher()

        await _feed_text(dp, bot, _E2E_TG_ID_2, "👤 My Profile")
        captured.clear()
        await _feed_cbq(dp, bot, _E2E_TG_ID_2, "announce:whats_new")
        texts = [getattr(m, "text", None) for m in captured]
        assert any(t and "What's New" in t for t in texts)
        assert await _get_real_last_seen_version(_E2E_TG_ID_2) != APP_VERSION  # viewed, not yet marked seen

        captured.clear()
        await _feed_cbq(dp, bot, _E2E_TG_ID_2, "announce:continue")
        assert await _get_real_last_seen_version(_E2E_TG_ID_2) == APP_VERSION
    finally:
        await _delete_real_player(_E2E_TG_ID_2)
