#!/usr/bin/env python3
"""Baseline Schema Recovery Tool.

Repairs schema drift between a live SQLite database and what the
Alembic migration chain says should exist at HEAD.

The source of truth is the migration chain itself, NOT the current
SQLAlchemy models. This tool builds a disposable "shadow" database by
running the real `alembic upgrade head` against a brand-new temporary
file, then diffs that shadow schema against the target database.
Recovery therefore restores exactly the *released* schema — whatever
the migration chain actually produces today — never whatever the ORM
models currently claim, which can differ if a model was edited before
its migration was written.

This tool contains no Baseline business logic: it never imports
`backend.app`. It only introspects SQLite schema (stdlib `sqlite3`)
and shells out to the real `alembic` CLI to build the shadow database.

`--db-path` is optional. When omitted, the target database is
auto-detected from `DATABASE_URL` — checked in the real process
environment first, then in the project's dotenv file (`.env`,
`.env.dev`, or `.env.production`, selected by the `ENV` variable the
same way `backend.app.core.config` picks one — that selection logic is
duplicated here in a few lines, not imported, to keep this tool fully
independent). Only a file-based SQLite URL can be auto-detected; if
`DATABASE_URL` points elsewhere, or can't be found at all, the tool
says so and asks for `--db-path` explicitly rather than guessing. This
means the same command works unchanged on a laptop and on the server:

    python scripts/schema_recovery.py --verify

Modes (mutually exclusive, exactly one required):

    --verify   Read-only. Builds the shadow schema, diffs it against
               the target database, and prints every difference.
               Never writes to the target database.

    --repair   Takes a mandatory file-level backup of the target
               database first, then applies ONLY additive differences
               found by the same diff --verify uses: missing tables,
               missing columns, missing indexes. Never drops or alters
               anything that already exists, and never touches
               existing row data. Re-runs verification afterward and
               reports the result. Never writes to `alembic_version` —
               recording that the schema is now current remains a
               separate, official `alembic stamp head`, run by a human.

If the diff ever finds a column that exists in both schemas but with a
different type/nullability, this is reported but never auto-repaired —
that is not a purely additive change and requires human judgement.

Usage:
    python scripts/schema_recovery.py --verify
    python scripts/schema_recovery.py --repair

    # or, to target a specific file explicitly:
    python scripts/schema_recovery.py --db-path ./baseline.db --verify
"""
import argparse
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

_IGNORED_TABLES = {"sqlite_sequence", "alembic_version"}

# Mirrors backend.app.core.config._resolve_env_file()'s own ENV -> file
# mapping exactly, duplicated here (not imported) to keep this tool
# fully independent of backend.app.
_ENV_FILE_BY_ENV = {
    "development": ".env.dev",
    "dev": ".env.dev",
    "production": ".env.production",
    "prod": ".env.production",
}


@dataclass
class TableSchema:
    name: str
    create_sql: str
    columns: dict  # column_name -> PRAGMA table_info row tuple
    indexes: dict  # index_name -> CREATE INDEX sql text


@dataclass
class SchemaDiff:
    missing_tables: list = field(default_factory=list)       # list[TableSchema]
    missing_columns: list = field(default_factory=list)      # list[(table, col_name, col_row)]
    missing_indexes: list = field(default_factory=list)      # list[(table, index_name, sql)]
    mismatched_columns: list = field(default_factory=list)   # list[(table, col_name, shadow_row, target_row)]

    def is_clean(self) -> bool:
        return not (self.missing_tables or self.missing_columns or self.missing_indexes)

    def has_unrepairable(self) -> bool:
        return bool(self.mismatched_columns)


def _read_schema(db_path: Path) -> dict:
    """table_name -> TableSchema. Read-only connection."""
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        tables: dict[str, TableSchema] = {}
        rows = conn.execute(
            "SELECT name, sql FROM sqlite_master WHERE type='table'"
        ).fetchall()
        for name, create_sql in rows:
            if name in _IGNORED_TABLES:
                continue
            columns = {}
            for row in conn.execute(f"PRAGMA table_info('{name}')").fetchall():
                columns[row[1]] = row  # row[1] is the column name
            indexes = {}
            for idx_name, idx_sql in conn.execute(
                "SELECT name, sql FROM sqlite_master WHERE type='index' AND tbl_name=? AND sql IS NOT NULL",
                (name,),
            ).fetchall():
                indexes[idx_name] = idx_sql
            tables[name] = TableSchema(name=name, create_sql=create_sql, columns=columns, indexes=indexes)
        return tables
    finally:
        conn.close()


def _foreign_keys(db_path: Path, table: str) -> list:
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        return conn.execute(f"PRAGMA foreign_key_list('{table}')").fetchall()
    finally:
        conn.close()


