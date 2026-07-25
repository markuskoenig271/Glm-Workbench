# E2E — Stepwise variable selection (pricing_engine/glm.py + pages/04_Frequency_Model.py)

Change under test: the first V1.x enhancement — automated stepwise variable
selection. Engine, in `pricing_engine/glm.py`:
`stepwise_selection(df, spec, family="poisson", direction="backward"|"forward",
criterion="aic"|"bic", on_fit=None) -> (selected_predictors: tuple[str, ...],
step_log: DataFrame)`. Backward starts from all spec predictors and each round
tries dropping each remaining predictor, taking the drop that most improves
(lowers) the criterion, stopping when no drop improves. Forward starts from
intercept-only (`target ~ 1` — built internally; `build_formula` still raises
on an empty spec) and adds the best improving predictor per round. `step_log`
columns: `step` (int), `action` (str, e.g. "start" / "drop Noise" /
"add Group"), `n_predictors` (int), `value` (float, the criterion after the
action); the "start" row records the starting model's criterion. `on_fit` is
an optional callback called with a short message before every candidate fit
(feeds the UI progress display). ValueError for unknown direction or criterion,
messages naming the valid options. UI: a new "Variable selection" section on
the EXISTING `pages/04_Frequency_Model.py` (decided: NO new tab) — direction
radio (backward default), criterion radio (AIC default), a "Run selection"
button → `st.status` streaming the `on_fit` messages while running → result
stored in session → the selected predictors, the step-log table, and an
"Adopt selected predictors" button that writes the selection into the shared
spec (the Feature Engineering multiselect and the formula preview follow
automatically via session state). DECIDED: candidate fits are NOT recorded in
the SQLite run history — only normal "Fit model" runs are.

BA scenarios (the user is an actuary learning GLMs; V1 is complete — the full
9-predictor Poisson fit on 678,013 freMTPL2 policies takes ~12 s and lands at
AIC 286,703):

- As an actuary, backward selection automates EXACTLY what I just did by hand
  on the Frequency Model screen: drop a term in Feature Engineering, refit,
  watch the AIC, repeat. One click should run that loop for me — same data,
  same offset, same family — and end where my hand-tuning would have ended.
- As a learner, the STEP LOG is the teaching artifact, not the final model:
  I want to see WHICH term fell first (the least informative one), how much
  the AIC moved at each step, and where the algorithm stopped because no drop
  improved anything. A table of (step, action, n_predictors, criterion) tells
  that story; the selected set alone teaches me nothing.
- As an actuary on 678k rows, I know p-values are the WRONG tool here —
  at this scale nearly everything is "significant" (the docs/TODO note this
  explicitly). Selection must be by information criterion (AIC default, BIC
  for a stiffer penalty), and the screen offering AIC/BIC — not a p-value
  threshold — is itself the lesson.
- As a user, a backward pass over 9 predictors is ~45 fits at ~12 s each —
  5 to 10 minutes. The app must not sit silent that long: I need a live
  progress display streaming which candidate is being tried, so I know it is
  working through the rounds and not hung. And I decide when to start it —
  the button, not a page load, triggers the work.
- As an actuary, ADOPTING the selection must flow into the shared spec with
  no re-typing: after "Adopt selected predictors" the formula preview shrinks
  to the selected terms and the Feature Engineering multiselect shows exactly
  that set — I never re-select anything by hand. Then one normal "Fit model"
  click gives me the adopted model, recorded in history like any other run.
- As a user, my RUN HISTORY is my experiment record — it must NOT be flooded
  by the ~45 candidate fits. Only deliberate "Fit model" runs appear; a
  selection pass adds zero history rows.
- As an actuary, I also know a legitimate outcome on real data is "nothing to
  drop": freMTPL2's 9 predictors are all real signals (the noise dummies live
  in the backlogged synthetic dataset), so backward may keep everything — or
  drop only where predictors overlap (Area IS the density band of Density —
  the realistic drop candidate). Either outcome must render sensibly, not as
  an error.
- As a user who wanders to Frequency Model before loading data, the existing
  guard covers the new section too: no radios, no "Run selection" button, no
  half-rendered selection UI before a dataset exists.

Test Agent notes from the BA interview: the UI exists, so per CLAUDE.md the
cases run via **Playwright (Python sync API)** against the running Streamlit
app; numeric truths (subset property, BonusMalus survival, step-log
monotonicity, on_fit counts, ValueErrors, timing, run-history non-flooding)
are asserted at the **engine level** in Python. Assumptions and mechanics,
carrying forward the accumulated lessons from `data-import.md` →
`prediction.md` Results:

- **TIMING is the design constraint of this slice.** A full backward pass over
  9 predictors on 678k rows is ~45 fits × ~12 s ≈ **5–10 minutes** — NOT
  suitable for an automated UI E2E. Split accordingly: the engine TC (TC3)
  runs on the REAL data but with a REDUCED spec —
  `dataclasses.replace(spec, predictors=("BonusMalus", "DrivAge", "VehGas"))`
  — 3 predictors → backward is at most ~6–9 fits ≈ 1.5–2.5 min (per-fit is
  also faster than 12 s with fewer design columns). The full 9-predictor UI
  run is MANUAL (TC4) with the duration stated so the human knows what they
  signed up for.
- **Click-and-abandon weighed and REJECTED (the call):** an automated path
  that clicks `Run selection`, asserts the `st.status` container appears
  within a few seconds, then ends the test without waiting is DIRTY —
  Streamlit executes the script run server-side to completion; closing the
  Playwright context does not interrupt a blocking statsmodels IRLS loop, so
  the abandoned run leaves the shared app process grinding through ~45 fits
  for 5–10 min, skewing any later TC's timings (and the user's own session if
  the app is reused). The only incremental proof (status appears, wiring from
  button to engine) is minutes of dirty CPU for seconds of value; the wiring
  is instead proven engine-side (TC3: on_fit streams messages) plus manually
  (TC4: the status display visibly streams them). `Run selection` is
  therefore **NOT clicked in any automated TC**.
- No defaults-only automated way to BOUND the UI run exists either: shrinking
  the spec to 3 predictors first would require changing the Feature
  Engineering variables multiselect — BaseWeb multiselect mutation is the
  brittle interaction deferred in every previous slice. Confirms the
  manual split.
- **Session state is per browser tab; `page.goto` reloads DROP it** (proven
  repeatedly). TC2 runs in ONE tab navigating via the **sidebar links**
  (`Data Import`, `Frequency Model`; URL slug `/Frequency_Model`). Only the
  guard TC (TC1) uses a direct `goto` in a **fresh context**.
- **Defaults-only + button clicks**, as always: the direction/criterion
  radios are NOT changed in automation (backward + AIC are the defaults and
  the engine TC covers forward explicitly). Unlike BaseWeb selectboxes,
  `st.radio` options render as REAL text — assert the option labels as page
  text (fragments `Backward`/`Forward` or lowercase variants, `AIC`, `BIC`;
  record actual labels). Reading which radio input is `checked` via the DOM
  is permitted if it works — record, don't require. New testid this slice:
  `stRadio` (verify once against the live DOM; fallback
  `[role="radiogroup"]`). `st.status` likely renders as `stStatus`/an
  expander-like container — manual-TC territory, note the actual testid if
  observed.
- **Expect-before-count** (the standing progressive-render lesson): after
  navigation and after any click, await the late-rendered section header with
  `expect(...)` FIRST, then issue non-waiting `.count()` assertions.
- Pre-run absence asserts must be SCOPED: the Frequency Model page may
  already show a Run history `stDataFrame` pre-fit (SQLite persists by
  design), so do NOT assert a global zero `stDataFrame` count — assert the
  absence of the `Adopt selected predictors` button and of a selected-result
  text instead; record whether the section renders any placeholder.
- Engine TC assertions (the numeric truths, on the reduced 3-predictor spec):
  selected is a tuple and a subset of the 3; **BonusMalus survives** (it is
  the strongest real effect in freMTPL2 — coef +0.0224, p ≪ 0.001; dropping
  it must worsen AIC, so backward keeps it and forward adds it); the step_log
  has a "start" row (n_predictors 3 backward / 0 forward) and **monotonically
  non-increasing criterion values** across rows (every accepted step
  improves); n_predictors moves by exactly ±1 per action row and ends at
  `len(selected)`; `on_fit` was called ≥ 3 times per direction (round 1 alone
  tries 3 candidates) with non-empty string messages — record the actual
  count and whether the start fit itself triggers a message (either is
  acceptable); ValueError for `direction="both"` and `criterion="deviance"`
  naming the valid options, raised fast (no fitting); a refit of the selected
  spec reproduces the log's final criterion value (the log describes real
  models). **Run-history non-flooding, engine half:** the count of
  `data/workbench.db` rows is identical before and after the stepwise calls —
  `stepwise_selection` never writes storage (the UI half — candidate fits
  from the button also add zero rows — is TC4 manual). Runtime per direction
  recorded; hard bound 360 s each (generous over the expected 1.5–2.5 min;
  exceeding it is a performance FAIL).
