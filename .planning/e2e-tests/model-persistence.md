# E2E — Fitted-model persistence (V3 slice 2: save on fit, Load from run history)

Change under test: every successful fit on `pages/04_Frequency_Model.py` /
`pages/07_Severity_Model.py` now **pickles the fitted model** (data-stripped,
`remove_data=True`) to `models/run{id:04d}_{kind}_{family}.pickle` (dir
overridable via `GLM_MODELS_DIR`, `models/*` gitignored) and records the path
on the run row (`storage.save_model`); `save_model` **deep-copies first**, so
the live session model keeps its residuals for Diagnostics after a fit+save.
The fit success message is now `Model fitted and recorded (AIC {aic:,.0f}) —
saved for reuse.` (the substring `Model fitted and recorded` is deliberately
kept — the old runners wait on it); a save failure produces `st.warning`
`Model recorded but the model file could not be saved: …` and the run row
keeps a NULL path. `ensure_schema` migrates older databases in place (ALTER
TABLE adds nullable `model_path`, idempotent); pre-slice-2 rows keep NULL and
are **excluded** from the new Load control. That control appears in Run
history on 04/07 only when eligible rows exist (eligibility: family in the
kind's family list AND `model_path` non-NULL): selectbox `Load a saved
frequency model` / `Load a saved severity model` (option labels `Run {id} ·
{created_at} · {family} · AIC {aic:,.0f}`), button `Load saved model`,
success flash `Loaded run {id} ({family}, AIC {aic:,.0f}) — no refit
needed.`, friendly errors (missing file: `Saved model file missing: …`;
unreadable pickle: `The saved model file could not be read — refit instead.
(…)`). Empty state (no eligible rows): caption `No saved frequency/severity
model files yet — runs recorded before model persistence have none; fit a
model to save one.` Loading fills the kind's session slot with the pickle
plus a meta **reconstructed from the DB row** (formula/family/kind derived
from the family/aic/bic/deviance/log_likelihood/n_obs/n_params = len of
`coefficients_json`) and `source="loaded"`; a fresh fit sets
`source="fitted"`. Diagnostics (05) for `source=="loaded"` renders metrics +
the coefficient CI chart + the coefficient table, then `st.info` `This model
was loaded from the run history — the saved file predicts and reports
coefficients, but carries no residual data. Refit in this session to see
residuals, the QQ plot, calibration and the full summary.` and `st.stop()` —
Residuals/QQ/Observed vs Predicted/Model summary are ABSENT
(`model.summary()` on a data-stripped model would raise TypeError).
Prediction (06) needs no change — loaded models predict fully (36,102
anchor). Headline behaviour: a **new browser session** (F5 in real life) can
load the dataset, click `Load saved model` and be predicting in seconds — no
~12 s refit.

BA scenarios (numbered as in the BA report):

- S1 — Fit on 04 auto-saves: success message with `saved for reuse`, run row
  gains a non-NULL `model_path`, the pickle exists with the documented name,
  the Load control appears in Run history, the empty-state caption is gone.
- S2 — HEADLINE: new browser session → load dataset → `Load saved model`
  (fast, no ~12 s refit) → 04 renders results from the reconstructed meta;
  Prediction single + batch fully work (36,102 anchor); Diagnostics shows
  metrics + coefficients + the loaded-model info hint; no traceback.
- S3 — Kind filtering: 04 offers only frequency runs, 07 only severity runs
  (disjoint family sets via `family_kind`; a saved poisson run must not make
  07's Load control appear).
- S4 — A fresh fit after a load flips `source` back to `"fitted"` — the full
  residual diagnostics return on 05.
- S5 — Old NULL-path rows are excluded from the Load control and the
  migration is idempotent. The real `data/workbench.db` holds ~30
  pre-slice-2 rows: once a saved run of a kind exists the empty-state
  caption must NOT appear, and the old rows must not be listed — asserted
  via **engine-level DB checks**, not by scraping the selectbox.
- S6 — Missing pickle file → friendly error flash, the session slot is
  UNCHANGED (the failed load must not evict or replace the live model).
- S7 — Slice-1 coexistence intact: a LOADED severity model and a FITTED
  frequency model live side by side, both usable across dataset switches;
  `predictions_kind` stale-batch tagging still hides the other kind's batch.
- S8 — Regression: V1/V2/slice-1 runners, pytest (75% gate), ruff, mypy.

Test Agent notes from the BA interview: mechanics per `e2e/README.md` /
`e2e/harness.py` and the slice-1 plan (`per-kind-model-slots.md`):

- Engine truths FIRST (TC1–TC2) — deterministic Python inline at the top of
  the committed runner. TC1's migration runs on a **synthetic old-schema DB
  in a temp dir**; TC2's save/load roundtrip does one real Gamma fit (~2 s)
  against **temp `GLM_DB_PATH` + `GLM_MODELS_DIR` overrides**. The overrides
  MUST be removed from `os.environ` before the harness starts the app —
  the UI flow is supposed to write the real `data/workbench.db` and
  `models/` (the subprocess inherits the environment).
- **NEVER touch the real `data/workbench.db`** beyond the rows the UI fits
  append (3 runs + 3 pickle files in `models/` — documented, expected, and
  what TC9 counts). Never delete or truncate the DB; leave the pickles.
- App headless on port 8598 via `e2e/harness.py`. TWO contexts, each ONE
  tab, sidebar links only after the first load: context A runs TC3–TC4
  (fit + save both kinds), context B runs TC5–TC8 — context B's opening
  `goto` is the sanctioned exception because a **fresh session is the
  point** (it simulates F5/browser restart, the headline scenario).
- Defaults-only widgets + the ONE sanctioned combobox route (click the first
  `[data-testid="stSelectbox"]` on Data Import, type `severity` /
  `frequency`, Enter) — used three times (TC4, TC7 twice). The Load control
  selectbox is NEVER typed into: `list_model_runs` is newest-first, so its
  default option is the newest eligible run — every Load click in this plan
  targets exactly that run by construction. Note 04/07 now carry a SECOND
  selectbox (Distribution + Load) — never address selectboxes on those pages
  by bare index.
- Absence-assertion TRAP specific to this slice: the loaded-model hint
  itself contains `residuals`, `QQ plot`, `calibration` and `full summary` —
  absence of the residual sections must be asserted via the widget/section
  labels `Residual kind` (the radio), `Observed vs Predicted`,
  `Calibration table` and `Full statsmodels summary`, never via bare
  `residual`/`QQ`/`summary` fragments.
- Exact texts spec'd by this slice and asserted VERBATIM: the loaded-model
  info hint (full text above) and the two empty-state captions. Flash and
  error messages are asserted on distinctive fragments (`saved for reuse`,
  `— no refit needed.`, `Saved model file missing:`, `could not be read —
  refit instead`, `could not be saved`) with actuals recorded in Results.
- First execution vs re-run: on the FIRST execution against the real DB the
  empty-state captions are visible before the fits (all ~30 rows are
  pre-slice-2 NULLs); a re-run finds saved runs from the previous execution,
  so the captions are already gone and the Load controls already present.
  TC3/TC4 record which precondition held instead of hard-asserting it; the
  POST-fit assertions (caption gone, control present) hold either way.
- Engine truths already unit-tested in `tests/test_storage.py` (migration,
  filename pattern, deep-copy save keeping the live model's residuals,
  data-stripped load, meta reconstruction, NULL-path/missing-file errors) —
  TC1/TC2 re-prove the load-bearing subset on the real stack; metric VALUES
  are never scraped from the UI (36,102 stays the only UI numeric anchor
  besides the load messages 678,013 / 26,444).

## TC1 — Engine: migration on a COPY of an old-schema DB + eligibility predicate (S5, S3)

Engine-level (deterministic, seconds; temp dir only — the real DB is not
opened for writing here):

```python
import os
import sqlite3
import tempfile
from pathlib import Path

tmp = Path(tempfile.mkdtemp())
os.environ["GLM_DB_PATH"] = str(tmp / "wb.db")       # engine TCs only —
os.environ["GLM_MODELS_DIR"] = str(tmp / "models")   # removed before app launch

from pricing_engine import storage
from pricing_engine.glm import FREQUENCY_FAMILIES, SEVERITY_FAMILIES, family_kind

OLD_SCHEMA = """
CREATE TABLE model_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    dataset TEXT NOT NULL, target TEXT NOT NULL, "offset" TEXT,
    formula TEXT NOT NULL, family TEXT NOT NULL, n_obs INTEGER NOT NULL,
    aic REAL NOT NULL, bic REAL NOT NULL, deviance REAL NOT NULL,
    log_likelihood REAL NOT NULL, coefficients_json TEXT NOT NULL
)
"""  # the pre-slice-2 schema, as in tests/test_storage.py

old_db = tmp / "old.db"
with sqlite3.connect(old_db) as raw:
    raw.execute(OLD_SCHEMA)
    for fam in ("poisson", "gamma"):  # one old row per kind
        raw.execute(
            """INSERT INTO model_runs (dataset, target, "offset", formula, family,
               n_obs, aic, bic, deviance, log_likelihood, coefficients_json)
               VALUES ('d', 't', NULL, 'f', ?, 1, 0, 0, 0, 0, '{}')""",
            (fam,),
        )
    raw.commit()

conn = storage.connect(old_db)  # migrates: ALTER TABLE adds model_path
cols = [r[1] for r in conn.execute("PRAGMA table_info(model_runs)")]
assert cols.count("model_path") == 1, cols
runs = storage.list_model_runs(conn)
assert len(runs) == 2 and runs["model_path"].isna().all()  # old rows keep NULL
conn.close()

conn = storage.connect(old_db)  # IDEMPOTENT: second connect is a no-op
cols2 = [r[1] for r in conn.execute("PRAGMA table_info(model_runs)")]
assert cols2 == cols

# a NULL-path row refuses to load with the friendly ValueError
try:
    storage.load_model(conn, 1)
    raise AssertionError("expected ValueError")
except ValueError as exc:
    assert "no saved model file" in str(exc), exc

# THE eligibility predicate the 04/07 Load controls use — both kinds empty
# despite two rows existing (NULL paths), and kind-disjoint by family:
for families in (FREQUENCY_FAMILIES, SEVERITY_FAMILIES):
    loadable = runs[runs["family"].isin(families) & runs["model_path"].notna()]
    assert loadable.empty, loadable
assert family_kind("poisson") == "frequency" and family_kind("gamma") == "severity"
print("PASS migration idempotent, old rows NULL and ineligible")
```

Expected: prints `PASS …`. A duplicated/missing `model_path` column, a lost
row, an old row becoming eligible, or the ValueError not raised is a FAIL.

## TC2 — Engine: save/load roundtrip on a real Gamma fit (S1, S2, S6 truths)

Engine-level, temp overrides from TC1 still in effect; the real Gamma fit
takes ~2 s (AIC ≈ 573,121 — record actuals):

```python
import numpy as np

from pricing_engine import diagnostics, storage
from pricing_engine.data import load_dataset
from pricing_engine.glm import build_formula, fit_severity_glm

df, spec = load_dataset("fremtpl2_sev")
assert len(df) == 26_444 and spec.kind == "severity"
formula = build_formula(spec)
model = fit_severity_glm(df, formula)  # gamma default
info = diagnostics.information_criteria(model)

conn = storage.connect()  # temp GLM_DB_PATH
run_id = storage.record_model_run(
    conn, dataset=spec.name, target=spec.target, offset=spec.offset,
    formula=formula, family="gamma", n_obs=info["n_obs"], aic=info["aic"],
    bic=info["bic"], deviance=info["deviance"],
    log_likelihood=info["log_likelihood"], coefficients=model.params.to_dict(),
)
path = storage.save_model(conn, run_id, model)
# filename contract + gitignore-relevant location (temp GLM_MODELS_DIR here)
assert path.name == f"run{run_id:04d}_severity_gamma.pickle", path.name
assert path.exists()
row = storage.list_model_runs(conn).iloc[0]
assert row["model_path"] == str(path)

# save deep-copies FIRST: the LIVE model keeps its residual arrays
# (Diagnostics right after a fit+save must still show residuals/QQ)
assert len(np.asarray(model.fittedvalues)) == 26_444
assert len(np.asarray(model.resid_deviance)) == 26_444

loaded, meta = storage.load_model(conn, run_id)
assert np.allclose(loaded.params.to_numpy(), model.params.to_numpy())
head = df.head(200)  # the data-stripped pickle predicts identically
assert np.allclose(np.asarray(loaded.predict(head)), np.asarray(model.predict(head)))
stripped = getattr(loaded, "fittedvalues", None)  # …but carries no residual data
assert stripped is None or len(np.atleast_1d(stripped)) == 0
# meta reconstructed from the run row, source flag flips
assert meta["source"] == "loaded" and meta["kind"] == "severity"
assert meta["family"] == "gamma" and meta["formula"] == formula
assert meta["aic"] == float(info["aic"]) and meta["n_obs"] == 26_444
assert meta["n_params"] == len(model.params)

path.unlink()  # missing file -> the friendly FileNotFoundError (temp dir!)
try:
    storage.load_model(conn, run_id)
    raise AssertionError("expected FileNotFoundError")
except FileNotFoundError as exc:
    assert "Saved model file missing" in str(exc), exc
conn.close()
print("PASS", run_id, round(info["aic"]))
```

Expected: prints `PASS 1 573121`-ish. A mutated live model (stripped
residuals after save — the deep-copy contract), drifted predictions from the
pickle, a wrong filename, or a raw unpickling traceback instead of the
friendly errors is a FAIL. **After TC1/TC2: delete `GLM_DB_PATH` and
`GLM_MODELS_DIR` from `os.environ`** so the app writes the real locations.

## TC3 — UI: fit on 04 auto-saves; Load control appears (S1, S5)

Snapshot first (TC9 step 1), then start the app; context A, one tab:

1. `goto /Data_Import`; click `Load dataset` with defaults; wait for
   `678,013` (≤ ~15 s).
2. Sidebar `Frequency Model`. Record the Run history precondition: on a
   first execution the VERBATIM caption `No saved frequency model files yet
   — runs recorded before model persistence have none; fit a model to save
   one.` is visible (all real rows are pre-slice-2 NULLs); on a re-run the
   Load control is already present instead. Record which; either way no
   `stException`.
3. Click `Fit model` (Distribution untouched — poisson); wait for `Model
   fitted and recorded` (timeout 180,000 ms). Assert `saved for reuse` ≥ 1
   and `could not be saved` == 0 (the warning path must not fire).
4. Run history (same page render): `Load a saved frequency model` visible,
   `Load saved model` button visible, the empty-state caption count == 0
   (S5 — a saved run now exists). No `stException`.
5. Runner-side (read-only sqlite on `data/workbench.db`): the newest row has
   a non-NULL `model_path`; the file exists and is named
   `run{id:04d}_frequency_poisson.pickle`; `git check-ignore -q <path>`
   exits 0 (models/* gitignored — no accidental staging risk).

## TC4 — UI: kind filtering on 07, then Gamma fit + save (S3, S1)

Same tab (context A):

1. Sidebar `Data Import`; combobox route: type `severity`, Enter; `Load
   dataset`; wait for `26,444`.
2. Sidebar `Severity Model`. S3's UI face: a saved POISSON run now exists,
   yet 07 must not offer it — on a first execution the VERBATIM caption
   `No saved severity model files yet — runs recorded before model
   persistence have none; fit a model to save one.` is visible (record; on a
   re-run the control already lists prior gamma runs instead). Always:
   `Load a saved frequency model` count == 0 on this page.
3. Click `Fit model` (gamma default); wait for `Model fitted and recorded`
   (timeout 30,000 ms); `saved for reuse` ≥ 1, `could not be saved` == 0.
4. Run history: `Load a saved severity model` + `Load saved model` visible;
   the severity empty-state caption count == 0. No `stException`.
5. Runner-side: newest row is gamma, `model_path` non-NULL, file
   `run{id:04d}_severity_gamma.pickle` exists. Close context A.

## TC5 — UI: THE HEADLINE — new session, load saved model, predict without refit (S2)

NEW context B (the sanctioned fresh-session `goto` — this IS the F5
simulation), one tab for TC5–TC8:

1. `goto /Data_Import`; `Load dataset` (defaults → frequency); wait for
   `678,013`. Session state is empty of models — exactly the post-F5 state.
2. Sidebar `Frequency Model`. Expected: NO results section (`stMetric`
   count == 0 — nothing fitted this session); Run history with the Load
   control; the default selectbox option is the NEWEST frequency run (TC3's
   poisson — record its `Run {id} · {created_at} · poisson · AIC …` label).
3. Click `Load saved model` (selectbox untouched). Wait for the flash
   fragment `— no refit needed.` (timeout 30,000 ms — a fallback into a
   ~12 s+ refit-scale wait is the failure mode; record the wall time) and
   `Loaded run` ≥ 1. Expected then on 04: 4 `stMetric` (AIC/BIC/Deviance/
   Parameters — the meta reconstructed from the DB row incl. `n_params`),
   `Coefficients` subheader + coefficient dataframe. No `stException`.
4. Sidebar `Prediction` (06 — unchanged by this slice, loaded models predict
   fully): `Single policy` visible; `Predict` (`exact=True`) → `Expected
   claim frequency`; click `Predict for loaded portfolio`; wait for `Total
   expected claims` (timeout 120,000 ms); `36,102` visible; `by
   construction` ≥ 1. No `stException`.
5. Sidebar `Diagnostics` (05 — the loaded-model guard). Expected:
   - 4 `stMetric`; `Coefficients with confidence intervals` visible;
     `stVegaLiteChart` ≥ 1 (the CI chart); `Coefficient table` expander
     present.
   - The info hint VERBATIM: `This model was loaded from the run history —
     the saved file predicts and reports coefficients, but carries no
     residual data. Refit in this session to see residuals, the QQ plot,
     calibration and the full summary.`
   - ABSENT (label-based — see the trap note): `Residual kind` == 0,
     `Observed vs Predicted` == 0, `Calibration table` == 0, `Full
     statsmodels summary` == 0.
   - No `Traceback` / `stException` — the TypeError from `model.summary()`
     on a data-stripped model is exactly what the `st.stop()` prevents.

## TC6 — UI: a fresh fit flips source back — full diagnostics return (S4)

Same tab:

1. Sidebar `Frequency Model`; click `Fit model`; wait for `Model fitted and
   recorded` (timeout 180,000 ms) — appends the third run + pickle;
   `saved for reuse` ≥ 1.
2. Sidebar `Diagnostics`. Expected (timeout 60,000 ms on the first): the
   full sections are BACK — `Residual kind` visible, `Observed vs Predicted`
   visible, `Calibration table` present, `Full statsmodels summary` present;
   `stVegaLiteChart` ≥ 2; the loaded hint is GONE: `This model was loaded
   from the run history` count == 0. No `stException`.

## TC7 — UI: coexistence — LOADED severity + FITTED frequency (S7, S3)

Same tab; the frequency slot is now `source="fitted"` (TC6), the severity
slot is about to be filled by a LOAD:

1. Sidebar `Data Import`; combobox route `severity`; `Load dataset`; wait
   for `26,444`.
2. Sidebar `Severity Model`: no results section yet in this session
   (`stMetric` == 0); Load control present; click `Load saved model`
   (default = newest severity run, TC4's gamma); wait for `— no refit
   needed.` (timeout 30,000 ms); 07 renders 4 metrics + `Coefficients`.
3. Sidebar `Diagnostics`: severity metrics + CI chart + the VERBATIM loaded
   hint; `Residual kind` == 0; no `stException`.
4. Sidebar `Prediction`: `Single claim` visible; click `Predict for loaded
   claims` (timeout 60,000 ms) → `Total expected claim amount` visible,
   `does not reproduce` ≥ 1; the stale FREQUENCY batch from TC5 is hidden —
   `Total expected claims` == 0, `36,102` == 0 (slice-1 `predictions_kind`
   tagging intact under a loaded model).
5. Sidebar `Data Import`; combobox route `frequency`; `Load dataset`; wait
   for `678,013`. Sidebar `Diagnostics`: the FITTED Poisson renders in FULL
   (`Residual kind` visible, loaded hint == 0) — a loaded severity model and
   a fitted frequency model coexist, neither evicted. Sidebar `Prediction`:
   the stale severity batch is hidden (`Total expected claim amount` == 0);
   no `stException` anywhere.

## TC8 — UI: missing pickle → friendly error, slot UNCHANGED (S6)

Same tab, frequency dataset loaded; runner-side file juggling in try/finally
(models/ only — never the DB):

1. Runner: from the DB, resolve the NEWEST frequency run's `model_path`
   (TC6's pickle — the Load control's default option) and RENAME it to
   `<name>.bak`.
2. Sidebar `Frequency Model`; click `Load saved model`. Expected: error
   flash with fragment `Saved model file missing:` (st.error); no
   `stException`.
3. The slot is untouched by the failed load: sidebar `Diagnostics` still
   shows the FULL fitted views (`Residual kind` visible, loaded hint == 0) —
   the fitted Poisson was neither evicted nor replaced.
4. Runner: rename the file back. Executed-if-time (a): on 04, `Load saved
   model` again → success flash `— no refit needed.` (recovery). Executed-
   if-time (b — unreadable pickle): copy the file to `.bak`, overwrite the
   original with garbage bytes, `Load saved model` → fragment `could not be
   read — refit instead` (no raw unpickling traceback), slot still
   unchanged; restore from `.bak`. Record executed/deferred.

## TC9 — DB/files: bracket — 3 new saved rows, old NULLs untouched (S5, S1)

Automated in the runner, bracketing the UI flow; read-only where possible:

1. BEFORE launching the app: on `data/workbench.db` record `n0 = COUNT(*)`,
   `max_id0 = MAX(id)`, `PRAGMA table_info(model_runs)` column names
   (`model_path` present — the real DB is migrated by any post-slice-2 app
   run; record if the migration happens on this run's first connect), and
   the set of ids with `model_path` NULL (~30 pre-slice-2 rows expected on
   the first execution — record the actual count).
2. AFTER the UI flow (app stopped): `n1 - n0 == 3` (TC3 poisson, TC4 gamma,
   TC6 poisson refit). Every row with `id > max_id0`: `model_path` non-NULL,
   the file exists, and the basename equals
   `run{id:04d}_{family_kind(family)}_{family}.pickle`.
3. Old rows: every id ≤ `max_id0` that had a NULL `model_path` STILL has
   NULL — loads never write paths, and re-migration touched nothing.
4. S5's "not listed", engine-level (never scraped from the selectbox): the
   eligibility predicate `family.isin(FREQUENCY_FAMILIES) &
   model_path.notna()` selects EXACTLY the new poisson rows plus any saved
   poisson rows from previous executions — no pre-slice-2 NULL row appears;
   severity analog for gamma. Schema otherwise unchanged vs step 1.
   **Never delete or truncate `data/workbench.db`; leave the pickles.**

## TC10 — Regression: existing suites green under the new save-on-fit (S8)

From the repo root, port 8598 free (runners launch their own app — never
concurrently):

1. `uv run pytest` — full suite green (record the count), 75% coverage gate
   met (incl. the `tests/test_storage.py` migration + save/load classes).
2. `uv run ruff check pricing_engine/ tests/ app.py pages/ e2e/`,
   `uv run ruff format --check …`, `uv run mypy pricing_engine/ tests/` —
   clean.
3. Runners, expected green UNCHANGED — the success-message substring `Model
   fitted and recorded` was deliberately preserved for them, but each fit
   they perform now ALSO writes a pickle to `models/` (new expected side
   effect, gitignored):
   - `uv run python e2e/e2e_model_slots.py` (slice 1 — the closest
     neighbor; its 3 fits append 3 runs + now 3 pickles; its TC12 row-count
     bracket still holds);
   - `uv run python e2e/e2e_freq_model.py`, `e2e/e2e_diag_pred.py`,
     `e2e/e2e_severity_model.py`, `e2e/e2e_severity_diag_pred.py` — verify
     none asserts the full old success text or a widget count that the new
     Run-history Load control (extra selectbox + button + captions on
     04/07) would break; record any surprise;
   - `uv run python e2e/e2e_dataset_spec.py`, `e2e_stepwise_tc3b.py`
     (engine-only, seconds) — unaffected sanity.

## TC11 — Deferred/manual: adopted-spec mismatch (G4), save-failure warning, variants

Not built / not automated — record status in Results:

1. G4 (BA-accepted gap, pre-existing edge, documented NOT built): a run
   fitted on an ADOPTED (trimmed) spec and loaded later under the full
   current spec — 06's what-if widgets come from the CURRENT spec, so a
   widget can exist for a term the loaded model never had (ignored by
   predict) — the single-policy form can mislead. Manual awareness only;
   no assertion, no fix in this slice.
2. Save-failure warning path (`Model recorded but the model file could not
   be saved:` + run row keeps NULL): needs an unwritable `models/` dir —
   manual only.
3. Non-default families saved/loaded (negative binomial; IG where it
   converges) — manual.
4. TC8's executed-if-time steps (recovery re-load, unreadable pickle) if
   they were skipped.
5. Load-speed observation: record the TC5/TC7 load wall times vs the ~12 s
   Poisson refit (observation, not a hard timing assertion beyond the
   30,000 ms flash timeout).

## Runner

Committed runner: **`e2e/e2e_model_persistence.py`** (engine TC1–TC2 + the
TC9 bracket inline; UI TC3–TC8 via Playwright against port 8598 through
`e2e/harness.py`; TC10 run separately from the shell). No existing runner
needs updating — the `Model fitted and recorded` wait-substring is preserved
by design; TC10 verifies that claim. Runner hygiene specific to this plan:

- TC1/TC2 set `GLM_DB_PATH`/`GLM_MODELS_DIR` to temp dirs and MUST `del`
  both from `os.environ` before `streamlit_app()` — the app subprocess
  inherits the environment, and the UI flow must hit the real
  `data/workbench.db` + `models/`.
- TC8's pickle rename/restore runs in try/finally so a mid-TC failure never
  leaves a saved run pointing at a missing file.

## Execution notes

- Prerequisites: both real Parquet files in `data/raw/`; Playwright +
  Chromium (`uv run playwright install chromium`); port 8598 free. **Never
  delete or truncate `data/workbench.db`** — the flow appends 3 real runs
  and 3 pickle files in `models/` (gitignored; expected behaviour under
  test — leave them in place, they are the re-run precondition).
- Order: TC1–TC2 (engine, temp overrides) and the TC9 step-1 snapshot
  FIRST; drop the env overrides; start the app once headless on 8598.
  Context A: TC3–TC4 in one tab (one combobox switch). Context B (fresh —
  the F5 simulation): TC5–TC8 in one tab, sidebar links only after the
  first load (two combobox switches in TC7); one retry max per combobox
  route, remaining chained TCs flip to manual on failure. `expect` before
  `count`; `.first` on fragments that can repeat; `exact=True` on
  `Predict`.
- Timeouts: default ~20,000 ms; 180,000 ms after each Poisson `Fit model`;
  30,000 ms after the Gamma fit AND after each `Load saved model` click
  (the load must be fit-free — record wall times); 120,000 ms after the
  frequency batch; 60,000 ms after the severity batch and on each first
  post-switch Diagnostics expectation.
- VERBATIM assertions: the loaded-model info hint and the two empty-state
  captions (texts in the header paragraph). Loose-fragment assertions with
  actuals recorded: `saved for reuse`, `— no refit needed.`, `Loaded run`,
  `Saved model file missing:`, `could not be read — refit instead`,
  `could not be saved` (expected count 0 in this flow), the Load option
  labels. The absence trap: the hint contains `residuals` / `QQ plot` /
  `calibration` / `full summary` — loaded-state absences use ONLY the
  labels `Residual kind`, `Observed vs Predicted`, `Calibration table`,
  `Full statsmodels summary`.
- First execution vs re-run: the pre-fit empty-state captions (TC3.2,
  TC4.2) are recorded, not hard-asserted — a previous execution's saved
  runs legitimately remove them. All post-fit and engine-bracket
  assertions are execution-count-independent (TC9 uses `max_id0`).
- FAIL conditions, in one place: a fit success without `saved for reuse` or
  with the `could not be saved` warning; a new run row with NULL
  `model_path`, a missing/misnamed pickle, or a non-gitignored pickle; an
  empty-state caption shown while an eligible run of that kind exists, or a
  Load control on 07 fed by frequency-only saved runs (TC4.2); a
  pre-slice-2 NULL row turning eligible or gaining a path (TC1, TC9); the
  headline load timing out at 30,000 ms or falling into a refit; a loaded
  model rendering `Residual kind` / `Observed vs Predicted` /
  `Calibration table` / `Full statsmodels summary`, or missing the verbatim
  hint, or missing the coefficient chart/table (TC5, TC7); full sections
  NOT returning after the TC6 refit; stale batch numbers of the other kind
  after a switch (TC7); a failed load evicting or replacing the live slot
  (TC8); a run-history delta ≠ 3, an old-NULL mutation, or a schema change
  (TC9); a raw unpickling traceback instead of the friendly messages; any
  `Traceback` / `stException` anywhere.
- Pre-authorized observations to record, not failures: TC2's gamma AIC, the
  Load option labels and flash actuals, load wall times, which empty-state
  precondition held (first run vs re-run), TC8's executed-if-time steps.

## Results

Executed 2026-08-31 via the committed runner `e2e/e2e_model_persistence.py`.
ALL EXECUTED TCs PASSED (TC1–TC9; TC10 from the shell; TC11 deferred/manual).
Bring-up needed several runner-side fixes (test mechanics, no app defects):
the TC9 snapshot must run the real DB's migration first
(`storage.connect(DB_PATH)` before the raw sqlite read — a raw connection
sees no `model_path` on a not-yet-migrated DB), and Streamlit mounts
metric/chart WIDGETS asynchronously after the text deltas, so every
`stMetric`/`stVegaLiteChart` `.count()` needs a preceding auto-waiting
`expect` on the LOCATOR itself (a text expect like "AIC" is not enough — it
matched the Load selectbox's option label instantly). The failed bring-up
runs each appended their TC3/TC4 fits to the real DB before dying (expected
runner behaviour; ~8 extra saved runs + pickles accumulated across attempts).

- TC1 PASS — migration idempotent on the synthetic old-schema DB; old rows
  keep NULL and stay ineligible for both kinds; NULL-path load raises the
  friendly ValueError.
- TC2 PASS — real Gamma roundtrip (AIC 573,121): filename contract
  `run0001_severity_gamma.pickle`, deep-copy save keeps the live model's
  26,444 residuals, the data-stripped pickle predicts identically, meta
  reconstructed (`source="loaded"`, n_params from coefficients_json),
  missing-file FileNotFoundError.
- TC3 PASS — fit on 04 auto-saves (`saved for reuse`, no warning); Load
  control appears, empty-state caption gone; pickle exists, correctly named,
  `git check-ignore` confirms gitignored. Precondition on this execution:
  Load control already present (earlier bring-up attempts had saved runs).
- TC4 PASS — 07 never offers the frequency runs (kind filter); Gamma fit
  saves `run00xx_severity_gamma.pickle`.
- TC5 PASS — THE HEADLINE: fresh session (F5 sim), Load saved model took
  **4.2 s** (vs the ~12 s refit); 04 renders the meta metrics + coefficient
  table; Prediction single + batch fully work (36,102, `by construction`);
  Diagnostics shows metrics + CI chart + coefficient table + the VERBATIM
  loaded hint; `Residual kind` / `Observed vs Predicted` /
  `Calibration table` / `Full statsmodels summary` all absent; no traceback.
- TC6 PASS — a fresh fit flips `source` back: all four sections return, the
  hint is gone.
- TC7 PASS — loaded severity + fitted frequency coexist across dataset
  switches; loaded-severity Diagnostics shows the hint, Prediction batch
  works (`does not reproduce`); stale batches hidden in both directions.
- TC8 PASS — renamed pickle → `Saved model file missing:` flash, the fitted
  slot untouched (full diagnostics still render); recovery re-load after the
  restore succeeded. The unreadable-pickle variant stays deferred (TC11).
- TC9 PASS — 39 → 42 runs (TC3 poisson, TC4 gamma, TC6 refit); every new row
  non-NULL with an existing, correctly named file; all 31 pre-slice-2 NULL
  rows untouched; schema unchanged.
- TC10 PASS — pytest 121 passed, 99.24% coverage; ruff check/format + mypy
  clean (incl. `e2e/`); regression runners `e2e_model_slots.py`,
  `e2e_diag_pred.py`, `e2e_severity_model.py`, `e2e_severity_diag_pred.py`
  all green unchanged (each fit now also writes a gitignored pickle — the
  documented new side effect).
- TC11 DEFERRED/manual — G4 adopted-spec what-if mismatch (accepted, not
  built), save-failure warning path, non-default families, unreadable-pickle
  variant.
