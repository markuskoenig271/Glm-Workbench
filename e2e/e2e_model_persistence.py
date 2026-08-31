"""Executes the TCs from .planning/e2e-tests/model-persistence.md (V3 slice 2).

Engine TCs (TC1-TC2, temp GLM_DB_PATH/GLM_MODELS_DIR overrides) and the TC9
snapshot first; the overrides are then REMOVED so the UI flow (TC3-TC8, two
contexts) hits the real data/workbench.db + models/. TC10 (pytest + the other
runners) runs separately from the shell; TC11 is deferred/manual. Run from the
repo root:
    uv run python e2e/e2e_model_persistence.py
"""

import os
import sqlite3
import subprocess
import tempfile
import time
from pathlib import Path

import numpy as np
from harness import streamlit_app
from playwright.sync_api import Page, expect, sync_playwright

from pricing_engine import diagnostics, storage
from pricing_engine.data import load_dataset
from pricing_engine.glm import (
    FREQUENCY_FAMILIES,
    SEVERITY_FAMILIES,
    build_formula,
    family_kind,
    fit_severity_glm,
)

# --- TC1: migration on a synthetic old-schema DB + eligibility predicate ------

tmp = Path(tempfile.mkdtemp())
os.environ["GLM_DB_PATH"] = str(tmp / "wb.db")  # engine TCs only —
os.environ["GLM_MODELS_DIR"] = str(tmp / "models")  # removed before app launch

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

try:  # a NULL-path row refuses to load with the friendly ValueError
    storage.load_model(conn, 1)
    raise AssertionError("expected ValueError")
except ValueError as exc:
    assert "no saved model file" in str(exc), exc

# THE eligibility predicate the 04/07 Load controls use — both kinds empty
for families in (FREQUENCY_FAMILIES, SEVERITY_FAMILIES):
    loadable = runs[runs["family"].isin(families) & runs["model_path"].notna()]
    assert loadable.empty, loadable
assert family_kind("poisson") == "frequency" and family_kind("gamma") == "severity"
conn.close()
print("TC1 PASS migration idempotent, old rows NULL and ineligible")

# --- TC2: save/load roundtrip on a real Gamma fit ------------------------------

df, spec = load_dataset("fremtpl2_sev")
assert len(df) == 26_444 and spec.kind == "severity"
formula = build_formula(spec)
model = fit_severity_glm(df, formula)  # gamma default
info = diagnostics.information_criteria(model)

