# E2E — Prediction slice (pricing_engine/prediction.py + pages/06_Prediction.py)

Change under test: the workflow's seventh and last V1 screen. Engine:
`pricing_engine/prediction.py` (replacing the stub) with
`predict_frequency(model, policies, spec) -> DataFrame` — returns a **copy** of
`policies` with two added columns: `expected_frequency` (claims per policy-year
from the model's linear predictor WITHOUT exposure — what the policy would
generate per full year) and `expected_claims` (= `expected_frequency * exposure`
when `spec.offset` is set, else `== expected_frequency`). Must work for a 1-row
frame (single policy) and the full 678k portfolio. Raises ValueError naming the
column when a predictor required by the model is missing from `policies`
(unseen categorical LEVELS raise from patsy naturally — acceptable behavior,
not part of the contract). UI: `pages/06_Prediction.py` — guard ("Fit a model
first — go to Frequency Model."); a "Single policy" section with input widgets
generated from the spec predictors using the loaded portfolio (numeric →
`st.number_input` defaulting to the portfolio median; categorical →
`st.selectbox` of observed levels) plus an Exposure input (default 1.0,
min 0.01) when the spec has an offset, and a "Predict" button → `st.metric`
showing expected claim frequency (per policy-year) and expected claims for the
entered exposure; a "Batch prediction" section with a button "Predict for
loaded portfolio" → runs `predict_frequency` over the full loaded portfolio,
stores the result in session, shows summary metrics (mean expected frequency,
total expected claims vs total observed claims), a head-20 preview table, and
`st.download_button` "Download predictions CSV" for the full result. No
storage changes.

BA scenarios (the user is an actuary learning GLMs, closing the Chapter-27
frequency loop on the real freMTPL2 data — 678,013 policies, overall observed
frequency 0.1007, 36,102 observed claims):

- As an actuary, the single-policy what-if is how I build INTUITION: enter one
  policy, click Predict, get its expected claim frequency. Then change one
  thing — Region, BonusMalus, Area — and watch the frequency move by exactly
  the relativity the coefficient table promised. The model stops being a table
  of betas and becomes a rating engine I can poke.
- As an actuary, the DEFAULTS are the median policy: every numeric input
  pre-filled with the portfolio median, every categorical at an observed
  level, Exposure at 1.0 (a full policy-year). My very FIRST click — no typing
  at all — must give a sensible baseline: a frequency in the neighborhood of
  the portfolio's typical policy, some plausible 0.0x–0.1x per policy-year,
  not 3.0 and not 0.0001. That first sanity number is what tells me the whole
  pipeline (spec → fit → predict) is wired correctly.
- As an actuary, I know frequency and claim count are different things and the
  screen must keep them straight: expected FREQUENCY is per policy-year;
  expected CLAIMS is frequency × my entered exposure. At Exposure 1.0 they
  coincide; at 0.5 the claims halve while the frequency stays put. Two
  metrics, correctly labeled.
- As an actuary, BATCH prediction closes the loop: predict for the whole
  loaded portfolio and compare total expected claims with total observed
  claims (36,102). This is the wonderful teaching moment — a Poisson GLM with
  an intercept reproduces the in-sample total BY CONSTRUCTION (the intercept's
  score equation forces sum(mu) = sum(y)) — so the two totals must agree
  almost exactly, and the screen putting them side by side TEACHES me that.
  If they disagree materially, the offset handling is broken.
- As an actuary, the CSV download is my HAND-OFF to pricing colleagues: the
  full portfolio with `expected_frequency` and `expected_claims` appended, one
  button, standard CSV they can open in Excel. Predictions that live only
  inside the app are useless to the pricing team.
- As a user, predicting over 678k rows must feel like a button-press, not a
  batch job — seconds, not minutes — and the preview (first 20 rows) shows me
  immediately what the output looks like without rendering 678k rows.
- As a user who wanders to Prediction before fitting anything (fresh tab), I
  get the friendly pointer to the RIGHT screen — "Fit a model first — go to
  Frequency Model." (not Data Import: the missing prerequisite here is the
  model) — an info box, not a traceback, and no half-rendered input widgets
  pretending a model exists.

