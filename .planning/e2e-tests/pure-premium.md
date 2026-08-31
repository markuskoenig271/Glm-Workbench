# E2E — Pure Premium quote calculator (V3 slice 3: predict_pure_premium + screen 08)

Change under test: new page `pages/08_Pure_Premium.py` (screen 9 in
ui_screens.md) — the quote calculator — over new engine functions in
`pricing_engine/prediction.py`: `predict_pure_premium(freq_model, sev_model,
policies, spec)` returns a copy with `expected_frequency` (annual, offset-free
rate), `expected_claim_amount`, `pure_premium = rate × amount` and
`expected_loss = pure_premium × Exposure`; the missing-predictor ValueError
covers the **union** of the spec's predictors and BOTH models' formula columns
(`formula_columns` / `required_columns` helpers). `premium_breakdown` decomposes
one quote exactly: premium = base × one combined factor per predictor
(categorical reference = first sorted level, numeric reference = the
**portfolio median** — BA gap G4 decision, so a median profile's factors are
all ≈ 1.0). Screen 08 guards IN ORDER: (1) no dataset → `Load a dataset first
— go to Data Import.`; (2) wrong kind → `The active dataset is a severity
dataset (claim amounts) — pure premium is quoted per policy. Load the
frequency dataset in Data Import.` (this guard precedes the model checks);
(3) both models missing → `Pure premium needs both models in session. Fit or
load a frequency model on Frequency Model, and a severity model on Severity
Model (load the severity dataset there first, then reload the frequency
dataset — model slots survive the switch).`; only frequency missing → `No
frequency model in session — fit or load one on Frequency Model.`; only
severity missing → the ROUND-TRIP text (BA gap G2 — no dead end): `No severity
model in session — load the severity dataset in Data Import, fit or load a
severity model on Severity Model, then reload the frequency dataset (model
slots survive the switch).`; (4) engineered columns missing → hint starting
`The models need column(s) not present in the loaded portfolio:`. Quote
section: caption `Take out a policy: defaults describe the median policy —
change the inputs and get the annual risk premium.`; one widget per required
column (numeric → number_input at the portfolio median, categorical →
selectbox of sorted levels; keys `pp_<col>`) plus `Exposure (policy-years)`
default 1.0 (key `pp_exposure`); button `Get quote` → 3 metrics `Expected
claim frequency` / `Expected claim amount` / `Risk premium` (headline —
expected_loss for the entered exposure), caption `Risk premium only — no
expenses, loadings, or profit. Assumes claim counts and claim sizes are
independent given the rating factors.`, then `Premium breakdown` table
(columns Rating factor / Your value / Frequency relativity / Severity
relativity / Combined) under a reference-premium caption (`Reference premium
{base} × the combined factors below × exposure reproduces the quote
exactly` … `The reference policy is artificial` …). Batch section `Portfolio
premiums`: button `Compute premiums for loaded portfolio` → session keys
`premium_batch` / `premium_batch_csv` (ISOLATED from screen 06's
`predictions`/`predictions_kind`), metrics `Total expected loss` / `Total
expected claims` / `Average annual premium`, the honesty caption (`No
observed-cost comparison is shown` … `covers only ~73% of the claims` …
`about −1.5% below the observed claim total` — BA gap G1 correction: NO
observed-cost metric exists on this page), the `Tariff spread` percentile
table (p25/p50/p75/p95/p99), a 20-row preview, and `Download premiums CSV`
(`pure_premium_predictions.csv`). Home (`app.py`) now shows per-slot status
captions (`{Kind} model: none — fit or load one on {screen}.` /
`{Kind} model: {source} ({family}, AIC {aic:,.0f})`) and, with both slots
filled, the success line `Both models in session — ready to quote on Pure
Premium.` No new storage in this slice — quotes and batches are not
persisted; fits still auto-save via slice 2.

BA scenarios (gap numbers G1–G8 as in the BA report):

- S1 — Quote a policy: defaults ARE the median policy; `Get quote` returns
  frequency, claim amount and the headline risk premium with the
  risk-premium-only honesty caption.
- S2 — Premium breakdown: base × Π(combined factors) reproduces the quote
  EXACTLY (log links, no interactions); numerics rebase at the portfolio
  median (G4) so the median profile's factors are all ≈ 1.0.
- S3 — Guard ladder: every dead end signposted, in the documented order; the
  severity-missing guard spells out the dataset round trip (G2) and the kind
  guard fires before the model guards even when both models are in session.
- S4 — Portfolio batch is HONEST: totals + average + percentile spread, NO
  observed-cost comparison (G1 — ~73% severity coverage makes it dishonest),
  the −1.5% Gamma-gap caveat, CSV download.
- S5 — Cross-checkable numbers: total expected claims matches the Prediction
  screen's 36,102 anchor; total expected loss lands in the plausible
  ≈ €80M band (36,102 × mean amount ≈ 2,231).
