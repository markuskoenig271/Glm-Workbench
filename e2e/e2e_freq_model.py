"""Executes the TCs from .planning/e2e-tests/frequency-model.md (TC8 deferred).

Run from the repo root:
    uv run python e2e/e2e_freq_model.py

Note: the UI TCs append two real runs to the run history in data/workbench.db
(that is the behavior under test); the storage TC uses throwaway temp DBs.
"""

import os
import tempfile
import time
from pathlib import Path

import numpy as np
from harness import streamlit_app
from playwright.sync_api import expect, sync_playwright

from pricing_engine import storage
from pricing_engine.data import load_dataset
from pricing_engine.diagnostics import coefficient_table, information_criteria
from pricing_engine.glm import build_formula, fit_frequency_glm

# --- TC6: engine truths on the real fit --------------------------------------

df, spec = load_dataset("fremtpl2_freq")
formula = build_formula(spec)
assert formula.startswith("ClaimNb ~ "), formula
assert "Exposure" not in formula, formula

t0 = time.perf_counter()
model = fit_frequency_glm(df, formula, family="poisson", offset_column="Exposure")
fit_seconds = time.perf_counter() - t0
assert fit_seconds < 120, f"fit too slow: {fit_seconds:.1f}s"
assert model.converged
assert int(model.nobs) == 678_013, model.nobs

base_frequency = float(np.exp(model.params["Intercept"]))
assert 0.01 < base_frequency < 0.3, base_frequency
assert model.params["BonusMalus"] > 0, model.params["BonusMalus"]
assert model.pvalues["BonusMalus"] < 1e-3, model.pvalues["BonusMalus"]

table = coefficient_table(model)
assert np.allclose(table["exp_coef"], np.exp(table["coef"]))
assert (table["significant"] == (table["p_value"] < 0.05)).all()
assert (table["ci_low"] <= table["coef"]).all() and (table["coef"] <= table["ci_high"]).all()

info = information_criteria(model)
assert all(np.isfinite(v) for v in info.values()), info
assert info["n_obs"] == 678_013

try:
    fit_frequency_glm(df, formula, family="gaussian")
    raise SystemExit("TC6 FAIL: no ValueError for gaussian")
except ValueError as e:
    assert "poisson" in str(e), e

print(
    f"TC6 PASS (fit {fit_seconds:.1f}s, base frequency exp(Intercept)={base_frequency:.4f}, "
    f"BonusMalus coef={model.params['BonusMalus']:.4f}, AIC={info['aic']:,.0f})"
)

# --- TC7: storage round-trip on temp DBs -------------------------------------

with tempfile.TemporaryDirectory() as tmp_dir:
    tmp_db_path = Path(tmp_dir) / "e2e_workbench.db"
    conn = storage.connect(tmp_db_path)
    common = dict(
        dataset="fremtpl2_freq",
        target="ClaimNb",
        offset="Exposure",
        family="poisson",
        n_obs=678_013,
        aic=info["aic"],
        bic=info["bic"],
        deviance=info["deviance"],
        log_likelihood=info["log_likelihood"],
        coefficients={"Intercept": -2.0},
    )
    storage.record_model_run(conn, formula="first", **common)
    storage.record_model_run(conn, formula="second", **common)
    runs = storage.list_model_runs(conn)
    assert list(runs["formula"]) == ["second", "first"]
    assert np.isfinite(runs["aic"]).all()
    conn.close()
    conn = storage.connect(tmp_db_path)  # reconnect: persistence
    assert len(storage.list_model_runs(conn)) == 2
    conn.close()

    override = Path(tmp_dir) / "e2e_override.db"
    os.environ["GLM_DB_PATH"] = str(override)
    conn = storage.connect()
    conn.close()
    assert override.exists()
    del os.environ["GLM_DB_PATH"]
print("TC7 PASS")

# --- UI TCs via Playwright ----------------------------------------------------

expect.set_options(timeout=20000)


def run_count() -> int:
    with storage.connect() as c:
        return len(storage.list_model_runs(c))


def wait_for_count(target: int, timeout_s: int = 180) -> None:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        if run_count() >= target:
            return
        time.sleep(2)
    raise SystemExit(f"FAIL: run count did not reach {target} (now {run_count()})")


n0 = run_count()

with streamlit_app() as URL, sync_playwright() as p:
    browser = p.chromium.launch()
    context = browser.new_context()
    page = context.new_page()

    # TC1 — guard
    page.goto(f"{URL}/Frequency_Model")
    expect(page.get_by_text("Load a dataset first").first).to_be_visible()
    assert page.get_by_text("Run history").count() == 0
    assert page.locator("[data-testid='stException']").count() == 0
    print("TC1 PASS")

    # TC2 — setup + formula preview
    page.get_by_role("link", name="Data Import").click()
    page.get_by_role("button", name="Load dataset").click()
    expect(page.get_by_text("Loaded freMTPL2")).to_be_visible()
    page.get_by_role("link", name="Frequency Model").click()
    expect(page.get_by_text("ClaimNb ~ Area").first).to_be_visible()
    expect(page.get_by_text("log(Exposure)").first).to_be_visible()
    print("TC2 PASS")

    # TC3 — fit happy path
    page.get_by_role("button", name="Fit model").click()
    expect(page.get_by_text("Model fitted and recorded").first).to_be_visible(timeout=180000)
    # wait on late-rendered sections first; counts don't auto-wait
    expect(page.get_by_text("Coefficients").first).to_be_visible()
    expect(page.get_by_text("risk relativity").first).to_be_visible()
    expect(page.get_by_text("Run history").first).to_be_visible()
    expect(page.locator("[data-testid='stMetric']").first).to_be_visible()
    assert page.locator("[data-testid='stMetric']").count() >= 4
    assert page.locator("[data-testid='stDataFrame']").count() >= 1
    wait_for_count(n0 + 1, timeout_s=30)
    print("TC3 PASS")

    # TC4 — second fit appends a run
    page.get_by_role("button", name="Fit model").click()
    wait_for_count(n0 + 2, timeout_s=180)
    print("TC4 PASS")

    # TC5 — spec change flows into the formula preview
    page.get_by_role("link", name="Feature Engineering").click()
    page.get_by_role("button", name="Create banded variable").click()
    expect(page.get_by_text("Added banded variable 'VehPower_band'").first).to_be_visible()
    page.get_by_role("link", name="Frequency Model").click()
    expect(page.get_by_text("VehPower_band").first).to_be_visible()
    print("TC5 PASS")

    browser.close()

print(f"ALL EXECUTED TCs PASSED (TC8 deferred/manual; run history {n0} -> {run_count()})")