Test Agent notes from the BA interview: the UI exists, so per CLAUDE.md the
cases run via **Playwright (Python sync API)** against the running Streamlit
app; numeric truths (in-sample balance, positivity, the copy contract, the
ValueError, timing) are asserted at the **engine level** in Python, where they
are deterministic. Assumptions and mechanics, carrying forward the accumulated
lessons from `data-import.md` → `frequency-model.md` Results:

- App started headless on port 8598 before the run:
  `uv run streamlit run app.py --server.port 8598 --server.headless true`
  from the repo root, real `data/raw/freMTPL2freq.parquet` present.
- **Session state is per browser tab; `page.goto` reloads DROP it** (proven
  live repeatedly). All post-setup TCs run in ONE tab and navigate via the
  **sidebar links** (assumed labels `Data Import`, `Frequency Model`,
  `Prediction`; URL slug `/Prediction` from `pages/06_Prediction.py` — record
  actuals). Only the guard TC uses a direct `goto` in a **fresh context**.
- Setup chain is the longest yet: load dataset (~15 s expect timeout) → fit
  (the proven **120,000 ms** post-`Fit model` timeout; observed 11.5–23.6 s
  last slice) → sidebar to Prediction. The fitted model lands in
  `st.session_state["freq_model"]` — the guard checks that key, not the
  portfolio.
- **Progressive-render lesson (tripped on it last run): after ANY button
  click, await the late-rendered section with `expect(...)` FIRST, and only
  then issue non-waiting `.count()` assertions.** Batch prediction over 678k
  rows takes real time — the summary-metrics `expect` uses a **60,000 ms**
  timeout (stated assumption; the engine budget is 30 s, so 60 s of UI slack
  covers serialization/rerun overhead; exceeding it is a FAIL, record actual).
- **Defaults-only + button clicks**, as in every slice: BaseWeb widgets
  (selectboxes, number inputs) are brittle to CHANGE via Playwright — the
  single-policy TC predicts with pure defaults (median policy, Exposure 1.0).
  Changing Region/BonusMalus for the what-if is manual/deferred (TC6), same
  precedent as always. Reading a number input's default VALUE via the DOM
  (`input` element `value` attribute) is permitted if it works — record, don't
  require.
- **Loose-match rule for the single-policy metric (stated):** metric values
  are implementation-formatted; do NOT assert an exact frequency. Assert the
  metric block exists (`[data-testid="stMetric"]`) and its value text contains
  the fragment `0.` (a sub-1.0 frequency — the median policy is nowhere near
  1 claim/year). The exact numeric truth is proven engine-side (TC5). A value
  NOT starting with a `0.`-something (e.g. `3.1`, `nan`, empty) is a FAIL.
- **Loose-match rule for the batch total (stated):** numbers render
  thousands-separated (proven: "678,013", "AIC 286,703"). Total expected
  claims ≈ 36,102 within 0.5% (engine-proven) ⇒ the UI text must contain a
  fragment matching `36,` short of asserting the exact rendering — i.e. the
  thousands group "36," followed by digits (regex `36,\d`). Also expect the
  observed total `36,102` somewhere in the summary (the "vs observed" metric).
  Record actual strings.
- **Do NOT click the actual download** in the automated run: `st.download_button`
  for the 678k-row CSV means Streamlit has already serialized ~tens of MB into
  the button payload; clicking it in headless Chromium triggers a real file
  download (needs download-event plumbing, large temp files, and adds nothing —
  the CSV CONTENT is the engine frame, proven in TC5). Assert the button is
  VISIBLE with its label; actually saving/opening the CSV is manual (TC6).
- Tables (`st.dataframe`) remain unassertable at cell level (glide-data-grid):
  assert the preview table's **container** (`[data-testid="stDataFrame"]`);
  the head-20 content is the same frame proven engine-side.
- Known testids: `stMetric`, `stDataFrame`, `stSelectbox`, `stNumberInput`
  (new this slice — verify once against the live DOM and record; fallback:
  `input[type="number"]`), `stDownloadButton` (new — fallback:
  `get_by_role("button", name=...)` with the download label), `stException`;
  buttons via `get_by_role("button", name=...)`, labels loose-matched.
