# E2E — Frequency Model slice (pricing_engine/glm.py + diagnostics.py + storage.py + pages/04_Frequency_Model.py)

Change under test: the workflow's fifth screen — the first one that actually fits
a GLM. Engine, three modules: `pricing_engine/glm.py` (replacing stubs) with
`build_formula(spec) -> str` ("ClaimNb ~ Area + VehPower + ..." from the spec
predictors; statsmodels/patsy auto-encodes string/categorical columns with
treatment coding) and `fit_frequency_glm(df, formula, family="poisson",
offset_column="Exposure"|None) -> fitted statsmodels GLMResults` (Poisson
default or negative_binomial, log link, log-exposure offset when
`offset_column` is given; ValueError for an unknown family).
`pricing_engine/diagnostics.py` (replacing two stubs):
`coefficient_table(model) -> DataFrame` with columns term, coef, std_err,
p_value, ci_low, ci_high, exp_coef (the risk relativity), significant (bool,
p < 0.05); `information_criteria(model) -> dict` with aic, bic, deviance,
log_likelihood, n_params, n_obs. NEW module `pricing_engine/storage.py`
(decision 7 — SQLite, first consumer is this slice): `connect(path=...)`
defaulting to `data/workbench.db` with a `GLM_DB_PATH` env override, creating
the `model_runs` table (id, created_at, dataset, target, offset, formula,
family, n_obs, aic, bic, deviance, log_likelihood, coefficients_json);
`record_model_run(conn, ...) -> run id`; `list_model_runs(conn) -> DataFrame`
(newest first). UI: `pages/04_Frequency_Model.py` — guard like the previous
screens ("Load a dataset first — go to Data Import."); Model setup with a
family selectbox (Poisson default, Negative Binomial), a formula preview
(`st.code` showing `build_formula` of the LIVE spec) and an offset note; a
"Fit model" button → spinner while fitting (a few seconds on 678k rows) →
fitted model + metadata stored in session state, the run recorded to SQLite, a
success message with the AIC. After the fit: a metrics row (AIC, BIC,
deviance, parameters); a "Coefficients" section — the coefficient_table as a
dataframe plus educational aids (a caption explaining exp(beta) relativities,
plain-language explanation lines for the most influential significant terms,
and a call-out of insignificant terms); a "Run history" section listing
`list_model_runs` — SQLite-backed, so it persists across sessions unlike the
dataset itself.

BA scenarios (the user is an actuary learning GLMs, working through the
Chapter-27 frequency workflow on the real freMTPL2 data — this is the screen
where the workbench earns its name):

- As an actuary, this is the payoff moment: fit the Chapter-27-style Poisson
  GLM (log link, exposure offset) on 678k REAL policies with one click. No
  formula syntax, no statsmodels incantations — the button does it, and a
  success message tells me it worked and what the AIC is.
- As an actuary, the formula preview is my CONTRACT with the fit — exactly
  what the Feature Engineering screen's "Current model specification" promised
  is what goes into the model: `ClaimNb ~ Area + VehPower + ...` over the live
  spec's predictors. If I changed the predictors upstream (dropped a variable,
  added a band), the preview must change BEFORE I fit, and refitting must
  produce a different formula and a NEW history row — not overwrite the old
  one. That is how I compare experiments.
