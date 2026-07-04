"""Admin Center — one module per concern, never a single growing file.

New Admin Center functionality is always a new module in this package
(players.py, matches.py, courts.py, tournaments.py, coaches.py,
system.py, ...), registered below — never added to auth.py or testing.py.
See docs/ARCHITECTURE.md for the full rule.
"""
from aiogram import Router

from backend.app.bot.handlers.admin import auth, system, testing

router = Router(name="admin")
router.include_router(auth.router)
router.include_router(testing.router)
router.include_router(system.router)
