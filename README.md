# 🎾 Baseline — Tennis Matchmaking Platform

Baseline is a tennis matchmaking platform. The Telegram Bot is the first client. The architecture is designed to support iOS, Android, and Web clients from day one — all business logic lives in the service layer, completely decoupled from Telegram.

---

## Architecture Overview

```
baseline/
├── backend/
│   └── app/
│       ├── api/          # FastAPI routers (REST API)
│       ├── bot/          # Aiogram bot (handlers, keyboards, states)
│       ├── services/     # Business logic (transport-agnostic)
│       ├── database/
│       │   ├── models/   # SQLAlchemy ORM models
│       │   └── repositories/  # Data access layer
│       ├── schemas/      # Pydantic v2 schemas
│       └── core/         # Config, logging
├── tests/                # pytest test suite
├── alembic/              # Database migrations
├── requirements.txt
└── .env.example
```

**Key principle:** Handlers never contain business logic. They receive Telegram events, call a service, and return a response. Services are testable in isolation.

---

## Installation

### 1. Clone and enter the project

```bash
git clone <repo-url>
cd baseline
```

### 2. Create a virtual environment

```bash
python3.12 -m venv .venv
source .venv/bin/activate      # Linux/macOS
# .venv\Scripts\activate       # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment

```bash
cp .env.example .env
```

Open `.env` and set your values:

```env
BOT_TOKEN=your_telegram_bot_token_here
DATABASE_URL=sqlite+aiosqlite:///./baseline.db   # development default
```

Get a bot token from [@BotFather](https://t.me/BotFather) on Telegram.

---

## Running the Telegram Bot

```bash
python -m backend.app.bot.main
```

The bot will:
1. Connect to Telegram via long-polling
2. Auto-create all database tables on first run
3. Log startup info to stdout

---

## Running the REST API

```bash
uvicorn backend.app.api.app:app --reload
```

The API will be available at:
- `http://localhost:8000`
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- Health check: `http://localhost:8000/health`

---

## Database Migrations (Alembic)

The bot and API both auto-create tables on startup via `create_all_tables()`. For production, use Alembic migrations:

```bash
# Generate a migration after model changes
alembic revision --autogenerate -m "describe your change"

# Apply all pending migrations
alembic upgrade head

# Downgrade one step
alembic downgrade -1
```

---

## Running Tests

```bash
pytest
```

Tests use an in-memory SQLite database — no `.env` needed. Coverage by feature:

| Test file | What it covers |
|---|---|
| `test_player_repository.py` | CRUD, partner search, availability |
| `test_game_repository.py` | Game + participation records |
| `test_player_service.py` | Full player lifecycle |
| `test_game_service.py` | Game creation, listing |

Run with verbose output:

```bash
pytest -v
```

---

## Bot Features (MVP)

| Feature | Description |
|---|---|
| `/start` | Registers new user, shows menu or starts onboarding |
| Onboarding | 4-step wizard: language → level → area → courts |
| 🎾 Find Partner | Lists players in same area ±0.5 NTRP level |
| 📅 Create Game | 5-step wizard: court → area → date → time → type/level |
| 🔥 Available Now | Mark yourself available for 2 hours; see others available |
| 👤 My Profile | View your profile summary |
| ⚙️ Settings | Change language, area, level, preferred courts |

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `GET` | `/api/v1/players/` | List all players |
| `POST` | `/api/v1/players/` | Create player |
| `GET` | `/api/v1/players/{id}` | Get player by ID |
| `PATCH` | `/api/v1/players/{telegram_id}` | Update player profile |
| `GET` | `/api/v1/players/{telegram_id}/partners` | Find matching partners |
| `GET` | `/api/v1/games/` | List open games (optional `?area=`) |
| `POST` | `/api/v1/games/` | Create game |
| `GET` | `/api/v1/games/{id}` | Get game by ID |

---

## Production Deployment

Switch to PostgreSQL by updating `.env`:

```env
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/baseline
APP_ENV=production
DEBUG=false
```

Then run migrations:

```bash
alembic upgrade head
```

### Automatic deployment (GitHub Actions)

Every push to `master` triggers `.github/workflows/deploy.yml`, which SSHes
into the Hetzner production server and redeploys the `baseline` systemd
service. The server is made to mirror GitHub exactly — any local changes
or drift on the server are discarded, not merged:

```
git fetch origin
git reset --hard origin/master
source .venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart baseline
sleep 3
sudo systemctl status baseline
```

`set -euo pipefail` means the job fails immediately if any step fails —
including `systemctl status` reporting the service as inactive after the
restart.

**Required GitHub Secrets** (repo → Settings → Secrets and variables →
Actions):

| Secret | Value |
|---|---|
| `SERVER_HOST` | Hetzner server hostname or IP |
| `SERVER_USER` | SSH user with access to `~/baseline-platform` |
| `SERVER_SSH_KEY` | Private key for `SERVER_USER` (PEM format) |

**Server-side prerequisite:** `SERVER_USER` must be able to run exactly
two commands under `sudo` without an interactive password prompt — nothing
broader:

```
# /etc/sudoers.d/baseline-deploy
SERVER_USER ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart baseline, /usr/bin/systemctl status baseline
```

Replace `SERVER_USER` with the actual deploy account name, and confirm the
binary path with `which systemctl` on the server (some distros symlink it
under `/bin`). No other command should be granted passwordless `sudo`.

**Manual test procedure:**

1. Confirm the three secrets above are set on the repository.
2. Confirm the sudoers entry above is installed on the server (`sudo -l -U
   SERVER_USER` should list only the two `systemctl` commands).
3. Go to the Actions tab → "Deploy to Production" → "Run workflow" (uses
   the `workflow_dispatch` trigger — no need to push a commit to test).
4. Watch the run: it should complete without printing the SSH key or any
   secret value.
5. On the server, confirm the deploy actually happened:
   ```bash
   sudo systemctl status baseline   # should show "active (running)"
   journalctl -u baseline -n 20     # recent restart, no crash loop
   git log -1                       # HEAD matches origin/master
   ```
6. Push a trivial commit to `master` and confirm the workflow fires
   automatically and the service restarts cleanly.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.12 |
| Bot framework | Aiogram 3.x |
| REST API | FastAPI |
| ORM | SQLAlchemy 2.x (async) |
| Migrations | Alembic |
| Validation | Pydantic v2 |
| Database (dev) | SQLite via aiosqlite |
| Database (prod) | PostgreSQL via asyncpg |
| Config | python-dotenv + pydantic-settings |
| Tests | pytest + pytest-asyncio |

---

## Future Roadmap

- Scheduled job to expire `available_now` flags
- Push notifications for game invitations
- iOS / Android / Web clients (service layer is already ready)
- ELO-based rating updates after match completion
- Court availability integration
