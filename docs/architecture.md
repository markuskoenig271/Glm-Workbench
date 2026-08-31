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
"V2 — Severity design" below. **V2 is complete.**

**Version 3 scope (proposed 2026-08-31): pure premium.** Split the single
active-model slot into per-kind slots so a frequency and a severity model can
coexist in session, add **fitted-model persistence** (models saved to disk on
fit, reloadable from the run history — no refit needed to price), then add a
Pure Premium screen framed as a **quote calculator**: enter a motor policy's
rating-factor values and get the annual risk premium λ(x) · μ(x), with a
multiplicative premium-breakdown table and a portfolio batch. See "V3 — Pure
premium design" below. Simulation (V3.x) and reporting remain later versions.

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
    ├── Prediction          (kind-aware since V2)
    └── Pure Premium        (V3 — quote calculator, frequency × severity)

    (V3.x+: Simulation, Reports)

pricing_engine/
    data.py            # import, validation, freMTPL2 loaders, dataset spec
    exploration.py     # aggregate-only: summary, one-way frequencies, histograms
    preprocessing.py
    glm.py             # frequency (V1) + severity (V2) fitting
    prediction.py      # frequency prediction (V1), pure premium (V3)
    diagnostics.py
    simulation.py      # (V3.x) compound Poisson Monte Carlo — yearly loss distribution
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
- **Fitted-model persistence (V3):** `model_runs.model_path` points to a
  statsmodels pickle in `models/` (saved on fit with `remove_data=True`,
  reloadable into the per-kind session slot from the run history — see
  "V3 — Pure premium design", slice 2)
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
- Pure Premium (V3) — needs both models in session at once: V2's single
  active-model slot (fitting severity replaces the active frequency model and
  vice versa) is split per kind. The **expected** yearly loss needs no
  simulation: E[S] = λ(x) · μ(x) (predicted frequency × predicted claim
  amount) — that IS the pure premium. See "V3 — Pure premium design" below.
- Aggregate loss simulation (V3.x, discussed 2026-07-30) — new module
  `simulation.py`: compound Poisson Monte Carlo of the **yearly loss
  distribution** (percentiles / exceedance probabilities — what the
  deterministic pure premium cannot give). Per policy profile (or whole
  portfolio): draw N ~ Poisson(λ(x)), then N severity draws, sum; repeat many
  sims. The fitted Gamma GLM defines a full per-profile severity
  distribution — mean μ(x) = exp(Xβ) plus the estimated dispersion φ
  (statsmodels `model.scale`), i.e. Gamma(shape = 1/φ, scale = μ(x)·φ) — so
  the engine must surface the dispersion, not just the mean.
  Prerequisites: V2 slice 3 (`predict_severity`) and the V3 per-kind model
  slots. Framing caveats (UI captions, not fine print): claim counts and
  sizes assumed independent given the rating factors; the Gamma is much
  lighter-tailed than the empirical severity (max ≈ 4.08m vs median 1,172),
  so simulated extreme years understate tail risk — the screen teaches the
  *method*, it does not produce a credible 1-in-200 (a spliced Pareto tail
  is a further-future idea).
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

## V3 — Pure premium design (proposed 2026-08-31)

Framing (Markus, 2026-08-31): the new screen is a **quote calculator** — you
"take out" a motor policy by entering its rating-factor values and get the
annual risk premium — and fitted models are **persisted** so pricing does not
require refitting (his ask: reuse stored fits instead of recomputing).
Decisions 2026-08-31: model selection on Diagnostics/Prediction goes by the
loaded dataset's kind (no picker widget); the premium breakdown ships in the
first cut; full persistence (save on fit + load from run history) rather than
session-only slots. Three slices, each through the Change Validation Workflow.

### Slice 1 — per-kind model slots (refactor, no new features)

- Session state: `model` / `model_meta` are replaced by two independent slots,
  `model_frequency` / `model_frequency_meta` and `model_severity` /
  `model_severity_meta`. The Frequency Model and Severity Model screens each
  write **their own** slot; fitting one kind no longer evicts the other.
- Diagnostics and Prediction select the slot by the **loaded dataset's kind**
  (`spec.kind`): a frequency dataset diagnoses/predicts with the frequency
  model, a severity dataset with the severity model. This keeps V2's
  dataset-kind ≙ model-kind invariant by construction (the reverse slot-swap
  crash trap disappears), and no model-picker widget is needed. New guard
  wording when the matching slot is empty: "Fit a <kind> model first."
  The `predictions_kind` batch tagging stays as-is.
- Kind-neutral rename (carried V2 note): `diagnostics.observed_vs_predicted`
  output columns `observed_frequency` / `predicted_frequency` become
  `observed_mean` / `predicted_mean` ("mean response per unit of offset";
  offset None → per-row mean). Pages 05's per-kind wording table absorbs the
  labels; tests updated.
