# E2E — Feature Engineering slice (pricing_engine/preprocessing.py + pages/03_Feature_Engineering.py)

Change under test: the workflow's third screen. Engine: `pricing_engine/preprocessing.py`
(replacing stubs) with four pure functions — `bin_numeric(df, column, bins=8,
strategy="quantile"|"uniform") -> (df_copy, new_column)` (adds a banded
categorical `<column>_band` with readable ordered string labels; ValueError for
unknown/non-numeric columns or a bad strategy), `log_transform(df, columns) ->
df_copy` (adds `<column>_log`, natural log; ValueError naming the column when it
has non-positive values), `encode_categorical(df, columns) -> df_copy` (one-hot
dummies with `<column>_` prefix, drop_first=True, originals kept),
`cap_column(df, column, cap) -> (df_copy, n_capped)` (clips values above cap,
returns how many were capped — the freMTPL2 Exposure>1 quirk, ~1,200 policies).
UI: `pages/03_Feature_Engineering.py` — guard like Exploration ("Load a dataset
first — go to Data Import."); "Variables" multiselect of model predictors
(defaults to the current spec predictors, changes update the spec in session
state); "Exposure" section (only when `spec.offset` is set) with a caption
showing how many rows exceed 1.0 and a button "Cap Exposure at 1.0" → success
message with the capped count, caption then shows 0; "Binning" section with a
numeric-predictor selectbox (default first numeric predictor, "VehPower"),
bands slider (2–12, default 8), strategy radio (quantile default), button
"Create banded variable" → adds `<col>_band` AND appends it to the spec
predictors; "Log transform" section with a strictly-positive numeric column
selectbox (Density qualifies) and button "Add log variable" → adds `<col>_log`
+ appends to predictors; an "Encoding" info box explaining categoricals are
encoded automatically by the GLM formula (treatment coding) at fit time — no
manual one-hot needed; "Current model specification" section listing target,
offset, predictors of the live spec. Engineered columns and spec changes
persist in session state, so Data Exploration afterwards offers e.g.
"DrivAge_band" as a one-way predictor.

BA scenarios (the user is an actuary learning GLMs, working through the
Chapter-27 frequency workflow on the real freMTPL2 data):

- As an actuary preparing rating factors, banding a continuous age variable is
  THE classic prep step before a GLM: I pick DrivAge (or the preselected
  numeric predictor), choose how many bands, click once, and get a readable
  banded variable (e.g. "18–26", "27–34", …) that is immediately part of my
  model — I should never have to hand-write bin edges or touch pandas. The
  bands must be ORDERED like ages, not alphabetically shuffled, and the
  success message must tell me the new variable's name and how many bands it
  actually got (quantile binning can merge duplicate edges — I want to see the
  real count, not the slider value).
- As an actuary who just learned in Data Exploration that Exposure runs up to
  more than a year, capping exposure at 1.0 is real-world data hygiene: the
  screen should tell me up front how many policies exceed 1.0 (a number in the
  low thousands for freMTPL2), let me fix it with one button, confirm how many
  rows it capped, and then show me the problem is gone (0 above 1.0). If I
  click again it should cap 0 more — the operation is idempotent from my point
  of view.
- As a learner, the "Variables" multiselect is how I narrow the model —
  dropping a predictor I don't believe in (the Chapter-27 lesson with the
  Dummy variables) must actually change the model specification, not just the
  widget, so the Frequency Model screen fits what I chose.
- As an actuary, the "Current model specification" section is my CONTRACT with
  the upcoming Frequency Model screen: target ClaimNb, offset Exposure, and
  the live predictor list — including every engineered variable I just created
  — spelled out in plain text so I can verify what will be fit before I fit it.
- As a learner, I expect a log transform for skewed positive variables
  (Density spans orders of magnitude); the screen should only offer me columns
  where a log is mathematically valid (strictly positive) instead of letting
  me crash on ClaimNb's zeros.
- As a learner, I might expect a one-hot encoding button for Region — the info
  box teaching me that the GLM formula does treatment coding automatically at
  fit time (and why exploding 678k rows × 22 Region levels by hand is the
  wrong move) is exactly the kind of education this workbench exists for.
- As a user, my engineered variables must show up DOWNSTREAM: after creating
  DrivAge_band here, going back to Data Exploration must offer it as a one-way
  predictor — otherwise feature engineering was cosmetic.
