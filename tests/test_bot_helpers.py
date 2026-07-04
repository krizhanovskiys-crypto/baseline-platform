"""Tests for backend/app/bot/handlers/helpers.py shared utilities."""
from types import SimpleNamespace
from urllib.parse import unquote

import pytest

from backend.app.bot.handlers.helpers import build_invite_share_url
from backend.app.bot.texts import t


class _FakeBot:
    def __init__(self, username: str) -> None:
        self._username = username

    async def get_me(self):
        return SimpleNamespace(username=self._username)


@pytest.mark.asyncio
async def test_build_invite_share_url_wraps_a_deep_link_to_this_bot():
    url = await build_invite_share_url(_FakeBot("baseline_bot"), "en", 243843943)

    assert url.startswith("https://t.me/share/url?")
    assert "t.me%2Fbaseline_bot%3Fstart%3Dinvite_243843943" in url


@pytest.mark.asyncio
async def test_build_invite_share_url_includes_localized_share_text():
    url = await build_invite_share_url(_FakeBot("baseline_bot"), "uk", 243843943)

    assert unquote(url.split("text=")[1]) == t("invite_share_text", "uk")


@pytest.mark.asyncio
async def test_build_invite_share_url_payload_identifies_the_inviting_player():
    """The payload is not parsed or acted on anywhere yet (no referral
    tracking) — this only prepares the URL format so it already carries
    the inviter's telegram_id for when that lands."""
    url_alice = await build_invite_share_url(_FakeBot("baseline_bot"), "en", 111)
    url_bob = await build_invite_share_url(_FakeBot("baseline_bot"), "en", 222)

    assert url_alice != url_bob
    assert "invite_111" in unquote(url_alice)
    assert "invite_222" in unquote(url_bob)


@pytest.mark.asyncio
async def test_build_invite_share_url_is_deterministic_for_the_same_player():
    url_1 = await build_invite_share_url(_FakeBot("baseline_bot"), "en", 111)
    url_2 = await build_invite_share_url(_FakeBot("baseline_bot"), "en", 111)

    assert url_1 == url_2
