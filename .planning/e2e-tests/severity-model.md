# E2E — Severity Model screen (V2 slice 2: Gamma/IG severity GLM, single active-model slot)

Change under test: the Severity Model screen (`pages/07_Severity_Model.py`)
and its engine function `glm.fit_severity_glm(df, formula, family="gamma")`.
Engine: families `gamma` (default) and `inverse_gaussian`, BOTH constructed
with an **explicit log link** (`sm.families.links.Log`) because statsmodels'
Gamma/InverseGaussian defaults are inverse-power links — the silent-bug trap
this slice must prove closed; **no offset parameter at all** (one row per
claim, no exposure); unknown family raises
`Unknown severity family '…' — valid: gamma, inverse_gaussian`. UI: guards for
no-dataset ("Load a dataset first — go to Data Import.") and for a frequency
dataset ("…frequency dataset (claim counts) — use the Frequency Model
screen…"); Model setup with a Distribution selectbox (Gamma first/default,
Inverse Gaussian), formula preview (`ClaimAmount ~ <nine factors>`), caption
"Log link, no offset — … multiplicatively on the expected claim amount"; Fit
button → spinner, AIC/BIC/Deviance/Parameters metrics, coefficient table with
the claim-size-relativity caption, strongest-effects bullets, an
insignificant-terms warning plus the teaching caption "Severity signal is
usually weaker than frequency signal…", shared Run history. **NO
stepwise/Variable-selection section on 07.** Architecture: a **single
active-model slot** — session keys `model` / `model_meta` with
`meta["kind"] ∈ {"frequency","severity"}`; screen 04 writes "frequency",
screen 07 writes "severity", each results section renders only when the kind
matches; Diagnostics (05) and Prediction (06) show an interim info guard when
the active model is a severity model ("…arrive[s] with the next slice…") —
kind-aware versions are slice 3. Storage: `record_model_run` is called with
`offset=None` for severity runs (`spec.offset` is None); rows distinguished by
`dataset=fremtpl2_sev` and `family`.

BA scenarios (the actuary from V1/slice 1 now fits the severity side of pure
premium):

- As an actuary with the severity dataset loaded, I open Severity Model and
  get a Model setup with Gamma preselected, the formula
  `ClaimAmount ~ Area + VehPower + VehAge + DrivAge + BonusMalus + VehBrand +
  VehGas + Density + Region`, and a primary Fit button; the fit on 26,444
  claims is fast; I get AIC/BIC/Deviance/Parameters, a coefficient table with
  p-values and exp(coef), and a success message — and NOTHING about exposure.
- As a learner, the educational surface must be severity-true: "claim
  frequency" appears NOWHERE on the rendered page (hard fail), the relativity
  caption talks about claim amount/size, "per policy-year" and "Exposure" do
  not appear. The insignificance warning is a teaching moment: on the real
  data I EXPECT a non-empty insignificant list (severity signal is weaker) —
  the opposite of the frequency screen.
- As an actuary choosing a distribution, the options are exactly Gamma and
  Inverse Gaussian (never Poisson/NegBin); IG must ALSO carry an explicit log
  link (its statsmodels default is 1/mu² — same silent-bug class); an unknown
  family raises the documented ValueError. If the IG fit fails numerically on
  the heavy tail, a caught friendly error is a pass — a traceback is a fail.
- As a returning user, Run history gains a new top row: dataset
  `fremtpl2_sev`, family `gamma`, formula starting `ClaimAmount ~`,
  n_obs 26,444, offset NULL; my pre-existing frequency runs are untouched
  (NEVER touch `data/workbench.db` destructively); the family column is
  visible so I can tell runs apart.
- As a user with the FREQUENCY dataset active who clicks Severity Model, I get
  an info box pointing me to the Frequency Model screen — no fitting UI at
  all (no Fit button, no selectbox, no formula). The guard is driven by the
  ACTIVE spec and must point AWAY correctly, not circle back.
- As a fresh-session user with no dataset, Severity Model says "Load a
  dataset first — go to Data Import." — no exception.
- As a V1 user, nothing regresses: screen 04 still fits frequency models and
  keeps its stepwise section (which lives on 04 ONLY); screen 04's
  severity-dataset guard still renders; after fitting a severity model,
  revisiting screen 04 degrades gracefully (its results section simply not
  shown), never crashes; the existing suite and the committed runner
  `e2e/e2e_severity_dataset.py` still pass.
