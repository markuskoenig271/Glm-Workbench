# GLM Workbench – UI Screen Definitions

**Version 1 scope:** the Chapter 27 car-insurance frequency example — see
[car-insurance.md](car-insurance.md). Seven screens; severity, pure premium, and
reporting screens arrive with later versions (roadmap at the bottom).

## 1. Home
- Load the synthetic Chapter 27 dataset (sample data)
- Workflow status
- Project summary + version roadmap

## 2. Data Import
- Load sample dataset (~20,000 policies) or file upload (CSV)
- Preview
- Column mapping to the Chapter 27 schema (target `Claims`, offset `Exposure`)
- Validation report (types, missing values, exposure checks)

## 3. Data Exploration
- Summary statistics
- Histograms
- One-way claim frequency by predictor (Age, LocationType, Region, VehicleAge,
  FuelType, NoClaimYears, Dummy1, Dummy2)
- Missing values
- Correlations

## 4. Feature Engineering
- Variable selection
- Binning of continuous predictors (Age, VehicleAge)
- Encoding of categoricals (LocationType, Region, FuelType, Dummy2)
- Offset selection (Exposure)

## 5. Frequency Model
- Poisson GLM, log link, exposure offset (v1; Negative Binomial later)
- Formula editor / variable picker
- Fit model
- Coefficient table with p-values, deviance, AIC
- Educational aids: risk relativities (`exp(beta)`), plain-language coefficient
  explanations, highlighting of insignificant variables (Dummy1/Dummy2 should
  surface here)

## 6. Diagnostics
- Coefficient estimates with confidence intervals
- Deviance and Pearson residual plots
- Observed vs Predicted
- Model summary
- Comparison of estimated coefficients with the hidden data-generating model

## 7. Prediction
- Single policy expected claim frequency
- Batch prediction
- Export CSV

---

## Future screens (roadmap, per car-insurance.md)

- **V2 — Severity Model:** distribution selection (Gamma / Inverse Gaussian),
  formula editor, fit, diagnostics
- **V3 — Pure Premium:** frequency × severity, variable contributions
- **V4 — Generic workbench:** arbitrary portfolios; Reports screen
  (HTML/PDF export, model summary)
