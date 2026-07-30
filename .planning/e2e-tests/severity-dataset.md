# E2E — Severity dataset slice (V2 slice 1: DatasetSpec.kind + fremtpl2_sev + kind-aware screens)

Change under test: the app's second built-in dataset. Engine
(`pricing_engine/data.py`): `DatasetSpec` gains `kind` — `"frequency"`
(default) | `"severity"`; new registered dataset `fremtpl2_sev` whose loader
inner-joins the severity table (IDpol, ClaimAmount; 26,639 claims) with the
frequency table's nine rating factors (Area, VehPower, VehAge, DrivAge,
BonusMalus, VehBrand, VehGas, Density, Region) on IDpol — one row per claim,
orphan claims (no matching policy) dropped; spec: target `ClaimAmount`,
**offset None** (no exposure), the same nine predictors, `kind="severity"`.
`validate_portfolio` becomes kind-aware: a severity target must be **strictly
positive** (Gamma requirement) and wording generalizes ("claim amounts", not
"claim counts"). UI: the Data Import built-in selectbox now offers BOTH
datasets; Data Exploration wording is kind-aware (headline = average claim
amount, one-way = average claim amount per predictor level — the engine
aggregation is already offset-None-safe: dividing by row count IS the
per-claim average); Feature Engineering works unchanged via the spec, with NO
exposure-cap section (no offset); the Frequency Model screen (04) **guards**
against a severity dataset with a friendly pointer to the upcoming Severity
Model screen instead of fitting nonsense. The Severity Model screen itself is
slice 2 — NOT tested here.

BA scenarios (the user is an actuary who finished the V1 frequency workflow
and now starts the severity side of pure premium):

- As an actuary starting V2, I open Data Import and the built-in selectbox now
  offers a second dataset — freMTPL2 **severity**. I pick it, click Load, and
  get one row per claim: the success message and preview caption tell me
  26,444 rows × 11 columns, so I can see the join happened (26,639 claims
  minus 195 orphans without a matching policy) without doing it myself in
  pandas.
- As a learner, the loaded severity portfolio looks like a modelling dataset,
  not a raw claims file: ClaimAmount plus the SAME nine rating factors I know
  from the frequency workflow, so everything I learned about the predictors
  carries over.
- As an actuary, validation must now enforce the Gamma prerequisite: claim
  amounts must be strictly positive. The real dataset passes cleanly (its
  minimum is 1.0); a file with a zero or negative claim amount must be called
  out per finding — and the wording must talk about claim amounts, because a
  message about "claim counts" on a severity dataset would teach the wrong
  thing.
- As an actuary on Data Exploration, the headline number for a severity
  dataset is the **average claim amount** (≈ 2,266 for freMTPL2), NOT a
  "claim frequency" of 2,266 — that label on that number would be absurd and
  would instantly destroy trust in the screen. One-way charts show average
  claim amount per level of each rating factor — the severity analogue of the
  one-way frequency I used in V1.
- As a learner, I know real claim severities are heavy-tailed: the ClaimAmount
  histogram will be dominated by a huge right tail (max ≈ 4.08m vs median
  1,172) with visible fixed-compensation spikes (1204.00 alone is ~4.8k
  claims). The screen showing that honestly is CORRECT behaviour, not a bug —
  it is the motivation for the Gamma/log-link model in slice 2.
- As a user, Feature Engineering just works on the severity dataset — binning
  DrivAge, log-transforming Density, the current-model-spec preview — because
  everything is spec-driven. There is NO exposure-cap prompt: severity has no
  exposure, and offering to cap a column that does not exist would be a
  spec-leak bug.
- As a user who loads the severity dataset and then clicks Frequency Model
  out of V1 habit, I get a friendly pointer to the Severity Model screen —
  not a Poisson fit of claim amounts (statistically meaningless) and not a
  traceback. The guard teaches; it doesn't just block.
- As a returning V1 user, nothing regresses: the frequency dataset still
  loads by default with one click, still validates clean, and Exploration on
  it still says claim frequency ≈ 0.1007.

Test Agent notes from the BA interview: the UI exists, so cases run via
**Playwright (Python sync API)** against the running Streamlit app; all
numeric truths (join counts, ClaimAmount stats, validation wording) are
proven at the **engine level** where they are deterministic. Mechanics carry
over the hard-won lessons from `data-import.md` / `data-exploration.md`
Results:

- App started headless on port 8598:
  `uv run streamlit run app.py --server.port 8598 --server.headless true`
  from the repo root; BOTH real Parquet files present
  (`data/raw/freMTPL2freq.parquet`, `data/raw/freMTPL2sev.parquet`).
  **Never delete or touch `data/workbench.db`.**
- **Session state is per browser tab; `page.goto` after loading DROPS it**
  (proven live in the Data Import slice). All post-load UI TCs run in ONE
  tab, navigating via **sidebar links only** (`app`, `Data Import`,
  `Data Exploration`, `Feature Engineering`, `Frequency Model`).
- **The severity dataset is NOT the selectbox default** (freMTPL2 frequency
  is first in the registry), and BaseWeb selectbox automation is exactly the
  interaction both previous slices deferred. Explicit decision for this
  slice, mirroring the data-import precedent (defaults automated, remapping
  manual): the severity **load itself is proven engine-level (TC2)**; the UI
  severity load (TC6) attempts the ONE minimal sanctioned interaction —
  click the combobox, type a distinctive fragment (`severity`), press Enter —
  as **best-effort automation**. If that interaction fails after a reasonable
  attempt, TC6 **falls back to manual**, and the UI TCs chained on it
  (TC7–TC9) are executed manually in the same sitting (they are pure
  click-and-read once the dataset is loaded). Record in Results which route
  was taken. Do NOT hunt dropdown DOM beyond click + type + Enter.
- Counts render thousands-separated ("26,444") — match loosely on
  distinctive fragments (`26,444` or `26` + `444`), record actual formatting
  in Results. Fragments appearing twice need `.first` under strict mode.
- Known-good selectors from previous runs: metrics `[data-testid="stMetric"]`,
  tables `[data-testid="stDataFrame"]`, charts `[data-testid="stVegaLiteChart"]`,
  selectboxes `[data-testid="stSelectbox"]`, exceptions
  `[data-testid="stException"]`. Combobox current values are NOT readable via
  `get_by_text`; glide-data-grid cell text is NOT assertable (hidden header
  cells also leak column names into the DOM — avoid `get_by_text` for table
  content).
- Exact labels/wording (severity dataset label, metric labels, one-way
  section header, guard message) are implementation-chosen. TCs name the
  distinctive fragments; wording drift is not a FAIL, a MISSING
  element/section or a traceback IS. Record actual wording in Results.
- The heavy right tail of ClaimAmount (max 4,075,400.56 vs median 1,172)
  makes the default 30-bin histogram look degenerate (nearly everything in
  bin 1). That is an EXPECTED artifact of real severity data, explicitly not
  a failure — note it in Results if observed; a log-scale/binning improvement
  would be a future UX item, not a defect of this slice.

## TC1 — Engine: registry and spec truths (kind, target, no offset)

Engine-level (deterministic, automated). Run via `uv run python <tempfile.py>`
from the repo root:

```python
from pricing_engine.data import DATASET_REGISTRY, list_datasets

specs = {s.name: s for s in list_datasets()}
assert set(specs) >= {"fremtpl2_freq", "fremtpl2_sev"}, specs.keys()

freq, sev = specs["fremtpl2_freq"], specs["fremtpl2_sev"]

# kind: new field, correct on both, frequency stays the default
assert freq.kind == "frequency", freq.kind
assert sev.kind == "severity", sev.kind

# severity spec shape: ClaimAmount target, NO offset, same nine predictors
assert sev.target == "ClaimAmount", sev.target
assert sev.offset is None, sev.offset
assert sev.predictors == freq.predictors, (sev.predictors, freq.predictors)
assert len(sev.predictors) == 9

# required_columns must NOT contain an offset slot
assert sev.required_columns == ("ClaimAmount", *sev.predictors)

# frequency spec untouched (regression)
assert freq.target == "ClaimNb" and freq.offset == "Exposure"
assert "severity" in sev.label.lower(), sev.label
print("PASS", sev.label)
```

Expected: prints `PASS` plus the severity label (record the label in
Results — the UI TCs match on its fragments).

## TC2 — Engine: severity load — join, orphan drop, ClaimAmount truths, friendly errors

Engine-level. Same mechanism (the load takes a few seconds — it reads both
Parquet files and joins):

