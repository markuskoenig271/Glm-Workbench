# TODO

Active work items and technical debt. Check this at the start of every session.

---

## V1 — Chapter 27 frequency workbench (docs/car-insurance.md)

- [ ] **Dataset spec + registry** — generic (target, offset, predictors) description
  per dataset (decision 6); built-ins: chapter27 synthetic + freMTPL2; CSV upload
  produces a spec via column mapping. Foundation for all pages.
- [ ] **freMTPL2 loaders** — `load_fremtpl2_freq`/`load_fremtpl2_sev` TDD-first
  (Parquet via pyarrow; data downloaded 2026-07-25 to `data/raw/`, download
  commands in README); friendly error when files are missing
- [ ] **Chapter 27 synthetic dataset generator** — `generate_chapter27_portfolio`
  TDD-first: ~20k policies, hidden data-generating model returned alongside
  (for the Diagnostics estimated-vs-true comparison); Dummy1/Dummy2 with no
  real effect; then wire the Home "load sample data" flow
- [ ] **Data Import slice** — `load_portfolio` + `validate_portfolio` TDD-first,
  then `pages/01_Data_Import.py` (preview, column mapping, validation report)
- [ ] **Data Exploration slice** — summary stats, histograms, one-way claim
  frequency by predictor
- [ ] **Feature Engineering slice** — binning (Age, VehicleAge), encoding, offset
- [ ] **Frequency Model slice** — `fit_frequency_glm` (Poisson, log link, exposure
  offset), coefficient table with p-values/deviance/AIC; educational aids
  (exp(beta) relativities, plain-language explanations, insignificance highlight)
- [ ] **Diagnostics slice** — CIs, deviance/Pearson residual plots, observed vs
  predicted, `compare_with_true_model`
- [ ] **Prediction slice** — `predict_frequency` single + batch, CSV export
- [ ] Decide what SQLite actually stores (projects? fitted model metadata? run
  history?) and add it to `docs/architecture.md` — still not specified

## Project setup (done)

- [x] Scaffold — DONE 2026-07-25 (see STATE.md); revised same day for the V1
  rescope: pages now 01–06 (Severity/Pure Premium/Reports removed → V2+),
  Chapter 27 schema constants + generator stub in `pricing_engine/data.py`,
  `predict_frequency` + residuals/true-model-comparison stubs added. Verified:
  pytest 7/7 + coverage gate, ruff + format + mypy clean, E2E smoke re-passed
  (`.planning/e2e-tests/scaffold-smoke.md`).
- [x] GLM library decision — statsmodels (decision 4 in `PROJECT.md`)
- [x] V1 scope decision — Chapter 27 frequency-only (decision 5 in `PROJECT.md`)
- [x] CLAUDE.md Quick Start filled
- [x] Doc drift (architecture.md repo layout) — fixed 2026-07-25 during the
  car-insurance.md incorporation