- Greedy forward and backward may legitimately select DIFFERENT subsets in
  general; on this 3-predictor space they will almost surely agree — record
  both selections, disagreement alone is not a FAIL.
- A small-fixture engine check (synthetic frame with a known noise column
  being dropped) belongs to the unit suite (TDD, already mandated) and is not
  duplicated here — the E2E's job is the real-data reduced-spec run and its
  recorded runtime.
- Signature assumptions to verify and record: keyword names
  (`direction`, `criterion`, `on_fit`), step_log column names/dtypes exactly
  `step`/`action`/`n_predictors`/`value`, action wording fragments
  ("start", "drop X", "add X" — loose-match, record actuals). Adaptation
  allowed without failing: exact keyword/message wording. NOT adaptable: the
  subset property, BonusMalus survival, monotonicity, the zero-new-history-
  rows truth, and the ValueErrors.
- Known testids: `stMetric`, `stDataFrame`, `stSelectbox`, `stCode`,
  `stException`; buttons via `get_by_role("button", name=...)`, labels
  loose-matched (`Run selection`, `Adopt selected predictors`, `Fit model`,
  `Load dataset`).

## TC1 — Guard: no Variable selection section before a dataset is loaded

Lightweight — the section lives on the existing Frequency Model page behind
its existing dataset guard; this only confirms the new content is behind it
too.

1. Open a **new browser context** (fresh Streamlit session),
   `page.goto("http://localhost:8598/Frequency_Model")` (slug proven in the
   frequency-model slice), wait for render.
2. Expected:
   - The existing guard info box: fragments `Load a dataset first` and
     `Data Import`.
   - NO selection content: no `Variable selection` text, no `Run selection`
     button, no `Adopt selected predictors` button, no `stRadio` /
     `[role="radiogroup"]` elements.
   - No `Fit model` button either (pre-existing guard behavior, unchanged).
   - `Traceback` absent; no `[data-testid="stException"]`.

## TC2 — Setup: load dataset → section renders with radios and button; run NOT started

1. In the SAME context/tab, click the sidebar link `Data Import`; click
   `Load dataset`; wait (≤ ~15 s) for the success message containing `Loaded`
   and `678`.
2. Click the sidebar link `Frequency Model` — **sidebar link, NOT goto**.
3. **Await the `Variable selection` section header with `expect` FIRST**
   (progressive render), then count.
4. Expected:
   - Existing content intact: the formula preview (`stCode` real text)
     containing `ClaimNb ~`, `Area`, and `BonusMalus` (the full 9-predictor
     spec — nothing adopted yet); the `Fit model` button present.
   - A `Variable selection` section header visible (loose fragment
     `Variable selection` — record actual wording).
   - **≥ 2** radio groups in/near the section (direction + criterion —
     testid `stRadio`, fallback `[role="radiogroup"]`; record the actual
     testid and count). Radio option labels visible as real page text:
     fragments matching `ackward` (Backward) AND `orward` (Forward) AND
     `AIC` AND `BIC` — record actual labels. Defaults (backward, AIC) NOT
     asserted via widget interaction (defaults-only rule); if the checked
     radio inputs are readable in the DOM, record them informationally.
   - A `Run selection` button present (role button, name loose-matched).
   - NO pre-run output: no `Adopt selected predictors` button, no
     selected-predictors result text, no step-log table WITHIN the section
     (scoped — a pre-existing Run history `stDataFrame` elsewhere on the
     page is fine and expected; record what the section shows pre-run).
   - **`Run selection` is deliberately NOT clicked** (see the
     click-and-abandon call in the notes — the full run is TC4, manual; the
     engine truths are TC3).
   - No traceback / `stException`.

## TC3 — Engine truths: reduced-spec stepwise on real data — both directions, log discipline, on_fit, errors, no history writes

