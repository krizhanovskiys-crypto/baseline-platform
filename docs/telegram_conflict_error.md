# TelegramConflictError — Duplicate Polling Instance

## Why only one polling instance may run

Telegram's Bot API delivers updates through long-polling: the bot opens an HTTP connection to `getUpdates`, Telegram holds it open until an update arrives, then the bot opens the next connection. Telegram enforces a **one active polling session per token** rule. If a second process calls `getUpdates` on the same token while the first is still connected, Telegram returns HTTP 409 Conflict. Aiogram raises this as `TelegramConflictError`.

The constraint is not a framework limitation — it is the protocol. Telegram cannot safely deliver the same update to two different processes, so it refuses the second connection entirely.

## What causes it

The most common causes during development:

- A previous bot process was not terminated before starting a new one (e.g. `Ctrl+C` was missed or the terminal was closed without killing the child process).
- Two terminal tabs both running `python -m backend.app.bot.main`.
- A crashed process left a zombie that still holds the polling connection open (rare; Telegram times these out after ~60 s).
- A deployment process started a new instance before the old one exited.

## How to detect duplicate processes

```bash
# List all Python processes running the bot entry point
ps aux | grep "backend.app.bot.main" | grep -v grep

# Alternative: find by port or token substring in the command line
ps aux | grep "bot" | grep "python" | grep -v grep
```

If you see more than one PID, you have a duplicate.

## How to stop them

```bash
# Kill by PID (replace <PID> with the value from ps output)
kill <PID>

# Kill all matching processes at once
pkill -f "backend.app.bot.main"

# Confirm they are gone
ps aux | grep "backend.app.bot.main" | grep -v grep
```

Wait 5–10 seconds after killing before starting a new instance. Telegram holds the previous session briefly before it times out on their side.

## Quick checklist when you see TelegramConflictError

1. Run `ps aux | grep "backend.app.bot.main" | grep -v grep` — count the PIDs.
2. Kill all but the one you intend to keep, or kill all and restart once.
3. If the error persists immediately after kill, wait 10 s and retry — Telegram is releasing the previous session.
4. Never run the bot with `--reload` (e.g. via uvicorn) or in a process supervisor that auto-restarts without waiting for the previous instance to exit cleanly.
