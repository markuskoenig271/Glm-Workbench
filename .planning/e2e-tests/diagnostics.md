# E2E — Diagnostics slice (pricing_engine/diagnostics.py + pages/05_Diagnostics.py)

Change under test: the workflow's sixth screen — "can I TRUST the model I just
fitted?" Engine, four additions to `pricing_engine/diagnostics.py` (all
aggregate-only — never 678k raw rows to the browser):
`residuals(model, kind="deviance"|"pearson") -> pd.Series` (implemented from
the stub; ValueError for an unknown kind naming the valid kinds);
`residual_histogram(model, kind="deviance", bins=40) -> DataFrame(residual,
count)` — binned residual distribution, `residual` the bin midpoint (float);
`qq_data(model, kind="deviance", points=100) -> DataFrame(theoretical, sample)`
— sample quantiles of the residuals vs standard-normal theoretical quantiles
(`points` rows, not 678k); `observed_vs_predicted(df, spec, model, groups=10)
-> DataFrame(group, exposure, observed_frequency, predicted_frequency)` — the
actuarial calibration view: policies grouped into `groups` quantile bands of
predicted frequency (fittedvalues/exposure), per band summed exposure,
observed claims/exposure, predicted claims/exposure; readable group labels,
bands ordered. UI: `pages/05_Diagnostics.py` — guard needing a FITTED MODEL
("Fit a model first — go to Frequency Model."; if no dataset at all, the SAME
message still points to fitting — a different guard than the dataset guard of
the earlier screens); a metrics row from the stored meta (AIC, BIC, Deviance,
Parameters); "Coefficients with confidence intervals" — an Altair chart of
exp(coef) relativities with CI whiskers (exp(ci_low)..exp(ci_high)) for the
top ~20 non-intercept terms by |coef| and a reference line at relativity 1.0,
plus the coefficient table in an expander; "Residuals" — kind radio (deviance
default / pearson) and the binned residual histogram (bar chart); "QQ plot" —
qq_data scatter/line with a 45-degree reference; "Observed vs Predicted" —
decile calibration chart with TWO series (observed vs predicted frequency per
band) plus the table in an expander; "Model summary" — statsmodels summary
text in an expander. No storage changes; the page reads the fitted model from
`st.session_state["freq_model"]` (+ meta in `"freq_model_meta"`), so a fit
must happen in the SAME browser session — sidebar navigation, never reload.

BA scenarios (the user is an actuary learning GLMs, one screen past the
payoff — the model is fitted, now the question is whether to believe it):

- As an actuary, my #1 check is CALIBRATION BY DECILE: sort policies by what
  the model predicts, band them, and compare observed vs predicted frequency
  in every band. If the two series sit close together in every band — low-risk
  deciles near ~0.05, high-risk deciles well above 0.1 — the model rates risk
  correctly across the whole portfolio, not just on average. The bands must be
  ordered and labeled readably, and the predicted series must rise
  monotonically across bands (it is what defines the bands); the observed
  series should broadly rise with it. That chart, two series per band, is the
  screen's centerpiece.
- As an actuary, CI whiskers tell me which relativities I can PRICE ON:
  BonusMalus with a hair-thin interval is bankable; a sparse Region level with
  a whisker spanning 0.7–1.4 is noise. The chart must show exp-scale
  relativities (not link-scale coefs) with a reference line at 1.0 so I can
  see at a glance which whiskers cross "no effect". Top ~20 terms by |coef|
  keeps it readable — 40 treatment-coded levels would be soup.
- As a learner, the residual histogram and QQ plot teach me the
  Poisson-on-counts REALITY: with ~95% zero-claim policies, deviance residuals
  come out lumpy/multi-modal (one clump per count value) and the QQ plot bends
  away from the 45-degree line in the tails. The page must show this honestly
  — educational framing ("this is expected for count data") is welcome, a
  cosmetically smoothed lie is not. Switching the radio to Pearson shows me
  the other classical flavor.
