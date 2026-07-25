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

## Data Exploration slice DONE (same session)

New `pricing_engine/exploration.py` — aggregate-only engine functions (suite 43,
coverage 99%). `pages/02_Data_Exploration.py`: guard → metrics row (freMTPL2:
678,013 policies / 358,499 exposure / 36,102 claims / frequency 0.1007) →
summary table → one-way frequency (Altair, `sort=None` to keep quantile-band
order; plain st.bar_chart would alphabetize) → histogram → correlations.
E2E TC1–TC8 all passed first run; TC9 (selectbox change) deferred/manual.
Performance: summary + all 9 one-ways on full data in 0.32s. Dataviz-skill
rules applied: single hue (#4c78a8), no legend on single series, tooltips,
table views accompany charts. SQLite decision 7 recorded earlier this session.

## Feature Engineering slice DONE (same session)

`pricing_engine/preprocessing.py` real (bin/log/encode/cap; suite 56, 99.5%
coverage). `pages/03_Feature_Engineering.py`: predictors multiselect → spec,
exposure cap (real data: 1,224 rows > 1.0), band + log builders that append to
the spec, encoding info note (GLM formula encodes automatically — no manual
one-hot on 678k rows), live spec summary. Key implementation pattern: ALL
mutations in on_click/on_change callbacks + flash messages — direct
session_state writes after widget instantiation would throw. E2E: engine +
guard/setup/cap/binning/downstream TCs all passed first run; TC8
deferred/manual.

## Frequency Model slice DONE (same session) — the workbench fits real GLMs

Engine: `glm.build_formula`/`fit_frequency_glm` (Poisson/NegBin, log link,
log-exposure offset), `diagnostics.coefficient_table` (exp_coef, significance)
+ `information_criteria`, NEW `storage.py` (decision 7 delivered: SQLite
model_runs, GLM_DB_PATH override). UI `pages/04_Frequency_Model.py`: family
select → formula preview → spinner fit → metrics → coefficient table with
plain-language strongest-effects lines + insignificance warning → persistent
run history. Suite 70 passed, 99.6% coverage, ruff/mypy clean.

**Real-data results (E2E-verified):** full Poisson fit on 678,013 rows in
~12 s; exp(Intercept)=0.0191; BonusMalus +2.3% per point (p≪0.001) — domain
truth holds; AIC 286,703. Playwright lesson added: after an action, await
late-rendered sections with expect() before non-waiting .count() asserts.

## Diagnostics + Prediction slices DONE (same session) — V1 COMPLETE

All 7 V1 screens are functional. Diagnostics: residuals/QQ/decile-calibration
engine functions (aggregate-only; 0.15s on 678k) + CI-whisker relativity chart,
residual histogram, QQ, observed-vs-predicted grouped bars, statsmodels summary.
Prediction: predict_frequency (offset-free rate × exposure; in-sample balance
EXACT — expected 36,102 = observed 36,102) + single-policy what-if with
median defaults + batch with CSV download. Suite 81 passed, 99.6% coverage,
ruff/mypy clean; both E2E plans executed green (widget-change TCs deferred
per precedent). tests/__init__.py added (mypy module-name fix); scipy in mypy
overrides.

## V1 committed (ba9cc3b) + stepwise slice built (V1.x, Markus' ask)

`glm.stepwise_selection` (backward/forward by AIC/BIC, progress callback,
step log; candidate fits NOT in run history) + "Variable selection" section on
the Frequency Model page with Adopt-into-spec button. Suite 87, ruff/mypy
clean. E2E: unit test proves Noise gets dropped; real-data reduced-spec run
kept all 3 genuine predictors (correct — stops round 1, 9s); UI section
renders; full UI run manual/deferred (minutes by design). Regularisation
recorded as backlog with the no-inference trade-off.

## Next steps

1. Commit the stepwise slice
2. Markus' manual walkthrough incl. the deferred/manual TCs (full stepwise
   UI run: expect ~5-10 min); promote Playwright scripts to `e2e/` (TODO)
3. Then V2 (severity) per roadmap — freMTPL2sev is already downloaded
