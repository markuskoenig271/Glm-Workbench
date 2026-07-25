# E2E — Data Exploration slice (pricing_engine/exploration.py + pages/02_Data_Exploration.py)

Change under test: the workflow's second screen. Engine: new module
`pricing_engine/exploration.py` with five **aggregate-only** functions (they
return small frames / scalars, never raw rows — 678k rows must stay fast):
`portfolio_frequency(df, spec)` (total claims / total exposure; falls back to
claims/policies when `spec.offset is None`), `summarize_portfolio(df, spec)`
(one row per required column: role, dtype kind, missing, unique, min/mean/max
for numerics), `one_way_frequency(df, spec, predictor, max_levels=12)` (the
classic actuarial one-way: group by predictor — numeric predictors with more
than `max_levels` distinct values are quantile-binned — with policies count,
exposure sum, claims sum, frequency per level; unknown predictor → `ValueError`
naming the valid ones), `histogram(df, column, bins=30)` (numeric → binned
counts, categorical → value counts), `correlation_matrix(df, spec)` (Pearson,
numeric required columns). UI: `pages/02_Data_Exploration.py` — guard when no
dataset is in session ("Load a dataset first — go to Data Import." via
`st.info`, nothing else rendered); headline `st.metric` row (policies, total
exposure, total claims, overall frequency); "Summary statistics" table;
"One-way claim frequency" section with a predictor selectbox (defaults to the
first predictor, "Area"), bar chart + aggregated table; "Histograms" section
with a column selectbox + bar chart; "Correlations" matrix table.

BA scenarios (the user is an actuary learning GLMs, working through the
Chapter-27 frequency workflow on the real freMTPL2 data):

- As an actuary who just loaded 678,013 policies, I need orientation before I
  model anything: how many policies, how much exposure, how many claims, and
  the overall claim frequency — all at a glance in one metrics row. For
  freMTPL2 I expect roughly 36,102 claims over ~358,499 policy-years, i.e. a
  frequency near 0.10 claims per policy-year; if the screen showed 1.0 or
  0.001 I would immediately distrust the load.
- As an actuary, the one-way claim frequency by rating factor is THE sanity
  check before fitting a GLM: picking a predictor (Area is preselected) must
  show frequency varying across its levels (denser Area bands should run
  higher; BonusMalus should trend strongly). Each level shows policies,
  exposure, claims, and frequency — exposure-weighted, not naive row averages —
  because that is exactly the table I would build in Excel, only instant.
- As a learner, the summary statistics table tells me per column what role it
  plays in the model (target / offset / predictor), its type, whether values
  are missing, and its range — so I discover, before modelling, that e.g.
  Exposure runs from a few days to a year and BonusMalus is bounded.
- As a learner, histograms show me the raw shape of each column (exposure
  clustered near 1.0, driver age distribution, claim counts almost all zero)
  without me needing to know that plotting 678k raw points would melt the
  browser — the app aggregates first, always.
- As an actuary, the correlation matrix warns me about collinear numeric
  predictors before I put them both in a formula.
- As a user who skipped Data Import (fresh tab straight to Data Exploration),
  I get a friendly pointer back to Data Import — an info box, not a Python
  traceback and not a blank screen. Nothing else on the page pretends to work.
- As a user on real data, no interaction on this screen may take noticeably
  long or crash the tab: every table and chart is built from aggregates
  (levels, bins), never from the 678k raw rows.

Test Agent notes from the BA interview: the UI exists, so per CLAUDE.md the
cases run via **Playwright (Python sync API)** against the running Streamlit
app; numeric truths (frequency values, level counts, error wording,
performance) are asserted at the **engine level** in Python, where they are
deterministic. Assumptions and mechanics, carrying over the previous slice's
hard-won lessons (`data-import.md` Results):

- App started headless on port 8598 before the run:
  `uv run streamlit run app.py --server.port 8598 --server.headless true`
  from the repo root, real `data/raw/freMTPL2freq.parquet` present.
- **Session state is per browser tab; `page.goto` reloads DROP it** (confirmed
  live last slice). All post-load TCs therefore run in ONE tab and navigate
  via the **sidebar links** — labelled `app`, `Data Import`,
  `Data Exploration` — never via `page.goto` after the dataset is loaded.
  Only the guard TC uses a direct `goto` in a **fresh context**, exploiting
  exactly that behaviour.
- Load the real dataset first via the `Load dataset` button on Data Import;
  allow ~15 s (`expect` timeout) for the 678k-row load, as before.