- S6 — Isolation: screen 06's batch never shows on 08 and the premium batch
  never alters 06 (`premium_batch` vs `predictions` session keys).
- S7 — Either route fills a slot: a LOADED severity model (slice 2) quotes
  exactly like a fitted one; Home tracks per-slot status and shows the
  ready-to-quote line only when both slots are filled.
- S8 — Regression: unit suite (132 tests, 75% gate), lint/type checks, and
  the existing runners stay green; Home's new captions are additive.

Test Agent notes from the BA interview: mechanics per `e2e/README.md` /
`e2e/harness.py` and the slice-1/2 plans (`per-kind-model-slots.md`,
`model-persistence.md`):

- Engine truths FIRST (TC1–TC2), inline at the top of the committed runner.
  Unlike slice 2 they touch NO database — `predict_pure_premium` /
  `premium_breakdown` are pure — so **no `GLM_DB_PATH`/`GLM_MODELS_DIR`
  juggling is needed**; the two real fits (Poisson ~12 s, Gamma ~2 s) are
  in-process and reused across TC1/TC2. The TC10 DB snapshot still runs
  BEFORE the app launches, and must call `storage.connect(DB_PATH)` first
  (slice-2 Results lesson: raw sqlite on a not-yet-migrated DB sees no
  `model_path`).
- App headless on port 8598 via `e2e/harness.py`. TWO contexts, ONE tab
  each, sidebar links only after the first load: context A runs TC3–TC8
  (guard ladder → two fits → quote → batch → isolation), context B runs TC9
  (the sanctioned fresh-session `goto` — a returning user quoting with a
  LOADED severity model; its Load precondition is guaranteed because TC5's
  gamma fit auto-saved a pickle earlier in the same execution).
- Defaults-only widgets + the ONE sanctioned combobox route (click the first
  `[data-testid="stSelectbox"]` on Data Import, type `severity` /
  `frequency`, Enter) — used six times (TC3 ×2, TC5 ×2, TC9 ×2). The quote
  widgets are NEVER typed into: changing `BonusMalus` via the number_input
  is beyond the sanctioned interaction set (screen-06 precedent), so the
  UI widget-change variation is deferred to TC12 and its truth
  (monotonicity, exposure-halving) is asserted at the engine level in TC1.
  Screen 08 carries 4 selectboxes of its own — never address selectboxes by
  bare index anywhere; the sanctioned route only ever runs on Data Import.
- README lesson honored throughout: `expect` the `stMetric` / `stDataFrame` /
  `stNumberInput` / `stSelectbox` LOCATOR itself (or a stable text on the
  same render) before ANY `.count()` — widget mounts lag the text deltas.
