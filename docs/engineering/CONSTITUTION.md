# Baseline Engineering Constitution

This document defines the mandatory engineering rules for the Baseline
project. Every rule uses **MUST** / **MUST NOT**. These are not
recommendations — they apply to every contributor, human or AI, on every
change.

---

## Mission

Engineering exists to help two people meet on a tennis court faster. Every
technical decision MUST be judged against that outcome, not against
engineering elegance for its own sake.

---

## Core Principles

- Every feature MUST solve a real, named user problem.
- Implementation MUST take the shortest viable user flow.
- Existing services, repositories, keyboards, and text keys MUST be reused
  before new ones are written.
- Future or unimplemented concepts (rating, reputation, coach verification,
  etc.) MUST NOT be exposed in user-facing text or UI until they ship.
- User-facing language MUST use product terms ("organize", "invite"), not
  internal/technical terms.

---

## Sprint Rules

- A sprint MUST implement only its approved scope — no adjacent features,
  no unrelated refactors.
- A new sprint MUST NOT start until the current sprint is committed and its
  documentation is updated.
- A "polish" sprint MUST NOT introduce new functionality, only presentation
  changes to existing behavior.
- Scope changes mid-sprint MUST be raised explicitly, not absorbed silently.

---

## Architecture Rules

- All new domains MUST follow Model → Repository → Service → Handler.
- Handlers MUST NOT contain business logic; they call a service and return
  a response.
- Repositories MUST only access data; they MUST NOT contain business rules.
- Services MUST be transport-agnostic (usable from bot, API, or tests
  identically).
- Every new ORM model MUST be registered in
  `backend/app/database/models/__init__.py`.
- Any database schema change MUST go through an Alembic migration —
  `create_all_tables()` MUST NOT be relied on for schema changes.
- An architecture change MUST NOT be introduced without a document
  (ADR or design doc) describing it — see Documentation Rules.

---

## Development Workflow

1. Understand the task before touching anything.
2. Read only the files required for the task.
3. Implement only what was requested.
4. Keep the existing architecture unchanged unless the task explicitly
   approves a change.
5. Run the full automated test suite.
6. Verify the bot dispatcher builds, for any bot-facing change.
7. Present a summary: modified files, deviations, tests, results.
8. Wait for human review.
9. Commit only after explicit approval.

---

## Git Rules

- A commit MUST NOT be created without explicit user approval.
- `git commit --amend`, force-push, and history rewrites MUST NOT be used
  unless explicitly requested.
- A commit message MUST describe exactly what was implemented, not restate
  the diff.
- One approved task SHOULD produce one commit; unrelated work MUST NOT be
  bundled into the same commit.
- Secrets and credentials MUST NOT be committed.

---

## Testing Rules

- Every feature MUST ship with automated tests covering its new behavior.
- The full `pytest` suite MUST pass before a task is reported complete.
- Tests MUST run against the in-memory SQLite fixtures — the database layer
  MUST NOT be mocked.
- A bug fix MUST include a regression test reproducing the original defect.

---

## Deployment Rules

- Untested code MUST NOT be deployed.
- Every deployment MUST pass this checklist first:

  - [ ] GitHub is up to date
  - [ ] Working tree clean
  - [ ] Correct branch
  - [ ] Tests pass
  - [ ] Python version verified
  - [ ] Requirements verified
  - [ ] Rollback available

- A deployment MUST NOT proceed if any checklist item fails.

---

## Documentation Rules

- Every feature MUST update the documentation that describes it
  (release notes, roadmap, design docs, or `CLAUDE.md`, as applicable).
- An architecture or workflow decision MUST NOT remain undocumented once
  implemented.
- Documentation updates MUST NOT invent scope beyond what was actually
  built.

---

## Decision Making

- A discovered conflict between instructions, code, or architecture MUST be
  surfaced before implementation — not silently resolved either way.
- A requirement MUST be clarified with the user rather than guessed when
  the decision is high-risk, destructive, or hard to reverse.
- A low-risk, reversible judgment call MAY proceed without asking, provided
  the reasoning is stated in the summary.
- Silence from the user on a past decision MUST NOT be read as blanket
  approval for unrelated future decisions.

---

## Definition of Done

A task is done only when all of the following are true:

- Implementation matches the approved scope exactly.
- Automated tests exist and pass for the new behavior.
- The full test suite passes.
- The dispatcher builds successfully (bot-facing changes).
- Relevant documentation is updated.
- A summary has been presented for human review.
- The change is committed only after explicit approval.

---

## Workflow

```
Feature
  → Test
    → Manual QA
      → Commit
        → Push
          → Documentation update
            → Next Sprint
```

Each stage MUST complete before the next one starts.

---

## Never

- Never implement a new feature before finishing the current Sprint.
- Never execute multiple dangerous commands without waiting for results.
- Never deploy untested code.
- Never skip documentation updates.
- Never introduce architecture changes without documenting them.