- Engine TC (TC5) runs as a separate Python script on a fresh `load_dataset`
  frame — one fit (~12–24 s warm process), then all predict assertions against
  that single fitted model. UI mutations cannot leak into it. **Performance
  requirement: full-portfolio `predict_frequency` < 30 s** (record actual).
- The in-sample balance constant: `df["ClaimNb"].sum()` is asserted against
  the spec'd 36,102 first, then used as the reference — if the raw total
  differs (it should not), record it and compare relatively.
- Signature assumption to verify and record: `predict_frequency(model,
  policies, spec)` — the spec parameter is NEW versus the old stub's
  `(frequency_model, policies)`. Adapt the script to the actual signature
  (a naming difference is not a FAIL; record it).
- Order WITHIN the UI run: TC2 → TC3 → TC4 strictly in sequence in the one
  tab (TC3 predicts single-policy BEFORE TC4's batch run so the first-click
  baseline is observed on a clean screen; TC4's session-stored result must
  not exist yet during TC3 — record if the screen shows any stale batch
  section earlier).

## TC1 — Guard: straight to Prediction without a fitted model

1. Open a **new browser context** (fresh Streamlit session — the one place a
   direct goto is correct), `page.goto("http://localhost:8598/Prediction")`
   (adjust the URL slug to the actual page name if needed — record it), wait
   for render.
2. Expected:
   - An info box visible with the pointer text — distinctive fragments
     `Fit a model first` and `Frequency Model` (spec'd wording: "Fit a model
     first — go to Frequency Model." — note this guard points at Frequency
     Model, NOT Data Import; the missing prerequisite is the model).
   - NO prediction content: no `Predict` button, no `Predict for loaded
     portfolio` button, no `Download predictions CSV` button, no
     `stNumberInput` / `stSelectbox` input widgets, no `stMetric`, no
     `Single policy` / `Batch prediction` section headers.
   - `Traceback` absent; no `[data-testid="stException"]`.

## TC2 — Setup: load → fit → reach Prediction; input widgets from the spec

1. In the SAME context/tab, click the sidebar link `Data Import`; click
   `Load dataset`; wait (≤ ~15 s) for the success message containing `Loaded`
   and `678`.
2. Click the sidebar link `Frequency Model`; click `Fit model`; wait for the
   success message (fragment `AIC`) — **`expect` timeout 120,000 ms** (proven
   budget from the previous slice; record actual wall time).
3. Click the sidebar link `Prediction` — **sidebar link, NOT goto**.
4. Expected:
   - Guard info box GONE (`Fit a model first` not present).
   - A `Single policy` section header visible, with input widgets generated
     from the 9 spec predictors: **≥ 4** `stNumberInput` elements (numeric
     predictors VehPower, VehAge, DrivAge, BonusMalus, Density — plus the
     Exposure input, since the spec has an offset) and **≥ 4** `stSelectbox`
     elements (categorical predictors Area, VehBrand, VehGas, Region) — await
     the section with `expect` first, then count; record actual counts.
     Defaults NOT asserted via widget interaction (defaults-only rule); if
     the number-input `value` attributes are readable in the DOM, record the
     Exposure default (spec: 1.0) informationally.
   - A `Predict` button present (role button, name loose-matched).
   - A `Batch prediction` section header visible with the button
     `Predict for loaded portfolio` present.
   - NO prediction output yet: no result `stMetric` blocks, no
     `Download predictions CSV` button, no preview `stDataFrame` in the batch
     section (record if the implementation renders any pre-click placeholders;
     extra captions are fine).
   - No traceback / `stException`.

## TC3 — Single policy, pure defaults: first click gives the median-policy baseline

The BA's "first click, sensible baseline" scenario — all widgets untouched
(median policy, Exposure 1.0).

1. Same tab: click the button `Predict`.
2. **Await the result with `expect` FIRST** (single-row predict is fast;
   default timeout): a `[data-testid="stMetric"]` block whose label
   loose-matches `frequency` (fragment, case-insensitive).
