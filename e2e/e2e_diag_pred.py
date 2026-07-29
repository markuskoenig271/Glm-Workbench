"""Executes the TCs from diagnostics.md and prediction.md E2E plans.

One shared real fit for the engine TCs; one browser session for both pages.
Run from the repo root:
    uv run python e2e/e2e_diag_pred.py
"""

import time

import numpy as np
from harness import streamlit_app
from playwright.sync_api import expect, sync_playwright

from pricing_engine.data import load_dataset
from pricing_engine.diagnostics import (
    observed_vs_predicted,
    qq_data,
    residual_histogram,
    residuals,
)
from pricing_engine.glm import build_formula, fit_frequency_glm
from pricing_engine.prediction import predict_frequency

df, spec = load_dataset("fremtpl2_freq")
model = fit_frequency_glm(df, build_formula(spec), offset_column=spec.offset)
assert model.converged

# --- Diagnostics engine TC ---------------------------------------------------

t0 = time.perf_counter()
res = residuals(model, "deviance")
assert len(res) == 678_013
res_p = residuals(model, "pearson")
assert len(res_p) == 678_013
try:
    residuals(model, "studentized")
    raise SystemExit("FAIL: no ValueError for bad residual kind")
except ValueError as e:
    assert "deviance" in str(e), e

hist = residual_histogram(model, bins=40)
assert len(hist) <= 40
assert hist["count"].sum() == 678_013

qq = qq_data(model, points=100)
assert len(qq) == 100
assert (np.diff(qq["theoretical"]) > 0).all()

ovp = observed_vs_predicted(df, spec, model, groups=10)
assert len(ovp) <= 10
total_exposure = df[spec.offset].sum()
assert abs(ovp["exposure"].sum() - total_exposure) / total_exposure < 0.01
weighted_pred = (ovp["predicted_frequency"] * ovp["exposure"]).sum() / ovp["exposure"].sum()
assert abs(weighted_pred - 0.1007) / 0.1007 < 0.01, weighted_pred
assert (np.diff(ovp["predicted_frequency"]) >= 0).all()
assert ovp["observed_frequency"].iloc[-1] > ovp["observed_frequency"].iloc[0]
diag_seconds = time.perf_counter() - t0
assert diag_seconds < 10, f"diagnostics too slow: {diag_seconds:.1f}s"
print(f"DIAG ENGINE TC PASS ({diag_seconds:.2f}s, weighted predicted freq {weighted_pred:.4f})")

# --- Prediction engine TC ----------------------------------------------------

t0 = time.perf_counter()
batch = predict_frequency(model, df, spec)
predict_seconds = time.perf_counter() - t0
assert predict_seconds < 30, f"predict too slow: {predict_seconds:.1f}s"
observed_total = df[spec.target].sum()
assert observed_total == 36_102, observed_total
expected_total = batch["expected_claims"].sum()
assert abs(expected_total - observed_total) / observed_total < 0.005, expected_total
assert (batch["expected_frequency"] > 0).all()
assert np.isfinite(batch["expected_frequency"]).all()
assert "expected_frequency" not in df.columns  # copy, not mutation

one = df.head(1)
single = predict_frequency(model, one, spec)
assert len(single) == 1
assert float(single["expected_claims"].iloc[0]) == float(
    single["expected_frequency"].iloc[0] * one["Exposure"].iloc[0]
)

try:
    predict_frequency(model, df.drop(columns=["BonusMalus"]), spec)
    raise SystemExit("FAIL: no ValueError for missing predictor")
except ValueError as e:
    assert "BonusMalus" in str(e), e
print(
    f"PRED ENGINE TC PASS ({predict_seconds:.1f}s, expected total {expected_total:,.0f} "
    f"vs observed {observed_total:,})"
)

# --- UI TCs -------------------------------------------------------------------

expect.set_options(timeout=20000)

with streamlit_app() as URL, sync_playwright() as p:
    browser = p.chromium.launch()

    # Guard TCs — fresh contexts
    for page_path in ("Diagnostics", "Prediction"):
        ctx = browser.new_context()
        pg = ctx.new_page()
        pg.goto(f"{URL}/{page_path}")
        expect(pg.get_by_text("Fit a model first").first).to_be_visible()
        assert pg.get_by_text("Load a dataset first").count() == 0
        assert pg.locator("[data-testid='stException']").count() == 0
        ctx.close()
    print("GUARD TCs PASS (both pages)")

    # Main session: load -> fit -> Diagnostics -> Prediction
    context = browser.new_context()
    page = context.new_page()
    page.goto(f"{URL}/Data_Import")
    page.get_by_role("button", name="Load dataset").click()
    expect(page.get_by_text("Loaded freMTPL2")).to_be_visible()
    page.get_by_role("link", name="Frequency Model").click()
    page.get_by_role("button", name="Fit model").click()
    expect(page.get_by_text("Model fitted and recorded").first).to_be_visible(timeout=180000)
    print("SETUP TC PASS")

    # Diagnostics sections
    page.get_by_role("link", name="Diagnostics").click()
    expect(page.get_by_text("Model summary").first).to_be_visible(timeout=60000)
    expect(page.get_by_text("Coefficients with confidence intervals").first).to_be_visible()
    expect(page.get_by_text("Residuals").first).to_be_visible()
    expect(page.get_by_text("QQ plot").first).to_be_visible()
    expect(page.get_by_text("Observed vs Predicted").first).to_be_visible()
    assert page.locator("[data-testid='stVegaLiteChart']").count() >= 2
    assert page.locator("[data-testid='stMetric']").count() >= 4
    assert page.locator("[data-testid='stException']").count() == 0
    print("DIAG SECTIONS TC PASS")

    # Prediction: single policy with defaults
    page.get_by_role("link", name="Prediction").click()
    expect(page.get_by_text("Single policy").first).to_be_visible()
    # "Batch prediction" renders after all input widgets — await it first
    expect(page.get_by_text("Batch prediction").first).to_be_visible()
    assert page.locator("[data-testid='stNumberInput']").count() >= 4
    assert page.locator("[data-testid='stSelectbox']").count() >= 4
    page.get_by_role("button", name="Predict", exact=True).click()
    expect(page.get_by_text("Expected claim frequency").first).to_be_visible()
    print("SINGLE POLICY TC PASS")

    # Prediction: batch
    page.get_by_role("button", name="Predict for loaded portfolio").click()
    expect(page.get_by_text("Total expected claims").first).to_be_visible(timeout=120000)
    expect(page.get_by_text("Total observed claims").first).to_be_visible()
    expect(page.get_by_text("36,102").first).to_be_visible()
    assert page.locator("[data-testid='stMetric']").count() >= 3
    expect(page.get_by_text("Download predictions CSV").first).to_be_visible()
    assert page.locator("[data-testid='stException']").count() == 0
    print("BATCH TC PASS (download button visible, not clicked — 678k payload)")

    browser.close()

print("ALL EXECUTED TCs PASSED (widget-change TCs deferred/manual per plans)")
