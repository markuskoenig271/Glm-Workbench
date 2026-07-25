# Project State

Rolling "where I left off" file (committed). Overwritten each session.
Read this + `TODO.md` at the start of every session. See `PROJECT.md` for the spec.

---

## Last updated: 2026-07-25 (session 1 — repo bootstrap, spec-only)

## Headline

Brand-new repo, **spec-only state** — no code yet. This session cleaned the bootstrap
files: the planning files (`STATE`/`TODO`) had been copied from another project
(Lex-VIA/Decision-Parsing) and were reset; CLAUDE.md was purged of leftovers from that
project; `PROJECT.md` was filled from `docs/architecture.md` + `docs/ui_screens.md`.
Policy change (Markus): private single-committer project — state file is plain
`STATE.md` and committed (only `.planning/archive/` stays gitignored).

## What exists

- `docs/architecture.md` — Streamlit app + `pricing_engine/` package design
- `docs/ui_screens.md` — 10 UI screens (Home → Reports)
- `.planning/PROJECT.md` — spec filled from the docs
- No `pyproject.toml`, no source, no tests

## Next steps

Scaffold the project (see TODO.md "Project setup"). Architecture-first rule is already
satisfied for the initial build — the design in `docs/` is the approved baseline.