- As an actuary, I think in RELATIVITIES, not link-scale coefficients: the
  coefficient table must show exp(beta) next to each estimate, with a caption
  teaching me why (a relativity of 1.25 means +25% expected frequency). The
  plain-language lines (e.g. "BonusMalus: each additional point multiplies
  expected claim frequency by X (+Y%)") are exactly the educational feature
  the docs promise.
- As an actuary, I know the domain truth and the model must recover it:
  BonusMalus comes out strongly POSITIVE and significant (worse bonus-malus =
  more claims — the strongest signal in freMTPL2), and the Area density bands
  should trend. The intercept's exp(beta) is the base frequency for the
  reference profile — it must be a plausible claim frequency (the portfolio
  average is 0.1007/policy-year), not garbage like 3.0 or 0.0001.
- As a learner, the highlighting of INSIGNIFICANT variables (p >= 0.05) is the
  Chapter-27 lesson (the Dummy-variable demo is backlogged, but real data has
  insignificant levels too — some VehBrand/Region levels); the screen should
  call them out so I learn to distrust them.
- As a user, fitting 678k rows takes seconds — the app must not hang silently.
  I need a spinner while it works and a clear success (or error) when it's
  done. And it must actually finish in a coffee-sip, not a coffee-break.
- As a user, my RUN HISTORY must survive a browser refresh. I know (painfully,
  from the earlier screens) that a refresh drops the loaded dataset — Streamlit
  session behavior — but the run history is SQLite (decision 7): reopen the
  app tomorrow, the runs are still listed. Fitting twice gives two rows,
  newest first, each with its formula, family, and AIC.
- As a user who skipped Data Import (fresh tab straight to Frequency Model), I
  get the friendly pointer back to Data Import — an info box, not a traceback,
  and no half-rendered model setup pretending to work.

Test Agent notes from the BA interview: the UI exists, so per CLAUDE.md the
cases run via **Playwright (Python sync API)** against the running Streamlit
app; numeric truths (convergence, coefficient signs/significance, AIC/BIC,
storage round-trips, timing) are asserted at the **engine level** in Python,
where they are deterministic. Assumptions and mechanics, carrying forward the
accumulated lessons from `data-import.md`, `data-exploration.md`, and
`feature-engineering.md` Results:

- App started headless on port 8598 before the run:
  `uv run streamlit run app.py --server.port 8598 --server.headless true`
  from the repo root, real `data/raw/freMTPL2freq.parquet` present.
- **Session state is per browser tab; `page.goto` reloads DROP it** (proven
  live repeatedly). All post-load TCs run in ONE tab and navigate via the
  **sidebar links** (assumed label `Frequency Model`, URL slug
  `/Frequency_Model` from `pages/04_Frequency_Model.py` — record actuals).
  Only the guard TC uses a direct `goto` in a **fresh context**.
- Load the real dataset first via `Load dataset` on Data Import; allow ~15 s
  (`expect` timeout) for the 678k-row load.
- **LONG fit timeout — stated assumption:** fitting a 9-predictor Poisson GLM
  on 678,013 rows (with Region×22 and VehBrand×11 treatment-coded levels)
  takes "a few seconds" warm but the FIRST fit in a fresh process may be much
  slower (patsy design-matrix build + statsmodels IRLS on ~40 columns). All
  `expect(...)` assertions that wait on the post-fit success message use a
  **120,000 ms timeout**. If 120 s is exceeded, that is a FAIL of the
  performance requirement, not a flaky test. Record the observed wall time.
- Do NOT assert the spinner itself — `st.spinner` is transient and may
  disappear before Playwright polls; the success message (long timeout) is
  the completion signal. If the spinner happens to be visible, record it.
- Selectboxes are BaseWeb widgets — current value unreadable via text, and
  changing them is brittle: all UI TCs are **defaults-only + button clicks**.
  Family therefore stays at its default (**assumed Poisson** — proven
  engine-side and, loosely, via the run-history/DB rows recording
  `family = "poisson"`). Changing to Negative Binomial is manual/deferred
  (TC8), same precedent as every previous slice.
- The formula preview is `st.code` — REAL text (unlike canvas dataframes), so
  `get_by_text` fragments work: assert `ClaimNb ~` and `Area`. Note the
  offset (`Exposure`) is NOT part of the formula string — it enters the model
  separately as log(Exposure); the offset note near the preview should say
  so (loose fragments `Exposure` + `offset`; record actual wording).
- Tables (`st.dataframe`) remain unassertable at cell level (glide-data-grid):
  for both the coefficient table and the run-history table, assert the
  **container** (`[data-testid="stDataFrame"]`) plus the section header text;
  row CONTENT (BonusMalus row values, history row formula) is proven
  engine-side (TC6/TC7) — same split as every previous slice.
- Educational aids are plain markdown/caption text — assertable: match
  loosely on the fragment `relativit` (relativity/relativities) or `exp(`
  for the caption, and at least one plain-language line containing
  `multipl` or a `%`. WHICH terms get explanation lines depends on the fitted
  coefficients ("most influential significant") — do not hard-require
  `BonusMalus` in the UI text; record which terms appeared. With 678k rows
  most terms ARE significant, so the insignificant-terms call-out may
  legitimately name only a few factor levels — or say none — assert the
  call-out area loosely (fragment `insignificant` or `p ≥`/`p >=`), record
  actual content. Wording drift is not a FAIL; a MISSING element or a
  traceback IS.
- Numbers render **thousands-separated** ("678,013"); AIC is a large float —
  match loosely (fragment `AIC` plus a digit group), record the value shown.
- **SQLite run counts:** the UI writes to the default DB `data/workbench.db`
  (repo-root relative). History-row growth is proven with a tiny engine-side
  count helper run BEFORE TC4 and after each fit (counts are RELATIVE —
  n0, n0+1, n0+2 — because the DB persists across test runs by design; never
  delete the user's DB). The isolated storage round-trip (TC7) uses a temp
  file in the session scratchpad via explicit path and via `GLM_DB_PATH`.
- Signature assumptions to verify against the implementation and record:
  `record_model_run` takes keyword args matching the table columns
  (dataset, target, offset, formula, family, n_obs, aic, bic, deviance,
  log_likelihood, and a coefficients payload — dict or pre-dumped JSON);
  `connect()` with no argument resolves `GLM_DB_PATH` first, then
  `data/workbench.db`. Adapt the TC7 script to the actual signatures (a
  signature difference is not a FAIL; record it).
- Known testids: `stMetric`, `stDataFrame`, `stSelectbox`, `stException`,
  buttons via `get_by_role("button", name=...)`. New this slice: code block
  `[data-testid="stCode"]` (fallback: `page.locator("code")`), possibly
  `stSpinner` (transient — informational only). Verify once against the live
  DOM and record.
- Order matters WITHIN the UI run: TC2 → TC3 → TC4 → TC5 strictly in sequence
  in the one tab (TC3 is the first fit; TC4 counts on TC3's row existing;
  TC5 mutates the spec AFTER the fit TCs so their formula stays the default
  9-predictor one). Engine TCs (TC6, TC7) are separate Python scripts, on a
  fresh `load_dataset` frame / temp DBs — UI mutations cannot leak into them.

## TC1 — Guard: straight to Frequency Model without a dataset

1. Open a **new browser context** (fresh Streamlit session — the one place a
   direct goto is correct),
   `page.goto("http://localhost:8598/Frequency_Model")` (adjust the URL slug
   to the actual page name if needed — record it), wait for render.
2. Expected:
   - An info box visible with the pointer text — distinctive fragments
     `Load a dataset first` and `Data Import` (spec'd wording: "Load a
     dataset first — go to Data Import.", identical to the previous guards).
   - NO model setup content: no `Fit model` button, no formula preview code
     block containing `ClaimNb ~`, no `stSelectbox` for family, no
     `Coefficients` / `Run history` headers, no `stMetric`.
   - `Traceback` absent; no `[data-testid="stException"]`.

## TC2 — Setup: load the dataset, reach Frequency Model, formula preview is the contract

1. In the SAME context/tab, click the sidebar link `Data Import`.
2. Click the button `Load dataset`; wait (≤ ~15 s) for the success message
   containing `Loaded` and `678`.
3. Click the sidebar link `Frequency Model` — **sidebar link, NOT goto**.
4. Expected:
   - Guard info box GONE (`Load a dataset first` not present).
   - Model setup renders: a family selectbox (`stSelectbox` present; default
     Poisson — NOT asserted via the widget, defaults-only), the formula
     preview visible as real text containing the fragments `ClaimNb ~` and
     `Area` (and, spot-check, `BonusMalus`), and an offset note mentioning
     `Exposure` and `offset` (loose fragments; record actual wording).
   - The `Fit model` button is present (role button, name loose-matched).
   - NO post-fit content yet: no metrics row, no `Coefficients` section with
     a populated table, no success message (a pre-existing Run history
     section MAY already show rows from earlier sessions — SQLite persists
     by design; record whether it is shown pre-fit and with how many rows).
   - No traceback / `stException`.

## TC3 — Fit happy path: one click → success with AIC, metrics, coefficients, education, history

Before this TC, record the current run count `n0` with the DB count helper
(see Execution notes; if `data/workbench.db` does not exist yet, `n0 = 0`).

1. Same tab: click the button `Fit model`.
2. Wait for the success message — **`expect` timeout 120,000 ms** (stated
   assumption: first fit on 678k rows; record actual wall time from click to
   success).
3. Expected:
   - A success message containing the fragment `AIC` and a digit group
     (record the AIC shown; its exact value is proven engine-side in TC6).
   - A metrics row with **≥ 4** `[data-testid="stMetric"]` elements (AIC,
     BIC, deviance, parameters — labels loose-matched, record actuals).
   - A `Coefficients` section header visible and at least one
     `[data-testid="stDataFrame"]` under/near it (cell content is canvas —
     engine-level TC6 proves the numbers).
   - Educational aids visible as plain text: a caption matching the loose
     fragment `relativit` OR `exp(`; at least one plain-language explanation
     line (loose: `multipl` or `%` — record which terms were explained); an
     insignificant-terms call-out area (loose fragment `insignificant` or a
     p-threshold mention — may legitimately report none/few; record).
   - A `Run history` section header visible with a `stDataFrame` present
     (row content proven engine-side; the DB count helper after this TC must
     return `n0 + 1`).
   - No traceback / `stException`.

## TC4 — Second fit adds another history run (idempotence-ish)

1. Same tab: click the button `Fit model` again; wait for the success
   message (long timeout again — the warm second fit should be faster;
   record its wall time).
2. Expected:
   - Success message again (same loose `AIC` match); no traceback.
   - The Run history `stDataFrame` still present.
   - **Engine-side count check (authoritative):** the DB count helper now
     returns `n0 + 2` — clicking Fit twice produced two distinct history
     rows, not an overwrite. (Optionally also assert via the helper that the
     newest row's formula equals the default 9-predictor formula and its
     family is `poisson`; record.)

## TC5 — Changed spec upstream → changed formula preview (button-driven, no refit required)

The BA's "refit after changing predictors" scenario, automated as far as
buttons allow: Feature Engineering's `Create banded variable` is defaults-only
button-driven (proven last slice — creates `VehPower_band` and appends it to
the spec).

1. Same tab: click the sidebar link `Feature Engineering`; in the Binning
   section click `Create banded variable`; wait for the success message
   naming `VehPower_band`.
2. Click the sidebar link `Frequency Model`.
3. Expected:
   - The formula preview NOW contains the fragment `VehPower_band` — the
     live spec drives the preview; the contract updated before any fit.
   - The previous fit's results may or may not still be displayed (session
     state holds the old model) — record the behavior; either is acceptable
     as long as there is no traceback. Ideal: some hint that the displayed
     model predates the current spec, but that is not required by the spec.
4. Optional (time-budget permitting): click `Fit model` a third time (long
   timeout). Expected: success; DB count helper returns `n0 + 3`; the newest
   row's formula (engine-side helper) contains `VehPower_band` — a DIFFERENT
   formula produced a NEW history row. Record whether executed.

## TC6 — Engine truths: formula, fit on real data, coefficients, criteria, errors, performance

Engine-level (deterministic, automated). Run via `uv run python <tempfile.py>`
(or `.venv\Scripts\python.exe` in the sandbox) from the repo root; script in
the session scratchpad, not the repo. This TC doubles as the **performance
TC**: the full fit must complete in **under 120 s** (record the actual time).

```python
import time

import numpy as np

from pricing_engine.data import load_dataset
from pricing_engine.diagnostics import coefficient_table, information_criteria
from pricing_engine.glm import build_formula, fit_frequency_glm

df, spec = load_dataset("fremtpl2_freq")
assert len(df) == 678_013, len(df)

# --- build_formula: target ~ all spec predictors, in order ---
formula = build_formula(spec)
assert formula.startswith("ClaimNb ~"), formula
for predictor in spec.predictors:          # all 9, Area..Region
    assert predictor in formula, predictor
assert "Exposure" not in formula.split("~")[1], formula  # offset is NOT a term

# --- full Poisson fit on the real data, exposure offset: the payoff ---
t0 = time.perf_counter()
model = fit_frequency_glm(df, formula, family="poisson", offset_column="Exposure")
elapsed = time.perf_counter() - t0
assert elapsed < 120.0, f"fit took {elapsed:.1f}s (performance requirement)"
assert model.converged, "IRLS did not converge"
assert int(model.nobs) == 678_013, model.nobs

# --- coefficient_table: schema, relativities, significance consistency ---
ct = coefficient_table(model)
expected_cols = {"term", "coef", "std_err", "p_value", "ci_low", "ci_high",
                 "exp_coef", "significant"}
assert expected_cols <= set(ct.columns), ct.columns
assert np.allclose(ct["exp_coef"], np.exp(ct["coef"])), "exp_coef != exp(coef)"
assert (ct["significant"] == (ct["p_value"] < 0.05)).all(), "significant flag drift"
assert (ct["ci_low"] <= ct["coef"]).all() and (ct["coef"] <= ct["ci_high"]).all()

# Intercept: base frequency for the reference profile — plausible range
intercept = ct.loc[ct["term"] == "Intercept"].iloc[0]
base_freq = float(intercept["exp_coef"])
assert 0.01 < base_freq < 0.3, base_freq       # portfolio average is 0.1007

# BonusMalus: the domain truth — strongly positive, highly significant
bm = ct.loc[ct["term"].str.contains("BonusMalus")].iloc[0]
assert float(bm["coef"]) > 0, bm["coef"]
assert float(bm["p_value"]) < 1e-3, bm["p_value"]
assert bool(bm["significant"]) is True

# --- information_criteria: keys, finiteness, bookkeeping ---
ic = information_criteria(model)
for key in ("aic", "bic", "deviance", "log_likelihood", "n_params", "n_obs"):
    assert key in ic, key
    assert np.isfinite(ic[key]), (key, ic[key])
assert int(ic["n_obs"]) == 678_013, ic["n_obs"]
assert ic["deviance"] > 0 and ic["aic"] > 0 and ic["bic"] > ic["aic"] - 1e-9
assert int(ic["n_params"]) == len(ct), (ic["n_params"], len(ct))

# --- unknown family -> ValueError naming the family ---
try:
    fit_frequency_glm(df.head(100), formula, family="gaussian",
                      offset_column="Exposure")
    raise SystemExit("FAIL: no ValueError for family='gaussian'")
except ValueError as e:
    assert "gaussian" in str(e), str(e)

print(f"PASS fit={elapsed:.1f}s base_freq={base_freq:.4f} "
      f"bm_coef={float(bm['coef']):.4f} aic={ic['aic']:.0f} terms={len(ct)}")
```

Expected: prints `PASS` with the fit time (< 120 s — record it),
a base frequency in (0.01, 0.3), a positive BonusMalus coefficient, a finite
AIC, and the term count (record all). Any assertion failure, non-convergence,
or unexpected exception is a FAIL. If `n_params != len(ct)` fails only because
the implementation counts a dispersion parameter, relax that single assert and
record the deviation — it is bookkeeping, not correctness.

## TC7 — Engine truths: storage round-trip on a temp SQLite file + GLM_DB_PATH override

Engine-level, isolated from the real `data/workbench.db`. Temp files in the
session scratchpad. Adapt keyword names to the actual `record_model_run`
signature if they differ (record any difference).

```python
import json
import os
from pathlib import Path

import numpy as np

from pricing_engine import storage

SCRATCH = Path(os.environ.get("SCRATCH_DIR", "."))  # session scratchpad
db_path = SCRATCH / "tc7_workbench.db"
if db_path.exists():
    db_path.unlink()

# --- round-trip: record one run -> list returns exactly that row ---
conn = storage.connect(db_path)
run_id = storage.record_model_run(
    conn,
    dataset="fremtpl2_freq",
    target="ClaimNb",
    offset="Exposure",
    formula="ClaimNb ~ Area + VehPower",
    family="poisson",
    n_obs=678_013,
    aic=250_000.5,
    bic=250_400.5,
    deviance=200_123.4,
    log_likelihood=-124_000.2,
    coefficients_json=json.dumps({"Intercept": -2.3, "VehPower": 0.01}),
)
assert isinstance(run_id, int) and run_id >= 1, run_id
runs = storage.list_model_runs(conn)
assert len(runs) == 1, len(runs)
row = runs.iloc[0]
assert row["formula"] == "ClaimNb ~ Area + VehPower", row["formula"]
assert row["family"] == "poisson" and int(row["n_obs"]) == 678_013
assert np.isfinite(float(row["aic"])), row["aic"]
assert row["created_at"] is not None and str(row["created_at"]) != ""
coefs = json.loads(row["coefficients_json"])
assert coefs["Intercept"] == -2.3, coefs

# --- second run -> 2 rows, NEWEST FIRST ---
run_id_2 = storage.record_model_run(
    conn, dataset="fremtpl2_freq", target="ClaimNb", offset="Exposure",
    formula="ClaimNb ~ BonusMalus", family="poisson", n_obs=678_013,
    aic=251_000.0, bic=251_300.0, deviance=201_000.0,
    log_likelihood=-125_000.0, coefficients_json="{}",
)
runs = storage.list_model_runs(conn)
assert len(runs) == 2, len(runs)
assert int(runs.iloc[0]["id"]) == run_id_2, "not newest-first"

# --- persistence across connections (the 'survives a refresh' truth) ---
conn.close()
conn2 = storage.connect(db_path)
assert len(storage.list_model_runs(conn2)) == 2
conn2.close()

# --- GLM_DB_PATH env override respected by connect() with no path ---
override = SCRATCH / "tc7_override.db"
if override.exists():
    override.unlink()
os.environ["GLM_DB_PATH"] = str(override)
try:
    conn3 = storage.connect()
    storage.record_model_run(
        conn3, dataset="d", target="t", offset=None, formula="y ~ x",
        family="poisson", n_obs=10, aic=1.0, bic=2.0, deviance=3.0,
        log_likelihood=-4.0, coefficients_json="{}",
    )
    assert override.exists(), "GLM_DB_PATH not respected"
    assert len(storage.list_model_runs(conn3)) == 1
    conn3.close()
finally:
    del os.environ["GLM_DB_PATH"]

print("PASS storage round-trip, newest-first, persistence, env override")
```

Expected: prints `PASS`. Any assertion failure or exception is a FAIL (except
pure signature-shape differences — adapt and record). The `offset=None` run
also probes that a NULL offset is storable (CSV uploads may have no offset);
if the implementation requires a string, record it as a finding.

## TC8 — Family selectbox (Negative Binomial) + full changed-spec refit loop — MANUAL / DEFERRED

BaseWeb selectbox changes are brittle in Playwright (deferred in every
previous slice); these are **specified for manual execution**:

1. With the dataset loaded, on Frequency Model change the family selectbox to
   `Negative Binomial`, click `Fit model`. Expected: success; metrics and
   coefficients render; the new history row shows family
   `negative_binomial` (or the label — record); AIC differs from the Poisson
   run's.
2. On Feature Engineering, remove a predictor (e.g. `VehBrand`) via the
   Variables multiselect; back on Frequency Model the formula preview no
   longer contains `VehBrand`; fit; the new history row's formula reflects
   the removal — the BA's full experiment-comparison loop, end to end.
3. Refresh the browser tab (F5). Expected: the dataset is gone (guard shows —
   known Streamlit behavior), but after reloading the dataset via Data
   Import, the Run history on Frequency Model still lists ALL earlier runs —
   the SQLite persistence promise, seen from the UI. (The engine-side
   persistence proof is TC7's reconnect assert.)
4. Record in Results whether executed manually or deferred.

## Execution notes

- Prerequisites: real `data/raw/freMTPL2freq.parquet` present; Playwright +
  Chromium installed (`uv run playwright install chromium`); statsmodels
  importable (`uv run python -c "import statsmodels"`).
- Start the app once for the whole run:
  `uv run streamlit run app.py --server.port 8598 --server.headless true`
  (background; kill after). Give it a few seconds before the first goto.
- TC1 in a **fresh context**; then TC2 → TC3 → TC4 → TC5 strictly in order in
  **ONE tab** of that context (TC3/TC4 must fit the DEFAULT 9-predictor
  formula BEFORE TC5 mutates the spec), **sidebar links only** after the
  load. TC6 and TC7 are independent Python scripts (order-free; fresh
  `load_dataset` frame and scratchpad temp DBs — UI mutations cannot leak
  into them). Scripts/temp files go in the session scratchpad, not the repo.
- **DB count helper** (engine-side, run from the repo root so the default
  path resolves; used before TC3 and after TC3/TC4/TC5-optional):
  `uv run python -c "from pricing_engine.storage import connect, list_model_runs; c = connect(); print(len(list_model_runs(c)))"`
  — record `n0` first; assert relative growth only (the DB persists across
  test runs by design; NEVER delete `data/workbench.db`).
- `playwright.sync_api` with auto-waiting `expect(...)`; timeouts: ~15,000 ms
  post-`Load dataset` (TC2), **120,000 ms** for the post-`Fit model` success
  message (TC3, TC4, TC5-optional — the stated first-fit-on-678k-rows
  assumption; exceeding it is a performance FAIL, record actual times),
  defaults elsewhere.
- Selector assumptions to verify once against the live DOM and record in
  Results: sidebar link label (`Frequency Model`) and URL slug
  (`/Frequency_Model`); buttons by role+name (`Fit model`, `Load dataset`,
  `Create banded variable` — labels may drift, match loosely); testids
  `stMetric`, `stDataFrame`, `stSelectbox`, `stCode` (fallback
  `page.locator("code")` for the formula preview), `stException`; spinner
  presence is informational only (transient).
- Key assumptions to confirm and record: (a) family selectbox default is
  Poisson (proven via DB rows' `family` column, not the widget); (b) the
  formula preview omits the offset and the offset note explains Exposure
  enters as log-offset; (c) `record_model_run` keyword names / `connect`
  env-override resolution match TC7's script (adapt + record if not);
  (d) the run-history table is `st.dataframe` (canvas — container-level
  assert only); (e) first-fit wall time (the 120 s budget).
- Exact-text caveats: guard wording "Load a dataset first — go to Data
  Import."; success/caption/educational wording implementation-chosen — match
  loosely on distinctive fragments (`AIC`, `relativit` / `exp(`, `multipl`,
  `insignificant`, `VehPower_band`, digit groups with thousands separators),
  record actual wording, labels, values, and timings in Results. Wording
  drift is not a FAIL; a missing element/message, a non-converged fit, an
  implausible coefficient truth (TC6), a lost history row, or a traceback IS.

## Results

- 2026-07-25 — **executed TCs ALL PASSED** (Playwright 1.61 / Chromium
  headless, port 8598, real data):
  - TC6 (engine) PASS — full Poisson fit on 678,013 rows in **11.5–23.6 s**
    (well under the 120 s bound; varies with machine load). Converged;
    `exp(Intercept)` = **0.0191** (baseline-levels frequency, plausible);
    **BonusMalus coef +0.0224, p ≪ 0.001** → each point ≈ +2.3% expected
    frequency — the domain-truth check holds; AIC **286,703**; coefficient
    table internally consistent (exp_coef, significance flag, CI ordering);
    ValueError for family="gaussian".
  - TC7 (storage) PASS — record→list round-trip, newest-first, reconnect
    persistence, GLM_DB_PATH override; scratchpad temp DBs only, the user's
    `data/workbench.db` untouched except by genuine UI fits.
  - TC1–TC5 (UI) PASS — guard; formula preview ("ClaimNb ~ Area…",
    "log(Exposure)" note); fit happy path (success "Model fitted and
    recorded (AIC 286,703).", 4 metrics, coefficient table, "risk relativity"
    educational text, run history section); second fit appended a run
    (history count n0→n0+2, verified engine-side against the same SQLite
    file); Feature Engineering band creation flowed into the formula preview
    ("VehPower_band" appears after sidebar round-trip).
- TC8 (Negative Binomial selectbox, predictor-multiselect removal, F5
  history-persistence loop) DEFERRED/manual per plan.
- Executor notes: Streamlit renders progressively — after the fit success
  message, later sections must be awaited with `expect(...)` BEFORE issuing
  non-waiting `.count()` assertions (first run tripped on this); run-count
  checks poll the SQLite file directly, which works fine concurrently with
  the app's own connection.
