# E2E — Kind-aware Diagnostics + Prediction (V2 slice 3: `predict_severity`, interim guards retired)

Change under test: the Diagnostics screen (`pages/05_Diagnostics.py`) and the
Prediction screen (`pages/06_Prediction.py`) become **kind-aware** — they read
the single active-model slot (`model` / `model_meta["kind"]`) and render the
severity variant for a Gamma/IG model instead of the slice-2 interim guard
("…arrives with the next slice…", which must be GONE). New engine function
`prediction.predict_severity(model, claims, spec)`: returns a **copy** of
`claims` with ONE new column `expected_claim_amount` (the model mean per
claim row — **no exposure scaling**, no `expected_frequency` /
`expected_claims` columns); a missing predictor raises a `ValueError` naming
it. The diagnostics engine is untouched (already offset-None-safe):
`observed_vs_predicted` on a severity model divides band sums by the row
count, so its `observed_frequency` / `predicted_frequency` columns ARE the
observed / predicted **average claim amount** per predicted-amount band.
UI: fresh-session guard "Fit a model first" (may point to both model
screens); a NEW **kind-mismatch guard** on both pages when the loaded
dataset's kind differs from the active model's kind (fragments `severity
model` + `frequency dataset`, and the reverse), preventing the
length-mismatch crash between `fittedvalues` and a re-loaded portfolio;
Diagnostics' calibration section additionally guards on a row-count
mismatch. Severity Diagnostics: same four sections with severity wording
(claim-size / claim amount relativity captions, a right-skew/heavy-tail
residual caption instead of the Poisson "mostly zero claims … lumpy"
teaching note, calibration axis "Average claim amount", band title
"Predicted-claim-amount band"). Severity Prediction: "Single claim" what-if
with one widget per predictor and **no exposure input**, ONE metric
"Expected claim amount"; batch button "Predict for loaded claims" →
metrics "Mean expected claim amount" / "Total expected claim amount" /
"Total observed claim amount", preview grid, CSV download; an HONEST caption
("…does not reproduce…") that a log-link Gamma does NOT balance the observed
total by construction (unlike Poisson). Batch results are tagged with their
kind (session key `predictions_kind`) so a stale batch from the other kind
is hidden, never rendered under the wrong wording.

BA scenarios (the actuary/learner from the earlier slices now runs the
severity model through the rest of the workflow):

- S1 — As an actuary who fitted the Gamma model on `fremtpl2_sev`, I open
  Diagnostics and get the FULL diagnostics for that model, not a guard:
  4 metrics, the `ClaimAmount ~ …` formula caption with family gamma, the
  coefficient-CI chart with relativities and the dashed 1.0 line, residual
  histogram + kind radio, QQ plot, and Observed vs Predicted with y-values in
  the thousands (≈1,000–5,000 — NEVER ≈0.1, which would mean an exposure
  divisor). The Poisson teaching caption must not show.
- S2 — As a learner I open Prediction with the severity model active and get
  a "Single claim" section: one widget per predictor, NO exposure/policy-years
  input, a Predict button; Predict shows ONE metric "Expected claim amount",
  a positive value in the low thousands for the median profile.
- S3 — As an actuary I click "Predict for loaded claims" and get batch
  results on the 26,444 claims: currency-style metrics (mean / total expected
  / total observed claim amount), a preview grid with `expected_claim_amount`,
  a CSV button. The total expected is ~1.5% BELOW observed (2,230.9 × 26,444
  ≈ 58.99m vs 59.91m) — that is CORRECT for a log-link Gamma and the page must
  say so honestly; a copy-pasted "reproduces the observed total by
  construction" caption on the severity view is a FAIL.
- S4 — As a slice-2 user I remember the interim guards; with a severity model
  active `next slice` appears NOWHERE on Diagnostics/Prediction.
- S5 — As a V1 user, nothing regresses on the frequency side: Poisson caption,
  calibration by predicted-frequency band (weighted 0.1007), "Single policy"
  with the exposure input and BOTH metrics, batch 36,102 == 36,102 with the
  by-construction caption; `e2e/e2e_diag_pred.py` stays green untouched.