Engine-level (deterministic, automated). Run via `uv run python <tempfile.py>`
(or `.venv\Scripts\python.exe` in the sandbox) from the repo root; script in
the session scratchpad, not the repo. REDUCED 3-predictor spec keeps this at
~6–9 fits per direction ≈ 1.5–2.5 min each (this TC doubles as the
**performance TC** — hard bound **360 s per direction**, record actuals).

```python
import time
from dataclasses import replace

import numpy as np

from pricing_engine import storage
from pricing_engine.data import load_dataset
from pricing_engine.diagnostics import information_criteria
from pricing_engine.glm import build_formula, fit_frequency_glm, stepwise_selection

df, spec = load_dataset("fremtpl2_freq")
assert len(df) == 678_013, len(df)

# run-history count BEFORE (read-only; never delete data/workbench.db)
conn = storage.connect()
n_runs_before = len(storage.list_model_runs(conn))
conn.close()

small = replace(spec, predictors=("BonusMalus", "DrivAge", "VehGas"))
LOG_COLS = {"step", "action", "n_predictors", "value"}

# --- ValueError cases: raise fast, naming the valid options, no fitting ---
t0 = time.perf_counter()
try:
    stepwise_selection(df, small, family="poisson", direction="both")
    raise SystemExit("FAIL: no ValueError for direction='both'")
except ValueError as e:
    msg = str(e)
    assert "both" in msg and "backward" in msg and "forward" in msg, msg
try:
    stepwise_selection(df, small, family="poisson", criterion="deviance")
    raise SystemExit("FAIL: no ValueError for criterion='deviance'")
except ValueError as e:
    msg = str(e)
    assert "deviance" in msg and "aic" in msg.lower() and "bic" in msg.lower(), msg
err_elapsed = time.perf_counter() - t0
assert err_elapsed < 10.0, f"errors took {err_elapsed:.1f}s — fitted before validating?"

messages: list[str] = []

def on_fit(message: str) -> None:
    assert isinstance(message, str) and message.strip(), repr(message)
    messages.append(message)

def check_log(log, start_n, delta):
    assert LOG_COLS <= set(log.columns), log.columns
    first = log.iloc[0]
    assert "start" in str(first["action"]).lower(), first["action"]
    assert int(first["n_predictors"]) == start_n, first["n_predictors"]
    vals = log["value"].to_numpy(dtype=float)
    assert np.isfinite(vals).all(), vals
    assert (np.diff(vals) <= 1e-9).all(), f"criterion increased: {vals}"
    n_preds = log["n_predictors"].to_numpy(dtype=int)
    if len(log) > 1:
        assert (np.diff(n_preds) == delta).all(), n_preds
    return float(vals[-1]), int(n_preds[-1])

# --- backward on the reduced spec ---
t0 = time.perf_counter()
sel_b, log_b = stepwise_selection(
    df, small, family="poisson", direction="backward", criterion="aic",
    on_fit=on_fit,
)
t_back = time.perf_counter() - t0
assert t_back < 360.0, f"backward took {t_back:.0f}s (performance bound)"
assert isinstance(sel_b, tuple), type(sel_b)
assert set(sel_b) <= set(small.predictors), sel_b
assert "BonusMalus" in sel_b, "strongest real effect was dropped"
final_b, n_final_b = check_log(log_b, start_n=3, delta=-1)
assert n_final_b == len(sel_b), (n_final_b, sel_b)
n_msgs_back = len(messages)
assert n_msgs_back >= 3, n_msgs_back  # round 1 alone tries 3 drops

# the log's final value describes a REAL model: refit the selection
refit = fit_frequency_glm(
    df, build_formula(replace(small, predictors=sel_b)),
    family="poisson", offset_column=spec.offset,
)
aic_refit = float(information_criteria(refit)["aic"])
assert abs(aic_refit - final_b) < max(1e-6 * abs(aic_refit), 0.01), (
    aic_refit, final_b)

# --- forward on the reduced spec ---
messages.clear()
t0 = time.perf_counter()
sel_f, log_f = stepwise_selection(
    df, small, family="poisson", direction="forward", criterion="aic",
    on_fit=on_fit,
)
t_fwd = time.perf_counter() - t0
assert t_fwd < 360.0, f"forward took {t_fwd:.0f}s (performance bound)"
assert set(sel_f) <= set(small.predictors), sel_f
assert "BonusMalus" in sel_f, "forward never added the strongest effect"
final_f, n_final_f = check_log(log_f, start_n=0, delta=+1)
assert n_final_f == len(sel_f), (n_final_f, sel_f)
assert len(sel_f) >= 1  # intercept-only cannot beat adding BonusMalus
n_msgs_fwd = len(messages)
assert n_msgs_fwd >= 3, n_msgs_fwd  # round 1 tries all 3 additions

# --- run history untouched: stepwise never writes storage ---
conn = storage.connect()
n_runs_after = len(storage.list_model_runs(conn))
conn.close()
assert n_runs_after == n_runs_before, (
    f"stepwise wrote {n_runs_after - n_runs_before} run-history rows")

print(f"PASS backward={t_back:.0f}s sel_b={sel_b} final_aic={final_b:.0f} "
      f"msgs={n_msgs_back} | forward={t_fwd:.0f}s sel_f={sel_f} "
      f"final_aic={final_f:.0f} msgs={n_msgs_fwd} | "
      f"agree={set(sel_b) == set(sel_f)}")
```

