"""Handler utilities — common helpers used across multiple handlers."""
import logging
from urllib.parse import quote

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from aiogram.types import Message
from aiogram.utils.markdown import markdown_decoration
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.bot.keyboards.keyboards import main_menu_keyboard
from backend.app.bot.texts import t
from backend.app.schemas.player import PlayerRead
from backend.app.services.player_service import PlayerService

logger = logging.getLogger(__name__)


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


async def notify_tournament_registration_closed(bot: Bot, session: AsyncSession, tournament_id: int) -> None:
    """Registration Closed Notification (Sprint 12) — shared by every
    trigger that closes a tournament's registration: the Admin's manual
    Close action, and the lazy deadline/max_players check on Browse/
    Details/Register. Transport-aware, so it lives here rather than in
    TournamentService, which stays transport-agnostic."""
    from backend.app.services.tournament_service import TournamentService

    service = TournamentService(session)
    tournament = await service.get_tournament(tournament_id)
    if tournament is None:
        return
    registrations = await service.get_registered_players(tournament_id)
    for reg in registrations:
        text = t(
            "tournament_registration_closed_notification",
            reg.language or "en",
            name=markdown_decoration.quote(tournament.name),
            date=tournament.start_date.strftime("%d.%m.%Y"),
            time=tournament.start_time.strftime("%H:%M"),
            court=tournament.court,
        )
        try:
            await bot.send_message(reg.telegram_id, text, parse_mode="Markdown")
        except TelegramAPIError:
            logger.warning(
                "Could not notify telegram_id=%s of tournament %s closing", reg.telegram_id, tournament_id
            )
