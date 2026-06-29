"""Invitation accept/decline handler."""
import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.bot.handlers.helpers import get_player_lang
from backend.app.bot.keyboards.keyboards import game_full_keyboard
from backend.app.bot.texts import t
from backend.app.database.models.game import GameStatus
from backend.app.services.game_service import GameService
from backend.app.services.invitation_service import InvitationService
from backend.app.services.player_service import PlayerService

logger = logging.getLogger(__name__)
router = Router(name="invitation")


@router.callback_query(F.data.startswith("inv:accept:"))
async def inv_accept(callback: CallbackQuery, session: AsyncSession) -> None:
    if not callback.data or not callback.message:
        return
    invitation_id = int(callback.data.split(":")[-1])
    user = callback.from_user

    inv_svc = InvitationService(session)
    inv, error, new_game_status = await inv_svc.accept(invitation_id, user.id)

    invitee = await PlayerService(session).get_by_telegram_id(user.id)
    lang = get_player_lang(invitee)

    if error:
        await callback.answer(t(error, lang), show_alert=True)
        return

    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass

    await callback.message.answer(t("inv_player_accepted", lang))
    await callback.answer()

    if not inv:
        return

    game = await GameService(session).get_game(inv.game_id)
    if not game:
        return
    organizer = await PlayerService(session).get_by_id(game.creator_id)
    if not organizer or not organizer.telegram_id:
        return

    org_lang = organizer.language or "en"
    name = invitee.first_name if invitee else user.first_name or "?"

    # Always notify organizer that someone accepted
    try:
        await callback.bot.send_message(
            organizer.telegram_id,
            t("inv_organizer_accepted", org_lang, name=name),
            parse_mode="Markdown",
        )
    except Exception:
        logger.warning("Could not notify organizer telegram_id=%s", organizer.telegram_id)

    # Additional notification when match becomes full
    if new_game_status == GameStatus.FULL:
        try:
            await callback.bot.send_message(
                organizer.telegram_id,
                t("game_full_notification", org_lang),
                reply_markup=game_full_keyboard(org_lang, inv.game_id),
                parse_mode="Markdown",
            )
        except Exception:
            logger.warning("Could not send game-full notification to telegram_id=%s", organizer.telegram_id)


@router.callback_query(F.data.startswith("inv:decline:"))
async def inv_decline(callback: CallbackQuery, session: AsyncSession) -> None:
    if not callback.data or not callback.message:
        return
    invitation_id = int(callback.data.split(":")[-1])
    user = callback.from_user

    inv_svc = InvitationService(session)
    inv, error = await inv_svc.decline(invitation_id, user.id)

    invitee = await PlayerService(session).get_by_telegram_id(user.id)
    lang = get_player_lang(invitee)

    if error:
        await callback.answer(t(error, lang), show_alert=True)
        return

    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass

    await callback.message.answer(t("inv_player_declined", lang))
    await callback.answer()

    if inv:
        game = await GameService(session).get_game(inv.game_id)
        if game:
            organizer = await PlayerService(session).get_by_id(game.creator_id)
            if organizer and organizer.telegram_id:
                org_lang = organizer.language or "en"
                name = invitee.first_name if invitee else user.first_name or "?"
                try:
                    await callback.bot.send_message(
                        organizer.telegram_id,
                        t("inv_organizer_declined", org_lang, name=name),
                        parse_mode="Markdown",
                    )
                except Exception:
                    logger.warning("Could not notify organizer telegram_id=%s", organizer.telegram_id)