- S6 — Kind mismatch, direction A: severity model active, then I load the
  FREQUENCY dataset. Diagnostics and Prediction show an info guard naming the
  mismatch — no charts, no Predict form, no crash, and emphatically no Gamma
  predictions silently computed on ClaimNb rows.
- S7 — Kind mismatch, direction B: frequency model active (678,013 fitted
  values), severity dataset loaded (26,444 rows). Same guard in reverse; the
  calibration must not run `fittedvalues` against the wrong frame (the
  length-mismatch traceback is the trap).
- S8 — Stale predictions: I ran the frequency batch (session key
  `predictions` holds 678k rows with `expected_claims`), then fit the severity
  model and open Prediction. The old frequency numbers ("Total expected
  claims", 36,102) must NOT render under the severity view, and no KeyError
  on `expected_claim_amount`.
- S9 — Reverse slot-swap: after S6, re-fitting Poisson restores S5 behaviour
  with no severity residue.
- S10 — Fresh session: `/Diagnostics` and `/Prediction` without any dataset
  or model show "Fit a model first"; zero metrics, no exception.
- Engine truths (asserted engine-level, never scraped): `predict_severity`
  mean within 1% of 2,230.9 (within 5% of observed 2,265.5), all values
  positive/finite, column set = original + `expected_claim_amount`,
  mean(`expected_claim_amount`) == mean(`fittedvalues`) to 1e-6 relative
  (row alignment + no exposure scaling), 1 row in → 1 row out, missing
  predictor → ValueError naming it; `observed_vs_predicted` exposure column ==
  claim counts summing to 26,444, predicted monotone across ≤10 bands.

Test Agent notes from the BA interview: mechanics carry over the hard-won
lessons in `e2e/README.md`, `e2e/e2e_diag_pred.py` and
`e2e/e2e_severity_model.py`:

- Engine truths FIRST (TC1–TC2) as deterministic Python from the repo root
  (`uv run python <tempfile.py>`, scripts in the session scratchpad — or
  inline in the committed runner, same precedent as slice 2).
- App headless on port 8598:
  `uv run streamlit run app.py --server.port 8598 --server.headless true`;
  both Parquet files present in `data/raw/`. **Never delete or truncate
  `data/workbench.db`** — the UI fits (TC5 Poisson, TC8 Gamma, optional TC11
  Poisson) each APPEND one real run; that is the behaviour under test.
- Session state is per browser tab; `page.goto` after loading DROPS it. All
  post-load UI TCs run in ONE tab of one context, **sidebar links only**
  (`Data Import`, `Frequency Model`, `Severity Model`, `Diagnostics`,
  `Prediction`). Fresh-session guards (TC3) use separate contexts with a
  direct `goto` — the sanctioned exception because an empty session is the
  point.
- The single-slot model dictates the ORDER of the UI flow (one tab):
  load freq → fit Poisson (~12 s, timeout 180,000 ms) → frequency batch on
  Prediction (creates the S8 stale-`predictions` precondition) → load
  severity via the combobox route → Diagnostics + Prediction guards (S7,
  direction B) → fit Gamma (~30,000 ms timeout) → Diagnostics severity happy
  path → Prediction severity single + batch (stale frequency batch hidden) →
  load frequency dataset again (S6, direction A) → optional Poisson re-fit
  (S9, executed-if-time or manual).
- Combobox: the ONE sanctioned BaseWeb route — click `[data-testid=
  "stSelectbox"]` first on Data Import, type `severity` (later `frequency`),
  press Enter — worked first try in slices 1 and 2; reuse verbatim, one
  retry max, manual fallback for the chained TCs if it stops taking. All
  other widget changes (Prediction selectboxes, residual-kind radio) stay in
  the deferred/manual bucket.
- `expect(...).to_be_visible()` before any `.count()`. Known-good selectors:
  `[data-testid="stMetric"]`, `[data-testid="stDataFrame"]`,
  `[data-testid="stVegaLiteChart"]`, `[data-testid="stNumberInput"]`,
  `[data-testid="stSelectbox"]`, `[data-testid="stException"]`,
  `get_by_role("button", name=..., exact=True)` (the `Predict` button name is
  a prefix of `Predict for loaded …` — always `exact=True`).
- Absence assertions use DISTINCTIVE full phrases: `claim frequency`,
  `policy-year`, `next slice`, `Expected claims`, `Single policy` — never
  bare `frequency` (sidebar link "Frequency Model") or bare `Exposure` on a
  page where a table/grid could legitimately contain it. Presence: `claim
  amount` ≥ 1 on severity views; `claim frequency` ≥ 1 on frequency views.
- Metric VALUES are not scraped (glide grids and metric text are unreliable
  for numerics); the only UI numeric assertions are the frequency `36,102`
  precedent and the severity `26,444` load message. Severity numerics are
  TC1/TC2 engine truths.
- Guard ORDER trap: model-present → dataset-kind matches model kind →
  row-count match. A fresh session must say "Fit a model first", never a
  kind-mismatch message.
- Exact captions/guard wording are implementation-chosen: match loosely on
  the fragments named per TC and record actuals in Results. Wording drift is
  not a FAIL. A guard where diagnostics should render, a `next slice`
  fragment, frequency wording on a severity view (or vice versa), an
  exposure input on the single-claim form, stale frequency batch numbers on
  the severity view, calibration values ≈0.1 on the severity model, or any
  traceback/`stException` IS a FAIL.

## TC1 — Engine: `predict_severity` contract on the real severity data

Engine-level (deterministic, automated). The Gamma fit takes a few seconds:

```python
import numpy as np
import pandas as pd

from pricing_engine.data import load_dataset
from pricing_engine.glm import build_formula, fit_severity_glm
from pricing_engine.prediction import predict_severity

df, spec = load_dataset("fremtpl2_sev")
assert len(df) == 26_444 and spec.kind == "severity" and spec.offset is None
model = fit_severity_glm(df, build_formula(spec))  # gamma default

batch = predict_severity(model, df, spec)

# Column contract: original columns + exactly one new column; NO frequency leakage
assert set(batch.columns) == set(df.columns) | {"expected_claim_amount"}, batch.columns
assert "expected_frequency" not in batch.columns and "expected_claims" not in batch.columns
assert "expected_claim_amount" not in df.columns  # copy, not mutation
assert len(batch) == 26_444

amounts = batch["expected_claim_amount"].to_numpy()
assert (amounts > 0).all() and np.isfinite(amounts).all()

# No exposure scaling + row alignment: in-sample identity with fittedvalues
fitted = np.asarray(model.fittedvalues)
assert abs(amounts.mean() - fitted.mean()) / fitted.mean() < 1e-6, (amounts.mean(), fitted.mean())
assert abs(amounts[0] - fitted[0]) / fitted[0] < 1e-6

# Calibration (slice-2 recorded mean fitted 2,230.9; observed 2,265.5)
mean_expected = float(amounts.mean())
assert abs(mean_expected - 2_230.9) / 2_230.9 < 0.01, mean_expected
assert abs(mean_expected - 2_265.5) / 2_265.5 < 0.05, mean_expected
observed_total = float(df[spec.target].sum())
expected_total = float(amounts.sum())
gap = (expected_total - observed_total) / observed_total
assert abs(gap) < 0.05, gap  # log-link Gamma: small shortfall expected, NOT exact balance

# Single claim: predictors only (no target column needed), 1 row in -> 1 row out
one = df.head(1)[list(spec.predictors)].copy()
single = predict_severity(model, one, spec)
assert len(single) == 1 and float(single["expected_claim_amount"].iloc[0]) > 0
assert abs(float(single["expected_claim_amount"].iloc[0]) - fitted[0]) / fitted[0] < 1e-6

# A row carrying an Exposure column must be ignored, not multiplied
with_exposure = df.head(5).assign(Exposure=0.5)
assert np.allclose(
    predict_severity(model, with_exposure, spec)["expected_claim_amount"], fitted[:5]
)

# Missing predictor -> ValueError naming it
try:
    predict_severity(model, df.drop(columns=["BonusMalus"]), spec)
    raise SystemExit("FAIL: no ValueError for missing predictor")
except ValueError as e:
    assert "BonusMalus" in str(e), e
print("PASS", round(mean_expected, 1), round(expected_total), round(observed_total), f"{gap:+.2%}")
```

Expected: prints `PASS` + mean expected (≈2,230.9), expected total (≈58.99m),
observed total (≈59.91m) and the gap (≈−1.5%) — record all four in Results;
the gap is the number the honest caption on the Prediction page explains.
`expected_frequency`/`expected_claims` in the result, an exposure
multiplication, or a mean outside the bands is a FAIL.

## TC2 — Engine: severity calibration bands are average claim amounts

Engine-level. Same fit as TC1 (rerun or share):

```python
import numpy as np

from pricing_engine.data import load_dataset
from pricing_engine.diagnostics import (
    observed_vs_predicted,
    qq_data,
    residual_histogram,
    residuals,
)
from pricing_engine.glm import build_formula, fit_severity_glm

df, spec = load_dataset("fremtpl2_sev")
model = fit_severity_glm(df, build_formula(spec))

for kind in ("deviance", "pearson"):
    res = residuals(model, kind)
    assert len(res) == 26_444 and np.isfinite(res).all(), kind
hist = residual_histogram(model, bins=40)
assert hist["count"].sum() == 26_444
qq = qq_data(model, points=100)
assert len(qq) == 100 and (np.diff(qq["theoretical"]) > 0).all()

ovp = observed_vs_predicted(df, spec, model, groups=10)
assert len(ovp) <= 10
# offset None -> the "exposure" weights are CLAIM COUNTS summing to the row count
assert ovp["exposure"].sum() == 26_444, ovp["exposure"].sum()
assert (ovp["exposure"] > 0).all()
# the "frequency" columns are per-claim AVERAGE CLAIM AMOUNTS, in the thousands
weighted_pred = (ovp["predicted_frequency"] * ovp["exposure"]).sum() / 26_444
assert abs(weighted_pred - 2_230.9) / 2_230.9 < 0.01, weighted_pred
assert (ovp["predicted_frequency"] > 500).all(), "values ~0.1 would mean an exposure divisor"
assert (np.diff(ovp["predicted_frequency"]) >= 0).all()
assert ovp["observed_frequency"].between(500, 10_000).all(), ovp["observed_frequency"].tolist()
print("PASS", len(ovp), round(weighted_pred, 1),
      round(ovp["observed_frequency"].min()), round(ovp["observed_frequency"].max()))
```

Expected: prints `PASS`, the band count, the weighted predicted mean
(≈2,230.9) and the observed band-mean range (roughly 1,000–5,000 — record
actuals). Any band value near 0.1 is the highest-severity failure here: the
calibration chart would then be plotting frequencies against a Gamma model.

## TC3 — UI: fresh-session guards on both pages

1. For each of `Diagnostics` and `Prediction`: open a **new browser
   context**, `page.goto("http://localhost:8598/<page>")` directly (empty
   session is the point).
2. Expected on each:
   - Info box containing `Fit a model first` (it may name both model
     screens — record wording).
   - NOT a kind-mismatch message (no `severity model` / `frequency dataset`
     fragments) — guard-order trap.
   - Zero `[data-testid="stMetric"]`, no `Predict` button (`exact=True`), no
     `Load a dataset first` text, no `Traceback`, no
     `[data-testid="stException"]`.
3. Close the contexts.

## TC4 — UI: frequency baseline + stale-batch precondition (S5, sets up S8)

Fresh context, ONE tab for TC4–TC11:

1. `goto /Data_Import`; click `Load dataset` with defaults untouched; wait
   for the `678,013` fragment (≤ ~15 s).
2. Sidebar `Frequency Model`; click `Fit model`; wait for `Model fitted and
   recorded` (timeout 180,000 ms). Appends one real run.
3. Sidebar `Diagnostics`. Expected (regression, frequency wording):
   - `Model summary`, `Coefficients with confidence intervals`, `Residuals`,
     `QQ plot`, `Observed vs Predicted` all visible (timeout 60,000 ms for the
     first); `stVegaLiteChart` ≥ 2; `stMetric` ≥ 4.
   - Frequency wording present: `claim frequency` or `Claim frequency` ≥ 1;
     the Poisson caption fragment `Poisson` ≥ 1.
   - ABSENT: `next slice`, `claim amount` (count == 0 — no severity
     residue), no `stException`.
4. Sidebar `Prediction`. Expected: `Single policy` visible, then `Batch
   prediction`; `stNumberInput` ≥ 4 (the exposure input among them);
   `Predict` (`exact=True`) → `Expected claim frequency` visible.
5. Click `Predict for loaded portfolio`; wait for `Total expected claims`
   (timeout 120,000 ms); `Total observed claims` and `36,102` visible;
   `Download predictions CSV` visible (not clicked — 678k payload). This
   leaves the frequency batch in session state — the S8 precondition.
   ABSENT: `claim amount`, `Single claim`, `next slice`; no `stException`.

## TC5 — UI: kind mismatch, direction B — frequency model + severity dataset (S7)

Same tab:

1. Sidebar `Data Import`; combobox route: click the first
   `[data-testid="stSelectbox"]`, type `severity`, Enter; click `Load
   dataset`; wait for `26,444` (≤ ~15 s). The Poisson model still sits in
   the slot.
2. Sidebar `Diagnostics`. Expected:
   - Info guard with fragments `frequency model` and `severity dataset`
     (pointing to re-fit / the matching screen — record wording).
   - NO diagnostics render: zero `stMetric`, zero `stVegaLiteChart`, no
     `Observed vs Predicted`; no `Traceback` / `stException` (the
     678,013-vs-26,444 length-mismatch crash is the trap).
3. Sidebar `Prediction`. Expected:
   - Same guard fragments; no `Predict` button (`exact=True`), no `Single
     policy`, no `Single claim`; the stale frequency batch metrics (`Total
     expected claims`) NOT rendered; no `stException`.

## TC6 — UI: severity fit (precondition for TC7–TC9)

Same tab:

1. Sidebar `Severity Model`; `Model setup` visible, formula `ClaimAmount ~
   Area` visible; click `Fit model`; wait for `Model fitted and recorded`
   (timeout 30,000 ms). Appends one real run (family gamma). No
   `stException`.

## TC7 — UI: severity Diagnostics happy path (S1, S4)

Same tab, sidebar `Diagnostics`. Expected (timeout 60,000 ms on the first):

- NO guard: `next slice` count == 0; no `frequency model` / `severity
  dataset` guard fragments; `Model summary` visible.
- Metric row `stMetric` count == 4 after expect-before-count (AIC / BIC /
  Deviance / Parameters); formula caption containing `ClaimAmount ~` and
  `gamma` (or `Gamma`).
- `Coefficients with confidence intervals` section with a `stVegaLiteChart`
  and the coefficient-table expander; caption with fragment `claim-size` or
  `claim amount`.
- `Residuals` with the kind radio (`[data-testid="stRadio"]` ≥ 1) and a
  chart; the Poisson teaching caption fragment `mostly zero claims` count ==
  0; a severity caption is expected (fragment `heavy` or `skew` or `large
  claims` — record wording; drift is not a FAIL, the Poisson caption IS).
- `QQ plot` section with a chart.
- `Observed vs Predicted` section with a chart, axis/caption fragments
  `Average claim amount` and `Predicted-claim-amount band` (or close
  wording — record); `Calibration table` expander present. `stVegaLiteChart`
  total ≥ 4.
- Whole-page ABSENT: `claim frequency` == 0, `policy-year` == 0,
  `predicted-frequency band` == 0, `next slice` == 0; `claim amount` ≥ 1.
- No `Traceback` / `stException`. (Band VALUES in the thousands are TC2's
  engine truth — not scraped.)

## TC8 — UI: severity Prediction — single claim + batch + stale batch hidden (S2, S3, S8)

Same tab, sidebar `Prediction`. Expected:

1. Before any click:
   - `Single claim` header visible; `Single policy` count == 0.
   - Input widgets: `stSelectbox` ≥ 4 and `stNumberInput` ≥ 4 for the nine
     predictors — and NO exposure input: `policy-year` count == 0 and no
     number input labelled with `Exposure` (assert `get_by_text("Exposure
     (policy-years)")` count == 0; bare `Exposure` is not asserted).
   - Batch section header visible (fragment `Batch prediction`); the
     **stale frequency batch is hidden**: `Total expected claims` count == 0,
     `36,102` count == 0, `Mean expected frequency` count == 0 (S8 — the
     frequency batch from TC4 step 5 is still in session state).
   - `next slice` == 0; no `stException`.
2. Click `Predict` (`exact=True`). Expected: metric `Expected claim amount`
   visible; `Expected claims` count == 0 and `Expected claim frequency`
   count == 0 (ONE metric for the single claim, not two). Value is the
   median-profile claim — engine-adjacent sanity only (positive; not scraped
   numerically; record if readable).
3. Click `Predict for loaded claims` (record the actual button label if it
   drifted). Expected (timeout 60,000 ms):
   - Metrics `Mean expected claim amount`, `Total expected claim amount`,
     `Total observed claim amount` visible; `stMetric` ≥ 3 (plus the single
     metric).
   - Honest caption fragment `does not reproduce` (or equivalent — record);
     the Poisson fragment `by construction` count == 0.
   - A `stDataFrame` preview grid; `Download predictions CSV` visible (the
     26k payload is safe to click — optional; record if clicked).
   - Whole-page ABSENT: `Total expected claims`, `claim frequency`,
     `policy-year`, `next slice` all count == 0; no `stException`.

## TC9 — UI: kind mismatch, direction A — severity model + frequency dataset (S6)

Same tab:

1. Sidebar `Data Import`; combobox route with the fragment `frequency`
   (one retry max; if the route fails here, record and mark TC9–TC10
   manual); click `Load dataset`; wait for `678,013`. The Gamma model still
   sits in the slot.
2. Sidebar `Diagnostics`. Expected: info guard with fragments `severity
   model` and `frequency dataset`; zero `stMetric`, zero `stVegaLiteChart`;
   no `stException`.
3. Sidebar `Prediction`. Expected: same guard fragments; no `Predict` button
   (`exact=True`); neither `Single claim` nor `Single policy`; the severity
   batch metrics (`Total expected claim amount`) NOT rendered; no
   `stException`. (Silently computing Gamma predictions on ClaimNb rows is
   the trap.)

## TC10 — UI: reverse slot-swap restores the frequency views (S9) — executed-if-time

Same tab (adds ~12 s and one history row; run if time permits, otherwise
record as manual):

1. Sidebar `Frequency Model`; click `Fit model`; wait for `Model fitted and
   recorded` (timeout 180,000 ms).
2. Sidebar `Diagnostics`. Expected: no guard; `Observed vs Predicted` and
   `Model summary` visible; `claim frequency` ≥ 1; `claim amount` == 0;
   `stMetric` ≥ 4; no `stException`.
3. Sidebar `Prediction`. Expected: `Single policy` visible, `Single claim`
   == 0; the severity batch from TC8 is hidden (`Total expected claim
   amount` == 0); no `stException`.

## TC11 — Regression: existing suites still green

From the repo root, with port 8598 free (the runners each launch their own
app instance — never concurrently):

1. `uv run pytest` — full suite passes (102 tests at slice-2 completion plus
   the new severity prediction/diagnostics unit tests — record the count)
   with the 75% coverage gate met.
2. `uv run python e2e/e2e_diag_pred.py` — the V1 frequency runner passes
   UNTOUCHED (S5).
3. `uv run python e2e/e2e_severity_model.py` — the slice-2 runner passes
   after its TC7 inversion: with a severity model active, Diagnostics and
   Prediction must now RENDER (`next slice` count == 0, `stMetric` ≥ 4 on
   Diagnostics, `Single claim` on Prediction) instead of showing the interim
   guard; the screen-04 severity-dataset guard assertion stays. Update
   `.planning/e2e-tests/severity-model.md` TC7 to match and note the
   inversion in its Results.
4. `uv run ruff check pricing_engine/ tests/ app.py pages/ e2e/`,
   `uv run ruff format --check …`, `uv run mypy pricing_engine/ tests/` —
   clean.

## TC12 — Deferred/manual: widget variations, CSV contents, IG in the slot

BaseWeb interactions beyond the sanctioned combobox route stay **manual**:

1. Single-claim what-if: change one selectbox (e.g. `VehBrand`) and one
   number input (e.g. `BonusMalus` 50 → 100), Predict — the expected claim
   amount moves in the direction of the coefficient sign shown on the
   Severity Model screen (BonusMalus is the one significant term: higher
   BonusMalus → higher expected claim amount).
2. Residual kind radio → `pearson` on the severity model: histogram and QQ
   re-render, no exception.
3. Click `Download predictions CSV` on the severity batch, open the file:
   26,444 rows, an `expected_claim_amount` column, NO `expected_frequency`
   / `expected_claims` columns.
4. Fit `Inverse Gaussian` on the Severity Model screen (friendly error per
   slice 2): the slot keeps the PREVIOUS Gamma model — Diagnostics must
   still show that model consistently (AIC 573,121-ish, not a crash).
5. TC10 if it was not executed. Record executed/deferred in Results.

## Execution notes

- Prerequisites: both real Parquet files in `data/raw/`; Playwright +
  Chromium installed (`uv run playwright install chromium`); port 8598 free.
  **Never delete or truncate `data/workbench.db`** — the UI fits (TC4 step
  2, TC6, optional TC10) each append one real run (expected behaviour).
- Engine TCs (TC1–TC2) run FIRST (scratchpad scripts or inline at the top
  of the committed runner `e2e/e2e_severity_diag_pred.py` — slice-2
  precedent). TC1's mean/total/gap and TC2's band range are the numbers
  behind the UI wording assertions.
- Start the app once headless on 8598. UI TCs: TC3 in throwaway contexts
  (direct goto sanctioned); TC4→TC10 sequentially in **ONE tab of one
  context**, **sidebar links only** after the first load. Timeouts: default
  ~20,000 ms; 180,000 ms after Poisson `Fit model`; 30,000 ms after Gamma
  `Fit model`; 120,000 ms after the frequency batch; 60,000 ms after the
  severity batch and on the first Diagnostics expectation.
- Combobox route (TC5 step 1 with `severity`, TC9 step 1 with `frequency`):
  click → type → Enter, one retry max; on failure the remaining chained TCs
  flip to manual — record the route either way. `expect` before `count`;
  `.first` on fragments that can appear twice; `exact=True` on `Predict`.
- Absence assertions use full distinctive phrases (`claim frequency`,
  `policy-year`, `next slice`, `Total expected claims`, `Single policy`,
  `Single claim`, `by construction`, `mostly zero claims`) — never bare
  `frequency`, `Model`, or `Exposure`.
- Exact-text caveats: captions, guard wording, button labels (`Predict for
  loaded claims`), axis titles and metric labels are implementation-chosen
  — match loosely on the fragments named per TC and record actuals in
  Results. Wording drift is not a FAIL. A guard where the severity
  diagnostics/prediction should render, a `next slice` fragment anywhere, a
  Poisson caption or `claim frequency` on a severity view (or `claim
  amount` on a frequency view), an exposure input on the single-claim form,
  two metrics for a single claim, stale batch numbers from the other kind,
  a `by construction` balance claim on the severity batch, calibration
  values ≈0.1 on the severity model (TC2), `expected_claims` /
  `expected_frequency` in a severity result (TC1), a crash on either kind
  mismatch (TC5/TC9), or any traceback/`stException` IS a FAIL.
- The ~1.5% Gamma total shortfall (TC1) and the real-data band range (TC2)
  are pre-authorized observations to record, not failures.

## Results

Executed 2026-08-25 via the committed runner `e2e/e2e_severity_diag_pred.py`
(engine TCs inline, UI TCs via Playwright against port 8598; TC11 run
separately from the shell). **TC1–TC11 all PASSED first run (TC10 executed,
not deferred); TC12 deferred/manual.**

- TC1 PASS — `predict_severity` column contract holds (original columns +
  `expected_claim_amount` only, copy semantics, 26,444 rows); in-sample
  identity with `fittedvalues` (mean and row 0 to 1e-6); an extra `Exposure`
  column is ignored, not multiplied; missing `BonusMalus` → ValueError naming
  it. **Mean expected claim amount 2,230.9; expected total 58,995,121 vs
  observed 59,909,216 → gap −1.53%** (the log-link Gamma balance point the
  Prediction caption explains; well inside the ±5% bound).
- TC2 PASS — 10 bands, claim-count weights sum to 26,444, weighted predicted
  mean 2,230.9, predicted band means monotone, **observed band averages
  1,586–5,453** (all in the thousands — no exposure-divisor bug).
- TC3 PASS — fresh-session guard on both pages: `Fit a model first — go to
  Frequency Model or Severity Model.`; not a mismatch guard; zero metrics.
- TC4 PASS — frequency baseline unchanged: all four Diagnostics sections,
  Poisson caption, `claim frequency` wording, no severity residue; Prediction
  `Single policy` + `Expected claim frequency`; batch `36,102` visible,
  frequency batch left in session state (S8 precondition).
- TC5 PASS — direction B guard wording: `The active model is a frequency
  model but the loaded dataset is a severity dataset — fit a severity model
  on it first (go to Severity Model) or reload the frequency dataset.`; no
  metrics/charts, no Predict form, stale batch hidden, no exception (the
  678,013-vs-26,444 length-mismatch trap is closed).
- TC6 PASS — Gamma fit recorded (one real run appended).
- TC7 PASS — severity Diagnostics: no `next slice`, exactly 4 metrics,
  caption `ClaimAmount ~ … (gamma, severity)`, `Claim-size relativities
  exp(coef)` caption, residual caption `Claim amounts are heavy-tailed: …
  typical for Gamma severity models`, Poisson caption absent, `Average claim
  amount` / `Predicted-claim-amount band` present, Calibration table
  expander (severity columns renamed to `claims` /
  `observed_avg_claim_amount` / `predicted_avg_claim_amount`), ≥ 4 charts;
  `claim frequency`, `policy-year`, `predicted-frequency band` all absent.
- TC8 PASS — `Single claim` section, nine predictor widgets, **no exposure
  input**, stale frequency batch hidden (`Total expected claims`, `36,102`,
  `Mean expected frequency` all count 0). Predict → ONE metric `Expected
  claim amount` = **1,504** for the median profile. `Predict for loaded
  claims` → metrics `2,231` / `58,995,121` / `59,909,216`, honest caption
  `Unlike Poisson, a log-link Gamma GLM does not reproduce the observed total
  exactly — …` (`by construction` absent), preview grid, CSV button visible
  (not clicked).
- TC9 PASS — combobox route with `frequency` worked; direction A guard
  wording mirrors TC5 (`…severity model but the loaded dataset is a frequency
  dataset … go to Frequency Model …`); no metrics/charts/Predict, severity
  batch metrics hidden, no exception.
- TC10 PASS (executed) — Poisson re-fit restores the frequency views: no
  guard, `claim frequency` wording back, `claim amount` absent, `Single
  policy` back, the severity batch hidden. Three real runs appended to
  `data/workbench.db` by this runner in total (expected behavior under test).
- TC11 PASS — `uv run pytest`: 109 passed, 99.43% coverage (7 new tests);
  `e2e/e2e_diag_pred.py` untouched: all TCs PASS; `e2e/e2e_severity_model.py`
  with TC7 inverted: TC1–TC7 PASS (IG still raises the documented
  `estimation infeasible` ValueError engine-side, caught by the friendly
  error on screen 07); ruff check/format and mypy clean (incl. `e2e/`).
- TC12 DEFERRED/manual per plan (widget variations, pearson radio, CSV
  contents, IG-failure-keeps-Gamma-in-slot) — added to the manual-walkthrough
  backlog item in `TODO.md`.

## V3 slice 1 inversions (2026-08-31, per-kind model slots)

The single active-model slot this plan tested was split into per-kind slots
(`.planning/e2e-tests/per-kind-model-slots.md`); the committed runner was
updated accordingly and re-executed green on 2026-08-31:

- TC3 INVERTED — a fresh session now shows the dataset-first guard
  (`Load a dataset first — go to Data Import.`); the dual "Fit a model
  first" wording is retired.
- TC5 INVERTED — frequency model + severity dataset now shows the kind guard
  `Fit a severity model first — go to Severity Model.`; the mismatch guard
  text is retired (asserted absent).
- TC9 INVERTED — with both kinds fitted, loading the frequency dataset now
  RENDERS the kept frequency views without a refit (this was the V2
  mismatch-guard state; it is the V3 headline behavior).
- TC2 columns renamed `observed_frequency`/`predicted_frequency` →
  `observed_mean`/`predicted_mean` (values unchanged: weighted_pred 2,230.9,
  bands 1,586–5,453).
