# GLM Workbench – Architecture

## Overview

GLM Workbench is a local Python + Streamlit application for actuarial pricing experiments.
It supports importing insurance data, fitting GLMs for frequency and severity, evaluating
models, and predicting pure premiums.

> **Reference:** See [UI Screen Definitions](ui_screens.md).
> **Reference:** See [Car Insurance](car-insurance.md).

**Version 1 scope:** reproduce the Chapter 27 motor-insurance **frequency** example from
*Pricing in General Insurance* (Parodi) — see [car-insurance.md](car-insurance.md).
Severity, pure premium, and reporting stay in the architecture as later versions
(roadmap below); the V1 UI exposes only the frequency workflow.

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
    data.py            # import, validation, Chapter 27 synthetic dataset
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

## Components

### Data Layer
- Import
- Validation
- Data typing
- Exposure checks
- Synthetic Chapter 27 dataset generator (~20k policies, hidden data-generating
  model kept alongside for the educational coefficient comparison)

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
- Comparison with the hidden data-generating model (educational)

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
