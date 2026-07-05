# Schema Recovery Procedure

**Purpose:** the complete, permanent procedure for repairing schema
drift between a live SQLite database and what the Alembic migration
chain says should exist at HEAD — using `scripts/schema_recovery.py`.
This is not a one-off incident fix; it's the standing process for
whenever a database's physical schema and its `alembic_version` record
disagree, whatever the cause.

**Background:** this tool exists because of TECH-010
(`docs/TECH_DEBT.md`) — `create_all_tables()` runs on every startup of
`bot/main.py` and `api/app.py` as a first-run safety net, but it only
creates *missing tables*; it never alters existing ones. If new models
are added to the codebase and the app is started before the matching
Alembic migration is ever run, the database ends up with the new
tables but not the new columns on already-existing tables — and
`alembic_version` never advances, because `create_all_tables()` doesn't
touch it. TECH-010 itself remains deferred (the long-term fix is to
stop relying on `create_all_tables()` in a persistent database at all);
this procedure exists to safely recover from its symptom whenever it
occurs, until that's done.

---

## When to use this

- The bot or API crashes with `sqlite3.OperationalError: no such
  column: ...` or a similar "table/column doesn't exist" error that
  clearly points at a schema mismatch, not application data.
- `alembic current` and the database's actual tables/columns disagree
  — e.g. `alembic_version` is empty or behind, but tables that a later
  migration creates already exist.
- Before running `alembic upgrade head` against any database where
  you're not certain every prior migration was actually applied via
  Alembic itself (as opposed to `create_all_tables()`).

## When NOT to use this

- **Never as a substitute for writing a real migration.** This tool
  only repairs drift against the *current* HEAD migration — it does
  not, and must not, become how new schema changes reach production.
  Every new schema change still goes through `alembic revision
  --autogenerate` + `alembic upgrade head`, exactly as
  `CLAUDE.md`/`docs/ARCHITECTURE.md` already require.
- **Not for data problems.** This tool never reads or writes a single
  row of existing data — it only adds missing tables/columns/indexes.
  If the actual complaint is about data (wrong values, corruption,
  missing rows), this is the wrong tool entirely.
- **Not if `--verify` reports a `TYPE MISMATCH`.** That means a column
  exists in both places but disagrees on type/nullability — not a
  purely additive difference. Stop and investigate by hand; the tool
  will refuse to `--repair` while any are present, on purpose.
- **Not against a database you haven't backed up through some means
  outside this tool as well**, if that's your organization's normal
  practice — `--repair` takes its own backup automatically, but there's
  no harm in an extra one if you have infrastructure for it already.

---

## Procedure: verify → repair → stamp → validate → rollback

### 1. Verify (read-only, safe to run anytime, changes nothing)

```bash
python scripts/schema_recovery.py --verify
```

`--db-path` is optional — the tool auto-detects the target file from
`DATABASE_URL` (checked in the real environment first, then the
project's `.env`/`.env.dev`/`.env.production`, the same way the
application itself resolves it), so this exact command works unchanged
on a laptop and on the server. It prints which path it detected and
where it came from. Only a file-based SQLite URL can be auto-detected;
if it can't determine one, it says so and asks for `--db-path`
explicitly rather than guessing — pass it yourself to target a specific
file:

```bash
python scripts/schema_recovery.py --db-path /path/to/production.db --verify
```

Reads every difference between what the Alembic migration chain
produces (built fresh, in a disposable temporary database, by actually
running `alembic upgrade head` there — never against your real
database) and what your target database actually contains. Prints one
of:

- `No drift detected. Schema matches the Alembic migration chain's HEAD
  exactly.` — nothing further to do.
- A list of `MISSING TABLE` / `MISSING COLUMN` / `MISSING INDEX` /
  `TYPE MISMATCH` lines. Only the first three are auto-repairable.

**Do this first, always, before `--repair`.** `--repair` also runs this
internally, but running it standalone first lets you read the plan
before anything is written.

### 2. Repair (writes to the target database)

```bash
python scripts/schema_recovery.py --repair
```

Same auto-detection as `--verify`. Refuses immediately if any
`TYPE MISMATCH` is present. Otherwise:

1. Copies the target file to `<path>.backup-<UTC timestamp>` —
   mandatory, always, before anything else.
2. Adds only what's missing: `CREATE TABLE` (verbatim, from the shadow
   schema) for missing tables, `ALTER TABLE ... ADD COLUMN` for missing
   columns (with an inline `REFERENCES` clause if the column is a
   foreign key — this is valid SQLite and does not require rebuilding
   the table), `CREATE INDEX`/`CREATE UNIQUE INDEX` for missing
   indexes.
3. Re-runs verification against the now-repaired database and prints
   the result.

If verification after repair is *not* clean, the tool exits non-zero
and tells you not to proceed to Step 3 — investigate before continuing.

### 3. Stamp (the one step this tool deliberately never does for you)

Only after `--repair` reports "Repair complete and verified clean":

```bash
alembic stamp head
```

This is the real, official Alembic CLI — not the recovery script. The
recovery tool never writes to `alembic_version` itself, on purpose:
that table's contents should only ever be written by Alembic's own
tooling, so there is exactly one place that can ever put it in an
inconsistent state, and it isn't this script.

### 4. Validate

```bash
alembic current
```

Should now print the HEAD revision. Then restart the bot/API and
confirm the original crash no longer reproduces — the specific error
message you started with is the best acceptance test available.

### 5. Rollback (if anything looks wrong after Step 2, 3, or 4)

Stop the bot/API. Replace the live database file with the
`<path>.backup-<timestamp>` file `--repair` created in Step 2. Restart.
Because SQLite is a single file, this is a complete, exact restoration
— there is no partial-rollback case to reason about. The backup is
never touched or deleted by the tool itself; it's yours to keep or
remove once you're confident the repair is correct.

---

## Notes

- Every step above is safe to re-run. `--verify` never writes.
  `--repair` re-checks before every write it makes; running it twice in
  a row on an already-repaired database does nothing the second time
  ("Nothing to repair").
- The tool contains no Baseline business logic — it never imports
  `backend.app`. It only introspects SQLite schema and shells out to
  the real `alembic` CLI to build its reference schema. See
  `scripts/schema_recovery.py`'s own module docstring for the full
  technical design.
