# TODO

Active work items and technical debt. Check this at the start of every session.

---

## V1 — frequency workbench on freMTPL2 (workflow per docs/car-insurance.md)

Primary V1 dataset is now **freMTPL2** (real data, decision 6); the synthetic
Chapter 27 generator moved to the backlog (2026-07-25, Markus' call).

- [x] **Dataset spec + registry — DONE 2026-07-25.** `DatasetSpec` frozen dataclass
  (name/label/target/offset/predictors, `required_columns`), `DATASET_REGISTRY`
  (fremtpl2_freq), `list_datasets()`, `load_dataset()` in `pricing_engine/data.py`.
- [x] **freMTPL2 loaders — DONE 2026-07-25.** `load_fremtpl2_freq`/`_sev` (Parquet,
  IDpol→int64, module-level default paths so tests can monkeypatch); missing file
  → FileNotFoundError with the curl command. **`validate_portfolio(df, spec)`
  implemented too** (missing columns, non-numeric/negative target, non-positive
  offset, NaN counts). TDD: 18 new unit tests (suite 26); E2E 8/8 PASSED against
  real data (`.planning/e2e-tests/dataset-spec-loaders.md` — load+validate 678k
  rows in 0.04s).
- [x] **Data Import slice — DONE 2026-07-25.** `load_portfolio` (CSV path or
  file-like upload, friendly missing-file error; 3 unit tests, suite 29) +
  `pages/01_Data_Import.py` (source radio; registry-driven built-in load into
  `st.session_state["portfolio"]`/`["spec"]`; CSV upload with column-mapping
  widgets building an ad-hoc DatasetSpec; preview + validation report) + Home
  workflow status reflects the active dataset. Playwright installed (first UI
  E2E): `.planning/e2e-tests/data-import.md` — TC1–TC4, TC6, TC7 PASSED, TC5
  deferred/manual. Known Streamlit behavior: browser refresh = new session =
  dataset must be reloaded.
- [x] **E2E runner harness — DONE 2026-07-29.** All eight scratchpad runners
  promoted to a committed `e2e/` directory: shared `harness.py` (headless app
  launch/teardown on port 8598, `FIXTURES` path), `fixtures/broken_portfolio.csv`,
  README with run instructions + the Playwright/Streamlit lessons. Scratchpad
  paths made repo-relative; freq-model storage TC now uses `tempfile` instead of
  scratchpad DBs. Run manually from the repo root, not collected by pytest
  (`testpaths = ["tests"]`). Ruff clean; all eight re-executed green 2026-07-29.
- [x] **Data Exploration slice — DONE 2026-07-25.** New module
  `pricing_engine/exploration.py` (aggregate-only: `portfolio_frequency`,
  `summarize_portfolio`, `one_way_frequency` with quantile binning,
  `histogram`, `correlation_matrix`; 14 unit tests, suite 43) +
  `pages/02_Data_Exploration.py` (guard, metric row, summary table, one-way
  Altair chart + expander table, histogram chart, correlation matrix).
  E2E `.planning/e2e-tests/data-exploration.md`: TC1–TC8 PASSED (freMTPL2
  frequency 0.1007; all-predictor aggregation in 0.32s), TC9 deferred/manual.
  architecture.md module diagram synced (exploration.py added).
- [x] **Feature Engineering slice — DONE 2026-07-25.**
  `pricing_engine/preprocessing.py` implemented (bin_numeric quantile/uniform →
  `<col>_band`, log_transform → `<col>_log`, encode_categorical drop_first,
  cap_column; 13 unit tests, suite 56) + `pages/03_Feature_Engineering.py`
  (variables multiselect wired to spec, exposure cap at 1.0 — real data: 1,224
  rows, binning + log-transform builders appending to spec predictors, encoding
  info note, live spec summary; all mutations via callbacks). E2E
  `.planning/e2e-tests/feature-engineering.md`: all executed TCs PASSED,
  TC8 deferred/manual.
- [x] **Frequency Model slice — DONE 2026-07-25.** `glm.build_formula` +
  `fit_frequency_glm` (Poisson/NegBin, log link, log-exposure offset),
  `diagnostics.coefficient_table` (exp_coef relativities, significance flag) +
  `information_criteria`, NEW `pricing_engine/storage.py` (decision 7 delivered:
  SQLite model_runs at data/workbench.db, GLM_DB_PATH override) +
  `pages/04_Frequency_Model.py` (family select, formula preview, spinner fit,
  metrics, coefficient table, plain-language strongest-effects + insignificance
  warning, persistent run history). 14 new unit tests (suite 70). E2E
  `.planning/e2e-tests/frequency-model.md`: all executed TCs PASSED (real fit
  11.5s, BonusMalus +2.3%/point p≪0.001, AIC 286,703), TC8 deferred/manual.
- [x] **Diagnostics slice — DONE 2026-07-25.** Engine: `residuals` (deviance/
  pearson), `residual_histogram`, `qq_data`, `observed_vs_predicted` (decile
  calibration, aggregate-only) + shared fitted-model fixtures in conftest.
  UI `pages/05_Diagnostics.py`: model guard, metrics, exp(coef) CI-whisker
  chart with 1.0 reference, residual histogram + kind radio, QQ plot,
  observed-vs-predicted grouped bars (2 series + legend), statsmodels summary
  expander. E2E `.planning/e2e-tests/diagnostics.md`: all executed TCs PASSED
  (4 diagnostics on 678k in 0.15s; weighted predicted freq 0.1007 == observed).
- [x] **Prediction slice — DONE 2026-07-25.** Engine: `predict_frequency`
  (offset-free rate + exposure-scaled claims, copy semantics, missing-predictor
  ValueError). UI `pages/06_Prediction.py`: model guard, single-policy what-if
  (median-default widgets per predictor + exposure input), batch prediction
  with summary metrics + preview + CSV download. E2E
  `.planning/e2e-tests/prediction.md`: all executed TCs PASSED (full predict
  2.0s; **in-sample balance exact: expected 36,102 = observed 36,102**).
  **→ V1 workflow complete: all 7 screens functional.**

## V1.x — enhancements (next up)

- [x] **Stepwise variable selection — DONE 2026-07-25** (as designed: no new
  tab). `glm.stepwise_selection` (backward/forward, AIC/BIC, on_fit progress
  callback, step log; candidate fits NOT recorded in run history) + "Variable
  selection" section on `pages/04_Frequency_Model.py` (radios, st.status
  progress, step-log table, Adopt button → shared spec). 6 unit tests (the
  synthetic Noise factor is correctly dropped; suite 87). E2E
  `.planning/e2e-tests/stepwise-selection.md`: engine TC on real data with a
  reduced 3-predictor spec — all three kept (all genuine effects; stops after
  round 1, 4 fits/9s), guard + section-render UI TCs passed; full UI run
  manual/deferred (minutes by design).
