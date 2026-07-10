"""Handler utilities — common helpers used across multiple handlers."""
import logging
from urllib.parse import quote

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from aiogram.types import InlineKeyboardMarkup, Message
from aiogram.utils.markdown import markdown_decoration
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.bot.keyboards.keyboards import main_menu_keyboard
from backend.app.bot.texts import t
from backend.app.schemas.player import PlayerRead
from backend.app.schemas.tournament import TournamentRead
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
    """The one Tournament Details entry point (Sprint 12.2) — reached
    from Browse, My Tournaments, or Admin's Tournament Administration
    alike. This function only orchestrates: fetch the tournament, run
    the lazy auto-close side effect, decide which list Back should
    return to, and decide which viewer sees which screen. The actual
    (text, keyboard) pairs are built by pure presenters — no
    view-assembly logic duplicated here.

    A Player always sees the same simplified view (unchanged since
    Sprint 12.2 — bot/presenters/tournament_details.py). An organizer/
    admin (can_manage) additionally sees the Tournament Dashboard
    (Sprint 16, Step 1 — bot/presenters/tournament_dashboard.py): the
    same header and management keyboard, plus round-by-round match
    cards. Telegram only renders what TournamentService/GameService
    already compute — no business logic lives here."""
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

    if can_manage:
        await _show_tournament_dashboard(message, session, lang, tournament, len(registrations), view.keyboard)
    else:
        await message.answer(view.text, reply_markup=view.keyboard, parse_mode="Markdown")


async def _show_tournament_dashboard(
    message: Message,
    session: AsyncSession,
    lang: str,
    tournament: TournamentRead,
    registered_count: int,
    management_keyboard: InlineKeyboardMarkup,
) -> None:
    """Fetch the data the Tournament Dashboard presenter needs — every
    Game generated for this tournament, each one's assembled match
    details, and standings once the tournament is COMPLETED — entirely
    through existing GameService/TournamentService methods, then hand
    it to the pure presenter and send whatever it returns, in order.
    No business logic here: this function is fetch-then-render only."""
    from backend.app.bot.presenters.tournament_dashboard import build_dashboard_views
    from backend.app.database.models.tournament import TournamentStatus
    from backend.app.services.game_service import GameService
    from backend.app.services.tournament_service import TournamentService

    game_service = GameService(session)
    games = await game_service.get_games_by_tournament(tournament.id)
    matches = []
    for game in games:
        details = await game_service.get_match_details(game.id)
        if details is not None:
            matches.append(details)

    standings = []
    if tournament.status == TournamentStatus.COMPLETED:
        standings = await TournamentService(session).get_standings(tournament.id)

    views = build_dashboard_views(lang, tournament, registered_count, matches, standings, management_keyboard)
    for view in views:
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
