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


async def show_tournament_menu(message: Message, session: AsyncSession, lang: str, telegram_id: int) -> None:
    """The role-aware Tournament Menu (Sprint 12.2) — the Main Menu's
    own 🏆 Tournaments entry point (bot/handlers/tournament.py), and
    also the return screen after actions that used to send a Verified
    Coach back to the old Admin/Coach Tournament Center, which a Coach
    must never land on again. Admin still returns to that screen via
    Dashboard — this helper is only for the Coach path."""
    from backend.app.bot.keyboards.keyboards import tournament_menu_keyboard
    from backend.app.services.tournament_service import TournamentService

    is_coach = await TournamentService(session).can_create_tournament(telegram_id)
    await message.answer(
        t("tournament_menu_header", lang),
        reply_markup=tournament_menu_keyboard(lang, is_coach),
        parse_mode="Markdown",
    )


async def show_tournament_details(
    message: Message, session: AsyncSession, bot: Bot, lang: str, telegram_id: int, tournament_id: int
) -> None:
    """The one Tournament Details screen (Sprint 12.2) — reached from
    Browse, My Tournaments, or Admin's Tournament Administration alike.
    This function only orchestrates: fetch the tournament, run the
    lazy auto-close side effect, decide which list Back should return
    to. The actual (text, keyboard) pair is built by the pure presenter
    in bot/presenters/tournament_details.py — no separate Player/Admin
    variant, and no view-assembly logic duplicated here."""
    from backend.app.bot.presenters.tournament_details import build_tournament_details_view
    from backend.app.services.permission_service import PermissionService
    from backend.app.services.player_service import PlayerService
    from backend.app.services.tournament_service import TournamentService

    service = TournamentService(session)

    just_closed = await service.check_and_auto_close(tournament_id)
    if just_closed:
        await notify_tournament_registration_closed(bot, session, tournament_id)

    tournament = await service.get_tournament(tournament_id)
    if tournament is None:
        await message.answer(t("tournament_browse_empty", lang), parse_mode="Markdown")
        return

    can_manage = await service.can_manage_tournament(telegram_id, tournament.organizer_player_id)
    registrations = await service.get_registered_players(tournament_id)
    is_registered = any(r.telegram_id == telegram_id for r in registrations)

    # Back returns to the list this tournament actually belongs to for
    # this viewer: their own My Tournaments if they organized it, an
    # Admin's own Browse if they're administering someone else's
    # tournament, or the general Browse otherwise — never a single
    # hardcoded target regardless of how the viewer relates to it.
    viewer = await PlayerService(session).get_by_telegram_id(telegram_id)
    if viewer and viewer.id == tournament.organizer_player_id:
        back_callback = "tourn_p:mine"
    elif await PermissionService(session).is_operator(telegram_id):
        back_callback = "tourn:browse"
    else:
        back_callback = "tourn_p:browse"

    view = build_tournament_details_view(
        lang, tournament, len(registrations), can_manage, is_registered, back_callback
    )
    await message.answer(view.text, reply_markup=view.keyboard, parse_mode="Markdown")


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
