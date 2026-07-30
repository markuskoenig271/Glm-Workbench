# GLM Workbench – Architecture

## Overview

GLM Workbench is a local Python + Streamlit application for actuarial pricing experiments.
It supports importing insurance data, fitting GLMs for frequency and severity, evaluating
models, and predicting pure premiums.

> **Reference:** See [UI Screen Definitions](ui_screens.md).
> **Reference:** See [Car Insurance](car-insurance.md).

**Version 1 scope:** the Chapter 27 motor-insurance **frequency** workflow from
*Pricing in General Insurance* (Parodi) — see [car-insurance.md](car-insurance.md) —
executed on the **real freMTPL2 dataset** (the synthetic Chapter 27 dataset and its
hidden-DGM educational features are backlogged; see Datasets below). **V1 is
complete.**

**Version 2 scope (approved 2026-07-29): severity.** Per-claim severity GLM
(Gamma default, Inverse Gaussian option; log link, no offset) on the joined
freMTPL2 severity table, delivered as a **second registered dataset** flowing
through the existing Import → Exploration → Feature Engineering screens
unchanged, plus a new Severity Model screen; Diagnostics and Prediction are
generalized to operate on whichever model is active (kind-aware wording). See
"V2 — Severity design" below. Pure premium and reporting remain later versions.

## Goals

- Import portfolio data
- Validate and profile data
- Feature engineering
- Frequency GLM (Poisson; Negative Binomial later) — **V1**
- Severity GLM (Gamma / Inverse Gaussian) — V2
- Pure premium calculation — V3
- Diagnostics and reporting

## High-Level Architecture

```text
Streamlit UI (V1 pages)
    │
    ├── Data Import
    ├── Exploration
    ├── Feature Engineering
    ├── Frequency Model
    ├── Severity Model      (V2)
    ├── Diagnostics         (kind-aware since V2)
    └── Prediction          (kind-aware since V2)

    (V3+: Pure Premium, Reports)

pricing_engine/
    data.py            # import, validation, freMTPL2 loaders, dataset spec
    exploration.py     # aggregate-only: summary, one-way frequencies, histograms
    preprocessing.py
    glm.py             # frequency (V1) + severity (V2) fitting
    prediction.py      # frequency prediction (V1), pure premium (V3)
    diagnostics.py
    report.py          # (V4)
```

## Repository Layout

```text
Glm-Workbench/
├── app.py
├── pyproject.toml
├── README.md
├── .env.example
├── docs/
│   ├── architecture.md
│   ├── ui_screens.md
│   └── car-insurance.md
├── pricing_engine/
├── pages/
├── data/
├── models/
├── reports/
└── tests/
```

## Datasets

Primary built-in dataset plus CSV upload; the synthetic dataset is backlogged:

1. **freMTPL2** (real French motor TPL data, licence CC0) — the **primary V1 dataset**:
   - `freMTPL2freq`: 678,013 policies — `ClaimNb` (target), `Exposure` (offset),
     predictors `Area`, `VehPower`, `VehAge`, `DrivAge`, `BonusMalus`, `VehBrand`,
     `VehGas`, `Density`, `Region`. Used in V1 (frequency).
   - `freMTPL2sev`: 26,639 claim amounts joined by `IDpol` (~99.3% match freq —
     known orphan records). **Used in V2 (severity)** as the registered dataset
     `fremtpl2_sev`: the loader inner-joins each claim row (`IDpol`,
     `ClaimAmount`) with the frequency table's nine rating factors — one row per
     claim, orphan claims (no matching policy) dropped with a logged count.
     Spec: target `ClaimAmount`, **no offset**, same nine predictors,
     `kind="severity"`.
   - Stored as Parquet in `data/raw/` (gitignored). Reproducible download from
     OpenML: `https://data.openml.org/datasets/0004/41214/dataset_41214.pq` (freq)
     and `.../0004/41215/dataset_41215.pq` (sev).
2. **Chapter 27 synthetic** (~20k policies, generated) — **backlogged** (2026-07-25).
   Joins later as a second registered dataset, bringing the educational features
   that need its hidden data-generating model (estimated-vs-true coefficient
   comparison, Dummy1/Dummy2 insignificance demo). See
   [car-insurance.md](car-insurance.md).

**Design consequence — generic dataset spec:** freMTPL2 does not map 1:1 onto the
Chapter 27 columns (Area is a density band, not urban/rural; BonusMalus ≠
NoClaimYears; VehPower/VehBrand/Density have no counterpart). The data layer
therefore describes every dataset by a spec (target column, offset column,
predictor columns + types) instead of hardcoding column names; pages and
`pricing_engine` operate on that spec. CSV uploads produce a spec via the
column-mapping step in Data Import.

