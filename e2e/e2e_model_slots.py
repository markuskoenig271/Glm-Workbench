"""Executes the TCs from .planning/e2e-tests/per-kind-model-slots.md (V3 slice 1).

Engine TCs (TC1-TC2) and the TC12 run-history snapshot first, then UI TCs
(TC3-TC11) — TC4-TC11 in ONE tab. TC13 (pytest + the other runners) is run
separately from the shell because each runner launches its own app on port
8598. TC14 is deferred/manual. Run from the repo root:
    uv run python e2e/e2e_model_slots.py
"""

import sqlite3
from pathlib import Path

import numpy as np
from harness import streamlit_app
from playwright.sync_api import Page, expect, sync_playwright

from pricing_engine.data import load_dataset
from pricing_engine.diagnostics import observed_vs_predicted
from pricing_engine.glm import build_formula, fit_frequency_glm, fit_severity_glm
from pricing_engine.prediction import predict_frequency

# --- TC1: observed_vs_predicted rename on the frequency model ------------------

df_freq, spec_freq = load_dataset("fremtpl2_freq")
assert len(df_freq) == 678_013 and spec_freq.kind == "frequency"
model_freq = fit_frequency_glm(df_freq, build_formula(spec_freq), offset_column=spec_freq.offset)
assert model_freq.converged

ovp = observed_vs_predicted(df_freq, spec_freq, model_freq, groups=10)
assert "observed_mean" in ovp.columns and "predicted_mean" in ovp.columns, ovp.columns
assert "observed_frequency" not in ovp.columns and "predicted_frequency" not in ovp.columns
assert len(ovp) <= 10

total_exposure = df_freq[spec_freq.offset].sum()
assert abs(ovp["exposure"].sum() - total_exposure) / total_exposure < 0.01
weighted_pred = (ovp["predicted_mean"] * ovp["exposure"]).sum() / ovp["exposure"].sum()
assert abs(weighted_pred - 0.1007) / 0.1007 < 0.01, weighted_pred
assert (np.diff(ovp["predicted_mean"]) >= 0).all()
assert ovp["observed_mean"].iloc[-1] > ovp["observed_mean"].iloc[0]

batch = predict_frequency(model_freq, df_freq, spec_freq)
total_expected = float(batch["expected_claims"].sum())
assert abs(total_expected - 36_102) / 36_102 < 0.01, total_expected
print(f"TC1 PASS weighted_pred={weighted_pred:.4f} total_expected={total_expected:,.0f}")

# --- TC2: severity calibration values survive the rename -----------------------

df_sev, spec_sev = load_dataset("fremtpl2_sev")
assert len(df_sev) == 26_444 and spec_sev.kind == "severity" and spec_sev.offset is None
model_sev = fit_severity_glm(df_sev, build_formula(spec_sev))  # gamma default

ovp = observed_vs_predicted(df_sev, spec_sev, model_sev, groups=10)
assert "observed_mean" in ovp.columns and "predicted_mean" in ovp.columns, ovp.columns
assert "observed_frequency" not in ovp.columns and "predicted_frequency" not in ovp.columns
assert len(ovp) <= 10
assert ovp["exposure"].sum() == 26_444, ovp["exposure"].sum()
weighted_pred = (ovp["predicted_mean"] * ovp["exposure"]).sum() / 26_444
assert abs(weighted_pred - 2_230.9) / 2_230.9 < 0.01, weighted_pred
assert (ovp["predicted_mean"] > 500).all(), "values ~0.1 would mean an exposure divisor"
assert (np.diff(ovp["predicted_mean"]) >= 0).all()
assert ovp["observed_mean"].between(500, 10_000).all(), ovp["observed_mean"].tolist()
print(
    f"TC2 PASS bands={len(ovp)} weighted_pred={weighted_pred:.1f} "
    f"observed_band_range={ovp['observed_mean'].min():.0f}-{ovp['observed_mean'].max():.0f}"
)

# --- TC12 snapshot: run-history count + schema BEFORE the UI flow --------------

DB_PATH = Path("data") / "workbench.db"


def run_history_state() -> tuple[int, list[str]]:
    if not DB_PATH.exists():
        return 0, []
    with sqlite3.connect(DB_PATH) as conn:
        n = conn.execute("SELECT COUNT(*) FROM model_runs").fetchone()[0]
        cols = [row[1] for row in conn.execute("PRAGMA table_info(model_runs)")]
    return n, cols


