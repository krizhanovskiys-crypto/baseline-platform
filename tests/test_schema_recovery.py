"""Integration test for scripts/schema_recovery.py.

This tool is a standalone, synchronous CLI script with no dependency on
`backend.app` — it is invoked as a real subprocess here, exactly as an
operator would run it, rather than imported and called in-process. The
in-repo `test_tournament_service.py` / lifecycle tests already cover
Baseline's own business logic; this file covers only the recovery
tool's own contract: --verify and --repair against an already-healthy
database must both report nothing to do and exit 0. Schema-drift
scenarios (missing tables/columns, idempotent repair, backup/rollback)
were verified manually against a precise reproduction of the reported
production incident before this tool was approved — this test adds the
one remaining case that wasn't yet covered by an automated check: the
healthy/no-op path.
"""
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "schema_recovery.py"


def _build_healthy_database(db_path: Path) -> None:
    """A database that has been migrated to HEAD via the real Alembic
    CLI — the same mechanism the recovery tool itself uses to build its
    own reference schema."""
    env = {**os.environ, "DATABASE_URL": f"sqlite+aiosqlite:///{db_path}"}
    result = subprocess.run(
        ["alembic", "upgrade", "head"],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"failed to build a healthy test database: {result.stderr}"


def _run_tool(db_path: Path, mode: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--db-path", str(db_path), mode],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )


def test_verify_on_healthy_database_reports_nothing_and_exits_zero(tmp_path) -> None:
    db_path = tmp_path / "healthy.db"
    _build_healthy_database(db_path)

    result = _run_tool(db_path, "--verify")

    assert result.returncode == 0, result.stderr
    assert "No drift detected" in result.stdout
    assert "MISSING" not in result.stdout
    assert "MISMATCH" not in result.stdout


def test_repair_on_healthy_database_reports_nothing_to_repair_and_exits_zero(tmp_path) -> None:
    db_path = tmp_path / "healthy.db"
    _build_healthy_database(db_path)

    result = _run_tool(db_path, "--repair")

    assert result.returncode == 0, result.stderr
    assert "Nothing to repair" in result.stdout
    # A healthy database must never be touched — --repair only creates
    # a backup once it has confirmed there is something to fix.
    backups = list(tmp_path.glob("healthy.db.backup-*"))
    assert backups == []
