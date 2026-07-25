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

A Streamlit app walks the user through the Chapter 27 frequency workflow: load the
synthetic portfolio (~20,000 policies; target `Claims`, offset `Exposure`, eight
predictors — two of them intentionally non-significant), explore it, engineer
features, fit a Poisson GLM (log link, exposure offset), inspect coefficients and
diagnostics, and predict expected claim frequency per policy. Educational aids
throughout: `exp(beta)` risk relativities, plain-language coefficient explanations,
highlighting of insignificant variables, and comparison of estimated coefficients
against the hidden data-generating model. All computation runs in the
`pricing_engine/` Python package; Streamlit is only the front-end.

## Scope

**In scope (V1 — frequency only, per `docs/car-insurance.md`)**
- Synthetic Chapter 27 dataset (generator with hidden data-generating model) + CSV import
- Data validation, profiling, one-way frequency analysis
- Feature engineering: binning, encoding, offset selection
- Frequency GLM: Poisson, log link, exposure offset
- Diagnostics: coefficients + CIs, deviance/Pearson residuals, observed vs
  predicted, AIC/deviance, estimated-vs-true comparison
- Single-policy and batch frequency prediction, CSV export
- Local single-user operation (SQLite storage)

**Later versions (roadmap)**
- V2 — Severity GLM (Gamma / Inverse Gaussian)
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

## Working conventions

- Architecture first for significant changes; TDD with a 75%+ coverage target.
- Never commit secrets (use `.env`); never install packages globally; prefer `uv`.
- Conventional commits; branch prefixes `feat/ fix/ refactor/ chore/ docs/`.
- Planning files: `PROJECT.md` (this spec), `STATE.md` (rolling progress),
  `TODO.md` (open work). No GSD multi-file structure.