3. Expected:
   - **≥ 2** `stMetric` blocks (expected claim frequency per policy-year AND
     expected claims for the entered exposure — labels loose-matched, record
     actuals).
   - **Loose-match rule (stated in the notes):** the frequency metric's value
     text contains the fragment `0.` — a plausible sub-1.0 frequency. Do NOT
     assert an exact value; the numeric truth is engine-side (TC5). A value
     not matching `0.`-something (e.g. `3.1`, `nan`, blank) is a FAIL. Record
     the value shown (BA plausibility note: the median policy should land
     somewhere in the broad neighborhood of the 0.1007 portfolio frequency —
     order of magnitude 0.0x–0.2x; record, judge, but only the `0.` fragment
     is the automated assert).
   - With Exposure at its default 1.0, expected claims should DISPLAY the
     same number as expected frequency (frequency × 1.0) — assert loosely
     that the claims metric also matches `0.` and record whether the two
     values agree as displayed.
   - No traceback / `stException`.

## TC4 — Batch prediction: totals reconcile, preview renders, download offered

The BA's teaching moment: in-sample Poisson with intercept reproduces the
observed total by construction.

1. Same tab: click the button `Predict for loaded portfolio`.
2. **Await the summary with `expect` FIRST — timeout 60,000 ms** (stated
   assumption: 678k-row predict + rerun overhead; the engine budget is 30 s;
   exceeding 60 s here is a FAIL, record actual wall time). Await a
   `stMetric` whose label loose-matches `expected` (fragment), THEN count.
