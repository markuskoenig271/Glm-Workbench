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
- [ ] **Data Import slice** — `load_portfolio` (CSV) TDD-first, then
  `pages/01_Data_Import.py` (dataset choice via registry, preview, validation
  report rendering `validate_portfolio` findings)
- [ ] **Data Exploration slice** — summary stats, histograms, one-way claim
  frequency by predictor; aggregate/sample for 678k rows (no raw-row rendering)
- [ ] **Feature Engineering slice** — binning (DrivAge, VehAge), encoding, offset
- [ ] **Frequency Model slice** — `fit_frequency_glm` (Poisson, log link, exposure
  offset), coefficient table with p-values/deviance/AIC; educational aids
  (exp(beta) relativities, plain-language explanations, insignificance highlight)
- [ ] **Diagnostics slice** — CIs, deviance/Pearson residual plots, observed vs
  predicted (true-model comparison is backlogged with the generator)
- [ ] **Prediction slice** — `predict_frequency` single + batch, CSV export
- [ ] Decide what SQLite actually stores (projects? fitted model metadata? run
  history?) and add it to `docs/architecture.md` — still not specified

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
