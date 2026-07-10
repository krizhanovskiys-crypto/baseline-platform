"""Tournament Dashboard presenter (Sprint 16, Step 1) — the organizer-
only view of Tournament Details. Pure: takes already-fetched data
(GameRead/MatchDetails/TournamentStandingEntry, all already returned by
existing services), returns view artifacts, never touches a session, a
repository, or a service. The orchestrating handler
(bot/handlers/helpers.py:show_tournament_details) decides *what* to
fetch; this module only decides what the screen looks like once that
data already exists — same split as tournament_details.py.

Not a replacement for tournament_details.py: the organizer still sees
that presenter's header text/management keyboard first (Edit, Delete,
Open/Close Registration, Generate Matches, ... — all pre-existing,
unchanged), then this presenter's additional messages (round info,
match cards) render below it. A Player never reaches this module —
show_tournament_details() only calls it when can_manage is True.
"""
from dataclasses import dataclass

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.utils.markdown import markdown_decoration

from backend.app.bot.texts import t
from backend.app.database.models.game import GameStatus
from backend.app.database.models.tournament import TournamentStatus
from backend.app.schemas.game import MatchDetails
from backend.app.schemas.tournament import TournamentRead, TournamentStandingEntry

_MATCH_STATUS_KEYS: dict[GameStatus, str] = {
    GameStatus.OPEN: "tournament_match_status_open",
    GameStatus.IN_PROGRESS: "tournament_match_status_in_progress",
    GameStatus.COMPLETED: "tournament_match_status_completed",
}


@dataclass
class DashboardMessageView:
    text: str
    keyboard: InlineKeyboardMarkup | None = None


def group_matches_by_round(matches: list[MatchDetails]) -> dict[int, list[MatchDetails]]:
    """Group already-fetched matches by Game.round, each round's list
    kept in a stable order (by game id — creation order). Matches with
    no round assigned (round is None; not expected for a generated
    tournament match, but not this presenter's job to assume it can
    never happen) are omitted — nothing to group them under."""
    grouped: dict[int, list[MatchDetails]] = {}
    for match in matches:
        if match.game.round is None:
            continue
        grouped.setdefault(match.game.round, []).append(match)
    for round_matches in grouped.values():
        round_matches.sort(key=lambda m: m.game.id)
    return grouped


def current_round(matches: list[MatchDetails]) -> int | None:
    """The lowest round number that still has a non-COMPLETED match —
    the round actually being played right now. If every match is
    COMPLETED, returns the highest round (the final that just
    finished). None if there are no matches yet."""
    if not matches:
        return None
    incomplete_rounds = [m.game.round for m in matches if m.game.status != GameStatus.COMPLETED and m.game.round]
    if incomplete_rounds:
        return min(incomplete_rounds)
    all_rounds = [m.game.round for m in matches if m.game.round]
    return max(all_rounds) if all_rounds else None


def build_dashboard_header_text(
    lang: str, tournament: TournamentRead, registered_count: int, round_now: int | None
) -> str:
    return t(
        "tournament_dashboard_header",
        lang,
        name=markdown_decoration.quote(tournament.name),
        area=tournament.area,
        court=tournament.court,
        registered=registered_count,
        max_players=tournament.max_players,
        status=t(f"tournament_status_{tournament.status.value}", lang),
        round_line=(
            t("tournament_dashboard_current_round", lang, round=round_now)
            if round_now is not None
            else t("tournament_dashboard_no_round", lang)
        ),
    )


def build_champion_banner(lang: str, standings: list[TournamentStandingEntry]) -> str | None:
    """None if no champion is determined yet (tournament not actually
    COMPLETED, or standings computation found no single winner) — the
    caller only invokes this for a COMPLETED tournament, but this
    function stays defensive rather than assuming that's always true."""
    champion = next((entry for entry in standings if entry.status == "champion"), None)
    if champion is None:
        return None
    return t("tournament_dashboard_champion", lang, name=markdown_decoration.quote(champion.first_name))


def build_round_label(lang: str, round_number: int) -> str:
    return t("tournament_dashboard_round_label", lang, round=round_number)


def build_empty_state_text(lang: str, status: TournamentStatus) -> str:
    """One clear message per reason the match list is empty — never a
    single generic "no matches" string standing in for every case."""
    key = {
        TournamentStatus.DRAFT: "tournament_dashboard_empty_draft",
        TournamentStatus.REGISTRATION_OPEN: "tournament_dashboard_empty_registration_open",
        TournamentStatus.REGISTRATION_CLOSED: "tournament_dashboard_empty_awaiting_bracket",
        TournamentStatus.CANCELLED: "tournament_dashboard_empty_cancelled",
    }.get(status, "tournament_dashboard_empty_no_matches")
    return t(key, lang)