- [ ] Manual walkthrough by Markus + the deferred/manual TCs from the E2E docs
  (selectbox/radio changes, CSV save, F5 history persistence; now also
  severity-dataset TC10: one-way/histogram switches on the severity data,
  bin/log on it, and the switch-back-to-frequency check). Kept in backlog
  2026-07-29 (Markus).
- [x] SQLite scope — DECIDED 2026-07-25 (decision 7 in `PROJECT.md`, storage
  section in `docs/architecture.md`): workbench state + model run history,
  never portfolio data; implemented lazily.
- [x] SQLite schema + `storage` module — DONE 2026-07-25 with the Frequency
  Model slice (model_runs table; workbench-state/"projects" tables follow when
  a consumer needs them)

## V2 — severity workbench (decision 8 in PROJECT.md; design in docs/architecture.md "V2 — Severity design")

Approved 2026-07-29 (Markus): per-claim grain, full-workflow scope. Three
slices, each through the Change Validation Workflow.

- [x] **Slice 1: severity dataset — DONE 2026-07-29 (uncommitted at save).**
  `DatasetSpec.kind` ("frequency" default / "severity"); registered dataset
  `fremtpl2_sev` (`load_fremtpl2_sev_joined`: inner join sev × freq rating
  factors on IDpol → 26,444 rows × 11 cols, 195 orphans dropped); kind-aware
  `validate_portfolio` (severity target strictly positive, "claim amounts"
  wording); kind-aware Data Exploration (Claims / Total claim amount /
  Average claim amount 2,266; one-way average claim amount); Frequency Model
  kind guard. Feature Engineering + Data Import needed zero changes
  (spec-driven). 10 new unit tests (suite 97, 99.41% cov). E2E
  `.planning/e2e-tests/severity-dataset.md` TC1–TC9 PASSED via committed
  runner `e2e/e2e_severity_dataset.py` (combobox click+type+Enter automation
  worked); TC10 deferred/manual. Findings recorded: joined mean 2,265.5 (raw
  2,278.5); freq parquet sorted claims-first.
