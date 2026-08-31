# E2E — Per-kind model slots (V3 slice 1: `model_frequency` / `model_severity`, mismatch guard retired)

Change under test: the single session model slot (`model` / `model_meta`) is
split into **two independent slots** — `model_frequency`/`model_frequency_meta`
written by `pages/04_Frequency_Model.py` and `model_severity`/
`model_severity_meta` written by `pages/07_Severity_Model.py` (per
`docs/architecture.md`, "V3 — Pure premium design", slice 1). Diagnostics
(`pages/05_Diagnostics.py`) and Prediction (`pages/06_Prediction.py`) select
the model by the **loaded dataset's kind** (`spec.kind`), so dataset and model
always match by construction and the V2 kind-mismatch guard is RETIRED — its
wording ("The active model is a … but the loaded dataset is a …") must appear
NOWHERE. New guard order on 05/06: (1) no dataset loaded → `Load a dataset
first — go to Data Import.` (2) matching slot empty → `Fit a frequency model
first — go to Frequency Model.` / `Fit a severity model first — go to Severity
Model.` The V2 fresh-session dual wording (`Fit a model first — go to
Frequency Model or Severity Model.`) is also retired. Headline behaviour:
after fitting BOTH kinds, switching datasets back and forth flips 05/06
between the two live models **without refitting** (V2 showed the mismatch
guard here). Engine rename: `diagnostics.observed_vs_predicted` columns
`observed_frequency`/`predicted_frequency` → **`observed_mean`/
`predicted_mean`** (values unchanged); the severity calibration table on 05
re-bases its rename to `observed_avg_claim_amount`/
`predicted_avg_claim_amount` from the new names. Refits of one kind never
evict the other slot; a failed Inverse Gaussian fit keeps the previous Gamma
AND leaves the frequency slot untouched; stepwise Adopt on 04 touches neither
slot (only `selection_result`). `predictions_kind` still hides a stale batch
of the other kind across dataset switches.

BA scenarios (numbered as in the BA report):

- S1 — Happy path: fit Poisson on the frequency data, run the batch on 06;
  load the severity dataset, fit Gamma; 05/06 show the severity views; switch
  back to the frequency dataset WITHOUT refitting → 05/06 render the
  still-alive Poisson views (V2 showed the mismatch guard here); arbitrary
  further switches, no exceptions.
- S2 — Fresh session: direct visit to 05/06 → dataset-first guard, no
  KeyError; frequency data loaded but nothing fitted → `Fit a frequency model
  first — go to Frequency Model.`; severity analog; the old dual wording is
  gone; the V2 mismatch text appears nowhere.
- S3 — Only one kind fitted, the other kind's dataset loaded → the kind
  guard, never the wrong model run against the wrong frame (the
  678,013-vs-26,444 length trap), no crash.
- S4 — Pages 04/07 keep their own results after the other kind is fitted
  (V2 hid them); 04's severity-dataset guard still stops before results.
- S5 — Refit of one kind never evicts the other; a failed Inverse Gaussian
  fit keeps the previous Gamma AND leaves the frequency slot untouched.
- S6 — Stepwise selection + Adopt on 04 touches neither slot (only
  `selection_result`; 05 metrics change only after an explicit Fit).
- S7 — Run history: every successful fit appends exactly one row to
  `model_runs`; schema unchanged; never delete `data/workbench.db`.
- S8 — Calibration: engine columns `observed_mean`/`predicted_mean`, values
  identical to V2 (frequency weighted mean ≈ 0.1007; severity weighted mean
  ≈ 2,230.9, observed band averages ≈ 1,586–5,453); the severity table rename
  is re-based (no KeyError); chart labels unchanged.
- S9 — `predictions_kind`: a stale batch of the other kind is hidden across
  dataset switches; no KeyError on missing columns; correct captions
  (`by construction` Poisson vs `does not reproduce` Gamma).

Test Agent notes from the BA interview: mechanics carry over the hard-won
lessons in `e2e/README.md`, `e2e/harness.py` and the three V2 runners:

- Engine truths FIRST (TC1–TC2) as deterministic Python from the repo root
  (inline at the top of the committed runner — slice-2/3 precedent). The
  Poisson fit takes ~12 s, the Gamma ~2 s; stepwise selection takes minutes
  and therefore stays out of the automated UI flow entirely (S6 is
  deferred/manual + the `e2e_stepwise.py` regression).
- App headless on port 8598 via `e2e/harness.py`:
  `uv run streamlit run app.py --server.port 8598 --server.headless true`;
  both Parquet files present in `data/raw/`. **Never delete or truncate
  `data/workbench.db`** — the UI fits (TC5 Poisson, TC7 Gamma, optional TC11
  Poisson refit) each APPEND one real run; that is S7's behaviour under test.
- Session state is per browser tab; `page.goto` after loading DROPS it. All
  post-load UI TCs run in ONE tab of one context, **sidebar links only**
  (`Data Import`, `Frequency Model`, `Severity Model`, `Diagnostics`,
  `Prediction`). Fresh-session guards (TC3) use separate contexts with a
  direct `goto` — the sanctioned exception because an empty session is the
  point.
- Combobox: the ONE sanctioned BaseWeb route — click the first
  `[data-testid="stSelectbox"]` on Data Import, type `severity` (later
  `frequency`), press Enter — proven in three slices; reuse verbatim, one
  retry max, remaining chained TCs flip to manual if it stops taking. This
  plan leans on it harder than any predecessor (three switches in TC6, TC9,
  TC10) because dataset switching IS the feature under test.
- `expect(...).to_be_visible()` before any `.count()`. Known-good selectors:
  `[data-testid="stMetric"]`, `[data-testid="stDataFrame"]`,
  `[data-testid="stVegaLiteChart"]`, `[data-testid="stNumberInput"]`,
  `[data-testid="stSelectbox"]`, `[data-testid="stException"]`,
  `get_by_role("button", name=..., exact=True)` (the `Predict` button name is
  a prefix of `Predict for loaded …` — always `exact=True`).
- Absence assertions use DISTINCTIVE full phrases. The retired-guard
  assertions are the heart of this plan: `The active model is a` and
  `but the loaded dataset is a` must count 0 on EVERY page state visited, and
  `or Severity Model` (the dual-wording tail) must count 0 on any guard.
  Other carried-over phrases: `claim frequency`, `claim amount`,
  `policy-year`, `Total expected claims`, `Total expected claim amount`,
  `Single policy`, `Single claim`, `by construction`, `does not reproduce`,
  `mostly zero claims`, `36,102` — never bare `frequency` (sidebar link
  "Frequency Model") or bare `Exposure`.
- Metric VALUES are not scraped; the only UI numeric assertions stay the
  frequency `36,102` and the load messages `678,013` / `26,444`. All other
  numerics are TC1/TC2 engine truths.
- Guard ORDER trap (INVERTED from V2): a fresh session must say `Load a
  dataset first`, never `Fit a … model first` (V2's model-first order is
  gone). A loaded-but-unfitted state must name the LOADED kind's screen only.
- Exact captions/guard wording are implementation-chosen: match loosely on
  the fragments named per TC and record actuals in Results — EXCEPT the three
  guard texts above, which are spec'd verbatim by this slice and asserted
  exactly. A mismatch-guard fragment anywhere, the dual wording, a guard
  where live views should render after a dataset switch, stale batch numbers
  from the other kind, old `observed_frequency`/`predicted_frequency` columns
  in the engine result, or any traceback/`stException` IS a FAIL.

## TC1 — Engine: `observed_vs_predicted` rename on the frequency model (S8)

Engine-level (deterministic, automated; the Poisson fit takes ~12 s):

