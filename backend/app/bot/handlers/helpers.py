"""Handler utilities — common helpers used across multiple handlers."""
from urllib.parse import quote

from aiogram import Bot
from aiogram.types import Message

from backend.app.bot.keyboards.keyboards import main_menu_keyboard
from backend.app.bot.texts import t
from backend.app.schemas.player import PlayerRead
from backend.app.services.player_service import PlayerService


async def send_main_menu(message: Message, lang: str) -> None:
    """Send the main menu to a user."""
    await message.answer(
        t("main_menu", lang),
        reply_markup=main_menu_keyboard(lang),
        parse_mode="Markdown",
    )


def get_player_lang(player: PlayerRead | None) -> str:
    """Return the player language or default."""
    return player.language or "en" if player else "en"


async def build_invite_share_url(bot: Bot, lang: str, telegram_id: int) -> str:
    """A Telegram share-sheet URL wrapping a deep link back to this bot —
    shared by every player-discovery empty state (Find Partner, Find
    Players for a Match).

    The deep-link payload is "invite_{telegram_id}" — telegram_id
    identifies the inviting player, but the payload is not parsed or
    acted on anywhere yet (no referral tracking). This only prepares the
    URL format; /start still ignores any payload it's given. Adding real
    referral tracking later means parsing this same payload in /start —
    the share mechanism and every caller's button stay unchanged.
    """
    me = await bot.get_me()
    deep_link = f"https://t.me/{me.username}?start=invite_{telegram_id}"
    share_text = t("invite_share_text", lang)
    return f"https://t.me/share/url?url={quote(deep_link, safe='')}&text={quote(share_text, safe='')}"
