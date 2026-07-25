# Car Insurance Example (Chapter 27)

## Purpose

The first version of the GLM Workbench reproduces the practical motor insurance
frequency modelling example from Chapter 27 of *Pricing in General Insurance*
(Pietro Parodi).

The objective is to build an educational workbench that follows the book as
closely as possible before extending it into a generic pricing platform.

This document is referenced from `architecture.md`.

---

# Objectives

The application should allow a user to:

1. Load the synthetic Chapter 27 dataset.
2. Explore the portfolio.
3. Fit a Frequency GLM.
4. Inspect model coefficients.
5. Evaluate model diagnostics.
6. Predict expected claim frequency for individual policies.

Version 1 intentionally focuses **only on frequency modelling**.

---

# Dataset

The synthetic portfolio contains approximately **20,000 policies**.

## Target

- Claims (claim count)

## Predictors

| Variable | Type |
|-----------|------|
| Age | Continuous |
| LocationType | Urban / Rural |
| Region | 5 Categories |
| VehicleAge | Continuous |
| FuelType | Electric / Diesel / Petrol |
| NoClaimYears | Ordinal |
| Dummy1 | Binary |
| Dummy2 | Categorical |
| Exposure | Continuous Offset |

Dummy1 and Dummy2 are intentionally unrelated to the response and should be
identified as non-significant during modelling.

---

# User Workflow

```text
Load Dataset
    ↓
Explore Data
    ↓
Select Variables
    ↓
Configure GLM
    ↓
Fit Model
    ↓
Diagnostics
    ↓
Prediction
```

---

# Screens

1. Home
2. Data Import
3. Data Exploration
4. Feature Engineering
5. Frequency Model
6. Diagnostics
7. Prediction

See `ui_screens.md` for the detailed UI specification.

---

# Frequency Model

Initial implementation:

- Poisson GLM
- Log Link
- Exposure Offset
- Coefficient Table
- p-values
- Deviance
- AIC

Future versions should add:

- Negative Binomial
- Variable Selection
- Cross Validation

---

# Diagnostics

The workbench should include:

- Coefficient estimates
- Confidence intervals
- Residual plots
- Observed vs Predicted
- Deviance residuals
- Pearson residuals
- Model summary

---

# Educational Features

The application is intended as an actuarial learning tool.

Recommended additions:

- Explain each coefficient in plain language.
- Display risk relativities (`exp(beta)`).
- Highlight statistically insignificant variables.
- Compare estimated coefficients with the hidden data-generating model.
- Show how exposure is incorporated as an offset.

---

# Future Roadmap

Version 1
- Frequency GLM

Version 2
- Severity GLM (Gamma)

Version 3
- Pure Premium (Frequency × Severity)

Version 4
- Generic Pricing Workbench supporting arbitrary insurance portfolios.
