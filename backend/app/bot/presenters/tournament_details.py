"""Tournament Details presenter (Sprint 12.2) — the one place that
builds the (text, keyboard) pair for the unified Tournament Details
screen. Pure: takes already-fetched data, returns view artifacts,
never touches a session, a repository, or Bot. The orchestrating
handler (bot/handlers/helpers.py:show_tournament_details) decides
*what* to fetch and *whether* a side effect (auto-close, the
notification) is needed; this module only decides what the screen
looks like once that data already exists.
"""
from dataclasses import dataclass

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.utils.markdown import markdown_decoration

from backend.app.bot.texts import t
from backend.app.database.models.tournament import TournamentStatus
from backend.app.schemas.tournament import TournamentRead


@dataclass
class TournamentDetailsView:
    text: str
    keyboard: InlineKeyboardMarkup


def build_tournament_details_view(
    lang: str,
    tournament: TournamentRead,
    registered_count: int,
    can_manage: bool,
    is_registered: bool,
    back_callback: str,
) -> TournamentDetailsView:
    """can_manage adds management actions (Admin, or the Verified Coach
    who organized this specific tournament); is_registered picks
    Register vs Withdraw, independent of can_manage — an organizer can
    also be a registered participant in their own tournament.
    back_callback is chosen by the caller, which knows the viewer's
    relationship to this tournament (their own, an Admin's blanket
    view, or a stranger's) — this presenter only places it on the
    button, it never decides which list is "correct" itself."""
    text = t(
        "tournament_details",
        lang,
        name=markdown_decoration.quote(tournament.name),
        area=tournament.area,
        court=tournament.court,
        start_date=tournament.start_date.strftime("%d.%m.%Y"),
        start_time=tournament.start_time.strftime("%H:%M"),
        deadline=tournament.registration_deadline.strftime("%d.%m.%Y"),
        registered=registered_count,
        max_players=tournament.max_players,
        status=t(f"tournament_status_{tournament.status.value}", lang),
    )

    builder = InlineKeyboardBuilder()
    rows = 0

    if can_manage:
        builder.button(text=t("tournament_btn_edit", lang), callback_data=f"tourn:edit:{tournament.id}")
        rows += 1
        if tournament.status == TournamentStatus.DRAFT:
            builder.button(
                text=t("tournament_btn_open_registration", lang), callback_data=f"tourn:open_reg:{tournament.id}"
            )
            rows += 1
        if tournament.status == TournamentStatus.REGISTRATION_OPEN:
            builder.button(
                text=t("tournament_btn_close_registration", lang), callback_data=f"tourn:close_reg:{tournament.id}"
            )
            rows += 1
        builder.button(text=t("tournament_btn_view_players", lang), callback_data=f"tourn:players:{tournament.id}")
        rows += 1
        if tournament.status in (TournamentStatus.REGISTRATION_OPEN, TournamentStatus.REGISTRATION_CLOSED):
            builder.button(
                text=t("tournament_btn_add_player", lang), callback_data=f"tourn:add_player:{tournament.id}"
            )
            rows += 1
        if tournament.status == TournamentStatus.REGISTRATION_CLOSED:
            builder.button(
                text=t("tournament_btn_generate_matches", lang), callback_data=f"tourn:generate:{tournament.id}"
            )
            rows += 1
        if tournament.status == TournamentStatus.IN_PROGRESS:
            builder.button(
                text=t("tournament_btn_mark_completed", lang), callback_data=f"tourn:complete:{tournament.id}"
            )
            rows += 1
        if tournament.status not in (TournamentStatus.COMPLETED, TournamentStatus.CANCELLED):
            builder.button(text=t("tournament_btn_delete", lang), callback_data=f"tourn:delete:{tournament.id}")
            rows += 1

    if is_registered:
        builder.button(text=t("tournament_btn_withdraw", lang), callback_data=f"tourn:withdraw:{tournament.id}")
    else:
        builder.button(text=t("tournament_btn_register", lang), callback_data=f"tourn:register:{tournament.id}")
    rows += 1

    builder.button(text=t("players_btn_back", lang), callback_data=back_callback)
    rows += 1

    builder.adjust(*([1] * rows))
    return TournamentDetailsView(text=text, keyboard=builder.as_markup())