Expected: prints `PASS` with both runtimes (< 360 s each — record actuals;
expected 1.5–2.5 min per direction), both selections (subsets of the 3, both
containing BonusMalus — a 3-predictor "keep everything" outcome is legitimate
if every drop worsens AIC; record it), monotone step logs, on_fit counts
(record; also record whether the start fit produced a message — either
behavior acceptable), the refit AIC matching the log's final value, and an
unchanged run-history count. Whether forward and backward agree is recorded,
not required (greedy paths may differ in general). Adaptation allowed without
failing: keyword names, action-string wording, log dtypes, the on_fit message
format. NOT adaptable: subset property, BonusMalus survival, monotonicity,
ValueErrors naming valid options, the unchanged history count, the 360 s
bounds.

## TC4 — Full 9-predictor UI selection run + adopt + refit — MANUAL / DEFERRED

The full backward pass over 9 predictors on 678k rows is ~45 fits × ~12 s ≈
**5–10 minutes** — specified for manual execution (know what you are signing
up for; the per-fit time shrinks as predictors drop, so later rounds speed
up). Precise steps:

1. With the app running, load the dataset on Data Import and go to Frequency
   Model. Record the run-history count first (DB helper below): `n0`.
2. In `Variable selection`, keep the defaults (Backward, AIC) and click
   `Run selection`. Expected: an `st.status` progress container appears
   within a few seconds and STREAMS the on_fit messages — you can watch it
   advance through candidates (e.g. "Trying without VehBrand…" — record the
   actual wording). Total wall time 5–10 min; record it.
3. On completion: the selected predictors are rendered, and the step-log
   table shows a "start" row with the full model's criterion (AIC ≈ 286,703)
   followed by any accepted drops with strictly improving AIC. **Record the
   teaching artifact: WHICH term fell first and by how much the AIC moved.**
   A legitimate real-data outcome is NO drops (all 9 freMTPL2 predictors are
   real signals — the noise dummies are backlogged with the synthetic
   dataset); the plausible drop is in the Area/Density overlap (Area is the
   density band). Either outcome must render sensibly — an empty-ish log
   with only the start row is a pass, not a failure.
4. Click `Adopt selected predictors`. Expected: the formula preview shrinks
   to exactly the selected terms (dropped terms gone) WITHOUT any refit.
   Sidebar to Feature Engineering: the variables multiselect now shows
   exactly the selected set — nothing re-selected by hand. Sidebar back to
   Frequency Model: the preview still shows the adopted formula (session
   state survives sidebar navigation).
5. Click `Fit model` (normal fit, ≤ 120 s). Expected: success with an AIC
   that matches the step log's final value (and is ≤ 286,703 if anything was
   dropped; equal if nothing was); the coefficient table contains only the
   selected terms.
6. **Non-flooding check (the DECIDED behavior, UI half):** the DB helper now
   returns exactly `n0 + 1` — one row for the deliberate Fit model click,
   ZERO rows from the ~45 candidate fits.
7. Optional (another 5–10 min each): repeat with direction Forward and/or
   criterion BIC (radio changes are fine manually); BIC's stiffer penalty
   may drop more — record the selections and step logs.
8. Record in Results whether executed manually or deferred.

DB helper (from the repo root):
`uv run python -c "from pricing_engine.storage import connect, list_model_runs; c = connect(); print(len(list_model_runs(c)))"`

## Execution notes

- Prerequisites: real `data/raw/freMTPL2freq.parquet` present; Playwright +
  Chromium installed; statsmodels importable.
