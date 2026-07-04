"""Process start time, captured once at import — the Admin Center
Dashboard's uptime figure is this module's only consumer. Import-time
capture is intentional: this module is imported once per process, near
process startup (see bot/main.py), and every later import reuses the
same timestamp.
"""
from datetime import datetime, timedelta, timezone

PROCESS_STARTED_AT = datetime.now(timezone.utc)


def get_uptime() -> timedelta:
    return datetime.now(timezone.utc) - PROCESS_STARTED_AT


def get_uptime_display() -> str:
    """Human-readable uptime — "45s", "12m", "2h 15m", or "3d 4h"."""
    total_seconds = int(get_uptime().total_seconds())
    days, remainder = divmod(total_seconds, 86_400)
    hours, remainder = divmod(remainder, 3_600)
    minutes, seconds = divmod(remainder, 60)

    if days:
        return f"{days}d {hours}h"
    if hours:
        return f"{hours}h {minutes}m"
    if minutes:
        return f"{minutes}m"
    return f"{seconds}s"