- As an actuary, the metrics row (AIC, BIC, Deviance, Parameters) restates the
  fit-screen numbers so I can compare without flipping back — and the full
  statsmodels summary is there in an expander when I want the whole ugly
  truth.
- As a user who wandered to Diagnostics before fitting (or in a fresh tab), I
  get pointed to the RIGHT screen: "Fit a model first — go to Frequency
  Model." — not the dataset guard, not a traceback, and no half-rendered
  charts. Even with no dataset loaded at all, fitting is the actual next step,
  so the same message applies.
- As a user, everything renders FAST: every chart and table is aggregated
  (40 histogram bins, 100 QQ points, 10 calibration bands, ~20 chart terms) —
  the browser never receives 678k rows, and the page appears in seconds after
  the (already-paid) fit.

Test Agent notes from the BA interview: the UI exists, so per CLAUDE.md the
cases run via **Playwright (Python sync API)** against the running Streamlit
app; numeric truths (residual counts, quantile monotonicity, exposure and
calibration reconciliation, timing) are asserted at the **engine level** in
Python, where they are deterministic. Assumptions and mechanics, carrying
forward ALL accumulated lessons from `data-import.md` through
`frequency-model.md` Results:

- App started headless on port 8598 before the run:
  `uv run streamlit run app.py --server.port 8598 --server.headless true`
  from the repo root, real `data/raw/freMTPL2freq.parquet` present.
- **Session state is per browser tab; `page.goto` reloads DROP it** (proven
  live repeatedly). The fitted model lives ONLY in session state (no storage
  changes this slice) — so the fit and the Diagnostics visit MUST happen in
  ONE tab via **sidebar links** (assumed label `Diagnostics`, URL slug
  `/Diagnostics` from `pages/05_Diagnostics.py` — record actuals). Only the
  guard TC uses a direct `goto` in a **fresh context**.
- **The long fit timeout applies again:** reaching Diagnostics requires
  fitting first — all `expect(...)` waits on the post-fit success message use
  the proven **120,000 ms timeout** (last run: 11.5–23.6 s engine-side;
  record the observed wall time). Dataset load allows ~15 s as before.
- **Expect-before-count (the newest lesson, from frequency-model Results):**
  Streamlit renders progressively — after any action (sidebar click, radio
  change), LATER sections must be awaited with `expect(...).to_be_visible()`
  BEFORE issuing non-waiting `.count()` assertions. Concretely: after
  navigating to Diagnostics, first `expect` the LAST section header ("Model
  summary") with a generous timeout (~60,000 ms — the page computes residuals
  /QQ/calibration on 678k rows on first render), THEN count charts/metrics.
- Chart containers: Altair charts render as
  `[data-testid="stVegaLiteChart"]` (possibly `stArrowVegaLiteChart` on this
  Streamlit version — check the live DOM once, record the actual testid, and
  use it consistently). Chart CONTENT is canvas/SVG internals — assert
  container counts only; the numbers behind every chart are proven
  engine-side (TC4), same split as the canvas dataframes in every previous
  slice.
- Section headers are real text — match loosely on distinctive fragments:
  `Coefficients` (full header "Coefficients with confidence intervals"),
  `Residuals`, `QQ`, `Observed vs Predicted`, `Model summary`. Record actual
  header wording. Note `Residuals` may substring-match inside other text —
  prefer `get_by_role("heading", ...)` or `.first` and record.
- Radio (`stRadio`) for the residual kind: Streamlit radios are plain
  label-clickable (NOT BaseWeb select brittleness), but per the precedent of
  every previous slice, UI TCs stay **defaults-only + button clicks**; the
  kind switch is manual/deferred (TC5). Deviance is the default — proven
  engine-side (default arg), not via the widget.
- Expanders (`stExpander` testid or the "Coefficient table" / summary label
  text): assert presence loosely; do NOT require them open. Opening is a
  click if needed, but content-level asserts stay engine-side.