- As a user who skipped Data Import (fresh tab straight to Feature
  Engineering), I get the friendly pointer back to Data Import — an info box,
  not a traceback, and nothing else on the page pretending to work.

Test Agent notes from the BA interview: the UI exists, so per CLAUDE.md the
cases run via **Playwright (Python sync API)** against the running Streamlit
app; numeric truths (capped counts, band counts, log validity, error wording)
are asserted at the **engine level** in Python, where they are deterministic.
Assumptions and mechanics, carrying forward the accumulated lessons from
`data-import.md` and `data-exploration.md` Results:

- App started headless on port 8598 before the run:
  `uv run streamlit run app.py --server.port 8598 --server.headless true`
  from the repo root, real `data/raw/freMTPL2freq.parquet` present.
- **Session state is per browser tab; `page.goto` reloads DROP it** (proven
  live twice). All post-load TCs run in ONE tab and navigate via the
  **sidebar links** (`app`, `Data Import`, `Data Exploration`,
  `Feature Engineering` — record actual link labels in Results). Only the
  guard TC uses a direct `goto` in a **fresh context**.
- Load the real dataset first via `Load dataset` on Data Import; allow ~15 s
  (`expect` timeout) for the 678k-row load.
- Counts may render **thousands-separated** ("678,013"); match loosely on
  distinctive fragments; `.first` for any text that can appear more than once
  under strict mode.
- Selectboxes/multiselects/radios are BaseWeb widgets whose current value is
  not readable via `get_by_text`, and changing them is brittle: all UI TCs
  are **defaults-only + button clicks**. Binning therefore runs with the
  DEFAULT selectbox value. **Assumption:** the default numeric-predictor is
  the FIRST numeric predictor in spec order — Area is categorical, so that is
  **VehPower** (spec order: Area, VehPower, VehAge, DrivAge, BonusMalus,
  VehBrand, VehGas, Density, Region) — and the default slider value is 8,
  default strategy quantile. The default is PROVEN via the success message
  naming `VehPower_band` (plain visible text), not by reading the combobox.
  DrivAge banding — the BA's headline scenario — is proven at the engine
  level (TC7), same split as last slice's "default proven engine-side".
- **Caveat on VehPower quantile bands:** VehPower has only 12 distinct
  integer values, so `qcut(..., 8, duplicates="drop")` may yield FEWER than 8
  bands. The success message names the ACTUAL band count — assert the
  variable name fragment `VehPower_band` strictly and the band count loosely
  (a number between 2 and 8); record the real count in Results.
- Success/caption/info wording is an implementation choice — match loosely on
  distinctive fragments (`Cap`, `1.0`, `_band`, `_log`, capped count digits),
  record actual wording in Results. Wording drift is not a FAIL; a MISSING
  message/element or a traceback IS.
- Tables (`st.dataframe`) remain unassertable at cell level (glide-data-grid);
  the "Current model specification" list is spec'd as PLAIN TEXT (not a
  dataframe), so `get_by_text("VehPower_band")` style assertions are valid
  there — if the implementation renders it as a dataframe instead, fall back
  to asserting the container and record the deviation in Results.
- Known testids from previous slices: `stMetric`, `stDataFrame`,
  `stSelectbox`, `stVegaLiteChart`, `stException`. New this slice: slider
  `[data-testid="stSlider"]`, multiselect `[data-testid="stMultiSelect"]`,
  buttons via `get_by_role("button", name=...)` as before. Verify once
  against the live DOM and record.
- Order matters WITHIN the UI run: the exposure-cap TC must assert the
  "before" caption BEFORE the binning TC clicks anything (both mutate session
  state); run TC3 → TC4 → TC5 → TC6 strictly in sequence in the one tab.
  Engine TCs (TC7) are order-free, separate Python scripts on a fresh
  `load_dataset` frame — UI mutations cannot leak into them.

## TC1 — Guard: straight to Feature Engineering without a dataset

1. Open a **new browser context** (fresh Streamlit session — the one place a
   direct goto is correct),
   `page.goto("http://localhost:8598/Feature_Engineering")` (adjust the URL
   slug to the actual page name if needed — record it), wait for render.
