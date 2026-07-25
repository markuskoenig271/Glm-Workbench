# GLM Workbench – UI Screen Definitions

**Version 1 scope:** the Chapter 27 car-insurance frequency workflow — see
[car-insurance.md](car-insurance.md) — on the **real freMTPL2 dataset** (the
synthetic Chapter 27 dataset is backlogged). Seven screens; severity, pure
premium, and reporting screens arrive with later versions (roadmap at the bottom).

## 1. Home
- Load the built-in dataset: **freMTPL2** (real French motor TPL, 678k policies);
  the Chapter 27 synthetic dataset joins later from the backlog
- Workflow status
- Project summary + version roadmap

## 2. Data Import
- Built-in dataset (freMTPL2) or file upload (CSV)
- Preview
- Dataset spec: target, offset, predictors — preset for built-ins, produced by
  column mapping for CSV uploads
- Validation report (types, missing values, exposure checks)

## 3. Data Exploration
- Summary statistics
- Histograms
- One-way claim frequency by predictor (per the active dataset's spec)
- Missing values
- Correlations
- Large datasets (freMTPL2): aggregate / sample for plots, never render raw rows

## 4. Feature Engineering
- Variable selection
- Binning of continuous predictors (e.g. Age/DrivAge, VehicleAge/VehAge)
- Encoding of categoricals (e.g. LocationType/Area, Region, FuelType/VehGas)
- Offset selection (Exposure)

## 5. Frequency Model
- Poisson GLM, log link, exposure offset (v1; Negative Binomial later)
- Formula editor / variable picker
- Fit model
- Coefficient table with p-values, deviance, AIC
- Educational aids: risk relativities (`exp(beta)`), plain-language coefficient
  explanations, highlighting of insignificant variables

## 6. Diagnostics
- Coefficient estimates with confidence intervals
- Deviance and Pearson residual plots
- Observed vs Predicted
- Model summary
- (Backlog, with the synthetic dataset) comparison of estimated coefficients
  with the hidden data-generating model

## 7. Prediction
- Single policy expected claim frequency
- Batch prediction
- Export CSV

---

## Future screens (roadmap, per car-insurance.md)

- **V2 — Severity Model:** distribution selection (Gamma / Inverse Gaussian),
  formula editor, fit, diagnostics (freMTPL2sev is already downloaded)
- **V3 — Pure Premium:** frequency × severity, variable contributions
- **V4 — Generic workbench:** arbitrary portfolios; Reports screen
  (HTML/PDF export, model summary)
- **Backlog:** Chapter 27 synthetic dataset + hidden-DGM educational features
  (true-model comparison, Dummy1/Dummy2 insignificance demo)
