# GLM Workbench – Architecture

## Overview

GLM Workbench is a local Python + Streamlit application for actuarial pricing experiments.
It supports importing insurance data, fitting GLMs for frequency and severity, evaluating
models, and predicting pure premiums.

> **Reference:** See [UI Screen Definitions](ui_screens.md).

## Goals

- Import portfolio data
- Validate and profile data
- Feature engineering
- Frequency GLM (Poisson / Negative Binomial)
- Severity GLM (Gamma / Inverse Gaussian)
- Pure premium calculation
- Diagnostics and reporting

## High-Level Architecture

```text
Streamlit UI
    │
    ├── Data Import
    ├── Exploration
    ├── Feature Engineering
    ├── Frequency Model
    ├── Severity Model
    ├── Pure Premium
    ├── Diagnostics
    └── Prediction

pricing_engine/
    data.py
    preprocessing.py
    glm.py
    prediction.py
    diagnostics.py
    report.py
```

## Repository Layout

```text
Glm-Workbench/
├── app.py
├── architecture.md
├── ui_screens.md
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

### Feature Engineering
- Encoding
- Transformations
- Offsets
- Interaction terms

### Modeling
- Frequency GLMs
- Severity GLMs
- Pure Premium

### Diagnostics
- Coefficients
- Residuals
- Calibration
- AIC/BIC

### Reporting
- HTML
- PDF
- CSV

## Future Ideas

- XGBoost comparison
- SHAP explainability
- Cross-validation
- Experiment tracking