- As an actuary sanity-checking the real-data fit: mean(fitted values) within
  ±5% of 2,265.5 on the default Gamma fit — NOT exp(Intercept), which is not
  the portfolio mean under treatment coding (wrong check); all fitted values
  strictly positive; few significant terms and a long insignificant list are
  expected; any extreme non-intercept relativity (>10 or <0.1) suggests a
  link/family bug.

Test Agent notes from the BA interview: mechanics carry over the hard-won
lessons in `e2e/README.md` and the slice-1 plan/runner
(`e2e/e2e_severity_dataset.py`):

- Engine truths FIRST (TC1–TC3), deterministic Python snippets run via
  `uv run python <tempfile.py>` from the repo root, scripts in the session
  scratchpad. The link-class assertion is engine-level and non-negotiable —
  a wrong default link would produce a page that LOOKS fine (the key trap).
- App started headless on port 8598:
  `uv run streamlit run app.py --server.port 8598 --server.headless true`;
  both Parquet files present in `data/raw/`.
  **Never delete or truncate `data/workbench.db`** — the UI fit (TC6)
  APPENDS one real run to it, which is the behavior under test (same
  precedent as `e2e_freq_model.py`); the storage-row assertions run against
  a TEMPFILE db via the `GLM_DB_PATH` override (TC3), never the real db.
- Session state is per browser tab; `page.goto` after loading DROPS it
  (proven twice). All post-load UI TCs run in ONE tab, sidebar links only
  (`app`, `Data Import`, `Frequency Model`, `Diagnostics`, `Prediction`,
  `Severity Model`).
- The severity dataset is NOT the selectbox default. The ONE sanctioned
  BaseWeb interaction — click the combobox, type `severity`, press Enter —
  worked FIRST TRY in slice 1; reuse it verbatim, one retry max, manual
  fallback for the chained TCs if it ever stops taking.
- `expect(...).to_be_visible()` before any `.count()` (strict-mode /
  progressive-render lesson). Known-good selectors:
  `[data-testid="stMetric"]`, `[data-testid="stDataFrame"]`,
  `[data-testid="stSelectbox"]`, `[data-testid="stException"]`,
  `get_by_role("button", name=...)`. Combobox current values are NOT
  readable via `get_by_text` — the Gamma DEFAULT is proven engine-level
  (TC1: `SEVERITY_FAMILIES[0] == "gamma"` → first option is the Streamlit
  default), not scraped. Glide-data-grid cell text is NOT assertable — Run
  history row CONTENT is proven engine-level (TC3); the UI asserts only the
  section + grid presence.
- The Gamma fit on 26k rows takes seconds — use a generous timeout
  (~30,000 ms) on the expectations immediately after clicking Fit.
- Absence assertions must use DISTINCTIVE fragments: assert `claim
  frequency` (full phrase) count == 0, never bare `frequency` — the sidebar
  link "Frequency Model" legitimately contains it.
- Exact captions/wording are implementation-chosen. TCs name distinctive
  fragments (`claim amount`, `claim-size relativity`, `Frequency Model`,
  `next slice`); wording drift is not a FAIL — a missing section/metric,
  frequency wording on the severity screen, a stepwise section on 07, or
  any traceback/`stException` IS.
- BaseWeb interactions beyond the one sanctioned combobox route (switching
  Distribution to Inverse Gaussian in the UI, prediction selectboxes) stay
  in the deferred/manual bucket (TC9) — the IG fit itself is proven
  engine-level in TC2.

## TC1 — Engine: severity family contract — log link on BOTH families, no offset, error wording

Engine-level (deterministic, automated). Run via `uv run python <tempfile.py>`
from the repo root:

```python
import inspect

import numpy as np
import pandas as pd
import statsmodels.api as sm

from pricing_engine.data import DATASET_REGISTRY
from pricing_engine.glm import (
    FREQUENCY_FAMILIES,
    SEVERITY_FAMILIES,
    build_formula,
    fit_severity_glm,
)

# Family lists: exactly gamma + inverse_gaussian, gamma FIRST (= UI default);
# frequency list untouched (no Poisson/offset copy-paste leakage either way)
assert SEVERITY_FAMILIES == ["gamma", "inverse_gaussian"], SEVERITY_FAMILIES
assert FREQUENCY_FAMILIES == ["poisson", "negative_binomial"], FREQUENCY_FAMILIES

# No offset parameter AT ALL in the severity fit signature
params = inspect.signature(fit_severity_glm).parameters
assert "offset" not in params and "offset_column" not in params, list(params)

# Unknown family -> exact ValueError contract (the Poisson copy-paste trap)
try:
    fit_severity_glm(pd.DataFrame({"y": [1.0], "x": [1.0]}), "y ~ x", family="poisson")
    raise SystemExit("FAIL: no ValueError for family='poisson'")
except ValueError as e:
    assert "Unknown severity family 'poisson'" in str(e), e
    assert "gamma, inverse_gaussian" in str(e), e

# THE trap: statsmodels' Gamma/InverseGaussian DEFAULT links are inverse
# power — both families must carry an explicit Log link, and no offset.
rng = np.random.default_rng(42)
tiny = pd.DataFrame(
    {"y": rng.gamma(2.0, 500.0, 400) + 1.0, "x": rng.normal(size=400)}
)
for name, fam_cls in [("gamma", sm.families.Gamma),
                      ("inverse_gaussian", sm.families.InverseGaussian)]:
    m = fit_severity_glm(tiny, "y ~ x", family=name)
    fam = m.model.family
    assert isinstance(fam, fam_cls), (name, type(fam))
    assert isinstance(fam.link, sm.families.links.Log), (name, type(fam.link))
    assert getattr(m.model, "offset", None) is None, (name, m.model.offset)
    assert (np.asarray(m.fittedvalues) > 0).all(), name

# Default family is gamma (no family kwarg)
m_default = fit_severity_glm(tiny, "y ~ x")
assert isinstance(m_default.model.family, sm.families.Gamma)

# Formula from the severity spec: full nine-factor ClaimAmount formula
sev_spec = DATASET_REGISTRY["fremtpl2_sev"]
assert build_formula(sev_spec) == (
    "ClaimAmount ~ Area + VehPower + VehAge + DrivAge + BonusMalus"
    " + VehBrand + VehGas + Density + Region"
), build_formula(sev_spec)
print("PASS")
```

Expected: prints `PASS`. A non-Log link class on EITHER family is the
highest-severity failure this plan can produce — it invalidates every
relativity the screen teaches while looking superficially healthy.

## TC2 — Engine: real-data Gamma fit calibration + IG fit attempt

Engine-level. The Gamma fit on 26,444 claims takes a few seconds:

```python
import numpy as np

from pricing_engine.data import load_dataset
from pricing_engine.diagnostics import coefficient_table, information_criteria
from pricing_engine.glm import build_formula, fit_severity_glm

df, spec = load_dataset("fremtpl2_sev")
formula = build_formula(spec)
model = fit_severity_glm(df, formula)  # gamma default

# Calibration: mean FITTED value within ±5% of the portfolio mean 2,265.5.
# (NOT exp(Intercept) — under treatment coding that is the baseline cell,
# not the portfolio mean; the BA flagged that as the wrong check.)
fitted = np.asarray(model.fittedvalues)
assert (fitted > 0).all()
mean_fitted = float(fitted.mean())
assert abs(mean_fitted - 2_265.5) / 2_265.5 < 0.05, mean_fitted

info = information_criteria(model)
assert info["n_obs"] == 26_444, info["n_obs"]
for key in ("aic", "bic", "deviance", "log_likelihood"):
    assert np.isfinite(info[key]), (key, info[key])
assert info["n_params"] > 20  # nine factors incl. multi-level categoricals

# Relativity sanity: extreme non-intercept relativities => link/family bug
table = coefficient_table(model)
non_int = table[table["term"] != "Intercept"]
rel = np.exp(non_int["coef"])
assert rel.between(0.1, 10).all(), non_int.loc[~rel.between(0.1, 10), "term"].tolist()

# The teaching moment: severity signal is weaker — expect a NON-EMPTY
# insignificant list on the real data (opposite of the frequency fit)
insig = non_int[~non_int["significant"]]
assert len(insig) > 0, "expected insignificant terms on real severity data"

# Inverse Gaussian ATTEMPT on the heavy tail: convergence is not guaranteed.
# If it fits: same log-link + positive-fitted checks. If it raises: record
# the exception type/message (feeds the deferred UI TC9) — NOT a failure,
# but the UI must then show a friendly error, never a traceback.
try:
    m_ig = fit_severity_glm(df, formula, family="inverse_gaussian")
    import statsmodels.api as sm
    assert isinstance(m_ig.model.family.link, sm.families.links.Log)
    assert (np.asarray(m_ig.fittedvalues) > 0).all()
    ig_outcome = f"IG fitted, AIC {float(m_ig.aic):,.0f}"
except Exception as e:  # numerical fragility is a documented possibility
    ig_outcome = f"IG raised {type(e).__name__}: {e}"
print("PASS", round(mean_fitted, 1), round(info["aic"], 0), len(insig), "|", ig_outcome)
```

