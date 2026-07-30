# Glm-Workbench — Project Spec

The stable "what & why" reference. Project definition, goals, scope, and key decisions.
For current progress see `STATE.md`; for open work see `TODO.md`.

---

## Purpose

A local workbench to test out and learn Generalized Linear Models for actuarial
pricing. **Version 1 reproduces the practical motor-insurance frequency modelling
example from Chapter 27 of *Pricing in General Insurance* (Pietro Parodi)** as an
educational tool, before growing into a generic pricing platform
(see `docs/car-insurance.md`).

## How it works

A Streamlit app walks the user through the Chapter 27 frequency workflow on the
real freMTPL2 portfolio (678k French motor TPL policies; target `ClaimNb`, offset
`Exposure`, nine rating factors): explore it, engineer features, fit a Poisson GLM
(log link, exposure offset), inspect coefficients and diagnostics, and predict
expected claim frequency per policy. Educational aids throughout: `exp(beta)` risk
relativities, plain-language coefficient explanations, highlighting of
insignificant variables. (The synthetic Chapter 27 dataset and its hidden-DGM
comparison are backlogged.) All computation runs in the `pricing_engine/` Python
package; Streamlit is only the front-end.

## Scope

**In scope (V1 — frequency only, per `docs/car-insurance.md`)**
- freMTPL2 real dataset (French motor TPL, 678k policies) as the primary dataset —
  frequency in V1; its severity table unlocks V2/V3. CSV import alongside.
- (Backlogged) synthetic Chapter 27 dataset (generator with hidden
  data-generating model + estimated-vs-true comparison)
- Data validation, profiling, one-way frequency analysis
- Feature engineering: binning, encoding, offset selection
- Frequency GLM: Poisson, log link, exposure offset
- Diagnostics: coefficients + CIs, deviance/Pearson residuals, observed vs
  predicted, AIC/deviance, estimated-vs-true comparison
- Single-policy and batch frequency prediction, CSV export
- Local single-user operation (SQLite storage)

**Later versions (roadmap)**
- V2 — Severity GLM (Gamma / Inverse Gaussian) — **in progress, decision 8**
- V3 — Pure Premium (frequency × severity), variable contributions
- V4 — Generic pricing workbench for arbitrary portfolios; reports (HTML/PDF)
- Negative Binomial frequency, variable selection, cross-validation
- ML challengers (XGBoost), SHAP (see "Future Ideas" in `docs/architecture.md`)

## Workflow steps (UI tabs)

Per `docs/ui_screens.md` — one Streamlit page per step (V1):

1. **Home** — load sample data, workflow status, roadmap
2. **Data Import** — sample dataset or CSV upload, preview, column mapping, validation
3. **Data Exploration** — summary stats, histograms, one-way frequencies, correlations
4. **Feature Engineering** — variable selection, binning, encoding, offset
5. **Frequency Model** — Poisson fit, coefficient table, educational aids
6. **Diagnostics** — CIs, residuals, observed vs predicted, true-model comparison
7. **Prediction** — single policy + batch expected frequency, CSV export

## Tech stack

Streamlit (UI + app server), SQLite (storage), Python `pricing_engine/` package
for all computation. Details: `docs/architecture.md`.

## Key decisions

- **Decision 1 — Streamlit over a split frontend/backend:** single local Python app,
  minimal infrastructure; the workbench is a learning/experimentation tool, not a product.
- **Decision 2 — SQLite for storage:** local single-user persistence, no server.
- **Decision 3 — computation lives in `pricing_engine/`, not in pages:** keeps the
  model code importable and testable without Streamlit (TDD requirement).
- **Decision 4 — statsmodels as the GLM library (2026-07-25):** first-class GLM
  families (Poisson, NegBin, Gamma, Inverse Gaussian), R-style formulas, and the
  inference output actuaries expect (std errors, p-values, AIC/BIC) — a natural fit
  for a learning tool, over scikit-learn's prediction-oriented API.
- **Decision 5 — V1 follows the book (2026-07-25):** reproduce Parodi Chapter 27
  frequency-only before generalizing; versioned roadmap V1 frequency → V2 severity →
  V3 pure premium → V4 generic workbench (`docs/car-insurance.md`).
- **Decision 6 — freMTPL2 as the real dataset (2026-07-25):** the standard actuarial
  GLM benchmark (CC0, OpenML 41214/41215; CASdatasets origin) with interpretable
  rating factors and a real severity table — chosen over anonymized Kaggle sets
  (no educational value) and the tiny/aggregated Swedish data. Consequence: the
  data layer uses a generic per-dataset spec (target/offset/predictors) rather than
  hardcoded Chapter 27 column names (`docs/architecture.md` "Datasets").
- **Decision 7 — SQLite stores workbench state, never portfolio data (2026-07-25):**
  SQLite holds (a) workbench state / "projects" — dataset choice, column mapping,
  feature-engineering settings, so a returning user restores their session — and
  (b) model run history — dataset, formula, family, coefficients, AIC/BIC/deviance,
  timestamp — enabling cross-session model comparison (seed of experiment
  tracking). Portfolio data stays in Parquet/CSV (SQLite would be a slower copy).
  Implemented lazily: tables arrive with their first consumer (model run history
  with the Frequency Model slice). Until then, in-session state only — a browser
  refresh drops the loaded dataset (known Streamlit behavior).
- **Decision 8 — V2 severity design (2026-07-29):** per-claim severity GLM
  (Gamma default / Inverse Gaussian, log link, no offset) on the freMTPL2
  severity table inner-joined with the frequency table's rating factors,
  registered as a second built-in dataset (`fremtpl2_sev`) so the existing
  Import/Exploration/Feature-Engineering screens work unchanged. `DatasetSpec`
  gains a `kind` field ("frequency"/"severity") driving screen guards, UI
  wording, and validation (severity targets strictly positive). Full-workflow
  scope: new Severity Model screen plus kind-aware Diagnostics and Prediction.
  Chosen over per-policy weighted averages (textbook per-claim setup is the
  educational standard) and over a fit-screen-only scope.

## Working conventions

- Architecture first for significant changes; TDD with a 75%+ coverage target.
- Never commit secrets (use `.env`); never install packages globally; prefer `uv`.
- Conventional commits; branch prefixes `feat/ fix/ refactor/ chore/ docs/`.
- Planning files: `PROJECT.md` (this spec), `STATE.md` (rolling progress),
  `TODO.md` (open work). No GSD multi-file structure.
