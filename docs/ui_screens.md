# GLM Workbench – UI Screen Definitions

**Version 1 scope:** the Chapter 27 car-insurance frequency workflow — see
[car-insurance.md](car-insurance.md) — on the **real freMTPL2 dataset** (the
synthetic Chapter 27 dataset is backlogged). **V2 (approved 2026-07-29)** adds
the Severity Model screen (8) and makes Diagnostics and Prediction kind-aware;
pure premium and reporting screens arrive with later versions (roadmap at the
bottom).

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
- Stepwise variable selection section (V1.x): backward/forward by AIC/BIC,
  live progress, step log, adopt-selected-predictors into the shared spec —
  no separate screen needed

## 6. Diagnostics
- Coefficient estimates with confidence intervals
- Deviance and Pearson residual plots
- Observed vs Predicted
- Model summary
- (V2) kind-aware wording: for a severity model the calibration chart reads
  "observed vs predicted average claim amount"
- (Backlog, with the synthetic dataset) comparison of estimated coefficients
  with the hidden data-generating model

## 7. Prediction
- Single policy expected claim frequency
- Batch prediction
- Export CSV
- (V2) kind-aware: for a severity model the what-if is a single **claim**
  (no exposure input) predicting expected claim amount; batch predicts per
  claim row

## 8. Severity Model (V2)
- Loads via Data Import like any dataset: built-in **freMTPL2 severity**
  (26.6k claims joined with the nine rating factors, per-claim grain)
- Family selection: Gamma (default) / Inverse Gaussian — log link, no offset
- Formula preview from the shared spec (same Feature Engineering screen applies)
- Fit; coefficient table with p-values, deviance, AIC
- Educational aids: claim-size relativities (`exp(beta)` = multiplicative
  effect on expected claim amount), plain-language explanations, highlighting
  of insignificant variables
- Run history (same model_runs table; family distinguishes runs)
- Kind guards: the Frequency Model screen points severity datasets here, and
  vice versa

---

## Future screens (roadmap, per car-insurance.md)

- **V3 — Pure Premium:** frequency × severity, variable contributions
  (expected yearly loss = predicted frequency × predicted claim amount —
  deterministic, no simulation needed)
- **V3.x — Simulation:** compound Poisson Monte Carlo of yearly losses from
  the two fitted models (see architecture.md "Modeling"). Single-profile
  what-if or whole portfolio; yearly-loss histogram, percentile /
  exceedance-probability table. Must carry two honest captions: claim counts
  and sizes assumed independent given the rating factors, and the Gamma's
  light tail understates extreme years (teaches the method, not a credible
  1-in-200)
- **V4 — Generic workbench:** arbitrary portfolios; Reports screen
  (HTML/PDF export, model summary)
- **Backlog:** Chapter 27 synthetic dataset + hidden-DGM educational features
  (true-model comparison, Dummy1/Dummy2 insignificance demo)