Expected: prints `PASS` + the mean fitted value, AIC, insignificant-term
count, and the IG outcome — record ALL of these in Results (the mean fitted
value and the insignificant list are re-used to interpret the UI run; the IG
outcome decides what TC9 must check manually).

## TC3 — Engine: storage row correctness on a TEMPFILE db (GLM_DB_PATH override)

Engine-level — proves the run-history row content the UI grid cannot expose
(glide-data-grid text is not assertable). Uses a scratchpad tempfile db via
`GLM_DB_PATH`; the real `data/workbench.db` is never touched by this TC:

```python
import os
import tempfile

import pandas as pd

os.environ["GLM_DB_PATH"] = os.path.join(tempfile.mkdtemp(), "e2e_sev_model.db")

from pricing_engine import storage
from pricing_engine.data import load_dataset
from pricing_engine.diagnostics import information_criteria
from pricing_engine.glm import build_formula, fit_severity_glm

df, spec = load_dataset("fremtpl2_sev")
formula = build_formula(spec)
model = fit_severity_glm(df, formula)
info = information_criteria(model)

# Mirror EXACTLY what pages/07_Severity_Model.py records (offset=spec.offset,
# which for the severity spec is None)
assert spec.offset is None, spec.offset
with storage.connect() as conn:
    storage.record_model_run(
        conn,
        dataset=spec.name,
        target=spec.target,
        offset=spec.offset,
        formula=formula,
        family="gamma",
        n_obs=info["n_obs"],
        aic=info["aic"],
        bic=info["bic"],
        deviance=info["deviance"],
        log_likelihood=info["log_likelihood"],
        coefficients=model.params.to_dict(),
    )
with storage.connect() as conn:
    runs = storage.list_model_runs(conn)

assert len(runs) == 1, len(runs)
row = runs.iloc[0]
assert row["dataset"] == "fremtpl2_sev", row["dataset"]
assert row["target"] == "ClaimAmount", row["target"]
assert row["family"] == "gamma", row["family"]
assert row["formula"].startswith("ClaimAmount ~"), row["formula"]
assert int(row["n_obs"]) == 26_444, row["n_obs"]
# The row must NOT lie: offset is NULL, not "Exposure" (the copy-paste trap)
assert row["offset"] is None or pd.isna(row["offset"]), row["offset"]
print("PASS", row["family"], row["offset"])
```

Expected: prints `PASS gamma None` (or NaN — record actual NULL rendering in
Results). An `offset` of `"Exposure"` on a severity row is a FAIL even though
nothing on screen would look wrong.

## TC4 — UI: no-dataset guard on a fresh session

1. Open a **new browser context**,
   `page.goto("http://localhost:8598/Severity_Model")` directly (goto is fine
   here — an empty session is the point).
2. Expected:
   - Info box with the text `Load a dataset first — go to Data Import.`
   - NO fitting UI: no `Fit model` button, no `Model setup` text, zero
     `[data-testid="stSelectbox"]`.
   - No `Traceback` text, no `[data-testid="stException"]`.

## TC5 — UI: reverse guard (frequency dataset active) + screen-04 regression

Same tab as TC4 (empty session so far):

1. Sidebar link `Data Import`; click `Load dataset` with **defaults
   untouched** (the frequency dataset loads — one-click default proven in
   slice 1). Wait for the success message (`678,013` fragment, ≤ ~15 s).
2. Sidebar link `Severity Model`. Expected:
   - Info guard whose text contains the fragments `frequency dataset` and
     `Frequency Model` — pointing AWAY to the frequency screen, not circling
     back (guard direction trap).
   - NO fitting UI: no `Fit model` button, no `Model setup`, no
     `Distribution` selectbox, no formula/`ClaimAmount ~` text.
   - No `Traceback` / `stException`.