- No storage changes in this slice; `model_runs` history is untouched.

### Slice 2 — fitted-model persistence (save on fit, load from history)

Markus' ask (2026-08-31): pricing should reuse stored fits — no refitting just
to compute premiums, and fitted models survive a browser refresh.

- **Storage:** `model_runs` gains a nullable `model_path` column (SQLite
  `ALTER TABLE ... ADD COLUMN` migration on init; old rows stay loadable with
  `NULL`). Pickles live in `models/` (already in the repo layout; gitignored —
  artifacts, not source). Filename `<run_id>_<kind>_<family>.pickle`.
- **Save:** after a successful fit, screens 04/07 call
  `storage.save_model(results, ...)` → `results.save(path, remove_data=True)`.
  `remove_data` keeps the pickle small (parameters and scalar fit statistics,
  no 678k-row data arrays): `predict()`, `params`/`bse`/`pvalues`/`conf_int`,
  AIC/BIC/deviance all survive; `resid_*` and `fittedvalues` do NOT.
- **Load:** the run-history tables on screens 04/07 get a per-row "Load"
  action (rows of the matching kind with a non-NULL `model_path`);
  `storage.load_model(run_id)` fills that kind's session slot, with
  `model_meta["source"] = "loaded"` (a fresh fit sets `"fitted"`). A missing
  file or a statsmodels version-mismatch unpickling error is caught with a
  friendly message (local tool — no cross-version guarantee needed).
- **Documented limitation (by design):** a loaded model prices and shows
  coefficients/criteria, but residual/QQ/calibration sections on Diagnostics
  need the data arrays stripped by `remove_data` — for a `source="loaded"`
  model those sections show an info hint ("refit in this session for residual
  diagnostics") instead of crashing. The coefficient CI chart and criteria
  metrics render normally. Prediction and Pure Premium work fully.

### Slice 3 — engine `predict_pure_premium` + Pure Premium screen

- Engine (`prediction.py`): `predict_pure_premium(freq_model, sev_model,
  portfolio, spec)` on a **frequency-kind** frame (per-policy grain). Returns a
  copy with `expected_frequency` (annual rate, offset-free),
  `expected_claim_amount` (severity model applied to the same rating factors),
  `pure_premium = expected_frequency * expected_claim_amount` (annual, per
  unit of exposure) and `expected_loss = pure_premium * Exposure` (the
  policy-period expectation). Missing-predictor ValueError like the existing
  predictors — note both models' predictors must exist in the policy frame
  (engineered columns used by either model must be built on the loaded
  portfolio; the page surfaces this as a friendly hint).
- UI `pages/08_Pure_Premium.py` (screen 9 in ui_screens.md):
  - Guards: frequency-kind dataset loaded; **both** model slots filled —
    freshly fitted or loaded from the run history via slice 2 (else point to
    the missing model screen).
  - **Quote section** ("take out a policy"): one widget per rating factor
    (median/mode defaults like screen 7) + exposure input (default 1.0 year).
    Metrics: expected claim frequency, expected claim amount, and the headline
    **annual risk premium** λ·μ (scaled by exposure).
  - **Premium breakdown table** (the V3 "variable contributions"): both GLMs
    are log-link, so the quote factors multiplicatively — base premium
    (reference profile) × per-factor combined relativity
    (`exp(β_freq) · exp(β_sev)` for the quoted levels), with the frequency and
    severity relativities shown separately. Teaches how a tariff table falls
    out of two GLMs.
  - **Portfolio batch**: premium for every loaded policy; summary metrics
    (total expected loss vs observed total claim cost, average premium,
    premium percentiles), preview, kind-tagged CSV download.
  - Honest captions: risk premium only (no expenses, loadings, or profit);
    frequency ⊥ severity assumed given the rating factors; the log-link
    Gamma's balance gap (−1.53% on freMTPL2) propagates into the premium
    total; with 41/42 severity terms insignificant, μ(x) is nearly flat —
    most tariff differentiation comes from the frequency model.
- No new storage in this slice: quotes and batches are not persisted; models
  are persisted by slice 2.



1. **V1** — Frequency GLM (Chapter 27 example) — **complete 2026-07-25**
2. **V2** — Severity GLM (Gamma) — **complete 2026-08-25** (slices 1–3)
3. **V3** — Pure Premium (Frequency × Severity) — **design proposed 2026-08-31**
   - **V3.x** — Aggregate loss simulation (compound Poisson Monte Carlo, see Modeling)
4. **V4** — Generic pricing workbench for arbitrary portfolios

## Future Ideas

- XGBoost comparison
- SHAP explainability
- Cross-validation
- Experiment tracking