```python
import numpy as np

from pricing_engine.data import load_dataset
from pricing_engine.diagnostics import observed_vs_predicted
from pricing_engine.glm import build_formula, fit_frequency_glm
from pricing_engine.prediction import predict_frequency

df, spec = load_dataset("fremtpl2_freq")
assert len(df) == 678_013 and spec.kind == "frequency"
model = fit_frequency_glm(df, build_formula(spec), offset_column=spec.offset)
assert model.converged

ovp = observed_vs_predicted(df, spec, model, groups=10)
# Rename contract: new names present, old names GONE
assert "observed_mean" in ovp.columns and "predicted_mean" in ovp.columns, ovp.columns
assert "observed_frequency" not in ovp.columns and "predicted_frequency" not in ovp.columns
assert len(ovp) <= 10

# Values identical to V2 (rename only): weighted mean ≈ 0.1007
total_exposure = df[spec.offset].sum()
assert abs(ovp["exposure"].sum() - total_exposure) / total_exposure < 0.01
weighted_pred = (ovp["predicted_mean"] * ovp["exposure"]).sum() / ovp["exposure"].sum()
assert abs(weighted_pred - 0.1007) / 0.1007 < 0.01, weighted_pred
assert (np.diff(ovp["predicted_mean"]) >= 0).all()
assert ovp["observed_mean"].iloc[-1] > ovp["observed_mean"].iloc[0]

# Batch anchor unchanged: total expected claims ≈ 36,102
batch = predict_frequency(model, df, spec)
total_expected = float(batch["expected_claims"].sum())
assert abs(total_expected - 36_102) / 36_102 < 0.01, total_expected
print("PASS", round(weighted_pred, 4), round(total_expected))
```

Expected: prints `PASS 0.1007 36102`-ish — record actuals in Results. An old
column name surviving, a KeyError on the new names, or a drifted anchor value
(the rename must be value-neutral) is a FAIL.

## TC2 — Engine: severity calibration values survive the rename (S8)

Engine-level. The Gamma fit takes ~2 s:

```python
import numpy as np

from pricing_engine.data import load_dataset
from pricing_engine.diagnostics import observed_vs_predicted
from pricing_engine.glm import build_formula, fit_severity_glm

df, spec = load_dataset("fremtpl2_sev")
assert len(df) == 26_444 and spec.kind == "severity" and spec.offset is None
model = fit_severity_glm(df, build_formula(spec))  # gamma default

ovp = observed_vs_predicted(df, spec, model, groups=10)
assert "observed_mean" in ovp.columns and "predicted_mean" in ovp.columns, ovp.columns
assert "observed_frequency" not in ovp.columns and "predicted_frequency" not in ovp.columns
assert len(ovp) <= 10
# offset None -> the "exposure" weights are CLAIM COUNTS summing to the row count
assert ovp["exposure"].sum() == 26_444, ovp["exposure"].sum()
# Values identical to V2: weighted predicted mean ≈ 2,230.9, bands in the thousands
weighted_pred = (ovp["predicted_mean"] * ovp["exposure"]).sum() / 26_444
assert abs(weighted_pred - 2_230.9) / 2_230.9 < 0.01, weighted_pred
assert (ovp["predicted_mean"] > 500).all(), "values ~0.1 would mean an exposure divisor"
assert (np.diff(ovp["predicted_mean"]) >= 0).all()
# V2 recorded observed band averages 1,586–5,453 — allow slack, record actuals
assert ovp["observed_mean"].between(500, 10_000).all(), ovp["observed_mean"].tolist()
print("PASS", len(ovp), round(weighted_pred, 1),
      round(ovp["observed_mean"].min()), round(ovp["observed_mean"].max()))
```

Expected: prints `PASS`, the band count, the weighted predicted mean
(≈2,230.9) and the observed band-mean range (≈1,586–5,453 — record actuals).
This is the number set behind TC8's UI wording assertions.

## TC3 — UI: fresh-session guard is now DATASET-first (S2, inverted from V2)

1. For each of `Diagnostics` and `Prediction`: open a **new browser
   context**, `page.goto("http://localhost:8598/<page>")` directly (empty
   session is the point).
