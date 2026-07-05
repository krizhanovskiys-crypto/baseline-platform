"""Admin Center — one module per concern, never a single growing file.

New Admin Center functionality is always a new module in this package
(matches.py, courts.py, tournaments.py, coaches.py, ...), registered
below — never added to auth.py, dashboard.py, or testing.py. See
docs/ARCHITECTURE.md for the full rule.
"""
from aiogram import Router

from backend.app.bot.handlers.admin import auth, dashboard, players, system, testing, tournaments

router = Router(name="admin")
router.include_router(auth.router)
router.include_router(dashboard.router)
router.include_router(players.router)
router.include_router(testing.router)
router.include_router(system.router)
router.include_router(tournaments.router)
