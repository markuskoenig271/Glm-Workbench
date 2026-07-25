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
hidden-DGM educational features are backlogged; see Datasets below). Severity, pure
premium, and reporting stay in the architecture as later versions (roadmap below);
the V1 UI exposes only the frequency workflow.

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
    ├── Diagnostics
    └── Prediction

    (V2+: Severity Model, Pure Premium, Reports)

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
     known orphan records). Unlocks V2 severity / V3 pure premium with real data.
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
- Severity GLMs (V2)
- Pure Premium (V3)

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

## Version Roadmap (per car-insurance.md)

1. **V1** — Frequency GLM (Chapter 27 example)
2. **V2** — Severity GLM (Gamma)
3. **V3** — Pure Premium (Frequency × Severity)
4. **V4** — Generic pricing workbench for arbitrary portfolios

## Future Ideas

- XGBoost comparison
- SHAP explainability
- Cross-validation
- Experiment tracking
