# Glm-Workbench — Project Spec

The stable "what & why" reference. Project definition, goals, scope, and key decisions.
For current progress see `STATE.md`; for open work see `TODO.md`.

---

## Purpose

A local workbench to test out and learn Generalized Linear Models for actuarial
pricing: import insurance portfolio data, fit frequency and severity GLMs, compute
pure premiums, and inspect diagnostics — all through a guided UI.

## How it works

A Streamlit app walks the user through the classic actuarial pricing workflow:
data goes in as a portfolio file (policies with exposure, claim counts, claim
amounts), gets profiled and feature-engineered, then a frequency GLM
(Poisson / Negative Binomial, exposure as offset) and a severity GLM
(Gamma / Inverse Gaussian) are fitted. Pure premium = predicted frequency ×
predicted severity. Diagnostics (coefficients, residuals, AIC/BIC, calibration)
support model comparison; results export as HTML/PDF/CSV reports. All computation
runs in the `pricing_engine/` Python package; Streamlit is only the front-end.

## Scope

**In scope**
- Portfolio data import, validation, profiling
- Feature engineering: binning, encoding, transforms, interactions, offsets
- Frequency + severity GLMs, pure premium calculation
- Diagnostics (coefficients, residuals, QQ, calibration, AIC/BIC, observed vs predicted)
- Single-policy and batch prediction, CSV export
- HTML/PDF report export
- Local single-user operation (SQLite storage)

**Out of scope (for now — see "Future Ideas" in `docs/architecture.md`)**
- ML challenger models (XGBoost), SHAP explainability
- Cross-validation, experiment tracking
- Multi-user / hosted deployment

## Workflow steps (UI tabs)

Per `docs/ui_screens.md` — one Streamlit page per step:

1. **Home** — load project / sample data, workflow status
2. **Data Import** — upload, preview, column mapping, validation report
3. **Data Exploration** — summary stats, histograms, missing values, correlations
4. **Feature Engineering** — selection, binning, encoding, transforms, interactions
5. **Frequency Model** — distribution, formula, offset, fit, coefficients, residuals
6. **Severity Model** — distribution, formula, fit, diagnostics
7. **Pure Premium** — frequency × severity, variable contributions
8. **Diagnostics** — AIC/BIC, QQ, residuals, observed vs predicted
9. **Prediction** — single policy + batch, CSV export
10. **Reports** — HTML/PDF export, model summary

## Tech stack

Streamlit (UI + app server), SQLite (storage), Python `pricing_engine/` package
for all computation. Details: `docs/architecture.md`.

## Key decisions

- **Decision 1 — Streamlit over a split frontend/backend:** single local Python app,
  minimal infrastructure; the workbench is a learning/experimentation tool, not a product.
- **Decision 2 — SQLite for storage:** local single-user persistence, no server.
- **Decision 3 — computation lives in `pricing_engine/`, not in pages:** keeps the
  model code importable and testable without Streamlit (TDD requirement).
- (Open) GLM library choice — statsmodels is the candidate; decide at scaffold time.

## Working conventions

- Architecture first for significant changes; TDD with a 75%+ coverage target.
- Never commit secrets (use `.env`); never install packages globally; prefer `uv`.
- Conventional commits; branch prefixes `feat/ fix/ refactor/ chore/ docs/`.
- Planning files: `PROJECT.md` (this spec), `STATE.md` (rolling progress),
  `TODO.md` (open work). No GSD multi-file structure.