n0, schema0 = run_history_state()
print(f"TC12 snapshot: {n0} runs before the UI flow")

# --- UI TCs -------------------------------------------------------------------

GUARD_NO_DATASET = "Load a dataset first — go to Data Import."
GUARD_NO_FREQ = "Fit a frequency model first — go to Frequency Model."
GUARD_NO_SEV = "Fit a severity model first — go to Severity Model."
RETIRED_MISMATCH = "The active model is a"
RETIRED_MISMATCH_TAIL = "but the loaded dataset is a"
RETIRED_DUAL_TAIL = "or Severity Model."


def no_exception(page: Page) -> None:
    assert page.get_by_text("Traceback").count() == 0
    assert page.locator("[data-testid='stException']").count() == 0


def no_retired_guards(page: Page) -> None:
    assert page.get_by_text(RETIRED_MISMATCH).count() == 0
    assert page.get_by_text(RETIRED_MISMATCH_TAIL).count() == 0
    assert page.get_by_text(RETIRED_DUAL_TAIL).count() == 0


def load_builtin(page: Page, fragment: str, rows_text: str) -> None:
    """Sanctioned combobox route: click the dataset selectbox, type, Enter, load."""
    page.get_by_role("link", name="Data Import").click()
    expect(page.get_by_text("Built-in dataset").first).to_be_visible()
    page.locator("[data-testid='stSelectbox']").first.click()
    page.keyboard.type(fragment)
    page.keyboard.press("Enter")
    page.get_by_role("button", name="Load dataset").click()
    expect(page.get_by_text(rows_text).first).to_be_visible()


expect.set_options(timeout=20000)