3. Sidebar link `Frequency Model` (regression — screen 04 unchanged for
   frequency). Expected:
   - Normal fitting UI renders: `Model setup` header, formula code block
     containing `ClaimNb ~`, `Fit model` button present, AND the
     `Variable selection` section present (stepwise lives on 04 ONLY).
   - No `Traceback` / `stException`.
   - **Actually fitting is NOT required here** (a full 678k Poisson fit
     takes ~12 s and adds a history row; the single-slot swap in the
     frequency→severity direction is exercised by TC6–TC7, and the reverse
     swap is deferred to TC9). Rendering the fitting UI is the required
     assertion; a fit is optional.

## TC6 — UI: the severity happy path — setup, fit, results, run history, wording

Same tab as TC5:

1. Sidebar link `Data Import`; the ONE sanctioned BaseWeb interaction: click
   the dataset combobox, type `severity`, press `Enter` (one retry max; on
   failure flip TC6–TC7 to manual per the slice-1 precedent and record the
   route). Click `Load dataset`; wait for `26,444` (≤ ~15 s).
2. Sidebar link `Severity Model`. Expected — Model setup BEFORE fitting:
   - `Model setup` header; a `Distribution` selectbox
     (`[data-testid="stSelectbox"]` ≥ 1 — its current value is NOT scraped;
     Gamma-as-default is TC1's `SEVERITY_FAMILIES[0]` truth).
   - Formula preview containing `ClaimAmount ~ Area` (and NOT `ClaimNb`).
   - Caption with fragments `Log link, no offset` and `claim amount`.
   - ABSENT on the whole page: `Variable selection` (stepwise leak),
     `Exposure`, `claim frequency`, `per policy-year` — each `.count() == 0`
     (full phrases; bare `frequency` matches the sidebar link — see notes).
3. Click `Fit model` (primary). Expected (generous timeout ~30 s):
   - Success message containing `Model fitted and recorded` and `AIC`.
   - Metric row: `[data-testid="stMetric"]` count == 4 after
     expect-before-count; labels `AIC`, `BIC`, `Deviance`, `Parameters`.
   - `Coefficients` section: caption with fragment `claim-size relativity`
     and `claim amount`; a `stDataFrame` grid.
   - Strongest-effects bullets (`What the strongest effects mean` fragment)
     with wording about `claim amount` — IF any significant terms exist
     (expected on real data, e.g. VehBrand/Region levels; record actuals).
   - The insignificant-terms warning IS present (TC2 proved the list is
     non-empty on the real data — an all-significant severity fit here means
     the screens disagree with the engine) AND the teaching caption fragment
     `Severity signal is usually weaker`.
   - `Run history` section with a `stDataFrame` grid (row CONTENT — family
     gamma, offset NULL, n_obs 26,444 — is TC3's engine-level truth; the
     grid text is not assertable). This click appends ONE real run to
     `data/workbench.db` — expected behavior, note the new top-row id in
     Results if visible.
4. Whole-page re-check after fitting: `claim frequency` count == 0,
   `per policy-year` count == 0, `Exposure` count == 0, `Variable selection`
   count == 0, no `Traceback`, no `stException`.

## TC7 — UI: single-slot stale-state — Diagnostics/Prediction interim guards, screen 04 no-crash

> **Inverted by V2 slice 3 (2026-08-25):** Diagnostics and Prediction are now
> kind-aware, so with a severity model active they RENDER instead of showing
> the interim guard. Steps 1–2 below are superseded by: Diagnostics shows
> `Model summary`, ≥ 4 `stMetric`, `next slice` count == 0, `claim frequency`
> count == 0; Prediction shows `Single claim` (no `Single policy`, `next
> slice` == 0) with a `Predict` button. Step 3 (screen-04 guard) is unchanged.
> The committed runner `e2e/e2e_severity_model.py` implements the inverted
> version; the full kind-aware behaviour is covered by
> `severity-diagnostics-prediction.md`.

Same tab as TC6 (severity model now the active model):

1. Sidebar link `Diagnostics`. Expected:
   - Info guard with fragments `severity model` and `next slice` (interim
     wording — kind-aware diagnostics are slice 3).
   - NO frequency diagnostics render: zero `[data-testid="stMetric"]`, no
     coefficient-CI chart, and emphatically no frequency wording applied to
     the Gamma model.
   - No `Traceback` / `stException`.
2. Sidebar link `Prediction`. Expected:
   - Info guard with fragments `severity model` and `next slice`.
   - No `Predict` button, no single-policy input form.
   - No `Traceback` / `stException`.
3. Sidebar link `Frequency Model`. Expected (the stale-state crash trap: a
   severity model sits in the single `model` slot while screen 04 renders):
   - The severity-DATASET guard from slice 1 still shows (fragments
     `severity dataset` and `Severity Model`) — the spec guard fires before
     any model-state access, so the page must NOT crash and must NOT render
     the frequency results section against the Gamma model (no `AIC` metric,
     no `Fit model` button).
   - No `Traceback` / `stException`.

## TC8 — Regression: existing suites still green

From the repo root, after (or before — order irrelevant) the UI TCs:

1. `uv run pytest` — the full suite passes (102 tests at slice completion;
   record the actual count) with the 75% coverage gate met.
2. `uv run python e2e/e2e_severity_dataset.py` — the committed slice-1
   runner still passes end-to-end (TC1–TC9 of that plan; its TC9 asserts
   screen 04's severity guard, which this slice must not have broken).
   Note: it launches its own Streamlit instance on port 8598 — do not run it
   while the TC4–TC7 app instance holds the port.

## TC9 — Deferred/manual: IG in the UI, reverse slot-swap, selectbox variations

BaseWeb interactions beyond TC6's single sanctioned combobox route stay
**manual**, per the standing precedent:

1. With the severity dataset loaded, switch `Distribution` to
   `Inverse Gaussian` and click `Fit model`. Expected per TC2's recorded IG
   outcome: EITHER a successful fit (metrics + coefficients, family
   `inverse_gaussian` in the new history row) OR a caught, friendly error
   message — a raw traceback / `stException` is a FAIL either way.
2. Reverse single-slot swap: on Data Import re-select the **frequency**
   dataset and load; on Frequency Model fit the Poisson model (~12 s).
   Expected: screen 04 shows its frequency results; Diagnostics and
   Prediction work again (guards gone); Severity Model now shows the
   frequency-dataset guard and does NOT render stale severity results
   (kind mismatch hides the results section).
3. Run history visual check while on either model screen: frequency and
   severity rows coexist, distinguishable by the `family` column; the
   severity row's offset is empty/NULL (engine truth from TC3).
4. Record in Results whether executed manually or deferred.

## Execution notes

- Prerequisites: both real Parquet files in `data/raw/`; Playwright +
  Chromium installed (`uv run playwright install chromium`); port 8598 free.
  **Never delete or truncate `data/workbench.db`** — TC6 appends one real
  run (under test); TC3's row assertions use a `GLM_DB_PATH` tempfile db.
- Engine TCs (TC1–TC3) run FIRST as independent scripts from the repo root
  (`uv run python <tempfile.py>`), scripts in the session scratchpad, not
  the repo. TC2's IG outcome feeds TC9; TC2's insignificant-term count is
  the expectation behind TC6's warning assertion.
- Start the app once:
  `uv run streamlit run app.py --server.port 8598 --server.headless true`
  (background; kill after). UI TCs run TC4→TC5→TC6→TC7 sequentially in
  **ONE tab of one context**, navigating via **sidebar links only** after
  any load (`page.goto` drops session state — proven twice; TC4's direct
  goto is the sanctioned exception because an empty session is the point).
  Default timeout ~15,000 ms; raise to ~30,000 ms for the expectations
  immediately after clicking `Fit model` (26k-row Gamma fit).
- Combobox route (TC6 step 1): click → type `severity` → Enter, one retry
  max; on failure TC6–TC7 flip to manual (click-and-read once loaded),
  record the route either way. `expect` before `count`; `.first` on
  fragments that appear twice.
- Absence assertions use full distinctive phrases (`claim frequency`,
  `per policy-year`, `Variable selection`, `Cap Exposure` — never bare
  `frequency`/`Model`, which the sidebar legitimately contains).
- Exact-text caveats: captions, guard wording, spinner text, and metric
  labels are implementation-chosen — match loosely on the distinctive
  fragments named per TC and record actuals in Results. Wording drift is
  not a FAIL. A missing section/metric, `claim frequency`/`Exposure`
  wording on the severity screen, a stepwise section on 07, a fittable
  Severity Model page under a frequency dataset, a crash on screens
  04/05/06 with a severity model in the slot, a wrong link class (TC1), an
  `offset="Exposure"` severity history row (TC3), or any
  traceback/`stException` IS a FAIL.
- The IG numerical outcome (TC2) and the run-history NULL rendering (TC3)
  are pre-authorized observations to record, not failures.

## Results

Executed 2026-07-30 via the committed runner `e2e/e2e_severity_model.py`
(engine TCs inline, UI TCs via Playwright against port 8598; TC8 run
separately from the shell). **TC1–TC8 all PASSED; TC9 deferred/manual per
plan.**

- TC1 PASS — both families carry the explicit Log link (the inverse-power
  default trap is closed); no offset parameter in the signature; exact
  ValueError wording confirmed; gamma first in `SEVERITY_FAMILIES`; formula
  is the full nine-factor `ClaimAmount ~ …`.
- TC2 PASS — **mean fitted 2,230.9** (1.5% below the observed 2,265.5 —
  within the ±5% calibration bound), AIC 573,121, n_obs 26,444, all
  relativities within 0.1–10. **Key real-data finding: 41 of 42
  non-intercept terms are INSIGNIFICANT — only `BonusMalus` is significant**
  (the weak-severity-signal teaching moment the BA predicted, in its most
  extreme form). **IG outcome: the Inverse Gaussian fit RAISES
  `ValueError: NaN, inf or invalid value detected in weights, estimation
  infeasible.`** on the real heavy tail — this finding drove an
  implementation fix DURING execution: `pages/07_Severity_Model.py` now
  wraps the fit in try/except and shows a friendly `st.error` ("…heavy-tailed
  claim amounts can make estimation infeasible. Try the Gamma family.")
  instead of a traceback. TC9's manual IG check should expect that message.
- TC3 PASS — tempfile-db row: `dataset fremtpl2_sev`, `target ClaimAmount`,
  `family gamma`, formula `ClaimAmount ~ …`, n_obs 26,444, **offset None**
  (renders as Python `None` via pandas object column). Runner variation from
  the plan: the override uses `storage.connect(path)` directly instead of the
  `GLM_DB_PATH` env var — same isolation, and nothing can leak into the app
  subprocess the runner launches later.
- TC4 PASS — fresh-session guard `Load a dataset first — go to Data Import.`;
  zero selectboxes, no Fit button, no exception.
- TC5 PASS — reverse guard wording: `The active dataset is a frequency
  dataset (claim counts) — use the Frequency Model screen to fit it.`; no
  fitting UI under a frequency dataset. Screen 04 regression: Model setup,
  `ClaimNb ~` formula, Fit button, and Variable selection section all render
  (no fit performed — optional per plan).
- TC6 PASS — **automated combobox route worked again** (click + type
  `severity` + Enter). Pre-fit: Model setup, Distribution selectbox, formula
  `ClaimAmount ~ Area…`, caption `Log link, no offset…`. Post-fit: success
  `Model fitted and recorded (AIC 573,121)`, exactly 4 metrics
  (AIC/BIC/Deviance/Parameters), claim-size-relativity caption, strongest
  effects section (BonusMalus bullet), insignificant-terms warning + teaching
  caption `Severity signal is usually weaker…`, Run history grid. Whole-page
  absences held before AND after fitting: `claim frequency`,
  `per policy-year`, `Exposure`, `Variable selection` all count 0; no
  exception. One real run appended to `data/workbench.db` (run 12; expected
  behavior under test).
- TC7 PASS — Diagnostics and Prediction both show the interim guard
  (`severity model` + `next slice` fragments), zero metrics / no Predict
  button, no crash; screen 04 shows its severity-dataset guard with the
  Gamma model sitting in the single `model` slot — no stale-state crash.
- TC8 PASS — full suite 102 passed (99.42% coverage; note: implementing
  `fit_severity_glm` required removing its stub line from
  `test_scaffold.py::test_stubs_fail_loudly` per that file's own contract —
  the stub's NotImplementedError also triggered a pytest-internal crash via
  patsy frame introspection when the now-implemented function was called with
  scaffold args). Slice-1 runner `e2e/e2e_severity_dataset.py` re-executed:
  all its TCs still green (its TC9 screen-04 guard intact).
- TC9 DEFERRED/manual per plan (IG in the UI — expect the friendly error per
  TC2's outcome; reverse slot-swap; run-history visual check).

Re-executed 2026-08-25 after V2 slice 3 with TC7 inverted (see the note
under TC7): result recorded in `severity-diagnostics-prediction.md` TC11.