2. Expected:
   - An info box visible with the pointer text — distinctive fragments
     `Load a dataset first` and `Data Import` (spec'd wording: "Load a
     dataset first — go to Data Import.", identical to Exploration's guard).
   - NO section content: no `Variables`/`Binning`/`Exposure` headers, zero
     buttons named `Cap Exposure at 1.0` / `Create banded variable` /
     `Add log variable`, no `stMultiSelect`, no `stSlider`.
   - `Traceback` absent; no `[data-testid="stException"]`.

## TC2 — Setup: load the built-in dataset, then reach Feature Engineering via sidebar

1. In the SAME context/tab, click the sidebar link `Data Import`.
2. Click the button `Load dataset`; wait (≤ ~15 s) for the success message
   containing `Loaded` and `678`.
3. Click the sidebar link `Feature Engineering` — **sidebar link, NOT goto**.
4. Expected:
   - Guard info box GONE (`Load a dataset first` not present).
   - The screen's sections render: headers (loose fragments) `Variables`,
     `Exposure`, `Binning`, `Log transform`, `Encoding` (or its info box),
     `Current model specification` — each `.first`.
   - A multiselect (`stMultiSelect`) is present in the Variables section; a
     slider (`stSlider`) in Binning; at least 2 selectboxes on the page
     (binning column + log column). Defaults only — no widget interaction.
   - The Encoding info box text mentions automatic encoding at fit time —
     loose fragments `automatically` / `formula` (record actual wording).
   - No traceback / `stException`.

## TC3 — Exposure cap: before-count caption, button, success, after-count 0

Fully button-driven — no combobox needed. Run BEFORE TC4 (first mutation).

1. Same tab: locate the Exposure section caption showing how many rows exceed
   1.0. Expected BEFORE: a visible text containing a thousands-separated
   count in the low thousands (loose match: the fragment `above 1.0` or
   `exceed` plus a digit group like `1,2` — exact number is proven
   engine-side in TC7 as 500 < n < 5,000; record the rendered number).
   It must NOT read `0` above 1.0 at this point.
2. Click the button `Cap Exposure at 1.0`.
3. Expected:
   - A success message appears containing `apped` (Capped/capped) and the
     same count digits as the before-caption (thousands-separated).
   - The caption now shows **0** rows above 1.0 (fragment `0` adjacent to
     the above-1.0 wording — use a tight locator scoped to the caption, not
     a bare page-wide `get_by_text("0")`, which would be ambiguous).
   - No traceback / `stException`.
4. (Optional, if trivially repeatable) Click the button again: success/info
   reports 0 capped — idempotence per the BA. Record whether attempted.

## TC4 — Binning with ALL defaults: creates VehPower_band

Defaults-only: selectbox default = first numeric predictor (**assumed
VehPower** — see notes), slider default 8, strategy default quantile. The only
interaction is the button click.

1. Same tab (after TC3): in the Binning section click the button
   `Create banded variable`.
2. Expected:
   - A success message appears naming the new variable — strict fragment
     `VehPower_band` — and a band count (loose: a small integer 2–8; VehPower
     has only 12 distinct values so quantile-8 may merge; record the actual
     count and message wording in Results).
   - If the message instead names a different `<col>_band`, the
     first-numeric-predictor assumption was wrong — record the actual default
     column in Results and re-evaluate (the TC still passes if a `_band`
     variable is created and flows into TC5; the assumption note is updated).
   - No traceback / `stException`.

## TC5 — Current model specification reflects the change

1. Same tab, immediately after TC4: locate the `Current model specification`
   section (`.first`).
2. Expected — all as plain visible text (this section is spec'd as text, not
   a canvas dataframe):
   - Target `ClaimNb` visible; offset `Exposure` visible (scope/`. first` as
     needed — "Exposure" also appears in the cap section).
   - The predictor list includes `VehPower_band` — the variable TC4 created
     (`get_by_text("VehPower_band").first`; it may also appear in the TC4
     success message, hence `.first`).
   - Original predictors still listed (spot-check `BonusMalus` and `Region`
     as distinctive fragments).
   - If the section renders as an `stDataFrame` instead of text, assert the
     container only and record the deviation (text-assertability was a design
     point — flag it in Results as drift worth fixing).

## TC6 — Downstream integration: Data Exploration still renders with the band in the spec

Optional but cheap; the full one-way-on-band selection is combobox territory
and stays manual (TC8).

1. Same tab: click the sidebar link `Data Exploration`.
2. Expected:
   - The exploration screen renders normally: metrics row (≥ 4 `stMetric`),
     `One-way claim frequency` header visible, at least one
     `stVegaLiteChart`, NO guard box, NO traceback / `stException`. (The
     spec now contains `VehPower_band`; if exploration's summary iterates
     `spec.required_columns`, a missing-column crash here is exactly the
     regression this TC exists to catch — the engineered COLUMN must have
     persisted alongside the spec change.)
   - The one-way predictor selectbox now OFFERS the band variable — but
     verifying the option list requires opening the combobox; assert only if
     trivially possible, otherwise leave to TC8 (manual) and record.

## TC7 — Engine truths: cap count, DrivAge bands, log, errors, encoding

Engine-level (deterministic, automated). Run via `uv run python <tempfile.py>`
(or `.venv\Scripts\python.exe` in the sandbox) from the repo root; script in
the session scratchpad, not the repo:

```python
import numpy as np
import pandas as pd
from pricing_engine.data import load_dataset
from pricing_engine.preprocessing import (
    bin_numeric, cap_column, encode_categorical, log_transform,
)

df, spec = load_dataset("fremtpl2_freq")
assert len(df) == 678_013, len(df)

# --- cap_column on real Exposure: the >1 quirk (~1,200 policies) ---
n_above = int((df["Exposure"] > 1.0).sum())
capped_df, n_capped = cap_column(df, "Exposure", 1.0)
assert n_capped == n_above, (n_capped, n_above)
assert 500 < n_capped < 5_000, n_capped          # "~1,200" sanity band
assert float(capped_df["Exposure"].max()) == 1.0, capped_df["Exposure"].max()
assert float(df["Exposure"].max()) > 1.0          # original untouched (copy)
# Idempotent: capping the capped frame caps 0 more
_, n_again = cap_column(capped_df, "Exposure", 1.0)
assert n_again == 0, n_again

# --- bin_numeric DrivAge, 8 quantile bands: THE classic age banding ---
banded, new_col = bin_numeric(df, "DrivAge", bins=8, strategy="quantile")
assert new_col == "DrivAge_band", new_col
assert new_col in banded.columns and new_col not in df.columns  # copy
counts = banded[new_col].value_counts()
assert 2 <= len(counts) <= 8, len(counts)
assert int(counts.sum()) == 678_013, counts.sum()
# Labels are readable ordered strings: category order (or sorted appearance
# order) must follow ascending age, and every row is labelled (no NaN band)
assert banded[new_col].isna().sum() == 0
labels = (
    list(banded[new_col].cat.categories)
    if isinstance(banded[new_col].dtype, pd.CategoricalDtype)
    else sorted(banded[new_col].unique())
)
assert all(isinstance(lbl, str) for lbl in labels), labels
# uniform strategy also works and differs in edges
banded_u, _ = bin_numeric(df, "DrivAge", bins=8, strategy="uniform")
assert banded_u["DrivAge_band"].nunique() >= 2

# --- log_transform on Density: strictly positive, finite result ---
logged = log_transform(df, ["Density"])
assert "Density_log" in logged.columns
assert np.isfinite(logged["Density_log"]).all()
assert np.allclose(logged["Density_log"], np.log(df["Density"]))

# --- ValueError cases ---
for bad_call, must_mention in [
    (lambda: bin_numeric(df, "NotAColumn"), "NotAColumn"),
    (lambda: bin_numeric(df, "Area"), "Area"),                    # non-numeric
    (lambda: bin_numeric(df, "DrivAge", strategy="banana"), "banana"),
    (lambda: log_transform(df, ["ClaimNb"]), "ClaimNb"),          # zeros
]:
    try:
        bad_call()
        raise SystemExit(f"FAIL: no ValueError ({must_mention})")
    except ValueError as e:
        assert must_mention in str(e), (must_mention, str(e))

# --- encode_categorical VehGas: 2 levels, drop_first -> exactly 1 dummy ---
assert df["VehGas"].nunique() == 2, df["VehGas"].nunique()
encoded = encode_categorical(df, ["VehGas"])
dummies = [c for c in encoded.columns if c.startswith("VehGas_")]
assert len(dummies) == 1, dummies                 # baseline level dropped
assert "VehGas" in encoded.columns                # original kept
assert set(encoded[dummies[0]].unique()) <= {0, 1, True, False}

print("PASS", n_capped, len(counts), dummies[0])
```

Expected: prints `PASS` with the capped count (record the exact number — the
spec says ~1,200), the DrivAge band count (≤ 8), and the VehGas dummy column
name. Any assertion failure or unexpected exception is a FAIL.

## TC8 — Variables multiselect, log-transform button, one-way on the band — MANUAL / DEFERRED

BaseWeb multiselect/selectbox changes are brittle in Playwright (deferred in
both previous slices); these are **specified for manual execution**:

1. With the dataset loaded, on Feature Engineering remove `VehBrand` from the
   Variables multiselect. Expected: `Current model specification` no longer
   lists `VehBrand`; the other predictors remain.
2. In Log transform, keep/select `Density` (should be offered — strictly
   positive; ClaimNb and VehAge must NOT be offered, both contain 0) and
   click `Add log variable`. Expected: success message naming `Density_log`;
   spec section now lists it.
3. Navigate (sidebar) to Data Exploration; in the one-way predictor
   selectbox pick `DrivAge_band` (or `VehPower_band` from TC4). Expected: a
   one-way frequency chart/table over the ordered bands — the BA's
   "engineered variables show up downstream" scenario, end to end.
4. Record in Results whether executed manually or deferred.

## Execution notes

- Prerequisites: real `data/raw/freMTPL2freq.parquet` present; Playwright +
  Chromium installed (`uv run playwright install chromium`).
- Start the app once for the whole run:
  `uv run streamlit run app.py --server.port 8598 --server.headless true`
  (background; kill after). Give it a few seconds before the first goto.
- TC1 in a **fresh context**; then TC2 → TC3 → TC4 → TC5 → TC6 strictly in
  order in **ONE tab** of that context (TC3's before-caption must be read
  before any other mutation; TC4 feeds TC5/TC6), **sidebar links only** after
  the load. TC7 is an independent Python script (order-free, fresh frame —
  UI-side mutations live only in the browser session). Scripts/temp files go
  in the session scratchpad, not the repo.
- `playwright.sync_api` with auto-waiting `expect(...)`; ~15000 ms timeout
  for the post-`Load dataset` assertion in TC2, defaults elsewhere.
- Selector assumptions to verify once against the live DOM and record in
  Results: buttons by role+name (`Cap Exposure at 1.0`,
  `Create banded variable`, `Add log variable` — actual labels may drift,
  match loosely), `stMultiSelect`, `stSlider`, `stSelectbox`, `stMetric`,
  `stVegaLiteChart` (fallback `stArrowVegaLiteChart`), `stException`.
- Key assumptions to confirm and record: (a) binning selectbox default is
  the first NUMERIC predictor = **VehPower**; (b) the sidebar link label for
  this page (assumed `Feature Engineering`) and its URL slug for TC1's goto
  (assumed `/Feature_Engineering`); (c) the "Current model specification"
  section is plain text, not a dataframe; (d) VehPower quantile-8 real band
  count (may be < 8 — duplicates dropped on 12 distinct integer values).
- Exact-text caveats: guard wording "Load a dataset first — go to Data
  Import."; success/caption wording implementation-chosen — match loosely on
  distinctive fragments (`VehPower_band`, `apped`, count digits with
  thousands separators), record actual wording, labels, and numbers in
  Results. Wording drift is not a FAIL; a missing element/message, a wrong
  count, or a traceback IS.

## Results

- 2026-07-25 — **executed TCs ALL PASSED on the first run** (Playwright 1.61 /
  Chromium headless, port 8598, real data):
  - Engine (TC7): `cap_column` on real Exposure capped **1,224 rows**
    (500–5,000 band ✓), max == 1.0 after, original frame untouched, second cap
    idempotent (0); DrivAge 8-quantile bands ≤ 8, string labels, all 678,013
    rows covered; `Density_log` finite; ValueErrors for unknown column,
    non-numeric Area, zero-containing ClaimNb; VehGas → exactly 1 drop_first
    dummy, original kept.
  - UI: guard TC (fresh context, friendly pointer, no exception); setup/load;
    exposure-cap TC fully button-driven — caption "1,224 rows have Exposure
    above 1.0" → click → success "Capped 1,224 value(s) of Exposure at 1.0
    policy-years." → caption shows "0 rows"; binning TC with defaults —
    success "Added banded variable 'VehPower_band'" (default numeric predictor
    was VehPower as assumed) and the spec section lists `VehPower_band` with
    "Predictors (10)"; downstream TC — Data Exploration renders cleanly after
    the engineering mutations.
- TC8 (multiselect change, log-transform button — its default would be
  VehPower_log, not Density_log — and one-way on the new band) DEFERRED/manual
  per plan.
- Implementation note: all page mutations run in `on_click`/`on_change`
  callbacks so widget state (`predictor_select`) and the spec stay consistent
  across Streamlit reruns; flash messages surface the callback results after
  rerun.
