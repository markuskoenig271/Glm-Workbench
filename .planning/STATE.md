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

## First implementation slice DONE: dataset spec + loaders (same session)

`pricing_engine/data.py` now real (first non-stub code): `DatasetSpec` frozen
dataclass, `DATASET_REGISTRY`/`list_datasets`/`load_dataset` (returns (df, spec)),
`load_fremtpl2_freq`/`_sev`, `validate_portfolio(df, spec)`. TDD: red (17 fail) →
green; suite 26 passed, coverage 99%, ruff/mypy clean. Change Validation Workflow
followed: BA/Test agent wrote `.planning/e2e-tests/dataset-spec-loaders.md`
(8 TCs), all executed against the real data — 8/8 PASS, load+validate 678k rows
in 0.04s. Two E2E-doc adjustments recorded in its Results section (tuple return
API; uint8 casts in the broken-portfolio TC). No architecture drift — code matches
the "Datasets" section.

## Data Import slice DONE (same session) — first real UI feature

Engine: `load_portfolio` (CSV path or upload buffer). UI: `pages/01_Data_Import.py`
(built-in load via registry → session_state, CSV upload + column mapping →
ad-hoc DatasetSpec, preview + validation report) and Home shows the active
dataset. Playwright (1.61 + Chromium) added as the E2E harness — first UI E2E:
`.planning/e2e-tests/data-import.md`, TC1–TC4/TC6/TC7 PASSED, TC5 deferred.
Suite 29 passed, ruff/mypy clean.

**Streamlit lessons (cost real debugging time, recorded in the E2E doc):**
sidebar-link navigation keeps `st.session_state`, a full reload/goto starts a
new session (dataset gone after browser refresh — expected behavior for now);
BaseWeb combobox values aren't readable via get_by_text; glide-data-grid
renders hidden header cells that shadow text queries; use `.first` for text
appearing in both message and caption.

## Next steps

1. Data Exploration slice (summary stats, histograms, one-way frequencies —
   aggregate/sample, no raw-row rendering)
2. Promote the scratchpad Playwright scripts into a committed `e2e/` dir
   (TODO item) once a second UI slice exists
3. Open decision: SQLite storage scope (TODO.md)