- Text-overlap TRAPS specific to this page (Playwright `get_by_text` is
  case-insensitive substring): the model caption contains `expected claim
  frequency × expected claim amount` and the honesty caption contains
  `Risk premium` — so the quote metrics `Expected claim frequency` /
  `Expected claim amount` / `Risk premium` must be asserted INSIDE
  `[data-testid="stMetric"]` locators (filter `has_text`), never via bare
  page text. Same for the batch metrics (`Average annual premium` vs the
  spread caption's `annual premium percentiles`). Guard absences use
  fragments unique to one guard (`Pure premium needs both models`, `No
  frequency model in session`, `No severity model in session`) — NOT
  `model slots survive the switch`, which appears in two guards, and NOT
  `fit or load`, which also appears in the Home captions.
- Canvas TRAP: `st.dataframe` renders in a canvas grid — the breakdown
  table's column headers (`Rating factor` … `Combined`), the percentile
  labels (`p25` … `p99`) and all cell values are NOT scrapable DOM text.
  Tables are asserted by `stDataFrame` presence/count; their contents are
  TC1/TC2 engine truths.
- Character TRAP: the page source uses `×` (U+00D7), `·` (U+00B7), `—`
  (em dash) and `−1.5%` with a REAL MINUS SIGN (U+2212) — runner fragments
  must copy these characters exactly from `pages/08_Pure_Premium.py`.
- Exact texts asserted VERBATIM: the five guards, the take-out caption, the
  Home none-captions and the Home success line (all quoted in the header
  paragraph). Everything else is distinctive fragments with actuals
  recorded. Metric VALUES are never scraped from the UI — 36,102 stays the
  only UI numeric anchor (on 06, and on 08 only AFTER its own batch).

## TC1 — Engine: real-data anchors — batch totals, exposure-halving, BonusMalus monotonicity (S1, S4, S5)

Engine-level, deterministic; two real fits (~15 s total), no DB touched:

```python
import numpy as np
import pandas as pd

from pricing_engine import prediction
from pricing_engine.data import load_dataset
from pricing_engine.glm import build_formula, fit_frequency_glm, fit_severity_glm

freq_df, freq_spec = load_dataset("fremtpl2_freq")
sev_df, sev_spec = load_dataset("fremtpl2_sev")
assert len(freq_df) == 678_013 and freq_spec.kind == "frequency"
assert len(sev_df) == 26_444 and sev_spec.kind == "severity"

freq_model = fit_frequency_glm(
    freq_df, build_formula(freq_spec), offset_column=freq_spec.offset
)  # poisson, ~12 s — the same model the UI fits on 04
sev_model = fit_severity_glm(sev_df, build_formula(sev_spec))  # gamma, ~2 s

# column helpers: both formulas are the plain spec main effects, and the
# dtype split pins screen 08's widget layout (5 numeric + 4 categorical)
required = prediction.required_columns(freq_model, sev_model, freq_spec)
assert required == list(freq_spec.predictors), required
assert prediction.formula_columns(freq_model) == list(freq_spec.predictors)
numeric = [c for c in required if pd.api.types.is_numeric_dtype(freq_df[c])]
assert numeric == ["VehPower", "VehAge", "DrivAge", "BonusMalus", "Density"], numeric

# full-portfolio batch — the numbers behind 08's batch metrics
batch = prediction.predict_pure_premium(freq_model, sev_model, freq_df, freq_spec)
for col in ("expected_frequency", "expected_claim_amount", "pure_premium", "expected_loss"):
    assert col in batch.columns and col not in freq_df.columns  # copy, not mutation
assert np.allclose(
    batch["pure_premium"], batch["expected_frequency"] * batch["expected_claim_amount"]
)
assert np.allclose(batch["expected_loss"], batch["pure_premium"] * batch["Exposure"])
assert (batch["pure_premium"] > 0).all() and np.isfinite(batch["pure_premium"]).all()

total_claims = float((batch["expected_frequency"] * batch["Exposure"]).sum())
assert abs(total_claims - 36_102) < 400, total_claims  # 06's in-sample anchor (S5)
mean_amount = float(batch["expected_claim_amount"].mean())
assert 2_100 < mean_amount < 2_400, mean_amount        # ≈ 2,230.9 — record actual
total_loss = float(batch["expected_loss"].sum())
assert 6.5e7 < total_loss < 9.5e7, total_loss          # ≈ 36,102 × ~2,231 ≈ €80M
spread = np.percentile(batch["pure_premium"], [25, 50, 75, 95, 99])
assert spread[0] > 0 and np.all(np.diff(spread) > 0)   # 08's tariff-spread rows

# the median policy — EXACTLY screen 08's widget defaults
profile: dict[str, object] = {}
for col in required:
    s = freq_df[col]
    profile[col] = (
        float(s.median())
        if pd.api.types.is_numeric_dtype(s)
        else sorted(str(v) for v in s.dropna().unique())[0]
    )
row = pd.DataFrame([profile]).assign(Exposure=1.0, ClaimNb=0)
quote = prediction.predict_pure_premium(freq_model, sev_model, row, freq_spec)
premium_1y = float(quote["expected_loss"].iloc[0])
assert premium_1y == float(quote["pure_premium"].iloc[0])  # exposure 1.0

# exposure 0.5 → same rate and amount, EXACTLY half the headline premium
half = prediction.predict_pure_premium(freq_model, sev_model, row.assign(Exposure=0.5), freq_spec)
assert float(half["pure_premium"].iloc[0]) == float(quote["pure_premium"].iloc[0])
assert float(half["expected_loss"].iloc[0]) == 0.5 * premium_1y  # exact in fp

# BonusMalus up → premium STRICTLY up (both models load positively on it)
premiums = [
    float(
        prediction.predict_pure_premium(
            freq_model, sev_model, row.assign(BonusMalus=float(v)), freq_spec
        )["pure_premium"].iloc[0]
    )
    for v in (50, 75, 100, 150)
]
assert all(a < b for a, b in zip(premiums, premiums[1:])), premiums
print("PASS", round(total_claims), round(mean_amount, 1), round(total_loss / 1e6, 1))
```

Expected: prints `PASS 36102-ish 2230.9-ish 80-ish` — record actuals. A
total-claims drift beyond ±400, a mean amount or loss total outside the
bands, a non-halved premium at exposure 0.5, or a non-monotone BonusMalus
sequence is a FAIL. Keep `freq_model`/`sev_model`/`row`/`quote` in scope for
TC2.

## TC2 — Engine: breakdown identity on a real profile + median baseline + union ValueError (S2, G4)

Same process, reusing TC1's fitted models:

```python
# breakdown identity on a REAL profile (portfolio row 0 — non-reference levels)
real = freq_df.iloc[[0]].copy()
base, factors = prediction.premium_breakdown(freq_model, sev_model, real, freq_df, freq_spec)
assert list(factors["predictor"]) == required
assert np.allclose(
    factors["combined_factor"], factors["frequency_factor"] * factors["severity_factor"]
)
premium = float(
    prediction.predict_pure_premium(freq_model, sev_model, real, freq_spec)[
        "pure_premium"
    ].iloc[0]
)
assert np.isclose(base * float(np.prod(factors["combined_factor"].to_numpy())), premium)

# the median/reference profile IS the base: every combined factor ≈ 1.0 —
# the UI caption's promise ("a median profile's factors are all ≈ 1.0", G4)
base2, f2 = prediction.premium_breakdown(freq_model, sev_model, row, freq_df, freq_spec)
assert np.allclose(f2["combined_factor"], 1.0), f2
assert np.isclose(base2, float(quote["pure_premium"].iloc[0]))

# union ValueError: a severity-model column OUTSIDE the frequency spec must
# raise the friendly message, not a cryptic patsy failure — on BOTH functions
rng = np.random.default_rng(3)
sev_extra = fit_severity_glm(
    sev_df.assign(Extra=rng.uniform(size=len(sev_df))), "ClaimAmount ~ BonusMalus + Extra"
)
assert prediction.formula_columns(sev_extra) == ["BonusMalus", "Extra"]
assert prediction.required_columns(freq_model, sev_extra, freq_spec) == (
    list(freq_spec.predictors) + ["Extra"]
)
for fn in (
    lambda: prediction.predict_pure_premium(freq_model, sev_extra, freq_df, freq_spec),
    lambda: prediction.premium_breakdown(freq_model, sev_extra, real, freq_df, freq_spec),
):
    try:
        fn()
        raise AssertionError("expected ValueError")
    except ValueError as exc:
        assert "Extra" in str(exc) and "Missing predictor column" in str(exc), exc
print("PASS base", round(base, 2), "premium", round(premium, 2))
```

Expected: prints `PASS …` — record base and premium. A breakdown product not
reproducing the premium, a median-profile factor off 1.0, or the extra
severity column slipping past the union check (patsy KeyError/traceback
instead of the ValueError naming `Extra`) is a FAIL. The engine truths here
re-prove on the real stack what `tests/test_prediction.py` proves on
synthetic data (132-test suite: column identities, breakdown exactness,
median-numeric baseline, union error).

## TC3 — UI: guard ladder — no dataset, wrong kind, both models missing + Home none-state (S3)

TC10 snapshot first, then start the app; context A, one tab:

1. `goto /Pure_Premium` (fresh session, nothing loaded). Expected: the
   VERBATIM guard `Load a dataset first — go to Data Import.`; `Quote a
   policy` count == 0 (expect the guard first, then count). No `stException`.
2. Sidebar `app` (Home). Expected VERBATIM captions `Frequency model: none —
   fit or load one on Frequency Model.` and `Severity model: none — fit or
   load one on Severity Model.`; the success line `Both models in session —
   ready to quote on Pure Premium.` count == 0.
3. Sidebar `Data Import`; combobox route: type `severity`, Enter; `Load
   dataset`; wait for `26,444`. Sidebar `Pure Premium`. Expected: the
   VERBATIM kind guard `The active dataset is a severity dataset (claim
   amounts) — pure premium is quoted per policy. Load the frequency dataset
   in Data Import.`; `Quote a policy` == 0.
4. Sidebar `Data Import`; combobox route `frequency`; `Load dataset`; wait
   for `678,013`. Sidebar `Pure Premium`. Expected: the VERBATIM both-missing
   guard `Pure premium needs both models in session. Fit or load a frequency
   model on Frequency Model, and a severity model on Severity Model (load
   the severity dataset there first, then reload the frequency dataset —
   model slots survive the switch).`; `Quote a policy` == 0. No
   `stException` anywhere.

## TC4 — UI: frequency fit → the severity-missing ROUND-TRIP guard (S3, G2)

Same tab (context A):

1. Sidebar `Frequency Model`; click `Fit model` (defaults — poisson); wait
   for `Model fitted and recorded` (timeout 180,000 ms); `saved for reuse`
   ≥ 1 (slice-2 auto-save — this run is counted by TC10).
2. Sidebar `Pure Premium`. Expected: the VERBATIM round-trip guard `No
   severity model in session — load the severity dataset in Data Import, fit
   or load a severity model on Severity Model, then reload the frequency
   dataset (model slots survive the switch).`; the both-missing fragment
   `Pure premium needs both models` == 0; `Quote a policy` == 0 — the guard
   must NOT be the dead-end "go to Severity Model" (G2: screen 08's own kind
   guard would block that route without the round-trip wording).
3. Sidebar `app`. Expected: fragment `Frequency model: fitted (poisson, AIC`
   (record the actual AIC); the severity none-caption still VERBATIM; the
   success line count == 0.

## TC5 — UI: severity fit fills the second slot; kind guard precedes; ready to quote (S3, S7)

Same tab:

1. Sidebar `Data Import`; combobox route `severity`; `Load dataset`; wait
   for `26,444`.
2. Sidebar `Severity Model`; click `Fit model` (gamma default); wait for
   `Model fitted and recorded` (timeout 30,000 ms); `saved for reuse` ≥ 1 —
   this auto-saved gamma pickle is TC9's Load precondition.
3. Sidebar `Pure Premium`. Expected: STILL the VERBATIM kind guard of TC3.3
   — with BOTH models now in session, the dataset-kind guard fires first
   (the documented guard order); `Quote a policy` == 0.
4. Sidebar `Data Import`; combobox route `frequency`; `Load dataset`; wait
   for `678,013`.
5. Sidebar `app`. Expected: fragments `Frequency model: fitted (poisson,
   AIC` and `Severity model: fitted (gamma, AIC` (record actuals); the
   VERBATIM success line `Both models in session — ready to quote on Pure
   Premium.`
6. Sidebar `Pure Premium`. Expected — the guard-free quote form:
   - every guard gone (each unique fragment == 0: `Load a dataset first`,
     `severity dataset (claim amounts)`, `Pure premium needs both models`,
     `No frequency model in session`, `No severity model in session`,
     `The models need column(s)`);
   - model caption fragment `Frequency model: poisson (fitted) · Severity
     model: gamma (fitted)` (note the `·` U+00B7);
   - `Quote a policy` subheader + the VERBATIM caption `Take out a policy:
     defaults describe the median policy — change the inputs and get the
     annual risk premium.`;
   - widgets (expect each locator before counting): `stNumberInput` count
     == 6 (VehPower, VehAge, DrivAge, BonusMalus, Density + the exposure
     input), `stSelectbox` count == 4 (Area, VehBrand, VehGas, Region —
     TC1's dtype split); labels `BonusMalus` and `Exposure (policy-years)`
     visible;
   - buttons `Get quote` and `Compute premiums for loaded portfolio`
     visible; `Portfolio premiums` subheader visible; `stMetric` count == 0
     (nothing quoted or batched yet). No `stException`.

## TC6 — UI: happy-path quote with the default (median) profile (S1, S2)

Same tab, on 08:

1. Click `Get quote` (all widgets untouched — the median policy, exposure
   1.0). Expected: `expect` the `stMetric` locator, then count == 3, with
   labels asserted INSIDE the metric locators (`has_text`): `Expected claim
   frequency`, `Expected claim amount`, `Risk premium` — never via bare page
   text (the overlap trap: the model caption and the honesty caption contain
   these words). Metric VALUES are not scraped — TC1 holds the numbers
   (median profile, exposure 1.0 → Risk premium == pure_premium).
2. Caption fragments ≥ 1 each: `Risk premium only — no expenses, loadings,
   or profit.` and `Assumes claim counts and claim sizes are independent`.
3. `Premium breakdown` visible; breakdown caption fragments `reproduces the
   quote exactly` and `The reference policy is artificial`; `expect` the
   `stDataFrame` locator, count == 1 (the factors table). Canvas trap: the
   column headers `Rating factor` / `Your value` / `Frequency relativity` /
   `Severity relativity` / `Combined` and the ≈ 1.0 factors are canvas
   pixels, not DOM text — presence only; the identities and values are
   TC1/TC2 engine truths.
4. No `stException`, no `Traceback`. Record the quote wall time
   (single-row predicts — should be a few seconds at most).

## TC7 — UI: screen 06's batch must NOT leak into 08 (S6, isolation direction 1)

Same tab:

1. Sidebar `Prediction` (06); `Single policy` visible; click `Predict for
   loaded portfolio`; wait for `Total expected claims` (timeout 120,000 ms);
   `36,102` visible; `Total observed claims` visible; `by construction` ≥ 1.
2. Sidebar `Pure Premium`. Expected: `expect` the `Portfolio premiums`
   subheader first, then: `Total expected loss` count == 0, `Average annual
   premium` == 0, `36,102` == 0, `stMetric` count == 0 — screen 06's fresh
   batch (`predictions`/`predictions_kind`) must not surface as a premium
   batch, and the TC6 quote metrics are legitimately gone after navigation
   (button output does not persist — expected Streamlit behavior, not a
   failure). No `stException`.

## TC8 — UI: portfolio premium batch — honest summary + isolation direction 2 (S4, S5, S6, G1)

Same tab, on 08:

1. Click `Compute premiums for loaded portfolio` (spinner `Pricing 678,013
   policies...`). Expected: `expect` the `stMetric` locator (timeout
   120,000 ms), count == 3, labels inside the metric locators: `Total
   expected loss`, `Total expected claims`, `Average annual premium`.
   Values not scraped — TC1's totals are the truth (the expected-claims
   metric will read ≈ 36,102, matching 06 by construction).
2. Honesty caption fragments ≥ 1 each: `No observed-cost comparison is
   shown`, `covers only ~73% of the claims`, `about −1.5% below the observed
   claim total` (REAL MINUS U+2212 — copy from the page source), and
   `Cross-check the expected-claims total on the Prediction screen`.
3. G1 negative: NO observed-cost comparison anywhere on 08 — fragment
   `Total observed` count == 0.
4. `Tariff spread — annual premium percentiles across the portfolio:`
   caption visible; `expect` `stDataFrame`, count == 2 (percentile table +
   20-row preview — contents canvas-rendered; p25–p99 values are TC1's
   monotone spread). `Download premiums CSV` button visible (the payload is
   `premium_batch_csv` = `pure_premium_predictions.csv`; the download click
   itself stays deferred, TC12).
5. Sidebar `Prediction` (06). Expected — the premium batch is invisible
   there: `Total expected claims` still visible with `36,102` and `Total
   observed claims` (06's own batch intact), while `Total expected loss` ==
   0 and `Average annual premium` == 0 on 06.
6. Sidebar `Pure Premium` again. Expected: the premium batch PERSISTS across
   navigation (session key, unlike the quote): `stMetric` count == 3 with
   `Total expected loss` present WITHOUT re-clicking. No `stException`
   anywhere. Close context A.

## TC9 — UI: fresh session — frequency-missing guard + quote with a LOADED severity model (S3, S7)

NEW context B (the sanctioned fresh-session `goto` — a returning user), one
tab:

1. `goto /Data_Import`; combobox route `severity`; `Load dataset`; wait for
   `26,444`.
2. Sidebar `Severity Model`. The Load control is present by construction
   (TC5's fit auto-saved a gamma THIS execution); click `Load saved model`
   (selectbox untouched — the default option is the newest severity run);
   wait for `— no refit needed.` (timeout 30,000 ms).
3. Sidebar `Data Import`; combobox route `frequency`; `Load dataset`; wait
   for `678,013`.
4. Sidebar `Pure Premium`. Expected: the VERBATIM guard `No frequency model
   in session — fit or load one on Frequency Model.`; `Quote a policy` == 0;
   the other guards' unique fragments == 0.
5. Sidebar `app`. Expected: fragment `Severity model: loaded (gamma, AIC`;
   the VERBATIM frequency none-caption; the success line count == 0.
6. Sidebar `Frequency Model`; click `Fit model`; wait for `Model fitted and
   recorded` (timeout 180,000 ms) — the third appended run of this
   execution.
7. Sidebar `Pure Premium`. Expected: model caption fragment `Severity model:
   gamma (loaded)`; click `Get quote` → `stMetric` count == 3 (the three
   quote metrics, asserted inside the locators) + `Premium breakdown` +
   `stDataFrame` count == 1 — a LOADED severity model quotes exactly like a
   fitted one (slice 2's "Prediction and Pure Premium work fully" promise).
   No `stException`. Close context B.

## TC10 — DB/files: bracket — 3 new saved runs, nothing else written (S8)

Automated in the runner, bracketing the UI flow; read-only sqlite:

1. BEFORE launching the app: `storage.connect(DB_PATH).close()` first (the
   slice-2 lesson — migrate before any raw read), then record `n0 =
   COUNT(*)`, `max_id0 = MAX(id)`, the schema (`PRAGMA
   table_info(model_runs)`, table list) and the count of NULL-`model_path`
   rows.
2. AFTER the UI flow (app stopped): `n1 - n0 == 3` (TC4 poisson, TC5 gamma,
   TC9 poisson). Every row with `id > max_id0`: `model_path` non-NULL, the
   file exists, basename == `run{id:04d}_{family_kind(family)}_{family}.pickle`.
3. Nothing else changed: schema identical, NULL-path count identical, no new
   tables — slice 3 adds NO storage (quotes and premium batches are never
   persisted). **Never delete or truncate `data/workbench.db`; leave the
   pickles** — they are the Load feature's data and the re-run precondition.

## TC11 — Regression: suites and runners green under the new page (S8)

From the repo root, port 8598 free (runners launch their own app — never
concurrently):

1. `uv run pytest` — full suite green (132 expected — record the count),
   75% coverage gate met (incl. the `TestPredictPurePremium` /
   `TestPremiumBreakdown` classes).
2. `uv run ruff check pricing_engine/ tests/ app.py pages/ e2e/`,
   `uv run ruff format --check …`, `uv run mypy pricing_engine/ tests/` —
   clean.
3. Runners, expected green UNCHANGED — this slice adds a page and Home
   captions but touches no existing screen logic:
   - `uv run python e2e/e2e_model_persistence.py` and `e2e_model_slots.py`
     (nearest neighbors — slots and save/load feed screen 08);
   - `uv run python e2e/e2e_data_import.py` — it navigates to Home (`app`
     link): verify the NEW status captions/success line are additive and
     break none of its assertions; record any surprise;
   - `uv run python e2e/e2e_freq_model.py`, `e2e_diag_pred.py`,
     `e2e_severity_model.py`, `e2e_severity_diag_pred.py` — sidebar now
     carries a `Pure Premium` link; verify no runner counts sidebar links
     or asserts a page census;
   - `uv run python e2e/e2e_dataset_spec.py`, `e2e_stepwise_tc3b.py`
     (engine-only, seconds) — unaffected sanity.
   Each UI fit still appends a run + pickle (documented slice-2 side
   effect).

## TC12 — Deferred/manual: widget variations, G6, G8, downloads, all-loaded variant

Not built / not automated — record status in Results:

1. UI widget-change quote variations — BonusMalus up → premium up on
   screen, selectbox level changes, exposure ≠ 1.0 via the widget: typing
   into `number_input`s is beyond the sanctioned interaction set
   (defaults-only + the one Data-Import combobox route — screen-06
   precedent). The truths are engine-asserted (TC1 monotonicity and
   exposure-halving); the UI variation is manual.
2. G6 — the engineered-column hint (`The models need column(s) not present
   in the loaded portfolio: …`): needs a model fitted on a Feature
   Engineering column and a raw portfolio reload — manual only (the engine
   side, the union `required_columns` check, is TC2).
3. G8 — unseen-level edge (quoting a categorical level the model never
   saw): cannot arise from defaults — the widget levels come from the same
   full portfolio both models were fitted on — manual awareness only.
4. CSV download content (`pure_premium_predictions.csv` — the
   `premium_batch_csv` bytes): download clicks stay deferred as in all
   prior plans; the payload is `to_csv` of the TC1-verified frame.
5. All-loaded variant (frequency AND severity slots both `source="loaded"`)
   — TC9 covers loaded-severity + fitted-frequency; the fully loaded combo
   is manual.
6. The −1.5% caption number is prose, not recomputed — observation only
   (record TC1's actual severity-side gap if computed manually).

## Runner

Committed runner: **`e2e/e2e_pure_premium.py`** (engine TC1–TC2 + the TC10
bracket inline; UI TC3–TC9 via Playwright against port 8598 through
`e2e/harness.py`; TC11 run separately from the shell). Runner hygiene
specific to this plan:

- NO env overrides needed (unlike slice 2): the engine TCs are pure — but
  the TC10 snapshot must still `storage.connect(DB_PATH)` before its raw
  sqlite read (migration lesson from the slice-2 Results).
- TC1's fitted models are module-level and reused by TC2 — do not refit.
- Every metric assertion goes through `[data-testid="stMetric"]` with
  `has_text` filtering (the caption-overlap trap); every `.count()` is
  preceded by an `expect` on the same locator or a same-render text.
- Fragments containing `×`, `·`, `—`, `−` are pasted from
  `pages/08_Pure_Premium.py`, never retyped.

## Execution notes

- Prerequisites: both real Parquet files in `data/raw/`; Playwright +
  Chromium (`uv run playwright install chromium`); port 8598 free. **Never
  delete or truncate `data/workbench.db`** — the flow appends 3 real runs
  and 3 pickles in `models/` (gitignored, expected, counted by TC10).
- Order: TC1–TC2 (engine, ~15 s of fits) and the TC10 step-1 snapshot
  FIRST; start the app once headless on 8598. Context A: TC3–TC8 in one
  tab, sidebar links only after the first load (combobox switches:
  severity→frequency in TC3, severity in TC5.1, frequency in TC5.4).
  Context B (fresh — the returning-user simulation): TC9 in one tab
  (combobox severity, then frequency). One retry max per combobox route;
  remaining chained TCs flip to manual on failure. `expect` before every
  `count`; `.first` on fragments that can repeat.
- Timeouts: default ~20,000 ms; 180,000 ms after each Poisson `Fit model`
  (TC4.1, TC9.6); 30,000 ms after the Gamma fit (TC5.2) and the
  `Load saved model` click (TC9.2 — must be fit-free, record wall time);
  120,000 ms after 06's batch (TC7.1) and 08's premium batch (TC8.1 — two
  full-portfolio predicts).
- VERBATIM assertions: the five guards, the take-out caption, the two Home
  none-captions, the Home success line (texts in the header paragraph).
  Fragment assertions with actuals recorded: the model caption
  (`poisson (fitted)` / `gamma (fitted)` / `gamma (loaded)`), the Home
  fitted/loaded captions incl. AICs, `saved for reuse`, `— no refit
  needed.`, the honesty-caption fragments, `Tariff spread`, `reproduces the
  quote exactly`, `The reference policy is artificial`.
- FAIL conditions, in one place: a guard text wrong, missing, or fired out
  of order (kind guard must precede the model guards — TC5.3); the
  severity-missing guard without the round-trip wording (G2 dead-end
  regression); the quote form rendering while any guard should hold, or a
  guard holding while both slots are filled on a frequency dataset; the
  Home success line before both slots are filled, or absent after (TC3.2,
  TC4.3, TC5.5, TC9.5); `Get quote` yielding ≠ 3 metrics, missing either
  honesty caption, or no breakdown dataframe (TC6, TC9.7); engine anchors
  out of band — |total expected claims − 36,102| ≥ 400, mean claim amount
  outside 2,100–2,400, total expected loss outside 6.5e7–9.5e7, exposure
  0.5 not EXACTLY halving the premium, a non-strictly-increasing BonusMalus
  premium sequence, a non-monotone percentile spread (TC1); base ×
  Π(combined) ≠ premium or a median-profile factor off 1.0 (TC2); the union
  ValueError absent or not naming the extra column — a raw patsy traceback
  is a FAIL (TC2); an observed-cost comparison APPEARING on 08 (G1 — `Total
  observed` must be 0 there, TC8.3); premium-batch metrics or `36,102` on
  08 before its own batch, or 06's views gaining/losing anything after the
  premium batch (TC7, TC8.5); the premium batch NOT persisting across
  navigation (TC8.6); the TC9 load falling into a refit or timing out at
  30,000 ms; a run-history delta ≠ 3, a NULL `model_path` on a new row, a
  missing/misnamed pickle, any schema change or NULL-count drift (TC10);
  a metric label asserted via bare page text instead of inside `stMetric`
  (runner defect); any `Traceback` / `stException` anywhere.
- Pre-authorized observations to record, not failures: TC1's actual totals
  (expected claims, mean claim amount ≈ 2,230.9, loss total ≈ €80M) and
  BonusMalus premium sequence; TC2's base and row-0 premium; the AIC
  fragments on Home; quote and batch wall times; TC9's load wall time;
  whether 07's Load control was already populated before TC5's fit (re-run
  vs first execution — TC5 fits regardless, so the flow is
  execution-count-independent).

## Results

Executed 2026-08-31 via the committed runner `e2e/e2e_pure_premium.py`. ALL
EXECUTED TCs PASSED (TC1–TC10; TC11 from the shell; TC12 deferred/manual).
Bring-up needed three runner-side timing hardenings (no app defects): metric
LABEL text mounts after the metric element (assert labels via
`expect(metric.filter(has_text=...))`, not bare count), and widget counts
need an `expect` on the LAST widget (`nth(5)`/`nth(3)`) or the form's bottom
elements before counting.

- TC1 PASS — real-data anchors: total expected claims **36,102** (exact
  Poisson balance), mean expected claim amount **2,132.0**, total expected
  loss **€79.8M** (inside the 36,102 × ~2,231 ≈ €80M band), median-policy
  annual premium **€97.22**; exposure 0.5 halves the premium exactly;
  BonusMalus 50→75→100→150 premiums strictly increasing; monotone percentile
  spread; dtype split confirms 5 numeric + 4 categorical widgets.
- TC2 PASS — breakdown identity on portfolio row 0: base 97.22 ×
  Π(combined factors) = 301.82 exactly; the median profile's factors are all
  1.0 and its base equals the median premium (G4 median rebase verified);
  union ValueError names `Extra` on BOTH functions (no patsy traceback).
- TC3 PASS — guard ladder verbatim (no dataset → wrong kind → both-missing)
  + Home none-captions, no ready-line.
- TC4 PASS — severity-missing ROUND-TRIP guard verbatim (G2 — no dead end);
  Home shows the fitted frequency caption.
- TC5 PASS — kind guard precedes the model guards even with both models in
  session; after reloading the frequency dataset: Home ready-to-quote line,
  guard-free form with 6 number inputs + 4 selectboxes, both buttons.
- TC6 PASS — default (median) quote: exactly 3 metrics (labels inside the
  metric locators), both honesty captions, breakdown caption + factors table.
- TC7 PASS — screen 06's fresh batch (36,102) does not leak into 08.
- TC8 PASS — premium batch: 3 honest metrics, the ~73%/−1.5% honesty caption,
  `Total observed` count 0 (G1 negative), tariff-spread + preview tables,
  CSV button; 06's views unchanged afterwards; the premium batch persists
  across navigation.
- TC9 PASS — fresh session: frequency-missing guard verbatim; severity slot
  filled via slice-2 Load ("no refit needed"); after the frequency fit the
  quote works identically with the LOADED severity model
  (`Severity model: gamma (loaded)` caption).
- TC10 PASS — 54 → 57 runs (TC4 poisson, TC5 gamma, TC9 poisson), schema and
  NULL-path count unchanged — slice 3 adds no storage.
- TC11 PASS — pytest 132 passed, 99.11% coverage; ruff check/format + mypy
  clean; regression battery all green: `e2e_dataset_spec`,
  `e2e_stepwise_tc3b`, `e2e_data_import` (Home captions additive),
  `e2e_model_slots`, `e2e_model_persistence`, `e2e_diag_pred`,
  `e2e_severity_model`, `e2e_severity_diag_pred`.
- TC12 DEFERRED/manual — widget-change quote variations (engine truths in
  TC1), G6 engineered-column hint, G8 unseen level, CSV download content,
  the all-loaded variant, the −1.5% prose figure.