conn = storage.connect()  # temp GLM_DB_PATH
run_id = storage.record_model_run(
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
path = storage.save_model(conn, run_id, model)
assert path.name == f"run{run_id:04d}_severity_gamma.pickle", path.name
assert path.exists()
row = storage.list_model_runs(conn).iloc[0]
assert row["model_path"] == str(path)

# save deep-copies FIRST: the LIVE model keeps its residual arrays
assert len(np.asarray(model.fittedvalues)) == 26_444
assert len(np.asarray(model.resid_deviance)) == 26_444

loaded, meta = storage.load_model(conn, run_id)
assert np.allclose(loaded.params.to_numpy(), model.params.to_numpy())
head = df.head(200)  # the data-stripped pickle predicts identically
assert np.allclose(np.asarray(loaded.predict(head)), np.asarray(model.predict(head)))
stripped = getattr(loaded, "fittedvalues", None)  # ...but carries no residual data
assert stripped is None or len(np.atleast_1d(stripped)) == 0
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
print(f"TC2 PASS run_id={run_id} aic={info['aic']:,.0f}")

# drop the overrides — the app subprocess must hit the real DB + models/
del os.environ["GLM_DB_PATH"]
del os.environ["GLM_MODELS_DIR"]

# --- TC9 snapshot: real DB state BEFORE the UI flow ----------------------------

DB_PATH = Path("data") / "workbench.db"
storage.connect(DB_PATH).close()  # first post-slice-2 touch migrates the real DB
with sqlite3.connect(DB_PATH) as raw:
    n0 = raw.execute("SELECT COUNT(*) FROM model_runs").fetchone()[0]
    max_id0 = raw.execute("SELECT COALESCE(MAX(id), 0) FROM model_runs").fetchone()[0]
    schema0 = [r[1] for r in raw.execute("PRAGMA table_info(model_runs)")]
    null_ids0 = {r[0] for r in raw.execute("SELECT id FROM model_runs WHERE model_path IS NULL")}
print(f"TC9 snapshot: {n0} runs, max_id={max_id0}, {len(null_ids0)} NULL-path rows")

# --- UI TCs -------------------------------------------------------------------

EMPTY_FREQ = (
    "No saved frequency model files yet — runs recorded before model "
    "persistence have none; fit a model to save one."
)
EMPTY_SEV = (
    "No saved severity model files yet — runs recorded before model "
    "persistence have none; fit a model to save one."
)
LOADED_HINT = (
    "This model was loaded from the run history — the saved file predicts and "
    "reports coefficients, but carries no residual data. Refit in this session "
    "to see residuals, the QQ plot, calibration and the full summary."
)


def no_exception(page: Page) -> None:
    assert page.get_by_text("Traceback").count() == 0
    assert page.locator("[data-testid='stException']").count() == 0


def load_builtin(page: Page, fragment: str, rows_text: str) -> None:
    """Sanctioned combobox route: click the dataset selectbox, type, Enter, load."""
    page.get_by_role("link", name="Data Import").click()
    expect(page.get_by_text("Built-in dataset").first).to_be_visible()
    page.locator("[data-testid='stSelectbox']").first.click()
    page.keyboard.type(fragment)
    page.keyboard.press("Enter")
    page.get_by_role("button", name="Load dataset").click()
    expect(page.get_by_text(rows_text).first).to_be_visible()


def newest_saved_run(families: list[str]) -> tuple[int, Path]:
    with sqlite3.connect(DB_PATH) as raw:
        placeholders = ",".join("?" * len(families))
        rid, mpath = raw.execute(
            f"SELECT id, model_path FROM model_runs "
            f"WHERE family IN ({placeholders}) AND model_path IS NOT NULL "
            f"ORDER BY id DESC LIMIT 1",
            families,
        ).fetchone()
    return int(rid), Path(mpath)


expect.set_options(timeout=20000)

with streamlit_app() as URL, sync_playwright() as p:
    browser = p.chromium.launch()

    # --- context A: TC3-TC4 (fit + save both kinds) ---------------------------
    ctx_a = browser.new_context()
    page = ctx_a.new_page()
    page.set_default_timeout(20000)

    # TC3 — fit on 04 auto-saves; Load control appears
    page.goto(f"{URL}/Data_Import")
    page.get_by_role("button", name="Load dataset").click()
    expect(page.get_by_text("678,013").first).to_be_visible()
    page.get_by_role("link", name="Frequency Model").click()
    expect(page.get_by_text("Run history").first).to_be_visible()
    precondition = "empty-state caption" if page.get_by_text(EMPTY_FREQ).count() else "Load control"
    no_exception(page)

    page.get_by_role("button", name="Fit model").click()
    expect(page.get_by_text("Model fitted and recorded").first).to_be_visible(timeout=180000)
    assert page.get_by_text("saved for reuse").count() >= 1
    assert page.get_by_text("could not be saved").count() == 0
    expect(page.get_by_text("Load a saved frequency model").first).to_be_visible()
    expect(page.get_by_role("button", name="Load saved model")).to_be_visible()
    assert page.get_by_text(EMPTY_FREQ).count() == 0
    no_exception(page)

    freq_id, freq_path = newest_saved_run(FREQUENCY_FAMILIES)
    assert freq_id > max_id0, (freq_id, max_id0)
    assert freq_path.exists()
    assert freq_path.name == f"run{freq_id:04d}_frequency_poisson.pickle", freq_path.name
    ignored = subprocess.run(["git", "check-ignore", "-q", str(freq_path)], check=False)
    assert ignored.returncode == 0, "pickle must be gitignored"
    print(f"TC3 PASS (precondition: {precondition}; saved {freq_path.name})")

    # TC4 — kind filtering on 07, then Gamma fit + save
    load_builtin(page, "severity", "26,444")
    page.get_by_role("link", name="Severity Model").click()
    expect(page.get_by_text("Run history").first).to_be_visible()
    sev_precondition = (
        "empty-state caption" if page.get_by_text(EMPTY_SEV).count() else "Load control"
    )
    assert page.get_by_text("Load a saved frequency model").count() == 0  # kind filter
    no_exception(page)

    page.get_by_role("button", name="Fit model").click()
    expect(page.get_by_text("Model fitted and recorded").first).to_be_visible(timeout=30000)
    assert page.get_by_text("saved for reuse").count() >= 1
    assert page.get_by_text("could not be saved").count() == 0
    expect(page.get_by_text("Load a saved severity model").first).to_be_visible()
    expect(page.get_by_role("button", name="Load saved model")).to_be_visible()
    assert page.get_by_text(EMPTY_SEV).count() == 0
    no_exception(page)

    sev_id, sev_path = newest_saved_run(SEVERITY_FAMILIES)
    assert sev_id > freq_id and sev_path.exists()
    assert sev_path.name == f"run{sev_id:04d}_severity_gamma.pickle", sev_path.name
    ctx_a.close()
    print(f"TC4 PASS (precondition: {sev_precondition}; saved {sev_path.name})")

    # --- context B: TC5-TC8 (fresh session — the F5 simulation) ---------------
    ctx_b = browser.new_context()
    page = ctx_b.new_page()
    page.set_default_timeout(20000)

    # TC5 — THE HEADLINE: load the saved model, predict without refit
    page.goto(f"{URL}/Data_Import")
    page.get_by_role("button", name="Load dataset").click()
    expect(page.get_by_text("678,013").first).to_be_visible()
    page.get_by_role("link", name="Frequency Model").click()
    expect(page.get_by_text("Load a saved frequency model").first).to_be_visible()
    assert page.locator("[data-testid='stMetric']").count() == 0  # nothing fitted here
    t0 = time.perf_counter()
    page.get_by_role("button", name="Load saved model").click()
    expect(page.get_by_text("no refit needed").first).to_be_visible(timeout=30000)
    load_seconds = time.perf_counter() - t0
    assert page.get_by_text("Loaded run").count() >= 1
    expect(page.locator("[data-testid='stMetric']").first).to_be_visible()  # results in
    assert page.locator("[data-testid='stMetric']").count() >= 4  # meta from the DB row
    expect(page.get_by_text("Coefficients").first).to_be_visible()
    no_exception(page)

    page.get_by_role("link", name="Prediction").click()
    expect(page.get_by_text("Single policy").first).to_be_visible()
    expect(page.get_by_text("Batch prediction").first).to_be_visible()
    page.get_by_role("button", name="Predict", exact=True).click()
    expect(page.get_by_text("Expected claim frequency").first).to_be_visible()
    page.get_by_role("button", name="Predict for loaded portfolio").click()
    expect(page.get_by_text("Total expected claims").first).to_be_visible(timeout=120000)
    expect(page.get_by_text("36,102").first).to_be_visible()
    expect(page.get_by_text("by construction").first).to_be_visible()
    no_exception(page)

    page.get_by_role("link", name="Diagnostics").click()
    expect(page.get_by_text("Coefficients with confidence intervals").first).to_be_visible(
        timeout=60000
    )
    expect(page.locator("[data-testid='stMetric']").first).to_be_visible()
    assert page.locator("[data-testid='stMetric']").count() >= 4
    expect(page.locator("[data-testid='stVegaLiteChart']").first).to_be_visible()
    assert page.locator("[data-testid='stVegaLiteChart']").count() >= 1
    expect(page.get_by_text("Coefficient table").first).to_be_visible()
    expect(page.get_by_text(LOADED_HINT).first).to_be_visible()
    # absence via section LABELS — the hint itself names residuals/QQ/summary
    assert page.get_by_text("Residual kind").count() == 0
    assert page.get_by_text("Observed vs Predicted").count() == 0
    assert page.get_by_text("Calibration table").count() == 0
    assert page.get_by_text("Full statsmodels summary").count() == 0
    no_exception(page)
    print(f"TC5 PASS (load took {load_seconds:.1f}s — no refit)")

    # TC6 — a fresh fit flips source back: full diagnostics return
    page.get_by_role("link", name="Frequency Model").click()
    page.get_by_role("button", name="Fit model").click()
    expect(page.get_by_text("Model fitted and recorded").first).to_be_visible(timeout=180000)
    assert page.get_by_text("saved for reuse").count() >= 1
    page.get_by_role("link", name="Diagnostics").click()
    expect(page.get_by_text("Observed vs Predicted").first).to_be_visible(timeout=60000)
    expect(page.get_by_text("Residual kind").first).to_be_visible()
    expect(page.get_by_text("Calibration table").first).to_be_visible()
    expect(page.get_by_text("Full statsmodels summary").first).to_be_visible()
    expect(page.locator("[data-testid='stVegaLiteChart']").nth(1)).to_be_visible()
    assert page.locator("[data-testid='stVegaLiteChart']").count() >= 2
    assert page.get_by_text("This model was loaded from the run history").count() == 0
    no_exception(page)
    print("TC6 PASS (full diagnostics back after the refit)")

    # TC7 — coexistence: LOADED severity + FITTED frequency
    load_builtin(page, "severity", "26,444")
    page.get_by_role("link", name="Severity Model").click()
    expect(page.get_by_text("Load a saved severity model").first).to_be_visible()
    assert page.locator("[data-testid='stMetric']").count() == 0
    page.get_by_role("button", name="Load saved model").click()
    expect(page.get_by_text("no refit needed").first).to_be_visible(timeout=30000)
    expect(page.locator("[data-testid='stMetric']").first).to_be_visible()  # results in
    assert page.locator("[data-testid='stMetric']").count() >= 4
    expect(page.get_by_text("Coefficients").first).to_be_visible()
    no_exception(page)

    page.get_by_role("link", name="Diagnostics").click()
    expect(page.get_by_text(LOADED_HINT).first).to_be_visible(timeout=60000)
    expect(page.locator("[data-testid='stMetric']").first).to_be_visible()
    assert page.locator("[data-testid='stMetric']").count() >= 4
    assert page.get_by_text("Residual kind").count() == 0
    no_exception(page)

    page.get_by_role("link", name="Prediction").click()
    expect(page.get_by_text("Single claim").first).to_be_visible()
    page.get_by_role("button", name="Predict for loaded claims").click()
    expect(page.get_by_text("Total expected claim amount").first).to_be_visible(timeout=60000)
    expect(page.get_by_text("does not reproduce").first).to_be_visible()
    assert page.get_by_text("Total expected claims").count() == 0  # stale freq batch hidden
    assert page.get_by_text("36,102").count() == 0
    no_exception(page)

    load_builtin(page, "frequency", "678,013")
    page.get_by_role("link", name="Diagnostics").click()
    expect(page.get_by_text("Residual kind").first).to_be_visible(timeout=60000)
    assert page.get_by_text("This model was loaded from the run history").count() == 0
    page.get_by_role("link", name="Prediction").click()
    expect(page.get_by_text("Single policy").first).to_be_visible()
    assert page.get_by_text("Total expected claim amount").count() == 0  # stale sev hidden
    no_exception(page)
    print("TC7 PASS (loaded severity + fitted frequency coexist)")

    # TC8 — missing pickle: friendly error, slot UNCHANGED
    newest_freq_id, newest_freq_path = newest_saved_run(FREQUENCY_FAMILIES)
    backup = newest_freq_path.with_suffix(".pickle.bak")
    newest_freq_path.rename(backup)
    try:
        page.get_by_role("link", name="Frequency Model").click()
        expect(page.get_by_text("Load a saved frequency model").first).to_be_visible()
        page.get_by_role("button", name="Load saved model").click()
        expect(page.get_by_text("Saved model file missing").first).to_be_visible(timeout=30000)
        no_exception(page)
        # the fitted Poisson slot is untouched by the failed load
        page.get_by_role("link", name="Diagnostics").click()
        expect(page.get_by_text("Residual kind").first).to_be_visible(timeout=60000)
        assert page.get_by_text("This model was loaded from the run history").count() == 0
        no_exception(page)
    finally:
        backup.rename(newest_freq_path)
    # executed-if-time (a): recovery re-load succeeds after the restore
    page.get_by_role("link", name="Frequency Model").click()
    expect(page.get_by_text("Load a saved frequency model").first).to_be_visible()
    page.get_by_role("button", name="Load saved model").click()
    expect(page.get_by_text("no refit needed").first).to_be_visible(timeout=30000)
    no_exception(page)
    print("TC8 PASS (missing pickle friendly, slot kept; recovery re-load OK)")

    browser.close()

# --- TC9: bracket — 3 new saved rows, old NULLs untouched ----------------------

with sqlite3.connect(DB_PATH) as raw:
    n1 = raw.execute("SELECT COUNT(*) FROM model_runs").fetchone()[0]
    schema1 = [r[1] for r in raw.execute("PRAGMA table_info(model_runs)")]
    new_rows = raw.execute(
        "SELECT id, family, model_path FROM model_runs WHERE id > ?", (max_id0,)
    ).fetchall()
    null_ids1 = {r[0] for r in raw.execute("SELECT id FROM model_runs WHERE model_path IS NULL")}
assert n1 - n0 == 3, (n0, n1)  # TC3 poisson, TC4 gamma, TC6 poisson refit
assert schema1 == schema0, (schema0, schema1)
for rid, fam, mpath in new_rows:
    assert mpath is not None, rid
    assert Path(mpath).exists(), mpath
    assert Path(mpath).name == f"run{rid:04d}_{family_kind(fam)}_{fam}.pickle", mpath
assert null_ids0 <= null_ids1  # loads never write paths; old NULLs untouched
assert null_ids1 - null_ids0 == set()  # and no new NULL rows either
print(f"TC9 PASS ({n0} -> {n1} runs, {len(null_ids0)} old NULL rows untouched)")

print("ALL EXECUTED TCs PASSED (TC10 run separately from the shell; TC11 deferred/manual)")