```python
from pricing_engine.data import load_dataset, load_fremtpl2_sev

df, spec = load_dataset("fremtpl2_sev")

# Join result: 26,639 severity rows minus 195 orphans = 26,444; 11 columns
assert len(df) == 26_444, len(df)
assert df.shape[1] == 11, list(df.columns)  # IDpol + ClaimAmount + 9 factors
for col in spec.required_columns:
    assert col in df.columns, col

# One row per claim, rating factors fully populated by the inner join
assert int(df[list(spec.required_columns)].isna().sum().sum()) == 0

# ClaimAmount truths (verified against the raw data)
ca = df["ClaimAmount"]
assert float(ca.min()) == 1.0, ca.min()
assert abs(float(ca.max()) - 4_075_400.56) < 0.01, ca.max()
assert 2_260 < float(ca.mean()) < 2_270, ca.mean()      # ≈ 2,265.5 on the JOINED table (raw table: 2,278.5 — orphans shift the mean)
assert 1_150 < float(ca.median()) < 1_190, ca.median()  # 1,172
assert (ca > 0).all()  # Gamma-ready: strictly positive

# Fixed-compensation spikes (real-data fingerprint of a correct join)
counts = ca.value_counts()
assert counts.loc[1204.00] == 4_792, counts.loc[1204.00]
assert counts.loc[1128.12] == 3_056, counts.loc[1128.12]

# Missing severity parquet -> friendly curl hint, no traceback-as-message
try:
    load_fremtpl2_sev("data/raw/does_not_exist.parquet")
    raise SystemExit("FAIL: no exception raised")
except FileNotFoundError as e:
    assert "curl" in str(e) and "41215" in str(e), e

# Frequency regression: still loads, still frequency kind
df_f, spec_f = load_dataset("fremtpl2_freq")
assert len(df_f) == 678_013 and spec_f.kind == "frequency"
print("PASS", df.shape)
```

Expected: prints `PASS (26444, 11)`. If the loader drops IDpol (10 columns)
that is an acceptable implementation choice — adjust the column-count
assertion, record it in Results, and make sure the UI caption TC (TC6) uses
the matching count.

## TC3 — Engine: severity-aware validation — strictly positive, wording generalized

Engine-level:

```python
import pandas as pd
from pricing_engine.data import load_dataset, validate_portfolio

df, spec = load_dataset("fremtpl2_sev")

# 1. Real severity data validates CLEAN (min ClaimAmount is 1.0)
assert validate_portfolio(df, spec) == [], validate_portfolio(df, spec)

# 2. Zero / negative claim amounts -> finding(s); wording talks claim AMOUNTS
broken = df.head(10).copy()
broken.iloc[0, broken.columns.get_loc("ClaimAmount")] = 0.0
broken.iloc[1, broken.columns.get_loc("ClaimAmount")] = -50.0
findings = validate_portfolio(broken, spec)
assert findings, "zero/negative ClaimAmount must be flagged for severity kind"
joined = " | ".join(findings)
assert "ClaimAmount" in joined, joined
# Both offending rows are covered (one 'non-positive: 2' finding or two findings)
assert "2" in joined or len(findings) >= 2, joined
assert "claim count" not in joined.lower(), joined  # wording generalized
# Distinctive severity wording — strictly positive / claim amounts (loose)
assert "positive" in joined.lower(), joined

# 3. Frequency behaviour unchanged: zero claim COUNTS remain valid
df_f, spec_f = load_dataset("fremtpl2_freq")
# NOTE (execution finding): the freq parquet is sorted claims-first, so
# head(1000) contains NO zeros — sample zero-count rows explicitly instead
sample = df_f[df_f["ClaimNb"] == 0].head(1000)
assert (sample["ClaimNb"] == 0).all()  # zeros present…
zero_findings = [f for f in validate_portfolio(sample, spec_f) if "ClaimNb" in f]
assert zero_findings == [], zero_findings  # …and NOT flagged for frequency kind
print("PASS", findings)
```

Expected: prints `PASS` plus the actual severity findings — record their
exact wording in Results (the wording is the teaching surface; only a missing
finding or "claim count" wording on a severity dataset is a FAIL).

## TC4 — Engine: exploration aggregates are per-claim averages (offset-None path)

Engine-level — this proves the numbers behind the kind-aware Exploration
screen (the UI TC7 then only asserts rendered text):