def build_match_card_view(lang: str, match: MatchDetails) -> DashboardMessageView:
    """One compact card per match — court, both players, status, and an
    action button appropriate to the match's current status. The Start
    Match button (OPEN) is wired (Sprint 16, Step 2 —
    bot/handlers/admin/tournaments.py). The Enter Result button
    (IN_PROGRESS) is still a placeholder: rendered only, no handler
    registered for its callback_data yet, so tapping it does nothing
    today, same as any other not-yet-wired callback in this codebase.

    Always exactly two participants for a generated tournament match
    (auto_join_creator=False; the organizer is never one of the two
    players) — player_a/player_b index directly into `match.players`
    rather than searching for is_organizer=False."""
    game = match.game
    player_a = match.players[0].name if len(match.players) > 0 else "—"
    player_b = match.players[1].name if len(match.players) > 1 else "—"

    winner_line = ""
    if game.status == GameStatus.COMPLETED and game.winner_player_id is not None:
        winner = next((p for p in match.players if p.player_id == game.winner_player_id), None)
        if winner is not None:
            winner_line = t("tournament_dashboard_winner_line", lang, name=markdown_decoration.quote(winner.name))

    text = t(
        "tournament_dashboard_match_card",
        lang,
        court=game.court,
        player_a=markdown_decoration.quote(player_a),
        player_b=markdown_decoration.quote(player_b),
        status=t(_MATCH_STATUS_KEYS.get(game.status, "tournament_match_status_open"), lang),
        winner_line=winner_line,
    )

    keyboard = None
    if game.status == GameStatus.OPEN:
        builder = InlineKeyboardBuilder()
        builder.button(text=t("tournament_dashboard_btn_start", lang), callback_data=f"tourn:start_match:{game.id}")
        keyboard = builder.as_markup()
    elif game.status == GameStatus.IN_PROGRESS:
        builder = InlineKeyboardBuilder()
        builder.button(
            text=t("tournament_dashboard_btn_result", lang), callback_data=f"tourn:enter_result:{game.id}"
        )
        keyboard = builder.as_markup()

    return DashboardMessageView(text=text, keyboard=keyboard)


def build_who_won_view(lang: str, match: MatchDetails) -> DashboardMessageView:
    """The 🏆 Enter Result prompt (Sprint 16, Step 3) — replaces one
    match card in place (same message, edited) with exactly two
    buttons, one per participant. Callback format is fixed:
    tourn:winner:{game_id}:{player_id} — player_id is the Player.id
    TournamentService.complete_match() expects as winner_player_id,
    already carried on PlayerSummary since Sprint 16, Step 1."""
    game = match.game
    builder = InlineKeyboardBuilder()
    for player in match.players:
        builder.button(
            text=t("tournament_dashboard_winner_option", lang, name=player.name),
            callback_data=f"tourn:winner:{game.id}:{player.player_id}",
        )
    builder.adjust(1)
    return DashboardMessageView(text=t("tournament_dashboard_who_won", lang), keyboard=builder.as_markup())


def build_winner_confirmed_text(lang: str, winner_name: str) -> str:
    return t("tournament_dashboard_winner_confirmed", lang, name=markdown_decoration.quote(winner_name))


def build_dashboard_views(
    lang: str,
    tournament: TournamentRead,
    registered_count: int,
    matches: list[MatchDetails],
    standings: list[TournamentStandingEntry],
    management_keyboard: InlineKeyboardMarkup,
) -> list[DashboardMessageView]:
    """Assemble the full ordered sequence of messages the handler sends
    for the organizer dashboard: header (carrying the existing,
    unchanged management keyboard) first, then an optional champion
    banner, then either one empty-state message or the round-by-round
    match cards. The handler only needs to iterate this list and call
    message.answer() for each — no further decisions made there."""
    round_now = current_round(matches)
    views = [
        DashboardMessageView(
            text=build_dashboard_header_text(lang, tournament, registered_count, round_now),
            keyboard=management_keyboard,
        )
    ]

    if tournament.status == TournamentStatus.COMPLETED:
        banner = build_champion_banner(lang, standings)
        if banner:
            views.append(DashboardMessageView(text=banner))

    if not matches:
        views.append(DashboardMessageView(text=build_empty_state_text(lang, tournament.status)))
        return views

    grouped = group_matches_by_round(matches)
    for round_number in sorted(grouped):
        views.append(DashboardMessageView(text=build_round_label(lang, round_number)))
        for match in grouped[round_number]:
            views.append(build_match_card_view(lang, match))

    return views
