# TODO

Active work items and technical debt. Check this at the start of every session.

---

## V1 — frequency workbench on freMTPL2 (workflow per docs/car-insurance.md)

Primary V1 dataset is now **freMTPL2** (real data, decision 6); the synthetic
Chapter 27 generator moved to the backlog (2026-07-25, Markus' call).

- [ ] **Dataset spec + registry** — generic (target, offset, predictors) description
  per dataset (decision 6); built-in: freMTPL2 (chapter27 synthetic joins later
  from the backlog); CSV upload produces a spec via column mapping. Foundation
  for all pages.
- [ ] **freMTPL2 loaders** — `load_fremtpl2_freq`/`load_fremtpl2_sev` TDD-first
  (Parquet via pyarrow; data downloaded 2026-07-25 to `data/raw/`, download
  commands in README); friendly error when files are missing
- [ ] **Data Import slice** — `load_portfolio` + `validate_portfolio` TDD-first,
  then `pages/01_Data_Import.py` (dataset choice, preview, validation report)
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