```python
import numpy as np
from pricing_engine.data import load_dataset
from pricing_engine.exploration import (
    histogram, one_way_frequency, portfolio_frequency, summarize_portfolio,
)

df, spec = load_dataset("fremtpl2_sev")

# Headline: with offset=None the "frequency" IS the average claim amount
avg = portfolio_frequency(df, spec)
assert 2_260 < avg < 2_270, avg  # ≈ 2,265.5 (joined; raw pre-join table: 2,278.5)

# Summary: one row per required column = target + 9 predictors = 10 (no offset)
summary = summarize_portfolio(df, spec)
assert len(summary) == len(spec.required_columns) == 10, len(summary)

# One-way on Area: 6 levels A–F, denominator = claim count per level,
# so the metric column is the per-level AVERAGE claim amount
ow = one_way_frequency(df, spec, "Area")
assert len(ow) == 6, ow
metric_col = [c for c in ow.columns if "req" in c.lower() or "amount" in c.lower()][0]
assert np.isfinite(ow[metric_col]).all() and (ow[metric_col] > 0).all(), ow
# Per-level averages must bracket sane severity values, not frequencies
assert ow[metric_col].between(500, 20_000).all(), ow[metric_col]
# No exposure column in the offset-None aggregation
assert not any("xposure" in c for c in ow.columns), ow.columns

# Numeric predictor still quantile-bins to <= 12 levels
assert len(one_way_frequency(df, spec, "DrivAge")) <= 12

# ClaimAmount histogram: 30 bins, heavy tail -> first bin dominates (EXPECTED)
h = histogram(df, "ClaimAmount")
assert len(h) <= 30
count_col = [c for c in h.columns if "count" in c.lower()][0]
assert h[count_col].max() / h[count_col].sum() > 0.9  # the known tail artifact
print("PASS", round(avg, 1))
```

Expected: prints `PASS 2278.5` (±, record exact value in Results). If the
one-way metric column has been renamed for severity (e.g. "avg_claim_amount"),
the sniff adjusts — record the real column names in Results.

## TC5 — UI regression: default (frequency) path unchanged with two datasets registered

1. Open a **new browser context**, `page.goto("http://localhost:8598/Data_Import")`.
2. Confirm "Built-in dataset" is the selected source and a dataset selectbox
   is present (`[data-testid="stSelectbox"]` ≥ 1). Do NOT read its value
   (BaseWeb); the default being the frequency dataset is proven by step 3.
3. Click `Load dataset` with **defaults untouched**.
4. Expected (≤ ~15 s):
   - Success message containing `Loaded`, the frequency label fragment
     `frequency`, and `678` + `013` — adding a second registry entry must NOT
     have changed the default.
   - Validation shows the clean-success message
     (`No issues found — portfolio is ready for modelling.`), no warnings.
   - No `Traceback` text, no `[data-testid="stException"]`.

## TC6 — UI: select and load the severity dataset (best-effort selectbox automation)

The ONE sanctioned BaseWeb interaction (see notes): in the SAME tab as TC5:

1. Click the built-in dataset combobox, type `severity`, press `Enter`.
   (If the combobox filters options this selects the severity entry; give it
   one retry. If it does not take after a reasonable attempt, STOP automating
   this interaction — mark TC6–TC9 **manual** and execute them by hand per
   the same steps, recording the route in Results.)
2. Click `Load dataset`.
3. Expected (≤ ~15 s — the join reads both Parquet files):
   - Success message containing `Loaded`, the severity label fragment
     `severity`, and the row count `26,444` (loose: `26` + `444`).
   - Preview section: dataframe grid + caption containing `26,444 rows` and
     `11 columns` (use the column count TC2 confirmed; loose-match
     thousands separators).
   - Validation report: the clean-success message, NO warning blocks — the
     real severity data has strictly positive amounts and no missing values
     in required columns (proven in TC2/TC3).
   - No `Traceback` / `stException`.
4. Optional follow-up: sidebar link `app` — Home workflow status names the
   severity dataset label and `26,444`.

## TC7 — UI: Data Exploration is kind-aware on the severity dataset

Same tab as TC6 (severity dataset in session), navigate via the sidebar link
`Data Exploration` — **never `page.goto`**:

1. Expected — headline metrics:
   - Metric row present (`[data-testid="stMetric"]` ≥ 2).
   - A metric whose label contains the fragment `claim amount` (kind-aware
     wording — e.g. "Average claim amount"); its value contains `2,266`
     (loose: `2` `266`; ≈ 2,265.5 per TC4 — a value near `0.10` here would
     be a FAIL: that is the frequency-wording bug this slice exists to
     prevent).
   - A claims-count metric containing `26,444` (loose).
   - The frequency-only concepts are ABSENT: no metric labelled with the
     fragment `frequency`, no `Total exposure` metric (there is no exposure).
2. Expected — sections:
   - The one-way section header contains `claim amount` (e.g. "One-way
     average claim amount"), NOT `claim frequency`; a selectbox, a chart
     container (`stVegaLiteChart`), and a table accompany it as in V1.
   - `Summary statistics`, `Histograms`, `Correlations` sections render with
     their tables/charts (same structural assertions as the
     data-exploration slice: `stDataFrame` ≥ 3 in total, chart containers
     ≥ 2).
3. Whole-page sanity: no `Traceback`, no `stException`. If the default
   histogram column is ClaimAmount and the chart looks like one giant bar —
   that is the EXPECTED heavy-tail artifact (see notes); record it, do not
   fail it.

## TC8 — UI: Feature Engineering unchanged, NO exposure-cap section

Same tab, sidebar link `Feature Engineering`:

1. Expected:
   - The page renders its normal spec-driven sections: `Variables`,
     `Binning`, `Log transform`, `Encoding`, `Current model specification`
     headers visible (`.first` where needed).
   - The `Exposure` subheader and the `Cap` button (label fragment
     `Cap` + `at 1.0`) are **ABSENT** — the severity spec has no offset, so
     the exposure-cap prompt must not appear (text fragment
     `Cap Exposure at 1.0` nowhere on the page).
   - No `Traceback` / `stException`.
2. Structural only — actually binning/logging variables uses BaseWeb widgets
   and stays in the deferred/manual bucket (TC10); the spec-driven engine
   path is unchanged code covered by the existing unit suite.

## TC9 — UI: Frequency Model screen guards against the severity dataset

Same tab, sidebar link `Frequency Model`:

1. Expected:
   - A friendly guard message (info/warning box) whose text contains the
     fragments `severity` and `Severity Model` — pointing the user to the
     (upcoming) Severity Model screen.
   - The frequency fitting UI does NOT render: no `Fit` button, no formula
     preview, no family selectbox, no stepwise-selection section
     (distinctive fragment check: the page must not offer to fit — assert
     the fit button role/name from V1 is absent).
   - No `Traceback` / `stException` — and emphatically no Poisson fit output.
2. (The reverse guard — Severity Model pointing frequency datasets away — is
   slice 2, screen 07 does not exist yet; out of scope here.)

## TC10 — Deferred/manual: selectbox variations on the severity dataset

BaseWeb selectbox changes beyond TC6's single sanctioned interaction remain
**manual**, same precedent as data-import TC5 / data-exploration TC9:

1. With the severity dataset loaded, on Data Exploration change the one-way
   predictor from `Area` to `VehBrand` and to `BonusMalus`; expected: chart
   and table update to average claim amount per level (≤ 12 levels for
   numeric predictors), values in the hundreds-to-thousands range.
2. Change the histogram column to `ClaimAmount` (if not the default);
   expected: the heavy-tail artifact described in the notes — dominated
   first bin. Confirm it renders fast and without error; visual usefulness
   is a known limitation, not a defect.
3. On Feature Engineering, bin `DrivAge` and log-transform `Density`;
   expected: identical behaviour to the frequency dataset (spec-driven),
   `Current model specification` updates accordingly.
4. Switch back: on Data Import re-select the **frequency** dataset and load;
   expected: Exploration reverts to frequency wording (claim frequency
   ≈ 0.1007, Total exposure metric returns) and the Frequency Model screen
   renders its normal fitting UI again (guard gone) — kind-awareness is
   driven by the ACTIVE spec, not sticky state.
5. Record in Results whether executed manually or deferred.

## Execution notes

- Prerequisites: BOTH real Parquet files in `data/raw/`
  (`freMTPL2freq.parquet` ~7.5 MB, `freMTPL2sev.parquet` — fetch via the
  README curl commands / OpenML 41214 + 41215 if missing); Playwright +
  Chromium installed. Do not touch `data/workbench.db`.
- Engine TCs (TC1–TC4) are independent Python scripts run from the repo root
  (`uv run python <tempfile.py>`); scripts go in the session scratchpad, not
  the repo. Run them FIRST — TC2's actual column count and TC1's actual label
  feed the UI assertions in TC6.
- Start the app once:
  `uv run streamlit run app.py --server.port 8598 --server.headless true`
  (background; kill after). UI TCs run TC5→TC6→TC7→TC8→TC9 sequentially in
  **ONE tab of one context** (TC6's severity load feeds TC7–TC9), navigating
  via **sidebar links only** after any load; `page.goto` drops session state
  (proven twice now). Default timeout ~15000 ms after each `Load dataset`
  click.
- **TC6 selectbox route:** click combobox → type `severity` → Enter, one
  retry max. On failure, TC6–TC9 flip to manual execution (they are
  click-and-read once loaded) — record the route in Results either way. The
  numeric substance is already locked in by TC1–TC4 regardless.
- Exact-text caveats: the severity dataset label, metric labels, one-way
  header, validation wording, and guard wording are implementation-chosen —
  match loosely on the distinctive fragments named per TC (`severity`,
  `claim amount`, `26,444`, `2,266`, `Severity Model`), record actuals in
  Results. Wording drift is not a FAIL; a missing section/finding, frequency
  wording on severity data (e.g. a "Claim frequency" metric showing 2,278),
  an exposure-cap prompt without an offset, a fittable Frequency Model page,
  or any traceback IS.
- The ClaimAmount-histogram tail artifact and the dropped-IDpol column-count
  variance are pre-authorized observations, not failures — see notes.

## Results

Executed 2026-07-29 via the committed runner `e2e/e2e_severity_dataset.py`
(engine TCs inline, UI TCs via Playwright against port 8598). **TC1–TC9 all
PASSED; TC10 deferred/manual per plan.**

- TC1 PASS — severity label: `freMTPL2 — French motor TPL, severity (26.4k
  claims)`; kind field present, frequency default intact.
- TC2 PASS — joined shape **(26,444 × 11)**, IDpol kept; spikes exact
  (1204.00 → 4,792; 1128.12 → 3,056); curl/41215 hint on missing file.
  **Correction found during execution:** the briefed mean ≈ 2,278.5 was the
  RAW severity table; the joined table's mean is **2,265.51** (orphan drop
  shifts it). Doc + assertions updated to the joined truth; min 1.0 / max
  4,075,400.56 / median 1,172 unchanged by the join.
- TC3 PASS — real data validates clean; broken frame yields exactly:
  `Target 'ClaimAmount' has 2 non-positive value(s) — claim amounts must be
  positive` (amounts wording, no "claim counts"). Frequency zeros not
  flagged. **Execution finding:** the freq parquet is sorted claims-first, so
  `head(1000)` contains no zero-claim rows — the snippet now samples
  `ClaimNb == 0` rows explicitly.
- TC4 PASS — headline average 2,265.5; summary 10 rows; one-way Area 6
  levels, per-level averages within 500–20,000, no exposure column; DrivAge
  binned ≤ 12; ClaimAmount histogram first bin > 90% (the expected
  heavy-tail artifact — confirmed, not a defect).
- TC5 PASS — frequency default unchanged: one-click load, `678,013 rows`,
  clean validation.
- TC6 PASS — **automated combobox route worked first try** (click + type
  `severity` + Enter): success message `… severity (26.4k claims): 26,444
  rows`, preview `26,444 rows × 11 columns`, clean validation; Home shows
  the severity label + 26,444.
- TC7 PASS — metrics: `Claims 26,444` / `Total claim amount` / `Average
  claim amount 2,266`; no `Claim frequency`, no `Total exposure` metric
  (implementation dropped the exposure slot entirely for severity, per this
  TC); one-way header `One-way average claim amount`; Summary/Histograms/
  Correlations all render (charts ≥ 2 after expect-before-count — the
  count-without-expect lesson bit once more during scripting).
- TC8 PASS — Variables/Binning/Log transform/Encoding/Current model
  specification render; no `Cap Exposure at 1.0` button, no exposure-cap
  caption anywhere.
- TC9 PASS — guard text: `The active dataset is a severity dataset (claim
  amounts) — use the Severity Model screen to fit it.`; no Fit button, no
  Model setup, no Variable selection section, no exception.
- TC10 DEFERRED/manual per plan (selectbox variations + switch-back check).