- [ ] **Slice 2: severity model screen** — `glm.fit_severity_glm` (Gamma
  default / Inverse Gaussian, log link explicitly — statsmodels' Gamma
  default is inverse power; no offset) + `pages/07_Severity_Model.py`
  mirroring screen 04 (family select, formula preview, fit, claim-size
  relativities `exp(beta)`, plain-language aids, insignificance warning, run
  history via same model_runs table) + reverse kind guard (severity screen
  points frequency datasets to screen 04).
- [ ] **Slice 3: kind-aware Diagnostics + Prediction** —
  `prediction.predict_severity` (expected claim amount per row, no exposure
  scaling); Diagnostics wording (observed vs predicted average claim
  amount); Prediction page severity mode (single-claim what-if without
  exposure input, batch, CSV). Engine is already offset-None-safe throughout.
- [ ] V2.x notes: generalize `stepwise_selection` beyond the frequency
  fitter; consider a log-scale/binning improvement for the heavy-tailed
  ClaimAmount histogram (first bin holds >90% — known artifact, TC4).

## Backlog

- [ ] **Chapter 27 synthetic dataset generator** (`generate_chapter27_portfolio`,
  ~20k policies) + the educational features that need its hidden data-generating
  model: `compare_with_true_model` diagnostic, Dummy1/Dummy2 insignificance demo.
  Slots in behind the dataset spec as a second registered dataset (stubs already
  in `pricing_engine/`). Deferred 2026-07-25 in favour of real-data-first.
- [ ] **Regularisation (lasso/ridge/elastic net) — REDISCUSS with Markus**
  (2026-07-25: he wants to revisit this and eventually put it in somehow, ahead
  of the original V4 deferral; 2026-07-29: confirmed keep in backlog for now). Sketch when discussing: a "Regularisation"
  option on the Frequency Model page (none default / lasso / ridge / elastic
  net + alpha input) via statsmodels `fit_regularized`; lasso's zeroed
  coefficients would complement stepwise as a second selection lens. The
  trade-off to settle in the discussion: penalised fits return no std
  errors/p-values/CIs → needs a degraded coefficient view (coefficients +
  relativities only, explicit note about missing inference; Diagnostics
  CI-whisker chart and significance highlighting don't apply). Typical
  actuarial practice keeps pricing GLMs unpenalised for interpretability —
  decide framing (educational comparison feature vs. modelling tool).
- [ ] V2+ roadmap items (severity, pure premium, generic workbench, reports) —
  tracked in `PROJECT.md` / `docs/architecture.md`

## Project setup (done)

- [x] Scaffold — DONE 2026-07-25 (see STATE.md); revised same day for the V1
  rescope (pages 01–06) and again for freMTPL2 + dataset-spec design
- [x] GLM library decision — statsmodels (decision 4 in `PROJECT.md`)
- [x] V1 scope decision — Chapter 27 frequency-only (decision 5)
- [x] freMTPL2 as real dataset + generic dataset spec (decision 6); data
  downloaded + verified, pyarrow added
- [x] CLAUDE.md Quick Start filled
- [x] Doc drift (architecture.md repo layout) — fixed 2026-07-25
