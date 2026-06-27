"""Developer Mode handler — hidden /dev command for internal testing only."""
import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.bot.handlers.helpers import get_player_lang, send_main_menu
from backend.app.bot.keyboards.keyboards import dev_menu_keyboard
from backend.app.bot.texts import t
from backend.app.core.config import get_settings
from backend.app.services.dev_service import DevService
from backend.app.services.player_service import PlayerService

logger = logging.getLogger(__name__)
router = Router(name="dev")


def _is_developer(telegram_id: int) -> bool:
    return telegram_id in get_settings().developer_ids_list


@router.message(Command("dev"))
async def cmd_dev(message: Message, session: AsyncSession) -> None:
    user = message.from_user
    if not user or not _is_developer(user.id):
        return

    service = PlayerService(session)
    player = await service.get_by_telegram_id(user.id)
    lang = get_player_lang(player)

    await message.answer(
        t("dev_menu_header", lang),
        reply_markup=dev_menu_keyboard(lang),
        parse_mode="Markdown",
    )
    logger.info("Dev menu opened by telegram_id=%s", user.id)


@router.callback_query(F.data == "dev:create_players")
async def dev_create_players(callback: CallbackQuery, session: AsyncSession) -> None:
    if not callback.from_user or not _is_developer(callback.from_user.id):
        return

    service = PlayerService(session)
    player = await service.get_by_telegram_id(callback.from_user.id)
    lang = get_player_lang(player)

    dev_svc = DevService(session)
    count = await dev_svc.create_test_players()
    key = "dev_players_created" if count > 0 else "dev_players_already_exist"
    await callback.message.answer(t(key, lang, count=count), parse_mode="Markdown")  # type: ignore[union-attr]
    await callback.answer()


@router.callback_query(F.data == "dev:reset_data")
async def dev_reset_data(callback: CallbackQuery, session: AsyncSession) -> None:
    if not callback.from_user or not _is_developer(callback.from_user.id):
        return

    service = PlayerService(session)
    player = await service.get_by_telegram_id(callback.from_user.id)
    lang = get_player_lang(player)

    dev_svc = DevService(session)
    count = await dev_svc.reset_test_data()
    key = "dev_data_reset" if count > 0 else "dev_nothing_to_reset"
    await callback.message.answer(t(key, lang, count=count), parse_mode="Markdown")  # type: ignore[union-attr]
    await callback.answer()


@router.callback_query(F.data == "dev:stats")
async def dev_stats(callback: CallbackQuery, session: AsyncSession) -> None:
    if not callback.from_user or not _is_developer(callback.from_user.id):
        return

    service = PlayerService(session)
    player = await service.get_by_telegram_id(callback.from_user.id)
    lang = get_player_lang(player)

    dev_svc = DevService(session)
    stats = await dev_svc.get_stats()
    await callback.message.answer(t("dev_stats", lang, **stats), parse_mode="Markdown")  # type: ignore[union-attr]
    await callback.answer()


@router.callback_query(F.data == "dev:exit")
async def dev_exit(callback: CallbackQuery, session: AsyncSession) -> None:
    if not callback.from_user or not _is_developer(callback.from_user.id):
        return

    service = PlayerService(session)
    player = await service.get_by_telegram_id(callback.from_user.id)
    lang = get_player_lang(player)

    await send_main_menu(callback.message, lang)  # type: ignore[union-attr]
    await callback.answer()