def _build_shadow_schema(tmp_dir: Path) -> Path:
    """Run the real `alembic upgrade head` against a fresh, empty,
    temporary SQLite file. This IS the source of truth — whatever the
    migration chain actually produces, never the ORM models."""
    shadow_path = tmp_dir / "shadow.db"
    env = {**os.environ, "DATABASE_URL": f"sqlite+aiosqlite:///{shadow_path}"}
    result = subprocess.run(
        ["alembic", "upgrade", "head"],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(
            "FATAL: could not build the reference schema — `alembic upgrade "
            "head` failed against a brand-new, empty database. The migration "
            "chain itself is broken; this tool cannot proceed.",
            file=sys.stderr,
        )
        print(result.stdout, file=sys.stderr)
        print(result.stderr, file=sys.stderr)
        sys.exit(2)
    return shadow_path


def _diff(shadow: dict, target: dict) -> SchemaDiff:
    diff = SchemaDiff()
    for name, shadow_table in shadow.items():
        if name not in target:
            diff.missing_tables.append(shadow_table)
            continue

        target_table = target[name]

        for col_name, shadow_row in shadow_table.columns.items():
            if col_name not in target_table.columns:
                diff.missing_columns.append((name, col_name, shadow_row))
                continue
            target_row = target_table.columns[col_name]
            # row = (cid, name, type, notnull, dflt_value, pk) — compare
            # everything except cid (ordinal position may legitimately differ).
            if shadow_row[2:] != target_row[2:]:
                diff.mismatched_columns.append((name, col_name, shadow_row, target_row))

        for idx_name, idx_sql in shadow_table.indexes.items():
            if idx_name not in target_table.indexes:
                diff.missing_indexes.append((name, idx_name, idx_sql))

    return diff


def _column_ddl(table: str, col_row, shadow_path: Path) -> str:
    """Build one additive `ADD COLUMN` clause from a shadow PRAGMA
    table_info row, including an inline REFERENCES clause if the
    shadow schema declares this column as a foreign key. A plain
    ADD COLUMN with an inline REFERENCES is valid SQLite and does not
    require Alembic's batch-mode table-rebuild dance (verified
    empirically before writing this tool)."""
    _, name, col_type, notnull, dflt_value, _pk = col_row

    if notnull and dflt_value is None:
        raise ValueError(
            f"{table}.{name} is declared NOT NULL with no default in the "
            "migration chain — cannot be added safely to a table that may "
            "already contain rows. Refusing to guess; this needs a human."
        )

    parts = [name, col_type]
    if notnull:
        parts.append("NOT NULL")
    if dflt_value is not None:
        parts.append(f"DEFAULT {dflt_value}")

    fk = next((row for row in _foreign_keys(shadow_path, table) if row[3] == name), None)
    if fk:
        # row = (id, seq, table, from, to, on_update, on_delete, match)
        parts.append(f"REFERENCES {fk[2]}({fk[4]})")

    return " ".join(parts)


def _print_diff(diff: SchemaDiff) -> None:
    if diff.is_clean() and not diff.has_unrepairable():
        print("No drift detected. Schema matches the Alembic migration chain's HEAD exactly.")
        return

    print("Schema drift detected:")
    for t in diff.missing_tables:
        print(f"  MISSING TABLE       {t.name}")
    for table, col, _ in diff.missing_columns:
        print(f"  MISSING COLUMN      {table}.{col}")
    for table, idx, _ in diff.missing_indexes:
        print(f"  MISSING INDEX       {idx} (on {table})")
    for table, col, shadow_row, target_row in diff.mismatched_columns:
        print(f"  TYPE MISMATCH       {table}.{col} — migration chain expects {shadow_row[2:]}, found {target_row[2:]}")

    if diff.mismatched_columns:
        print(
            "\nType mismatches are NOT auto-repairable by this tool "
            "(changing an existing column is not purely additive). "
            "--repair will refuse to run while any are present."
        )


def verify(db_path: Path) -> SchemaDiff:
    with tempfile.TemporaryDirectory() as tmp:
        shadow_path = _build_shadow_schema(Path(tmp))
        shadow_schema = _read_schema(shadow_path)
        target_schema = _read_schema(db_path)
        diff = _diff(shadow_schema, target_schema)
    _print_diff(diff)
    return diff


def repair(db_path: Path) -> None:
    print("Running verification first...\n")
    diff = verify(db_path)

    if diff.has_unrepairable():
        print(
            "\nRefusing to repair: unrepairable (non-additive) differences "
            "are present. Resolve those manually first.",
            file=sys.stderr,
        )
        sys.exit(1)

    if diff.is_clean():
        print("\nNothing to repair.")
        return

    backup_path = db_path.with_name(
        f"{db_path.name}.backup-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    )
    shutil.copy2(db_path, backup_path)
    print(f"\nBackup created: {backup_path}")

    with tempfile.TemporaryDirectory() as tmp:
        shadow_path = _build_shadow_schema(Path(tmp))

        conn = sqlite3.connect(db_path)
        try:
            for t in diff.missing_tables:
                print(f"Creating table: {t.name}")
                conn.execute(t.create_sql)
                for idx_sql in t.indexes.values():
                    conn.execute(idx_sql)

            for table, col_name, col_row in diff.missing_columns:
                ddl = _column_ddl(table, col_row, shadow_path)
                print(f"Adding column: {table}.{col_name}")
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {ddl}")

            for table, idx_name, idx_sql in diff.missing_indexes:
                print(f"Creating index: {idx_name} (on {table})")
                conn.execute(idx_sql)

            conn.commit()
        except Exception:
            conn.rollback()
            print(
                f"\nRepair failed and was rolled back. The backup at "
                f"{backup_path} was never touched; the target database is "
                f"unchanged from before this run.",
                file=sys.stderr,
            )
            raise
        finally:
            conn.close()

    print("\nRe-running verification to confirm the repair...")
    post_diff = verify(db_path)
    if not post_diff.is_clean() or post_diff.has_unrepairable():
        print(
            "\nWARNING: differences remain after repair. Do NOT run "
            "`alembic stamp head` until --verify reports clean.",
            file=sys.stderr,
        )
        sys.exit(1)

    print(
        "\nRepair complete and verified clean.\n"
        "This tool never touches alembic_version. To record that the "
        "schema now matches head, run:\n\n"
        "    alembic stamp head\n"
    )


def _resolve_env_file() -> Path:
    """Which dotenv file to read DATABASE_URL from, if it's not already
    in the real process environment — same ENV-based selection
    backend.app.core.config uses, duplicated rather than imported."""
    env = os.environ.get("ENV", "").strip().lower()
    candidate = _ENV_FILE_BY_ENV.get(env)
    if candidate and (REPO_ROOT / candidate).is_file():
        return REPO_ROOT / candidate
    return REPO_ROOT / ".env"


def _read_database_url_from_dotenv(env_file: Path) -> str | None:
    if not env_file.is_file():
        return None
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        if key.strip().upper() == "DATABASE_URL":
            return value.strip().strip('"').strip("'")
    return None


def _sqlite_path_from_url(database_url: str) -> Path | None:
    """Extract the file path from a sqlite[+driver]:///<path> URL.
    Returns None for :memory: or any non-sqlite URL — this tool cannot
    auto-detect a target in either case."""
    if "sqlite" not in database_url:
        return None
    _, _, path_part = database_url.partition(":///")
    if not path_part or path_part == ":memory:":
        return None
    path = Path(path_part)
    if not path.is_absolute():
        path = REPO_ROOT / path
    return path


def _resolve_db_path(explicit: Path | None) -> Path:
    """--db-path always wins if given. Otherwise, auto-detect from
    DATABASE_URL: the real environment first (matching
    pydantic-settings' own precedence — real env vars override the
    dotenv file), then the ENV-selected dotenv file. Only ever used for
    a file-based SQLite target; anything else asks for --db-path
    explicitly rather than guessing."""
    if explicit is not None:
        return explicit

    database_url = os.environ.get("DATABASE_URL")
    source = "the DATABASE_URL environment variable"
    if not database_url:
        env_file = _resolve_env_file()
        database_url = _read_database_url_from_dotenv(env_file)
        source = f"DATABASE_URL in {env_file}"

    if not database_url:
        print(
            "FATAL: --db-path was not given, and no DATABASE_URL could be "
            "found (checked the environment, then .env/.env.dev/"
            ".env.production per the ENV variable). Pass --db-path explicitly.",
            file=sys.stderr,
        )
        sys.exit(2)

    db_path = _sqlite_path_from_url(database_url)
    if db_path is None:
        print(
            f"FATAL: found {source} = {database_url!r}, but this is not a "
            "file-based SQLite URL this tool can locate automatically "
            "(not sqlite, or :memory:). Pass --db-path explicitly.",
            file=sys.stderr,
        )
        sys.exit(2)

    print(f"Auto-detected database path from {source}: {db_path}")
    return db_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--db-path",
        type=Path,
        default=None,
        help=(
            "Path to the target SQLite database file. Optional — if omitted, "
            "auto-detected from DATABASE_URL (the real environment, then the "
            "project's .env file), the same way the application resolves it."
        ),
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--verify", action="store_true", help="Read-only: print differences, write nothing.")
    mode.add_argument("--repair", action="store_true", help="Back up, then apply additive-only fixes.")
    args = parser.parse_args()

    db_path = _resolve_db_path(args.db_path)

    if not db_path.exists():
        print(f"FATAL: {db_path} does not exist.", file=sys.stderr)
        sys.exit(2)

    if args.verify:
        verify(db_path)
    else:
        repair(db_path)


if __name__ == "__main__":
    main()