- Start the app once for the whole run:
  `uv run streamlit run app.py --server.port 8598 --server.headless true`
  (background; kill after). Give it a few seconds before the first goto.
- TC1 in a **fresh context**; TC2 in ONE tab of that context, **sidebar
  links only** after the first load (`page.goto` drops session state —
  proven repeatedly). TC3 is an independent Python script (fresh
  `load_dataset` frame; scripts/temp files in the session scratchpad, not
  the repo; NEVER delete `data/workbench.db` — the history count is asserted
  relatively). TC4 manual.
- `playwright.sync_api` with auto-waiting `expect(...)`; timeouts: ~15,000 ms
  post-`Load dataset` (TC2), defaults elsewhere — no automated TC waits on a
  fit in this slice (the 120,000 ms fit budget applies only inside manual
  TC4). **After navigation/clicks, `expect` the late-rendered section BEFORE
  any non-waiting `.count()` call** — the standing progressive-render rule.
- **`Run selection` is NOT clicked in automation** — the click-and-abandon
  option was weighed and rejected (see notes: Streamlit finishes the script
  run server-side even after the context closes; a blocking IRLS loop is not
  interruptible, leaving 5–10 min of dirty CPU on the shared app process for
  no incremental proof). Engine wiring is TC3; the visible streaming +
  adopt + refit loop is TC4.
- Selector assumptions to verify once against the live DOM and record in
  Results: `stRadio` testid (fallback `[role="radiogroup"]`), radio option
  label wording, the `Variable selection` header wording, button labels
  (`Run selection`, `Adopt selected predictors` — loose-matched), the
  `st.status` container's testid (manual TC, informational), step-log action
  wording ("start" / "drop X" / "add X").
- Key assumptions to confirm and record: (a) the section is dataset-gated by
  the EXISTING guard (TC1); (b) `stepwise_selection` keyword names and
  step_log column names match the spec (adapt TC3 + record if different);
  (c) the start row's criterion for the full 9-predictor backward run equals
  the known full-model AIC ≈ 286,703 (TC4, manual); (d) candidate fits add
  zero SQLite rows — engine half TC3, UI half TC4; (e) reduced-spec runtimes
  (the 360 s bounds; record actuals as the calibration for future slices).
- Exact-text caveats: header/button/status/action wording is
  implementation-chosen — match loosely on distinctive fragments
  (`Variable selection`, `Run selection`, `Adopt`, `AIC`, `BIC`, `ackward`,
  `orward`, `start`, `drop`, `add`), record actual wording, labels, values,
  selections, and timings in Results. Wording drift is not a FAIL; a missing
  element/button, a radio group short of two, a criterion value that
  INCREASES across an accepted step, a dropped BonusMalus, a run-history row
  from a candidate fit, a runtime over the stated bounds, or a traceback /
  `stException` IS.

## Results

- 2026-07-25 — **executed TCs ALL PASSED** (real data; Playwright for UI TCs):
  - TC3 (engine, reduced 3-predictor spec) PASS, both directions:
    - **Backward**: all three predictors kept — no drop improves AIC (all are
      genuine effects), stops after round one: 4 fits, **9 s**. The
      "algorithm actually drops junk" behavior is pinned by the unit test
      where the synthetic Noise factor is eliminated.
    - **Forward** (12 s, 10 fits): adds in order of effect strength —
      `start -> add BonusMalus -> add DrivAge -> add VehGas` — the step log
      as teaching artifact, exactly as the BA scenario hoped. Monotone
      non-increasing criterion, ±1 n_predictors discipline, ≥3 non-empty
      on_fit messages per direction.
    - Refit with the selected predictors reproduces the log's final AIC
      (289,075, |diff| < 0.5). ValueErrors raise in < 1 s (validation before
      any fitting). `data/workbench.db` row count unchanged (6 → 6).
  - TC1 guard PASS (no "Variable selection" text before a dataset is loaded);
    TC2 section render PASS (radios, Run selection button visible; "Run
    history" awaited first per the expect-before-count rule; button NOT
    clicked, per the plan's explicit rejection of click-and-abandon).
- TC4 (full 9-predictor UI run -> step log -> Adopt -> refit) MANUAL/deferred
  as planned (~5-10 min by design). Prediction for the manual run: all 9
  predictors survive — freMTPL2's rating factors are all real effects, which
  is itself the educational point.