- Metrics row: **≥ 4** `[data-testid="stMetric"]` (AIC, BIC, Deviance,
  Parameters — labels loose-matched, record actuals). AIC shown should
  loosely match the known real-fit value (fragment `286,` with thousands
  separator — record; drift after upstream spec changes is possible, so a
  different plausible value is a finding, not a FAIL, as long as it matches
  the fit screen's).
- Known real-fit engine truths to reconcile against (from frequency-model
  Results): AIC **286,703**, exp(Intercept) **0.0191**, BonusMalus coef
  **+0.0224** (p << 0.001), portfolio observed frequency **0.1007**
  claims/policy-year, total exposure **~358,499** policy-years (pre-cap; TC4
  asserts against `df[spec.offset].sum()` so a capped total also passes —
  record the actual).
- Engine TC economics: fit ONCE, reuse the model for all four diagnostics
  functions; the < 10 s combined performance budget EXCLUDES the fit itself.
- Order matters WITHIN the UI run: TC1 fresh context; TC2 → TC3 strictly in
  sequence in ONE tab (TC2 ends ON Diagnostics with the model fitted; TC3
  asserts that page). TC4 is a separate Python script (fresh `load_dataset`
  frame — UI mutations cannot leak in). Scripts/temp files go in the session
  scratchpad, not the repo. Never delete `data/workbench.db` (TC2's fit will
  add a genuine history row — that is by design, not cleanup-worthy).

## TC1 — Guard chain: straight to Diagnostics with no dataset and no model

1. Open a **new browser context** (fresh Streamlit session — the one place a
   direct goto is correct), `page.goto("http://localhost:8598/Diagnostics")`
   (adjust the URL slug to the actual page name if needed — record it), wait
   for render.
2. Expected:
   - An info box visible with the MODEL-guard pointer — distinctive fragments
     `Fit a model first` and `Frequency Model` (spec'd wording: "Fit a model
     first — go to Frequency Model."). This is deliberately DIFFERENT from
     the dataset guard ("Load a dataset first — go to Data Import.") — assert
     `Load a dataset first` is NOT the message shown (record if both appear).
   - NO diagnostics content: no `stMetric`, no chart containers
     (`stVegaLiteChart`/actual testid), no `Residuals` / `QQ` /
     `Observed vs Predicted` / `Model summary` headers, no radio, no
     expanders.
   - `Traceback` absent; no `[data-testid="stException"]`.
3. Guard chain, second link — dataset loaded but NOT fitted (same context):
   click the sidebar link `Data Import`, click `Load dataset`, wait (≤ ~15 s)
   for the success containing `Loaded` and `678`; then click the sidebar link
   `Diagnostics`. Expected: the SAME model guard ("Fit a model first…") —
   a dataset alone does not unlock the page; still no charts/metrics, no
   traceback. (This step doubles as the start of the TC2 pipeline — the
   dataset stays loaded in this tab.)

## TC2 — Setup pipeline: fit on Frequency Model, sidebar to Diagnostics

Continues in the SAME tab as TC1 step 3 (dataset already loaded).

1. Click the sidebar link `Frequency Model`; confirm the formula preview
   (`ClaimNb ~` fragment) renders.
2. Click the button `Fit model`; wait for the success message containing
   `AIC` — **`expect` timeout 120,000 ms** (record actual wall time; this
   also appends a genuine run-history row to `data/workbench.db` — expected,
   leave it).
3. Click the sidebar link `Diagnostics` — **sidebar link, NOT goto** (a goto
   would drop the fitted model from session state and re-show the guard).
4. Expected:
   - Guard GONE: `Fit a model first` NOT present.
   - The page begins rendering diagnostics content (first evidence: the
     metrics row or the `Coefficients` header appears — full section asserts
     are TC3's job).
   - No traceback / `stException` at any point during the transition.

## TC3 — Sections render: five headers, charts, metrics — aggregate-only and fast

Same tab, directly after TC2. **Expect-before-count discipline:** step 1 MUST
complete before any `.count()` in steps 2–4.

1. `expect(page.get_by_text("Model summary"))` (or role heading) to be
   visible with **timeout 60,000 ms** — the LAST section; its appearance
   means the whole page (residuals, QQ, calibration on 678k rows) finished
   computing. Record the observed render wall time from sidebar click to
   visibility (informational; the BA's "renders fast" expectation — minutes
   would be a finding even if the expect passes).
2. Section headers all visible (loose fragments, record actual wording):
   `Coefficients` (full: "Coefficients with confidence intervals"),
   `Residuals`, `QQ`, `Observed vs Predicted`, `Model summary`.
3. Counts (non-waiting, safe now):
   - Chart containers `[data-testid="stVegaLiteChart"]` (or the actual
     testid recorded from the live DOM) **≥ 2** — the spec has four charts
     (coefficient whiskers, residual histogram, QQ, calibration); assert the
     conservative ≥ 2, record the actual count.
   - `[data-testid="stMetric"]` **≥ 4** (AIC, BIC, Deviance, Parameters —
     record labels and the AIC value shown; it should match the fit screen's
     success message from TC2).
4. Supporting widgets present (loose):
   - A radio (`stRadio`) in/near the Residuals section (kind selector;
     defaults-only — do NOT change it here, that is TC5).
   - At least two expanders (`stExpander` or label text — coefficient table,
     observed-vs-predicted table, model summary; record which labels exist).
5. `Traceback` absent; `[data-testid="stException"]` count == 0.

## TC4 — Engine truths: residuals, histogram, QQ, calibration + the 10 s performance budget

Engine-level (deterministic, automated). Run via `uv run python <tempfile.py>`
(or `.venv\Scripts\python.exe` in the sandbox) from the repo root; script in
the session scratchpad, not the repo. Fit ONCE, reuse; the **< 10 s combined**
performance budget covers the four diagnostics calls only (fit excluded).

```python
import time

import numpy as np
import pandas as pd

from pricing_engine.data import load_dataset
from pricing_engine.diagnostics import (
    RESIDUAL_KINDS,
    observed_vs_predicted,
    qq_data,
    residual_histogram,
    residuals,
)
from pricing_engine.glm import build_formula, fit_frequency_glm

df, spec = load_dataset("fremtpl2_freq")
assert len(df) == 678_013, len(df)
model = fit_frequency_glm(
    df, build_formula(spec), family="poisson", offset_column=spec.offset
)
assert model.converged, "IRLS did not converge"

# --- performance: all four diagnostics computations, combined, < 10 s ------
t0 = time.perf_counter()
res_dev = residuals(model)                                   # default deviance
hist = residual_histogram(model, kind="deviance", bins=40)
qq = qq_data(model, kind="deviance", points=100)
ovp = observed_vs_predicted(df, spec, model, groups=10)
elapsed = time.perf_counter() - t0
assert elapsed < 10.0, f"diagnostics took {elapsed:.1f}s (budget 10s, fit excluded)"

# --- residuals: full-length series, kinds differ, unknown kind ValueError --
assert isinstance(res_dev, pd.Series) and len(res_dev) == 678_013, len(res_dev)
assert np.isfinite(res_dev).all(), "non-finite deviance residuals"
res_pea = residuals(model, kind="pearson")
assert len(res_pea) == 678_013
assert not np.allclose(res_dev, res_pea), "deviance == pearson (?)"
try:
    residuals(model, kind="bogus")
    raise SystemExit("FAIL: no ValueError for kind='bogus'")
except ValueError as e:
    msg = str(e)
    for valid in RESIDUAL_KINDS:                 # error must NAME valid kinds
        assert valid in msg, (valid, msg)

# --- residual_histogram: <= bins rows, counts conserve all 678k policies ---
assert set(hist.columns) >= {"residual", "count"}, hist.columns
assert len(hist) <= 40, len(hist)
assert int(hist["count"].sum()) == 678_013, hist["count"].sum()
assert (hist["count"] >= 0).all()
assert pd.api.types.is_float_dtype(hist["residual"]), hist["residual"].dtype
assert hist["residual"].is_monotonic_increasing, "bin midpoints not ordered"

# --- qq_data: exactly `points` rows, theoretical strictly increasing -------
assert set(qq.columns) >= {"theoretical", "sample"}, qq.columns
assert len(qq) == 100, len(qq)
assert (np.diff(qq["theoretical"]) > 0).all(), "theoretical not strictly increasing"
assert qq["sample"].is_monotonic_increasing, "sample quantiles not sorted"
assert np.isfinite(qq[["theoretical", "sample"]].to_numpy()).all()

# --- observed_vs_predicted: the calibration truths -------------------------
assert set(ovp.columns) >= {
    "group", "exposure", "observed_frequency", "predicted_frequency"
}, ovp.columns
assert len(ovp) <= 10, len(ovp)
assert ovp["group"].astype(str).str.len().gt(0).all(), "unreadable group labels"

# exposure reconciles with the frame's offset total (pre-cap ~358,499;
# assert against the actual df so a capped implementation also passes)
total_exposure = float(df[spec.offset].sum())
assert abs(ovp["exposure"].sum() / total_exposure - 1) < 0.01, (
    ovp["exposure"].sum(), total_exposure
)

# exposure-weighted predicted frequency reconciles with the portfolio
# observed frequency (~0.1007) — Poisson-with-intercept balance property
overall_observed = float(df[spec.target].sum()) / total_exposure
w_pred = float(
    (ovp["predicted_frequency"] * ovp["exposure"]).sum() / ovp["exposure"].sum()
)
assert abs(w_pred / overall_observed - 1) < 0.01, (w_pred, overall_observed)

# bands ordered: predicted monotone non-decreasing (defines the bands);
# observed broadly increasing — last band clearly above first (Spearman-lite)
pred = ovp["predicted_frequency"].to_numpy()
assert (np.diff(pred) >= -1e-12).all(), "predicted not monotone across bands"
obs = ovp["observed_frequency"].to_numpy()
assert obs[-1] > obs[0], (obs[0], obs[-1])
assert (ovp["observed_frequency"] >= 0).all() and (pred >= 0).all()

print(
    f"PASS diag={elapsed:.2f}s hist_rows={len(hist)} qq_rows={len(qq)} "
    f"bands={len(ovp)} exposure={ovp['exposure'].sum():,.0f} "
    f"overall_obs={overall_observed:.4f} w_pred={w_pred:.4f} "
    f"obs_first={obs[0]:.4f} obs_last={obs[-1]:.4f}"
)
```

Expected: prints `PASS` with the combined diagnostics time (< 10 s — record
it), 100 QQ rows, ≤ 40 histogram rows conserving 678,013 policies, ≤ 10
ordered bands whose exposure reconciles to `df[Exposure].sum()` within 1%,
exposure-weighted predicted frequency within 1% of the ~0.1007 observed, and
last-band observed frequency clearly above the first. Any assertion failure
or unexpected exception is a FAIL. Two pre-authorized adaptations (record
either): (a) if quantile banding with heavily tied predictions yields fewer
than 10 bands, that satisfies `<= groups` — record the actual count; (b) if
`observed_vs_predicted`'s signature orders arguments differently, adapt the
call — a signature-shape difference is a finding, not a FAIL.

## TC5 — Residual-kind radio (Pearson) — MANUAL / DEFERRED

Widget-state changes stay out of the automated UI run per the precedent of
every previous slice (defaults-only + button clicks). Specified for manual
execution:

1. With the model fitted and Diagnostics rendered (TC2/TC3 state), switch the
   Residuals radio from `Deviance` to `Pearson`. Expected: the histogram
   re-renders without a traceback (Pearson residuals on count data have a
   different, more skewed shape than deviance — a visibly different chart is
   the informal confirmation); the QQ plot follows the kind selection if the
   implementation ties them together (record whether it does).
2. Switch back to `Deviance`. Expected: the original shape returns; no
   exception either way.
3. Engine-side backstop (already automated): TC4 proves
   `residuals(model, kind="pearson")` works and differs from deviance — the
   radio is only wiring.
4. Record in Results whether executed manually or deferred.

## Execution notes

- Prerequisites: real `data/raw/freMTPL2freq.parquet` present; Playwright +
  Chromium installed (`uv run playwright install chromium`); statsmodels
  importable.
- Start the app once for the whole run:
  `uv run streamlit run app.py --server.port 8598 --server.headless true`
  (background; kill after). Give it a few seconds before the first goto.
- TC1 opens a **fresh context**; TC1 step 3 → TC2 → TC3 run strictly in
  order in **ONE tab** of that context, **sidebar links only** after the
  initial goto (the fitted model is session-state-only this slice — any
  reload/goto sends the page back to the guard, which is expected behavior,
  not a bug; do not "fix" a mid-run goto by refitting without recording it).
  TC4 is an independent Python script (order-free; fresh `load_dataset`
  frame). Scripts/temp files go in the session scratchpad, not the repo.
- Timeouts: ~15,000 ms post-`Load dataset`; **120,000 ms** for the
  post-`Fit model` success (the proven first-fit budget — exceeding it is a
  performance FAIL); **60,000 ms** for the first Diagnostics section await
  (TC3 step 1 — page-side diagnostics computation on 678k rows); defaults
  elsewhere. Record all observed wall times (fit, Diagnostics render, TC4
  combined diagnostics).
- **Expect-before-count** (frequency-model Results lesson, now standing
  policy): after every navigation or action, `expect(...)` the LAST
  late-rendered section before any non-waiting `.count()` assertion.
- Selector assumptions to verify once against the live DOM and record in
  Results: sidebar link label (`Diagnostics`) and URL slug (`/Diagnostics`);
  the chart-container testid (`stVegaLiteChart` vs `stArrowVegaLiteChart`);
  testids `stMetric`, `stRadio`, `stExpander`, `stException`; section header
  wording (asserted via loose fragments `Coefficients`, `Residuals`, `QQ`,
  `Observed vs Predicted`, `Model summary`).
- Key assumptions to confirm and record: (a) guard wording "Fit a model
  first — go to Frequency Model." shown BOTH with no dataset and with a
  dataset-but-no-model (TC1 steps 2 and 3); (b) deviance is the radio
  default (proven engine-side via the default arg, not the widget);
  (c) chart count on the page (expected 4; asserted ≥ 2); (d) the AIC metric
  matches the fit screen's success value (~286,703 on the default
  9-predictor spec); (e) `observed_vs_predicted` band count actually
  produced (≤ 10; ties may reduce it).
- Exact-text caveats: wording is implementation-chosen — match loosely on
  distinctive fragments, record actual wording, labels, values, and timings
  in Results. Wording drift is not a FAIL; a missing section/chart/guard, a
  traceback, a busted calibration reconciliation (TC4), or a blown time
  budget IS.

## Results

- 2026-07-25 — **executed TCs ALL PASSED** (Playwright 1.61 / Chromium
  headless, port 8598, real data; combined runner with the Prediction slice):
  - TC4 (engine) PASS — all four diagnostics on the fitted 678k-row model in
    **0.15 s** (budget 10 s): residuals length 678,013 both kinds +
    kind-ValueError; histogram ≤ 40 bins conserving all rows; qq_data exactly
    100 strictly-ordered points; calibration exposure within 1% of 358,499,
    **exposure-weighted predicted frequency 0.1007** (== observed), predicted
    monotone across bands, last-band observed > first-band observed.
  - TC1 guard PASS (both "no dataset" and implicit variants show "Fit a model
    first — go to Frequency Model.", never the dataset guard); TC2 setup PASS;
    TC3 sections PASS (all five headers, ≥2 charts, ≥4 metrics, radio +
    expanders, no exception; "Model summary" awaited before counts per the
    progressive-render rule).
- TC5 (Pearson radio switch) DEFERRED/manual per precedent; engine TC covers
  both kinds numerically.
