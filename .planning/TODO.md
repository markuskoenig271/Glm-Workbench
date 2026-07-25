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
- [ ] E2E runner harness: promote the scratchpad Playwright scripts into a
  committed `e2e/` directory (run manually, not part of `pytest`) once a second
  UI slice exists — currently the executed scripts live only in the session
  scratchpad
- [x] **Data Exploration slice — DONE 2026-07-25.** New module
  `pricing_engine/exploration.py` (aggregate-only: `portfolio_frequency`,
  `summarize_portfolio`, `one_way_frequency` with quantile binning,
  `histogram`, `correlation_matrix`; 14 unit tests, suite 43) +
  `pages/02_Data_Exploration.py` (guard, metric row, summary table, one-way
  Altair chart + expander table, histogram chart, correlation matrix).
  E2E `.planning/e2e-tests/data-exploration.md`: TC1–TC8 PASSED (freMTPL2
  frequency 0.1007; all-predictor aggregation in 0.32s), TC9 deferred/manual.
  architecture.md module diagram synced (exploration.py added).
- [ ] **Feature Engineering slice** — binning (DrivAge, VehAge), encoding, offset
- [ ] **Frequency Model slice** — `fit_frequency_glm` (Poisson, log link, exposure
  offset), coefficient table with p-values/deviance/AIC; educational aids
  (exp(beta) relativities, plain-language explanations, insignificance highlight)
- [ ] **Diagnostics slice** — CIs, deviance/Pearson residual plots, observed vs
  predicted (true-model comparison is backlogged with the generator)
- [ ] **Prediction slice** — `predict_frequency` single + batch, CSV export
- [x] SQLite scope — DECIDED 2026-07-25 (decision 7 in `PROJECT.md`, storage
  section in `docs/architecture.md`): workbench state + model run history,
  never portfolio data; implemented lazily.
- [ ] SQLite schema + `storage` module (first consumer: record model runs) —
  build WITH the Frequency Model slice per decision 7

## Backlog

- [ ] **Chapter 27 synthetic dataset generator** (`generate_chapter27_portfolio`,
  ~20k policies) + the educational features that need its hidden data-generating
  model: `compare_with_true_model` diagnostic, Dummy1/Dummy2 insignificance demo.
  Slots in behind the dataset spec as a second registered dataset (stubs already
  in `pricing_engine/`). Deferred 2026-07-25 in favour of real-data-first.
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
