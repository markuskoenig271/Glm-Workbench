# Project State

Rolling "where I left off" file (committed). Overwritten each session.
Read this + `TODO.md` at the start of every session. See `PROJECT.md` for the spec.

---

## Last updated: 2026-07-25 (session 1 — bootstrap, scaffold, V1 rescope)

## Headline

Repo went from empty to a verified running scaffold, then **rescoped to V1 =
Chapter 27 frequency-only** after Markus added `docs/car-insurance.md` (Parodi,
*Pricing in General Insurance*): the app reproduces the book's motor frequency
example before generalizing (roadmap V1 frequency → V2 severity → V3 pure
premium → V4 generic).

Earlier in the session: bootstrap cleanup (planning files had been copied from
another project and were reset; CLAUDE.md purged; plain committed `STATE.md`
policy) — pushed as `2b306ca`. Scaffold + rescope are NOT yet committed.

## What the rescope changed

- `docs/ui_screens.md` rewritten: 7 V1 screens, V2+ screens moved to a roadmap
  section; `docs/architecture.md` updated (V1 markers, roadmap, Chapter 27
  generator in the data layer) + repo-layout drift fixed
- `pages/`: now 01–06 (Data Import, Exploration, Feature Engineering, Frequency
  Model, Diagnostics, Prediction); Severity/Pure Premium/Reports pages deleted
- `pricing_engine/data.py`: Chapter 27 schema constants (target `Claims`, offset
  `Exposure`, 8 predictors incl. no-effect Dummy1/Dummy2) +
  `generate_chapter27_portfolio` stub returning (portfolio, hidden true coefficients)
- `prediction.py` gained `predict_frequency` (V1); `diagnostics.py` gained
  `residuals` + `compare_with_true_model`; PROJECT.md decision 5 recorded

## Verified (after rescope)

- `uv run pytest`: 7/7 passed, coverage gate green; ruff + format + mypy clean
- E2E smoke re-passed: HTTP 200, clean log, exactly the 6 V1 pages
  (`.planning/e2e-tests/scaffold-smoke.md`)

## freMTPL2 added as the real dataset (same session, after user question)

freMTPL2 freq+sev downloaded from OpenML (CC0) as Parquet into `data/raw/`
(gitignored; download commands in README) and **verified**: freq 678,013 × 12
(36,102 claims / ~358k policy-years), sev 26,639 claim amounts, 99.3% IDpol join.
pyarrow added as dependency. Decision 6 recorded (PROJECT.md): freMTPL2 over
anonymized Kaggle sets; consequence = **generic dataset spec** (target/offset/
predictors per dataset) instead of hardcoded Chapter 27 columns — architecture.md
"Datasets" section + ui_screens (Home/Import/Exploration) updated, freMTPL2
constants + loader stubs in `pricing_engine/data.py`. Suite 8/8, ruff/mypy clean.
`docs/car-insurance.md` (Markus' book spec) deliberately untouched.

## Synthetic generator backlogged (Markus' call, end of session)

freMTPL2 is now the V1 primary dataset; the Chapter 27 generator + the
educational features needing its hidden DGM (`compare_with_true_model`,
Dummy1/Dummy2 demo) moved to the TODO Backlog. Docs synced on Markus'
instruction: architecture.md (Datasets reordered, backlog markers),
ui_screens.md (Home/Import freMTPL2-only, backlog markers, roadmap), and
car-insurance.md got an implementation-status note at the top — its book-spec
body deliberately unchanged.

## Next steps

1. First implementation slice per TODO: dataset spec/registry, then freMTPL2
   loaders (TDD-first), then Data Import
2. Open decision: SQLite storage scope (TODO.md)