- Row/claim counts may render **thousands-separated** ("678,013") — match
  loosely on distinctive fragments and record actual formatting in Results.
  Text appearing more than once on the page needs `.first` under strict mode.
- `st.metric` renders its label and value as visible text —
  `expect(page.get_by_text("Policies")).to_be_visible()` style assertions
  work. Exact metric labels are an implementation choice; the TCs name
  expected concepts (policies / exposure / claims / frequency) and match
  loosely, recording actual labels in Results.
- Tables (`st.dataframe`) are canvas-based glide-data-grid: cell contents are
  NOT reliably assertable, and **hidden header cells render column names into
  the DOM** (false positives AND strict-mode traps — do not assert table
  content via `get_by_text`). Assert table presence via
  `[data-testid="stDataFrame"]` count/visibility plus the section headers.
- Charts are canvas/vega — pixels and data values are not assertable. Assert
  the chart **container** exists. **Assumed testid:**
  `[data-testid="stVegaLiteChart"]` (newer Streamlit; older builds use
  `stArrowVegaLiteChart`). The executor should check the DOM once and adjust
  the selector — record the actual testid in Results. If the page uses
  `st.bar_chart`, it still renders as a vega-lite container.
- Selectboxes are BaseWeb comboboxes whose current value is not readable via
  `get_by_text`; all UI TCs work with **defaults only** (one-way predictor
  defaults to "Area", first in `spec.predictors`). Changing the selection is
  deferred to a manual case. The default is instead PROVEN at the engine
  level (TC7 asserts `one_way_frequency(..., "Area")` returns the 6 A–F
  levels — the same call the UI makes with its default).
- Section headers ("Summary statistics", "One-way claim frequency",
  "Histograms", "Correlations") are ordinary heading text — assert with
  `get_by_text(...).first`.

## TC1 — Guard: straight to Data Exploration without a dataset

1. Open a **new browser context** (fresh Streamlit session — this is the one
   place a direct goto is correct),
   `page.goto("http://localhost:8598/Data_Exploration")`, wait for render.