2. Expected on each:
   - Info box with the exact text `Load a dataset first — go to Data Import.`
   - NOT a model guard: `Fit a frequency model first` count == 0, `Fit a
     severity model first` count == 0, and the retired dual wording tail
     `or Severity Model` count == 0 (guard-order inversion — V2 said "Fit a
     model first" here; that is now a FAIL).
   - Retired mismatch fragments: `The active model is a` count == 0,
     `but the loaded dataset is a` count == 0.
   - Zero `[data-testid="stMetric"]`, no `Predict` button (`exact=True`), no
     `Traceback`, no `[data-testid="stException"]` (the KeyError on the
     removed `model` key is the trap).
3. Close the contexts.

## TC4 — UI: frequency loaded, nothing fitted → per-kind guard (S2)

Fresh context, ONE tab for TC4–TC11:

1. `goto /Data_Import`; click `Load dataset` with defaults untouched; wait
   for the `678,013` fragment (≤ ~15 s).
2. Sidebar `Diagnostics`. Expected:
   - Info box with the exact text `Fit a frequency model first — go to
     Frequency Model.`
   - ABSENT: `or Severity Model` (dual wording), `Severity Model` inside the
     guard region is not asserted directly — assert `Fit a severity model
     first` count == 0 instead; `The active model is a` count == 0; `Load a
     dataset first` count == 0; zero `stMetric`; no `stException`.
3. Sidebar `Prediction`. Expected: same guard text and absences; no `Predict`
   button (`exact=True`), no `Single policy` / `Single claim`.

## TC5 — UI: Poisson fit, frequency baseline, stale-batch precondition (S1, S9 setup)

Same tab:

1. Sidebar `Frequency Model`; click `Fit model`; wait for `Model fitted and
   recorded` (timeout 180,000 ms). Appends one real run (S7). Screen 04 shows
   its results section (metrics + coefficient table) — record.
2. Sidebar `Diagnostics`. Expected (regression, frequency wording; timeout
   60,000 ms on the first): `Model summary`, `Coefficients with confidence
   intervals`, `Residuals`, `QQ plot`, `Observed vs Predicted` all visible;
   `stVegaLiteChart` ≥ 2; `stMetric` ≥ 4; `claim frequency` ≥ 1; Poisson
   caption fragment `mostly zero claims` ≥ 1; ABSENT: `claim amount` == 0,
   `The active model is a` == 0; no `stException`. (Chart labels unchanged by
   the rename — `Predicted-frequency band`, `Claim frequency` present.)
3. Sidebar `Prediction`. Expected: `Single policy` visible; `stNumberInput`
   ≥ 4 (exposure among them); `Predict` (`exact=True`) → `Expected claim
   frequency` visible.
4. Click `Predict for loaded portfolio`; wait for `Total expected claims`
   (timeout 120,000 ms); `36,102` visible; `by construction` caption fragment
   ≥ 1 (S9 — the Poisson caption); `Download predictions CSV` visible (not
   clicked). This leaves the frequency batch + `predictions_kind ==
   "frequency"` in session state — the S9 precondition.

## TC6 — UI: severity dataset + only-frequency-fitted → kind guard, not mismatch (S3, S9)

Same tab:

1. Sidebar `Data Import`; combobox route: click the first
   `[data-testid="stSelectbox"]`, type `severity`, Enter; click `Load
   dataset`; wait for `26,444` (≤ ~15 s). `model_frequency` is alive,
   `model_severity` is empty.
2. Sidebar `Diagnostics`. Expected:
   - Info box with the exact text `Fit a severity model first — go to
     Severity Model.`
   - THE retired guard is the trap: `The active model is a` count == 0 and
     `but the loaded dataset is a` count == 0 (V2 showed the mismatch guard
     in this exact state).
   - NO diagnostics render: zero `stMetric`, zero `stVegaLiteChart`; no
     `Traceback` / `stException` (the 678,013-vs-26,444 length-mismatch crash
     — the Poisson model must never run against the severity frame).
3. Sidebar `Prediction`. Expected: same guard text and absences; no `Predict`
   button (`exact=True`); the stale frequency batch is hidden — `Total
   expected claims` count == 0, `36,102` count == 0 (S9, `predictions_kind`
   filter on a page that stops at the guard — no KeyError); no `stException`.
4. Sidebar `Frequency Model` (S4 first half): 04's severity-dataset guard
   still stops before results — guard fragment `severity dataset` visible, no
   `Fit model` button, no results metrics; no `stException`.

## TC7 — UI: Gamma fit — second slot filled, 07 keeps its results (S1, S4)

Same tab:

1. Sidebar `Severity Model`; `Model setup` visible, formula `ClaimAmount ~`
   visible; click `Fit model`; wait for `Model fitted and recorded` (timeout
   30,000 ms). Appends one real run (S7). Results section visible on 07
   (metrics + coefficients). No `stException`.

## TC8 — UI: severity Diagnostics + Prediction render from the severity slot (S1, S8, S9)

Same tab:

1. Sidebar `Diagnostics`. Expected (timeout 60,000 ms on the first):
   - NO guard: `Fit a severity model first` == 0, `The active model is a`
     == 0; `Model summary` visible; `stMetric` count == 4;
     formula caption containing `ClaimAmount ~` and `gamma` (or `Gamma`).
   - Severity wording: `claim amount` ≥ 1, `Average claim amount` and
     `Predicted-claim-amount band` fragments present (labels unchanged by the
     rename); `Calibration table` expander present — expand it and assert the
     grid renders WITHOUT exception (the re-based rename to
     `observed_avg_claim_amount`/`predicted_avg_claim_amount` is the trap: a
     stale rename mapping from the old engine names would KeyError or leave
     raw `observed_mean` headers — record the visible column headers).
   - `stVegaLiteChart` ≥ 4; whole-page ABSENT: `claim frequency` == 0,
     `policy-year` == 0, `mostly zero claims` == 0; no `stException`.
     (Band VALUES in the thousands are TC2's engine truth — not scraped.)
2. Sidebar `Prediction`. Expected:
   - `Single claim` visible, `Single policy` == 0; no exposure input
     (`policy-year` == 0); the stale frequency batch is hidden: `Total
     expected claims` == 0, `36,102` == 0 (S9).
   - `Predict` (`exact=True`) → ONE metric `Expected claim amount`;
     `Expected claim frequency` == 0.
   - Click `Predict for loaded claims` (timeout 60,000 ms): metrics `Mean
     expected claim amount` / `Total expected claim amount` / `Total observed
     claim amount` visible; honest caption fragment `does not reproduce` ≥ 1
     and `by construction` == 0 (S9 — correct caption per kind); a
     `stDataFrame` preview; no `stException`.

## TC9 — UI: THE HEADLINE — switch back to frequency WITHOUT refit (S1, S4, S9)

Same tab. In V2 this exact sequence produced the mismatch guard; now both
slots are alive and the frequency views must simply come back:

1. Sidebar `Data Import`; combobox route with `frequency` (one retry max; on
   failure record and flip TC9–TC11 to manual); click `Load dataset`; wait
   for `678,013`. NO model is refitted.
2. Sidebar `Diagnostics`. Expected:
   - FULL frequency diagnostics render from the still-alive Poisson slot:
     `Model summary` visible (timeout 60,000 ms), `stMetric` ≥ 4,
     `stVegaLiteChart` ≥ 2, `claim frequency` ≥ 1.
   - Retired guard NOWHERE: `The active model is a` == 0, `but the loaded
     dataset is a` == 0; also `Fit a frequency model first` == 0 (the slot is
     not empty); `claim amount` == 0 (no severity residue); no `stException`.
3. Sidebar `Prediction`. Expected: `Single policy` visible, `Single claim`
   == 0; the stale SEVERITY batch from TC8 is hidden — `Total expected claim
   amount` == 0, `Mean expected claim amount` == 0 (S9, reverse direction);
   `Predict` button present (`exact=True`); no `stException`.
4. Sidebar `Frequency Model` (S4): 04 shows its KEPT results — no guard,
   results metrics/coefficient section visible even though a severity model
   was fitted in between (V2 hid them); no `stException`.

## TC10 — UI: arbitrary switching — severity again, 07 keeps its results (S1, S4)

Same tab:

1. Sidebar `Data Import`; combobox route with `severity`; click `Load
   dataset`; wait for `26,444`.
2. Sidebar `Diagnostics`. Expected: severity views render immediately (no
   refit): `Model summary` visible, `ClaimAmount ~` caption, `claim amount`
   ≥ 1, `claim frequency` == 0; `The active model is a` == 0; no
   `stException`.
3. Sidebar `Severity Model` (S4): 07 shows its KEPT Gamma results — no
   guard, results section visible despite the interleaved frequency work; no
   `stException`.

## TC11 — UI: refit never evicts the other slot (S5) — executed-if-time

Same tab (adds ~12 s and one history row; run if time permits, otherwise
record as manual):

1. Sidebar `Data Import`; combobox route with `frequency`; `Load dataset`;
   wait for `678,013`.
2. Sidebar `Frequency Model`; click `Fit model`; wait for `Model fitted and
   recorded` (timeout 180,000 ms) — a REFIT into `model_frequency`.
3. Sidebar `Data Import`; combobox route with `severity`; `Load dataset`;
   wait for `26,444`.
4. Sidebar `Diagnostics`. Expected: the Gamma views STILL render (`Model
   summary` visible, `claim amount` ≥ 1, `Fit a severity model first` == 0)
   — the Poisson refit did not evict `model_severity`; no `stException`.

The reverse eviction check (Gamma refit keeps the Poisson slot) and the
IG-failure variant are TC14 items.

## TC12 — DB: run history appends exactly one row per successful fit (S7)

Automated in the runner, bracketing the UI flow:

1. BEFORE launching the app: `n0 = SELECT COUNT(*) FROM model_runs` on
   `data/workbench.db` (read-only sqlite3 connection; if the file does not
   exist yet, `n0 = 0`). Record the schema:
   `PRAGMA table_info(model_runs)` column names.
2. AFTER the UI flow: `n1 = COUNT(*)`. Expected: `n1 - n0` == the number of
   successful UI fits performed (2 without TC11 — one Poisson TC5, one Gamma
   TC7 — or 3 with TC11's refit). The stepwise/Adopt path appends nothing
   (S6 — but stepwise is not exercised here, so this is a no-extra-rows
   check). Schema unchanged vs the recorded `PRAGMA` (no new/renamed
   columns). **Never delete or truncate `data/workbench.db`.**

## TC13 — Regression: existing suites green, retired assertions inverted

From the repo root, port 8598 free (runners launch their own app instance —
never concurrently):

1. `uv run pytest` — full suite passes (record the count) with the 75%
   coverage gate met (unit tests updated for `observed_mean`/`predicted_mean`
   and the per-kind slots).
2. `uv run python e2e/e2e_diag_pred.py` — green after TWO updates:
   - fresh-session assertion (`Fit a model first`, line ~104) → the new exact
     text `Load a dataset first — go to Data Import.`;
   - engine `ovp` column assertions `observed_frequency`/
     `predicted_frequency` (lines ~53–56) → `observed_mean`/`predicted_mean`.
3. `uv run python e2e/e2e_severity_model.py` — expected green UNCHANGED: its
   screen-04 severity-dataset guard assertion stays valid (S4), and its
   inverted TC7 (Diagnostics/Prediction render with the severity model on the
   severity dataset) still holds under per-kind slots. Verify; record any
   surprise.
4. `uv run python e2e/e2e_severity_diag_pred.py` — green after FOUR updates
   (note the inversions in that plan's Results, per precedent):
   - engine TC2 column names (lines ~83–91) → `observed_mean`/
     `predicted_mean`;
   - its TC3 fresh-session assertions (lines ~126–127) → `Load a dataset
     first — go to Data Import.` (not `Fit a model first`);
   - its TC5 (direction B, `MISMATCH_B` line ~96) INVERTED: frequency model +
     severity dataset now shows `Fit a severity model first — go to Severity
     Model.` and the mismatch text must be ABSENT;
   - its TC9 (direction A, `MISMATCH_A` line ~97) INVERTED: by that point the
     runner has fitted BOTH kinds, so loading the frequency dataset must
     RENDER the full frequency diagnostics/prediction from the kept
     `model_frequency` slot (the V3 headline), not any guard.
5. `uv run ruff check pricing_engine/ tests/ app.py pages/ e2e/`,
   `uv run ruff format --check …`, `uv run mypy pricing_engine/ tests/` —
   clean.

## TC14 — Deferred/manual: stepwise, IG failure, reverse eviction, CSV

Long fits and BaseWeb interactions beyond the sanctioned combobox route stay
**manual**:

1. S6 — Stepwise: on 04 (frequency dataset + Poisson fitted), note the
   Diagnostics AIC; run `Run stepwise selection` (takes MINUTES — hence
   manual) and click `Adopt`; the 04 fitted-results metrics and the 05
   Diagnostics metrics are UNCHANGED (only `selection_result` is written);
   after an explicit `Fit model` with the adopted spec they change. Switching
   to the severity dataset mid-way still renders the Gamma views (neither
   slot touched). `e2e_stepwise.py` staying green (TC13) covers the engine
   path.
2. S5 — IG failure keeps BOTH slots: with Gamma + Poisson both fitted, select
   `Inverse Gaussian` on 07 and `Fit model` → the documented friendly error;
   05 on the severity dataset still shows the PREVIOUS Gamma (AIC
   573,121-ish), and switching to the frequency dataset still shows the
   Poisson views (the failed fit touched neither slot).
3. Reverse of TC11: Gamma refit (07) does not evict `model_frequency`.
4. CSV contents on both batches: frequency CSV has `expected_claims` and no
   `expected_claim_amount`; severity CSV the reverse.
5. TC11 if it was not executed. Record executed/deferred in Results.

## Runner

Committed runner: **`e2e/e2e_model_slots.py`** (engine TC1–TC2 + DB TC12
inline, UI TC3–TC11 via Playwright against port 8598 through
`e2e/harness.py`; TC13 run separately from the shell). Existing runners to
update BEFORE running TC13 — the retired-behaviour assertions from the BA
report's last section:

- `e2e/e2e_diag_pred.py`: fresh-session guard text → `Load a dataset first —
  go to Data Import.`; `observed_frequency`/`predicted_frequency` →
  `observed_mean`/`predicted_mean`.
- `e2e/e2e_severity_diag_pred.py`: same column rename in its engine TC2;
  fresh-session TC3 → dataset-first text; mismatch TC5 inverted to the
  severity kind guard; mismatch TC9 inverted to the rendered frequency views
  (both slots alive). Note the inversions in
  `.planning/e2e-tests/severity-diagnostics-prediction.md` Results.
- `e2e/e2e_severity_model.py`: expected unchanged (screen-04 guard and its
  slice-3 TC7 still valid) — verify green.

## Execution notes

- Prerequisites: both real Parquet files in `data/raw/`; Playwright +
  Chromium installed (`uv run playwright install chromium`); port 8598 free.
  **Never delete or truncate `data/workbench.db`** — TC12 counts the
  appended rows (2–3 real runs, expected behaviour under test).
- Engine TCs (TC1–TC2) and the TC12 `n0` snapshot run FIRST; then start the
  app once headless on 8598. UI TCs: TC3 in throwaway contexts (direct goto
  sanctioned); TC4→TC11 sequentially in **ONE tab of one context**,
  **sidebar links only** after the first load. Timeouts: default ~20,000 ms;
  180,000 ms after each Poisson `Fit model`; 30,000 ms after the Gamma
  `Fit model`; 120,000 ms after the frequency batch; 60,000 ms after the
  severity batch and on each first post-switch Diagnostics expectation.
- Combobox route runs FOUR times in the main flow (TC6 `severity`, TC9
  `frequency`, TC10 `severity`, TC11 `frequency`+`severity`): click → type →
  Enter, one retry max each; on a failure the remaining chained TCs flip to
  manual — record the route either way. `expect` before `count`; `.first` on
  fragments that can appear twice; `exact=True` on `Predict`.
- The three guard texts are asserted EXACTLY (`Load a dataset first — go to
  Data Import.`, `Fit a frequency model first — go to Frequency Model.`,
  `Fit a severity model first — go to Severity Model.`); all other captions,
  button labels and axis titles are matched loosely on fragments with actuals
  recorded in Results. Wording drift there is not a FAIL.
- FAIL conditions, in one place: any occurrence of `The active model is a` /
  `but the loaded dataset is a` (retired mismatch guard) or `or Severity
  Model` in a guard (retired dual wording); a guard on 05/06 when the loaded
  kind's slot is alive (TC8–TC11); the wrong kind's views or stale batch
  numbers after a switch; `observed_frequency`/`predicted_frequency` in the
  engine result (TC1/TC2); a KeyError from the calibration-table rename
  (TC8); hidden results on 04/07 when their own slot is alive (TC9.4/TC10.3);
  a run-history delta ≠ the fit count or a schema change (TC12); any
  traceback/`stException` anywhere.
- Pre-authorized observations to record, not failures: TC1's weighted mean /
  total, TC2's band range, the honest Gamma caption wording, the exact
  results-section layout on 04/07.

## Results

Executed 2026-08-31 via the committed runner `e2e/e2e_model_slots.py`
(TC1–TC12; TC13 from the shell; TC14 deferred/manual). ALL EXECUTED TCs
PASSED. Two runner-side fixes during bring-up (test mechanics, not app
defects): the TC8 calibration-grid assertion needed a `visible=true` filter
(`.first` resolved to the hidden grid inside the collapsed "Coefficient
table" expander), and TC9's `Predict`-button check needed `expect(...)`
auto-waiting instead of an instantaneous `count()`.

- TC1 PASS — rename contract holds; weighted_pred 0.1007, total_expected
  36,102 (value-neutral rename).
- TC2 PASS — bands 10, weighted_pred 2,230.9, observed band range
  1,586–5,453 (identical to V2).
- TC3 PASS — fresh sessions on 05/06 show `Load a dataset first — go to Data
  Import.`; no model guard, no retired wording, no KeyError.
- TC4 PASS — frequency loaded, nothing fitted: exact guard `Fit a frequency
  model first — go to Frequency Model.` on both pages.
- TC5 PASS — Poisson fit + full frequency diagnostics/prediction baseline;
  36,102 with the `by construction` caption; batch left in session state.
- TC6 PASS — severity data + only-frequency-fitted: exact guard `Fit a
  severity model first — go to Severity Model.`; mismatch wording absent; no
  length-mismatch crash; stale frequency batch hidden; 04's severity-dataset
  guard intact.
- TC7 PASS — Gamma fit; 07 shows its results.
- TC8 PASS — severity Diagnostics from the severity slot (AIC 573,121 view,
  `ClaimAmount ~` caption); calibration table opens without KeyError
  (re-based rename); severity Prediction: single claim, batch with `does not
  reproduce` caption; stale frequency batch hidden.
- TC9 PASS — THE HEADLINE: switching back to the frequency dataset WITHOUT a
  refit renders the live Poisson views (V2 showed the mismatch guard here);
  stale severity batch hidden; 04 keeps its results.
- TC10 PASS — severity again: Gamma views render immediately; 07 keeps its
  results.
- TC11 PASS — Poisson refit did not evict the Gamma slot.
- TC12 PASS — run history 27 → 30 (3 fits: TC5 Poisson, TC7 Gamma, TC11
  refit), schema unchanged.
- TC13 PASS — `uv run pytest`: 109 passed, 99.43% coverage; ruff
  check/format + mypy clean (incl. `e2e/`); `e2e_diag_pred.py` green after
  its two updates; `e2e_severity_diag_pred.py` green after its four updates
  (TC3/TC5/TC9 inversions noted in that plan's Results);
  `e2e_severity_model.py` green unchanged.
- TC14 DEFERRED/manual — stepwise Adopt slot-neutrality, IG failure keeps
  BOTH slots, Gamma-refit reverse eviction, CSV contents (added to the
  manual-walkthrough backlog item in TODO.md).
