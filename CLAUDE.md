# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

GLM Workbench — a local tool to test out and learn Generalized Linear Models for
actuarial pricing. **V1 reproduces the Chapter 27 car-insurance frequency example**
from Parodi's *Pricing in General Insurance* (`docs/car-insurance.md`); severity,
pure premium, and a generic workbench follow as V2–V4. Spec lives in
`.planning/PROJECT.md`; design in `docs/architecture.md` + `docs/ui_screens.md`.

## Tech Stack

- **Frontend and Backend:** Streamlit (single local app)
- **Storage:** SQLite

## Commands

### Quick Start

```bash
uv sync                            # install dependencies
uv run streamlit run app.py        # launch the app
```

```bash
# Tests (coverage gate: 75%)
uv run pytest

# Lint & type check
uv run ruff check pricing_engine/ tests/ app.py pages/
uv run ruff format --check pricing_engine/ tests/ app.py pages/
uv run mypy pricing_engine/ tests/

# Auto-fix lint & formatting
uv run ruff check . --fix
uv run ruff format .
```

## Architecture

See `docs/architecture.md` (approved baseline). In short: a Streamlit UI
(`app.py` + `pages/`, one page per screen in `docs/ui_screens.md`) over a
`pricing_engine/` package (data, preprocessing, glm, prediction, diagnostics, report).

## Rules

- Architecture first — no significant implementation without approved design in `docs/`
- TDD mandatory — tests before implementation, 75%+ coverage target
- NEVER commit secrets — use `.env` (see `.env.example`)
- NEVER install packages globally — use virtual environment
- PREFER `uv` over `poetry` over `pip`

## Git

**Branch:** `feat/`, `fix/`, `refactor/`, `chore/`, `docs/`

**Commits:** Conventional commits (`feat(scope): message`)

**Author:** use the identity from `git config user.name` — no Co-Authored-By or other references.

## Change Validation Workflow

When making changes, always follow this multi-agent workflow:

1. **BA-Agent** — Spawn a Business Analyst agent that thinks as an end-user. It identifies the user-facing scenarios and acceptance criteria affected by the change.
2. **Test Agent Interview** — A Testing agent interviews the BA-Agent to extract concrete E2E test cases. These are written as `.md` files (stored in `.planning/e2e-tests/`) describing step-by-step scenarios to execute.
3. **E2E Test Execution** — Once coding is complete, the Test Agent executes these test cases:
   - **If a UI is present:** via Playwright (browser automation).
   - **If no UI is present:** via API calls, CLI invocation, or another suitable tool matching the interface under test.

All changes must pass the documented E2E scenarios before being considered done.

## Documentation Paths

Planning is intentionally minimal — no GSD/phase structure.

| Path                          | Purpose                                                  | Shared?              |
| ----------------------------- | ------------------------------------------------------- | -------------------- |
| `.planning/PROJECT.md`        | Project spec: definition, scope, key decisions          | **committed**        |
| `.planning/TODO.md`           | Living list of open work items and technical debt       | **committed**        |
| `.planning/STATE.md`          | Rolling "where I left off" state                        | **committed**        |
| `.planning/archive/`          | Superseded state snapshots (historical only)            | local (gitignored)   |
| `docs/`                       | Architecture and design docs                            | committed            |

This is a private single-committer project, so all planning files (`PROJECT.md`, `TODO.md`,
`STATE.md`) are committed — no per-committer state-file scheme.

## Key Testing Patterns

- Tests use a `tmp_db` fixture (pytest `tmp_path`-based) for isolated SQLite databases
- Pure computation (GLM fitting, metrics) is tested directly on the `pricing_engine/`
  package — keep it importable without Streamlit
- (Extend this section as the test suite takes shape)

## Session Continuity

At the start of every session:
1. Read `.planning/STATE.md` — where you left off (create it if absent)
2. Read `.planning/TODO.md` — the canonical list of open work items and technical debt
3. Skim `.planning/PROJECT.md` if you need the project spec / scope

At natural stopping points or before the user exits (e.g. when the user says "save session"):
1. Update `.planning/TODO.md` with any new items discovered or items completed
2. Overwrite `.planning/STATE.md` with what was done, open issues, and next steps
3. Check whether this session's changes made `docs/architecture.md` (or related `docs/` design
   docs) out of date — i.e. the "Architecture first" rule's design no longer matches the code.
   If so, add a TODO item flagging exactly what drifted (file + what changed) so the doc can be
   brought back in sync. Do not silently rewrite the architecture doc as part of saving.