2. Expected:
   - An info box visible containing the pointer text — distinctive fragments
     `Load a dataset first` and `Data Import` (spec'd wording: "Load a
     dataset first — go to Data Import."; loose-match trivial drift, record
     actual wording in Results).
   - NO metrics row (no text fragment `678` anywhere; zero
     `[data-testid="stMetric"]` elements), NO section headers ("Summary
     statistics" etc. not present), NO dataframes, NO charts.
   - The word `Traceback` does NOT appear on the page, and no Streamlit
     exception element (`[data-testid="stException"]`) exists.

## TC2 — Setup: load the built-in dataset, then reach Data Exploration via sidebar

1. In the SAME context (same tab is fine — the guard page has the sidebar),
   click the sidebar link `Data Import`.
2. Click the button `Load dataset`; wait (≤ ~15 s) for the success message
   containing `Loaded` and `678` (thousands-separated count, per last slice).
3. Click the sidebar link `Data Exploration` — **sidebar link, NOT goto**
   (a goto would drop the session and re-trigger the guard).
4. Expected: the guard info box is GONE (text `Load a dataset first` not
   present) and the exploration content renders (asserted in detail by
   TC3–TC6, which continue in this same tab).

## TC3 — Headline metrics: policies, exposure, claims, frequency

1. Continuing in the same tab, locate the metrics row.
2. Expected:
   - At least 4 `[data-testid="stMetric"]` elements are visible.
   - Metric labels covering the four concepts are visible (match loosely,
     e.g. `Policies`, `exposure`, `claims`, `frequency` — case/wording per
     implementation, record actual labels in Results).
   - Value spot-checks as visible text, loose on formatting: policies
     contains `678` and `013`; total claims contains `36` and `102`
     (36,102); overall frequency contains `0.10` (≈ 0.1007 — if rendered as
     a percentage `10.1`, note in Results; a value like `1.0` or `0.001` is
     a FAIL). Total exposure is asserted only as a non-empty numeric value
     here — its exact sum (~358,499) is proven engine-side in TC7.
   - Use `.first` for any fragment that also appears elsewhere on the page.

## TC4 — Summary statistics section

1. Same tab: find the header `Summary statistics` (`.first`).
2. Expected:
   - The header is visible and is followed by a dataframe container
     (`[data-testid="stDataFrame"]` — at least one on the page; do NOT
     assert cell text, per the glide-data-grid lesson).
   - The page renders quickly — the `expect` assertions here and in TC3
     resolve within the default timeout without any long spinner; if the
     screen takes more than ~10 s to settle after navigation, record it in
     Results as a performance smell (the hard < 5 s aggregate-speed
     guarantee is TC8, engine-level).

## TC5 — One-way claim frequency: default predictor "Area", chart + table

1. Same tab: find the header `One-way claim frequency` (loose fragment
   `One-way` if the final wording differs; `.first`).
2. Expected:
   - The header is visible; a selectbox widget is present in the section
     (`[data-testid="stSelectbox"]`). Do NOT try to read its value (BaseWeb
     combobox — not readable via get_by_text); the "defaults to Area"
     behaviour is proven by TC7 asserting the A–F levels of the exact call
     the UI issues by default.
   - A chart container is visible — assumed selector
     `[data-testid="stVegaLiteChart"]` (fallback `stArrowVegaLiteChart`;
     record which matched in Results). At least one exists on the page at
     this point.
   - An aggregated table (`stDataFrame`) accompanies the chart — the page's
     total `stDataFrame` count is now ≥ 2 (summary + one-way).
   - NO traceback / `stException` on the page.

## TC6 — Histograms and Correlations sections

1. Same tab: find the header `Histograms` (`.first`), then `Correlations`
   (`.first`).
2. Expected:
   - `Histograms` header visible with a column selectbox (`stSelectbox`
     count on the page ≥ 2 — predictor + histogram column; defaults only,
     no interaction) and a second chart container (total chart-container
     count ≥ 2).
   - `Correlations` header visible, followed by a table/matrix container
     (`stDataFrame` count now ≥ 3, or a styled table — record what renders).
   - Whole-page sanity: `Traceback` absent, no `stException`.

## TC7 — Engine truths: overall frequency, one-way Area levels, binning, error message

Engine-level (deterministic, automated). Run via `uv run python <tempfile.py>`
(or `.venv\Scripts\python.exe` in the sandbox) from the repo root:

```python
import numpy as np
from pricing_engine.data import load_dataset
from pricing_engine.exploration import (
    correlation_matrix, histogram, one_way_frequency,
    portfolio_frequency, summarize_portfolio,
)

df, spec = load_dataset("fremtpl2_freq")
assert len(df) == 678_013, len(df)

# Overall frequency: 36,102 claims / ~358,499 policy-years ≈ 0.1007
f = portfolio_frequency(df, spec)
assert 0.09 < f < 0.11, f

# Summary: one row per required column (target + offset + 9 predictors = 11)
summary = summarize_portfolio(df, spec)
assert len(summary) == len(spec.required_columns), (len(summary), spec.required_columns)

# One-way on Area: exactly the 6 bands A–F, positive exposure, finite frequency
ow = one_way_frequency(df, spec, "Area")
assert len(ow) == 6, ow
exposure_col = [c for c in ow.columns if "xposure" in c][0]
freq_col = [c for c in ow.columns if "req" in c.lower()][0]
assert (ow[exposure_col] > 0).all(), ow
assert np.isfinite(ow[freq_col]).all(), ow

# One-way on a numeric predictor: quantile-binned to <= 12 levels
ow_age = one_way_frequency(df, spec, "DrivAge")
assert len(ow_age) <= 12, len(ow_age)
assert (ow_age[exposure_col] > 0).all()

# Unknown predictor -> ValueError naming valid predictors
try:
    one_way_frequency(df, spec, "NotAColumn")
    raise SystemExit("FAIL: no ValueError raised")
except ValueError as e:
    assert "Area" in str(e), e  # names the valid predictors

# Histogram and correlations stay small (aggregates, never raw rows)
h_num = histogram(df, "DrivAge")
h_cat = histogram(df, "Area")
assert len(h_num) <= 30 and len(h_cat) == 6, (len(h_num), len(h_cat))
corr = correlation_matrix(df, spec)
assert corr.shape[0] == corr.shape[1] and corr.shape[0] >= 2, corr.shape
assert np.allclose(np.diag(corr), 1.0)

print("PASS", round(f, 4))
```

Expected: prints `PASS 0.1007` (frequency within ±0.01 tolerance band; exact
4-dp value may differ slightly — record it in Results).

## TC8 — Performance: full-portfolio aggregation under 5 seconds (engine)

1. Same mechanism as TC7 (separate script or appended; time AFTER the data is
   already loaded — loading is Data Import's cost, not Exploration's):

```python
import time
from pricing_engine.data import load_dataset
from pricing_engine.exploration import one_way_frequency, summarize_portfolio

df, spec = load_dataset("fremtpl2_freq")
t0 = time.perf_counter()
summarize_portfolio(df, spec)
for p in spec.predictors:
    one_way_frequency(df, spec, p)
elapsed = time.perf_counter() - t0
assert elapsed < 5.0, f"too slow: {elapsed:.2f}s"
print(f"PASS {elapsed:.2f}s")
```

2. Expected: prints `PASS` with elapsed well under 5 s — summary plus a
   one-way for EVERY predictor (harsher than the UI, which computes one) on
   the full 678k rows. Record the elapsed time in Results.

## TC9 — Changing the one-way predictor / histogram column — MANUAL / DEFERRED

Automating BaseWeb selectbox changes is brittle (previous slice deferred the
same interaction), so this is **specified for manual execution**:

1. With the dataset loaded, on Data Exploration change the one-way predictor
   from `Area` to `BonusMalus` (click + type + Enter if attempted in
   Playwright).
2. Expected: chart and table update to BonusMalus levels (≤ 12, since it is
   numeric and has > 12 distinct values); frequency should trend clearly
   upward with BonusMalus — the actuarial signal the BA called out.
3. Change the histogram column to `Exposure`; expected: distribution
   concentrated near 1.0, update is near-instant.
4. Record in Results whether this was executed manually or deferred.

## Execution notes

- Prerequisites: real `data/raw/freMTPL2freq.parquet` (7.5 MB) present;
  Playwright + Chromium installed (`uv run playwright install chromium`).
- Start the app once for the whole run:
  `uv run streamlit run app.py --server.port 8598 --server.headless true`
  (background; kill after). Give it a few seconds before the first goto.
- Run TC1 in a **fresh context**; then TC2→TC3→TC4→TC5→TC6 sequentially in
  **ONE tab of that context** (TC2's load feeds everything after it), using
  **sidebar links only** for navigation after the load — `page.goto` drops
  session state (proven last slice). TC7/TC8 are independent Python scripts
  (order-free). Scripts and temp files go in the session scratchpad, not the
  repo.
- Use `playwright.sync_api` with auto-waiting `expect(...)`; default timeout
  ~15000 ms for the post-`Load dataset` assertion in TC2, defaults elsewhere.
- Selector assumptions to verify once against the live DOM and record in
  Results: chart container `[data-testid="stVegaLiteChart"]` (fallback
  `stArrowVegaLiteChart`), metrics `[data-testid="stMetric"]`, tables
  `[data-testid="stDataFrame"]`, selectboxes `[data-testid="stSelectbox"]`,
  exceptions `[data-testid="stException"]`.
- Exact-text caveats: spec'd guard wording is "Load a dataset first — go to
  Data Import."; section headers "Summary statistics", "One-way claim
  frequency", "Histograms", "Correlations"; metric labels are
  implementation-chosen. Match loosely on distinctive fragments; wording
  drift is not a FAIL, a MISSING element/message or a traceback IS. Record
  actual wording, labels, number formatting (thousands separators,
  frequency as ratio vs percentage) in Results.
- TC7's column-name discovery (`exposure_col` / `freq_col` sniffing) is
  deliberate: the one-way frame's exact column names are an implementation
  choice — if the sniff fails, read the actual columns, adjust, and record
  the real names in Results.

## Results

- 2026-07-25 — **executed TCs ALL PASSED on the first full run** (Playwright
  1.61 / Chromium headless, app on port 8598, real data):
  - TC7 PASS — overall frequency **0.1007** (spot on the expected ≈0.1007);
    Area one-way = 6 levels, positive exposure, finite frequencies; DrivAge
    binned to ≤ 12; ValueError names the valid predictors; histogram/corr
    frames small; diagonal of corr = 1.
  - TC8 PASS — summary + one-way for ALL 9 predictors on the full 678k rows in
    **0.32 s** (limit 5 s).
  - TC1–TC6 PASS via UI. Metric labels: "Policies / Total exposure /
    Total claims / Claim frequency"; counts thousands-separated ("678,013",
    "36,102"); frequency rendered as ratio "0.1007". Chart container testid
    that matched: **`stVegaLiteChart`** (2 containers); 3 `stDataFrame`
    containers (summary, one-way expander table, correlations); guard wording
    exactly "Load a dataset first — go to Data Import."
- TC9 (selectbox changes) DEFERRED/manual per plan, same precedent as the
  Data Import slice's TC5.
- Implementation notes vs the plan: the one-way table sits inside an
  `st.expander` ("One-way table") — counted as a regular `stDataFrame`;
  charts are Altair (bundled with Streamlit) with `sort=None` so quantile-bin
  band order is preserved (plain `st.bar_chart` would re-sort labels
  alphabetically).