with streamlit_app() as URL, sync_playwright() as p:
    browser = p.chromium.launch()

    # TC3 — fresh-session guard is DATASET-first (inverted from V2)
    for page_path in ("Diagnostics", "Prediction"):
        ctx = browser.new_context()
        pg = ctx.new_page()
        pg.goto(f"{URL}/{page_path}")
        expect(pg.get_by_text(GUARD_NO_DATASET).first).to_be_visible()
        assert pg.get_by_text("Fit a frequency model first").count() == 0
        assert pg.get_by_text("Fit a severity model first").count() == 0
        no_retired_guards(pg)
        assert pg.locator("[data-testid='stMetric']").count() == 0
        assert pg.get_by_role("button", name="Predict", exact=True).count() == 0
        no_exception(pg)
        ctx.close()
    print("TC3 PASS")

    context = browser.new_context()
    page = context.new_page()
    page.set_default_timeout(20000)

    # TC4 — frequency loaded, nothing fitted → per-kind guard
    page.goto(f"{URL}/Data_Import")
    page.get_by_role("button", name="Load dataset").click()
    expect(page.get_by_text("678,013").first).to_be_visible()
    for link in ("Diagnostics", "Prediction"):
        page.get_by_role("link", name=link).click()
        expect(page.get_by_text(GUARD_NO_FREQ).first).to_be_visible()
        assert page.get_by_text("Fit a severity model first").count() == 0
        assert page.get_by_text(GUARD_NO_DATASET).count() == 0
        no_retired_guards(page)
        assert page.locator("[data-testid='stMetric']").count() == 0
        assert page.get_by_role("button", name="Predict", exact=True).count() == 0
        assert page.get_by_text("Single policy").count() == 0
        assert page.get_by_text("Single claim").count() == 0
        no_exception(page)
    print("TC4 PASS")

    # TC5 — Poisson fit, frequency baseline, stale-batch precondition
    page.get_by_role("link", name="Frequency Model").click()
    page.get_by_role("button", name="Fit model").click()
    expect(page.get_by_text("Model fitted and recorded").first).to_be_visible(timeout=180000)

    page.get_by_role("link", name="Diagnostics").click()
    expect(page.get_by_text("Model summary").first).to_be_visible(timeout=60000)
    for section in (
        "Coefficients with confidence intervals",
        "Residuals",
        "QQ plot",
        "Observed vs Predicted",
    ):
        expect(page.get_by_text(section).first).to_be_visible()
    assert page.locator("[data-testid='stVegaLiteChart']").count() >= 2
    assert page.locator("[data-testid='stMetric']").count() >= 4
    assert page.get_by_text("claim frequency").count() >= 1
    assert page.get_by_text("mostly zero claims").count() >= 1
    assert page.get_by_text("claim amount").count() == 0
    no_retired_guards(page)
    no_exception(page)

    page.get_by_role("link", name="Prediction").click()
    expect(page.get_by_text("Single policy").first).to_be_visible()
    expect(page.get_by_text("Batch prediction").first).to_be_visible()
    assert page.locator("[data-testid='stNumberInput']").count() >= 4
    page.get_by_role("button", name="Predict", exact=True).click()
    expect(page.get_by_text("Expected claim frequency").first).to_be_visible()
    page.get_by_role("button", name="Predict for loaded portfolio").click()
    expect(page.get_by_text("Total expected claims").first).to_be_visible(timeout=120000)
    expect(page.get_by_text("36,102").first).to_be_visible()
    assert page.get_by_text("by construction").count() >= 1
    expect(page.get_by_text("Download predictions CSV").first).to_be_visible()
    no_exception(page)
    print("TC5 PASS (frequency batch left in session state)")

    # TC6 — severity dataset + only-frequency-fitted → kind guard, not mismatch
    load_builtin(page, "severity", "26,444")
    for link in ("Diagnostics", "Prediction"):
        page.get_by_role("link", name=link).click()
        expect(page.get_by_text(GUARD_NO_SEV).first).to_be_visible()
        no_retired_guards(page)
        assert page.locator("[data-testid='stMetric']").count() == 0
        assert page.locator("[data-testid='stVegaLiteChart']").count() == 0
        assert page.get_by_role("button", name="Predict", exact=True).count() == 0
        assert page.get_by_text("Total expected claims").count() == 0  # stale batch hidden
        assert page.get_by_text("36,102").count() == 0
        no_exception(page)

    page.get_by_role("link", name="Frequency Model").click()
    expect(page.get_by_text("severity dataset").first).to_be_visible()
    assert page.get_by_role("button", name="Fit model").count() == 0
    assert page.locator("[data-testid='stMetric']").count() == 0
    no_exception(page)
    print("TC6 PASS")

    # TC7 — Gamma fit: second slot filled, 07 keeps its results
    page.get_by_role("link", name="Severity Model").click()
    expect(page.get_by_text("Model setup").first).to_be_visible()
    expect(page.get_by_text("ClaimAmount ~").first).to_be_visible()
    page.get_by_role("button", name="Fit model").click()
    expect(page.get_by_text("Model fitted and recorded").first).to_be_visible(timeout=30000)
    assert page.locator("[data-testid='stMetric']").count() >= 4
    expect(page.get_by_text("Coefficients").first).to_be_visible()
    no_exception(page)
    print("TC7 PASS")

    # TC8 — severity Diagnostics + Prediction render from the severity slot
    page.get_by_role("link", name="Diagnostics").click()
    expect(page.get_by_text("Model summary").first).to_be_visible(timeout=60000)
    assert page.get_by_text("Fit a severity model first").count() == 0
    no_retired_guards(page)
    assert page.locator("[data-testid='stMetric']").count() >= 4
    expect(page.get_by_text("ClaimAmount ~").first).to_be_visible()
    expect(page.get_by_text("Average claim amount").first).to_be_visible()
    expect(page.get_by_text("Predicted-claim-amount band").first).to_be_visible()
    expect(page.get_by_text("Calibration table").first).to_be_visible()
    page.get_by_text("Calibration table").first.click()  # re-based rename must not KeyError
    # .first would hit the HIDDEN grid inside the collapsed "Coefficient table"
    # expander above — filter to visible grids (the opened calibration table)
    expect(page.locator("[data-testid='stDataFrame'] >> visible=true").first).to_be_visible()
    assert page.locator("[data-testid='stVegaLiteChart']").count() >= 4
    assert page.get_by_text("claim frequency").count() == 0
    assert page.get_by_text("policy-year").count() == 0
    assert page.get_by_text("mostly zero claims").count() == 0
    no_exception(page)

    page.get_by_role("link", name="Prediction").click()
    expect(page.get_by_text("Single claim").first).to_be_visible()
    assert page.get_by_text("Single policy").count() == 0
    assert page.get_by_text("policy-year").count() == 0
    assert page.get_by_text("Total expected claims").count() == 0  # stale freq batch hidden
    assert page.get_by_text("36,102").count() == 0
    page.get_by_role("button", name="Predict", exact=True).click()
    expect(page.get_by_text("Expected claim amount").first).to_be_visible()
    assert page.get_by_text("Expected claim frequency").count() == 0
    page.get_by_role("button", name="Predict for loaded claims").click()
    expect(page.get_by_text("Mean expected claim amount").first).to_be_visible(timeout=60000)
    expect(page.get_by_text("Total expected claim amount").first).to_be_visible()
    expect(page.get_by_text("does not reproduce").first).to_be_visible()
    assert page.get_by_text("by construction").count() == 0
    expect(page.locator("[data-testid='stDataFrame']").first).to_be_visible()
    no_exception(page)
    print("TC8 PASS (severity batch left in session state)")

    # TC9 — THE HEADLINE: switch back to frequency WITHOUT refit → live Poisson views
    load_builtin(page, "frequency", "678,013")
    page.get_by_role("link", name="Diagnostics").click()
    expect(page.get_by_text("Model summary").first).to_be_visible(timeout=60000)
    no_retired_guards(page)
    assert page.get_by_text("Fit a frequency model first").count() == 0
    assert page.locator("[data-testid='stMetric']").count() >= 4
    assert page.locator("[data-testid='stVegaLiteChart']").count() >= 2
    assert page.get_by_text("claim frequency").count() >= 1
    assert page.get_by_text("claim amount").count() == 0
    no_exception(page)

    page.get_by_role("link", name="Prediction").click()
    expect(page.get_by_text("Single policy").first).to_be_visible()
    expect(page.get_by_text("Batch prediction").first).to_be_visible()  # widgets rendered
    expect(page.get_by_role("button", name="Predict", exact=True)).to_be_visible()
    assert page.get_by_text("Single claim").count() == 0
    assert page.get_by_text("Total expected claim amount").count() == 0  # stale sev batch hidden
    assert page.get_by_text("Mean expected claim amount").count() == 0
    no_exception(page)

    page.get_by_role("link", name="Frequency Model").click()
    expect(page.get_by_text("Coefficients").first).to_be_visible()  # kept results, no guard
    assert page.locator("[data-testid='stMetric']").count() >= 4
    no_exception(page)
    print("TC9 PASS (frequency views back with NO refit — per-kind slots)")

    # TC10 — arbitrary switching: severity again, 07 keeps its results
    load_builtin(page, "severity", "26,444")
    page.get_by_role("link", name="Diagnostics").click()
    expect(page.get_by_text("Model summary").first).to_be_visible(timeout=60000)
    expect(page.get_by_text("ClaimAmount ~").first).to_be_visible()
    assert page.get_by_text("claim frequency").count() == 0
    no_retired_guards(page)
    no_exception(page)

    page.get_by_role("link", name="Severity Model").click()
    expect(page.get_by_text("Coefficients").first).to_be_visible()  # kept results, no guard
    assert page.locator("[data-testid='stMetric']").count() >= 4
    no_exception(page)
    print("TC10 PASS")

    # TC11 — Poisson refit does not evict the Gamma slot
    load_builtin(page, "frequency", "678,013")
    page.get_by_role("link", name="Frequency Model").click()
    page.get_by_role("button", name="Fit model").click()
    expect(page.get_by_text("Model fitted and recorded").first).to_be_visible(timeout=180000)
    load_builtin(page, "severity", "26,444")
    page.get_by_role("link", name="Diagnostics").click()
    expect(page.get_by_text("Model summary").first).to_be_visible(timeout=60000)
    assert page.get_by_text("Fit a severity model first").count() == 0
    expect(page.get_by_text("ClaimAmount ~").first).to_be_visible()
    no_exception(page)
    print("TC11 PASS (Poisson refit kept the Gamma slot)")

    browser.close()

# --- TC12: run history appended exactly one row per successful fit -------------

n1, schema1 = run_history_state()
fits_performed = 3  # TC5 Poisson + TC7 Gamma + TC11 Poisson refit
assert n1 - n0 == fits_performed, (n0, n1)
assert schema1 == schema0 or n0 == 0, (schema0, schema1)
print(f"TC12 PASS ({n0} -> {n1} runs, schema unchanged)")

print("ALL EXECUTED TCs PASSED (TC13 run separately from the shell; TC14 deferred/manual)")