3. Expected:
   - **≥ 3** `stMetric` blocks in the batch summary (mean expected frequency,
     total expected claims, total observed claims — labels loose-matched,
     record actuals).
   - **Loose-match rule (stated):** page text contains a fragment matching
     regex `36,\d` — the thousands-separated total expected claims near
     36,102 (engine-proven within 0.5%, i.e. 35,921–36,283, so the `36,`
     group is stable at this tolerance) — and the observed total `36,102`
     (the "vs observed" side). Record both rendered values; they should agree
     almost exactly (the BA's by-construction lesson).
   - The mean-expected-frequency metric value matches the `0.` fragment
     (portfolio mean ≈ 0.10x; record shown value).
   - A preview `stDataFrame` container present (head-20; cell content is
     canvas — the frame itself is proven engine-side in TC5).
   - The `Download predictions CSV` button **VISIBLE** (`stDownloadButton`
     testid or role+name fallback). **Do NOT click it** — a real 678k-row
     download in headless Chromium needs download-event plumbing and large
     temp files while proving nothing the engine TC doesn't already prove;
     actually saving/opening the CSV is manual (TC6).
   - No traceback / `stException`.

## TC5 — Engine truths: balance, positivity, single-row round-trip, copy, errors, performance

Engine-level (deterministic, automated). Run via `uv run python <tempfile.py>`
(or `.venv\Scripts\python.exe` in the sandbox) from the repo root; script in
the session scratchpad, not the repo. Fit ONCE, then all predict assertions
against that model. This TC doubles as the **performance TC**: full-portfolio
predict must complete in **under 30 s** (record the actual time).

```python
import time
from dataclasses import replace

import numpy as np

from pricing_engine.data import load_dataset
from pricing_engine.glm import build_formula, fit_frequency_glm
from pricing_engine.prediction import predict_frequency

df, spec = load_dataset("fremtpl2_freq")
assert len(df) == 678_013, len(df)
observed_total = float(df[spec.target].sum())
assert abs(observed_total - 36_102) < 1, observed_total  # the spec'd constant

model = fit_frequency_glm(df, build_formula(spec), family="poisson",
                          offset_column=spec.offset)
assert model.converged

# --- full-portfolio predict: shape, copy contract, performance ---
n_cols_before = df.shape[1]
t0 = time.perf_counter()
result = predict_frequency(model, df, spec)
elapsed = time.perf_counter() - t0
assert elapsed < 30.0, f"predict took {elapsed:.1f}s (performance requirement)"
assert result is not df, "must return a copy, not the input frame"
assert df.shape[1] == n_cols_before, "input frame was mutated"
assert "expected_frequency" not in df.columns, "input frame was mutated"
assert len(result) == 678_013
assert {"expected_frequency", "expected_claims"} <= set(result.columns)
# original columns preserved alongside the two new ones
assert set(df.columns) <= set(result.columns)

# --- positivity / finiteness (log link => mu > 0) ---
ef = result["expected_frequency"].to_numpy(dtype=float)
ec = result["expected_claims"].to_numpy(dtype=float)
assert np.isfinite(ef).all() and (ef > 0).all()
assert np.isfinite(ec).all() and (ec > 0).all()

# --- the relationship: claims = frequency * exposure (offset set) ---
assert np.allclose(ec, ef * df[spec.offset].to_numpy(dtype=float), rtol=1e-10)

# --- THE teaching moment: in-sample Poisson balance (intercept score eq.) ---
expected_total = float(ec.sum())
rel_err = abs(expected_total - observed_total) / observed_total
assert rel_err < 0.005, (
    f"total expected {expected_total:.1f} vs observed {observed_total:.0f} "
    f"({rel_err:.2%}) — in-sample balance broken"
)

# frequency is per policy-year: mean should sit near the portfolio's 0.1007
mean_freq = float(ef.mean())
assert 0.02 < mean_freq < 0.5, mean_freq  # sanity band, record actual

# --- 1-row frame (single policy) round-trips ---
one = df.head(1).copy()
r1 = predict_frequency(model, one, spec)
assert len(r1) == 1
assert {"expected_frequency", "expected_claims"} <= set(r1.columns)
f1 = float(r1["expected_frequency"].iloc[0])
c1 = float(r1["expected_claims"].iloc[0])
x1 = float(one[spec.offset].iloc[0])
assert np.isfinite(f1) and f1 > 0
assert abs(c1 - f1 * x1) < 1e-12 * max(1.0, abs(c1)), (c1, f1, x1)
# consistency: the same row inside the full-portfolio result agrees
assert np.isclose(f1, float(result["expected_frequency"].iloc[0]), rtol=1e-10)

# --- no offset in the spec -> expected_claims == expected_frequency ---
spec_no_offset = replace(spec, offset=None)
r5 = predict_frequency(model, df.head(5).copy(), spec_no_offset)
assert np.allclose(r5["expected_claims"], r5["expected_frequency"], rtol=1e-12)

# --- missing predictor column -> ValueError naming it ---
dropped = df.drop(columns=["BonusMalus"]).head(100)
try:
    predict_frequency(model, dropped, spec)
    raise SystemExit("FAIL: no ValueError for missing 'BonusMalus'")
except ValueError as e:
    assert "BonusMalus" in str(e), str(e)

print(f"PASS predict={elapsed:.1f}s total_expected={expected_total:.1f} "
      f"observed={observed_total:.0f} rel_err={rel_err:.4%} "
      f"mean_freq={mean_freq:.4f} single={f1:.4f}")
```

Expected: prints `PASS` with the predict time (< 30 s — record it), a total
expected claims within 0.5% of 36,102 (record the relative error — it should
be near machine precision, the by-construction balance), a mean frequency
near 0.10, and a finite positive single-policy frequency (record all). Any
assertion failure or unexpected exception is a FAIL. Adaptation allowed
without failing: the exact `predict_frequency` parameter names (adapt +
record); the no-offset branch if `replace(spec, offset=None)` is rejected by
validation elsewhere (record how the else-branch was proven instead). NOT
adaptable: the balance tolerance, positivity, the copy contract, and the
ValueError naming the column.

## TC6 — What-if input changes + actual CSV save — MANUAL / DEFERRED

BaseWeb widget changes and real file downloads are brittle in Playwright
(deferred in every previous slice); these are **specified for manual
execution**:

1. With a fitted model, on Prediction change one categorical (e.g. Region)
   in the Single policy section and click `Predict`. Expected: the frequency
   metric CHANGES versus the default-policy baseline, in the direction the
   coefficient table's relativity for that level implies — the BA's
   intuition-building what-if.
2. Change BonusMalus upward (e.g. median → 100). Expected: frequency
   increases (the domain truth: positive BonusMalus coefficient).
3. Set Exposure to 0.5. Expected: expected claims halves while expected
   frequency is unchanged — the per-policy-year semantics made visible.
4. Click `Download predictions CSV` after a batch run; open the file.
   Expected: 678,013 data rows; original columns plus `expected_frequency`
   and `expected_claims`; spot-check one row's values against the on-screen
   preview. (Content is engine-proven; this checks the download plumbing.)
5. Record in Results whether executed manually or deferred.

## Execution notes

- Prerequisites: real `data/raw/freMTPL2freq.parquet` present; Playwright +
  Chromium installed (`uv run playwright install chromium`); statsmodels
  importable.
- Start the app once for the whole run:
  `uv run streamlit run app.py --server.port 8598 --server.headless true`
  (background; kill after). Give it a few seconds before the first goto.
- TC1 in a **fresh context**; then TC2 → TC3 → TC4 strictly in order in
  **ONE tab** of that context, **sidebar links only** after the first load
  (`page.goto` drops session state — proven repeatedly). TC5 is an
  independent Python script (fresh `load_dataset` frame; one fit; scripts /
  temp files in the session scratchpad, not the repo). TC6 manual.
- `playwright.sync_api` with auto-waiting `expect(...)`; timeouts: ~15,000 ms
  post-`Load dataset` (TC2), **120,000 ms** post-`Fit model` (TC2 — proven
  budget), **60,000 ms** post-`Predict for loaded portfolio` (TC4 — stated
  assumption over the 30 s engine budget), defaults elsewhere. **After every
  click, `expect` the late-rendered section BEFORE any non-waiting `.count()`
  call** — the standing progressive-render lesson from the last slice.
- Selector assumptions to verify once against the live DOM and record in
  Results: sidebar link label (`Prediction`) and URL slug (`/Prediction`);
  buttons by role+name (`Predict`, `Predict for loaded portfolio`,
  `Download predictions CSV`, plus `Load dataset` / `Fit model` from earlier
  slices — labels may drift, match loosely); testids `stMetric`,
  `stDataFrame`, `stSelectbox`, `stException`, and NEW this slice
  `stNumberInput` (fallback `input[type="number"]`) and `stDownloadButton`
  (fallback role+name).
- Key assumptions to confirm and record: (a) the guard checks
  `st.session_state["freq_model"]` (model-gated, not portfolio-gated — a tab
  with a loaded dataset but no fit must still show the guard; spot-check
  informally if convenient); (b) `predict_frequency(model, policies, spec)`
  signature (adapt TC5 + record if different); (c) widget counts per the
  9-predictor spec (5 numeric + Exposure, 4 categorical); (d) the download
  button is NOT clicked in automation (reason stated in the notes: 678k-row
  payload, download-event plumbing, no incremental proof); (e) batch predict
  wall time (60 s UI budget / 30 s engine budget).
- Exact-text caveats: guard wording "Fit a model first — go to Frequency
  Model."; metric labels and summary wording implementation-chosen — match
  loosely on distinctive fragments (`frequency`, `expected`, `0.`, regex
  `36,\d`, `36,102`, `Download`), record actual wording, labels, values, and
  timings in Results. Wording drift is not a FAIL; a missing element/button,
  a frequency value not matching the `0.` rule, a balance total outside
  0.5%, a traceback / `stException`, or a mutated input frame IS.

## Results

- 2026-07-25 — **executed TCs ALL PASSED** (Playwright 1.61 / Chromium
  headless, port 8598, real data; combined runner with the Diagnostics slice):
  - TC5 (engine) PASS — full-portfolio predict in **2.0 s** (budget 30 s);
    **total expected claims 36,102 vs observed 36,102** — the in-sample
    Poisson balance holds to the claim (well inside the 0.5% bound);
    positivity/finiteness; copy-not-mutation; 1-row round-trip with
    expected_claims == expected_frequency × Exposure; ValueError names the
    dropped BonusMalus.
  - TC1 guard PASS ("Fit a model first", not the dataset guard); TC2 setup
    PASS (≥4 stNumberInput + ≥4 stSelectbox after awaiting the
    "Batch prediction" header — the input widgets render progressively, one
    more instance of the expect-before-count rule); TC3 single-policy
    defaults-only PASS ("Expected claim frequency" metric renders); TC4 batch
    PASS (summary metrics incl. "36,102", download button visible and per
    plan NOT clicked — 678k payload).
- TC6 (input what-ifs, actual CSV save) DEFERRED/manual per plan.