**Spec `kind` (V2):** `DatasetSpec.kind` is `"frequency"` (default) or
`"severity"`. It drives which model screen fits the dataset (each guards
against the other kind), UI wording (claim frequency vs average claim amount),
and validation strictness (a severity target must be strictly positive — Gamma
requires it). Engine aggregation functions stay generic: with `offset=None`
they divide by row count, which for severity data is exactly the per-claim
average.

**Scale note:** freMTPL2freq is ~678k rows (vs 20k synthetic). Exploration plots
must aggregate or sample, and fitted models should be cached in session state —
no naive per-row rendering.

## Components

### Data Layer
- Import (built-in datasets via registry, CSV upload via column mapping)
- Dataset spec (target / offset / predictors) — see Datasets above
- Validation
- Data typing
- Exposure checks
- freMTPL2 Parquet loaders (pyarrow)
- (Backlog) Synthetic Chapter 27 dataset generator (~20k policies, hidden
  data-generating model kept alongside for the educational coefficient comparison)

### Storage (SQLite — decision 7 in `.planning/PROJECT.md`)
- **Workbench state / projects:** dataset choice, column mapping,
  feature-engineering settings — restores a returning user's session
- **Model run history:** dataset, formula, family, coefficients,
  AIC/BIC/deviance, timestamp — cross-session model comparison
- **Never portfolio data** — that stays in Parquet/CSV
- Implemented lazily: tables arrive with their first consumer (run history with
  the Frequency Model slice). Until then, in-session state only; a browser
  refresh drops the loaded dataset.

### Feature Engineering
- Encoding
- Transformations
- Offsets
- Interaction terms

### Modeling
- Frequency GLMs (V1: Poisson, log link, exposure offset)
- Stepwise variable selection by information criterion (V1.x) —
  `glm.stepwise_selection` looping the fitter; UI section on the Frequency
  Model screen; only the adopted final fit enters the run history
- Severity GLMs (V2) — `glm.fit_severity_glm`: per-claim Gamma (default) or
  Inverse Gaussian, **log link explicitly** (statsmodels' Gamma default is
  inverse power), no offset; `exp(beta)` = multiplicative effect on expected
  claim amount. Stepwise selection stays frequency-only for now (generalizing
  it is a V2.x note).
- Pure Premium (V3) — will need both models in session at once; V2 keeps the
  single active-model slot (fitting severity replaces the active frequency
  model and vice versa), V3 splits it per kind.
- (Deferred to V4, with ML challengers) regularised fits — trade-off: no
  classical inference (std errors/p-values/CIs) on penalised estimates

### Diagnostics
- Coefficients (estimates, confidence intervals, `exp(beta)` relativities)
- Residuals (deviance, Pearson)
- Calibration / observed vs predicted
- AIC/BIC, deviance
- (Backlog, with the synthetic dataset) comparison with the hidden
  data-generating model

### Reporting (V4)
- HTML
- PDF
- CSV

## V2 — Severity design (approved 2026-07-29)

Decisions (Markus, 2026-07-29): **per-claim grain** (one row per claim — the
textbook educational setup — rather than per-policy weighted averages) and
**full workflow scope** (not just the fit screen).

Delivered in three slices, each through the Change Validation Workflow:

1. **Data slice** — `DatasetSpec.kind`; `fremtpl2_sev` registered dataset
   (join loader, orphan handling); severity-aware `validate_portfolio`
   (strictly positive target); kind-aware wording on the Exploration page
   (engine untouched — already offset-None-safe).
2. **Model slice** — `glm.fit_severity_glm`; `pages/07_Severity_Model.py`
   mirroring the Frequency Model screen (family select, formula preview, fit,
   coefficient table with claim-size relativities, plain-language aids, run
   history via the same `model_runs` table — `family` distinguishes);
   kind guards on both model screens.
3. **Diagnostics + Prediction slice** — kind-aware wording on Diagnostics
   (calibration = observed vs predicted average claim amount);
   `prediction.predict_severity` (expected claim amount per row, no exposure
   scaling) + kind-aware Prediction page (single-claim what-if, batch, CSV).

## Version Roadmap (per car-insurance.md)

1. **V1** — Frequency GLM (Chapter 27 example) — **complete 2026-07-25**
2. **V2** — Severity GLM (Gamma) — **in progress**
3. **V3** — Pure Premium (Frequency × Severity)
4. **V4** — Generic pricing workbench for arbitrary portfolios

## Future Ideas

- XGBoost comparison
- SHAP explainability
- Cross-validation
- Experiment tracking
