# START HERE — Baseline Context Rebuild

Copy this file's contents into the first message of every new Claude or
ChatGPT session that will work on this repository. It instructs both AI
systems identically.

---

You are continuing the Baseline project.

Do not trust chat history.

Do not trust memory.

Do not fully trust documentation either — the repository itself is the
only source of truth. Priority order when anything conflicts:

**Repository > `docs/ai/PROJECT_STATE.md` > everything else.**

Git is truth. `PROJECT_STATE.md` is a fast index into that truth, not a
replacement for it.

## STEP 0 — Repository Reality Check

Before reading any documentation, inspect the actual repository:

- `git status`
- `git branch`
- `git log -5 --oneline`
- Latest migration (`alembic/versions/`, most recent file)
- Latest test count, if available (run the suite or check the most
  recent run's output)
- Current modified/untracked files

Compare what this shows against `docs/ai/PROJECT_STATE.md`. If they
differ — a different sprint, a different commit, a different test
count, uncommitted changes `PROJECT_STATE.md` doesn't mention — **STOP.
Update `docs/ai/PROJECT_STATE.md` first.** Only then continue.

## STEP 1 — Context Rebuild

Run Context Rebuild (see `CLAUDE.md` → "AI Context Rebuild") — read the
files in the exact order specified there.

## STEP 2 — Project Summary

Return exactly:

- Current Sprint
- Current Priority
- Current Task
- Completed Features
- Architecture Decisions
- Files that must not be modified
- Known Constraints
- Known Technical Debt
- Next Task

## STEP 3 — CTO Review

Wait for CTO Review. The CTO reviews the Project Summary against:

- architecture
- current sprint
- current priorities
- previous decisions
- duplicate work
- contradictions

If the CTO requests corrections, return to **STEP 0** and rebuild —
do not patch the summary in place.

## STEP 4 — Implementation

Only after explicit CTO approval may implementation begin.
