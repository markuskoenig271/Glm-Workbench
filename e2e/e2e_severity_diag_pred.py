"""Executes the TCs from .planning/e2e-tests/severity-diagnostics-prediction.md.

Engine TCs (TC1-TC2) first, then UI TCs (TC3-TC10) — TC4-TC10 in ONE tab.
TC11 (pytest + the other runners) is run separately from the shell because
each runner launches its own app on port 8598. Run from the repo root:
    uv run python e2e/e2e_severity_diag_pred.py
"""

import numpy as np
from harness import streamlit_app
from playwright.sync_api import Page, expect, sync_playwright

from pricing_engine.data import load_dataset
from pricing_engine.diagnostics import (
    observed_vs_predicted,
    qq_data,
    residual_histogram,
    residuals,
)
from pricing_engine.glm import build_formula, fit_severity_glm
from pricing_engine.prediction import predict_severity

# --- TC1: predict_severity contract on the real severity data -----------------

df, spec = load_dataset("fremtpl2_sev")
assert len(df) == 26_444 and spec.kind == "severity" and spec.offset is None
model = fit_severity_glm(df, build_formula(spec))  # gamma default

batch = predict_severity(model, df, spec)
assert set(batch.columns) == set(df.columns) | {"expected_claim_amount"}, batch.columns
assert "expected_frequency" not in batch.columns and "expected_claims" not in batch.columns
assert "expected_claim_amount" not in df.columns  # copy, not mutation
assert len(batch) == 26_444

amounts = batch["expected_claim_amount"].to_numpy()
assert (amounts > 0).all() and np.isfinite(amounts).all()

fitted = np.asarray(model.fittedvalues)
assert abs(amounts.mean() - fitted.mean()) / fitted.mean() < 1e-6, (amounts.mean(), fitted.mean())
assert abs(amounts[0] - fitted[0]) / fitted[0] < 1e-6

mean_expected = float(amounts.mean())
assert abs(mean_expected - 2_230.9) / 2_230.9 < 0.01, mean_expected
assert abs(mean_expected - 2_265.5) / 2_265.5 < 0.05, mean_expected
observed_total = float(df[spec.target].sum())
expected_total = float(amounts.sum())
gap = (expected_total - observed_total) / observed_total
assert abs(gap) < 0.05, gap  # log-link Gamma: small shortfall expected, NOT exact balance

one = df.head(1)[list(spec.predictors)].copy()
single = predict_severity(model, one, spec)
assert len(single) == 1 and float(single["expected_claim_amount"].iloc[0]) > 0
assert abs(float(single["expected_claim_amount"].iloc[0]) - fitted[0]) / fitted[0] < 1e-6

with_exposure = df.head(5).assign(Exposure=0.5)
scaled = predict_severity(model, with_exposure, spec)["expected_claim_amount"]
assert np.allclose(scaled, fitted[:5])

try:
    predict_severity(model, df.drop(columns=["BonusMalus"]), spec)
    raise SystemExit("TC1 FAIL: no ValueError for missing predictor")
except ValueError as e:
    assert "BonusMalus" in str(e), e
print(
    f"TC1 PASS mean_expected={mean_expected:.1f} expected_total={expected_total:,.0f} "
    f"observed_total={observed_total:,.0f} gap={gap:+.2%}"
)

# --- TC2: severity calibration bands are average claim amounts ----------------

for res_kind in ("deviance", "pearson"):
    res = residuals(model, res_kind)
    assert len(res) == 26_444 and np.isfinite(res).all(), res_kind
hist = residual_histogram(model, bins=40)
assert hist["count"].sum() == 26_444
qq = qq_data(model, points=100)
assert len(qq) == 100 and (np.diff(qq["theoretical"]) > 0).all()

ovp = observed_vs_predicted(df, spec, model, groups=10)
assert len(ovp) <= 10
assert ovp["exposure"].sum() == 26_444, ovp["exposure"].sum()
assert (ovp["exposure"] > 0).all()
weighted_pred = (ovp["predicted_mean"] * ovp["exposure"]).sum() / 26_444
assert abs(weighted_pred - 2_230.9) / 2_230.9 < 0.01, weighted_pred
assert (ovp["predicted_mean"] > 500).all(), "values ~0.1 would mean an exposure divisor"
assert (np.diff(ovp["predicted_mean"]) >= 0).all()
assert ovp["observed_mean"].between(500, 10_000).all(), ovp["observed_mean"].tolist()
print(
    f"TC2 PASS bands={len(ovp)} weighted_pred={weighted_pred:.1f} "
    f"observed_band_range={ovp['observed_mean'].min():.0f}-"
    f"{ovp['observed_mean'].max():.0f}"
)

# --- UI TCs -------------------------------------------------------------------

MISMATCH_B = "The active model is a frequency model but the loaded dataset is a severity dataset"
MISMATCH_A = "The active model is a severity model but the loaded dataset is a frequency dataset"


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


expect.set_options(timeout=20000)

with streamlit_app() as URL, sync_playwright() as p:
    browser = p.chromium.launch()

    # TC3 — fresh-session guards on both pages (separate contexts; goto is the point)
    # V3 slice 1: no dataset loaded means no kind to select a model by — the pages
    # now show the dataset-first guard (the V2 dual "Fit a model first" wording retired)
    for page_path in ("Diagnostics", "Prediction"):
        ctx = browser.new_context()
        pg = ctx.new_page()
        pg.goto(f"{URL}/{page_path}")
        expect(pg.get_by_text("Load a dataset first").first).to_be_visible()
        assert pg.get_by_text("Fit a model first").count() == 0  # V2 wording gone
        assert pg.get_by_text("loaded dataset is a").count() == 0  # not a mismatch guard
        assert pg.locator("[data-testid='stMetric']").count() == 0
        assert pg.get_by_role("button", name="Predict", exact=True).count() == 0
        no_exception(pg)
        ctx.close()
    print("TC3 PASS")

    context = browser.new_context()
    page = context.new_page()
    page.set_default_timeout(20000)

    # TC4 — frequency baseline + stale-batch precondition
    page.goto(f"{URL}/Data_Import")
    page.get_by_role("button", name="Load dataset").click()
    expect(page.get_by_text("678,013 rows").first).to_be_visible()
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
    assert page.get_by_text("Poisson").count() >= 1
    assert page.get_by_text("next slice").count() == 0
    assert page.get_by_text("claim amount").count() == 0
    no_exception(page)

    page.get_by_role("link", name="Prediction").click()
    expect(page.get_by_text("Single policy").first).to_be_visible()
    expect(page.get_by_text("Batch prediction").first).to_be_visible()
    assert page.locator("[data-testid='stNumberInput']").count() >= 4
    page.get_by_role("button", name="Predict", exact=True).click()
    expect(page.get_by_text("Expected claim frequency").first).to_be_visible()
    page.get_by_role("button", name="Predict for loaded portfolio").click()
    expect(page.get_by_text("Total expected claims").first).to_be_visible(timeout=120000)
    expect(page.get_by_text("Total observed claims").first).to_be_visible()
    expect(page.get_by_text("36,102").first).to_be_visible()
    expect(page.get_by_text("Download predictions CSV").first).to_be_visible()
    assert page.get_by_text("claim amount").count() == 0
    assert page.get_by_text("Single claim").count() == 0
    assert page.get_by_text("next slice").count() == 0
    no_exception(page)
    print("TC4 PASS (frequency batch left in session state)")

    # TC5 — severity dataset loaded while the severity slot is still empty:
    # V3 slice 1 kind guard (the V2 mismatch guard is impossible by construction)
    load_builtin(page, "severity", "26,444 rows")
    page.get_by_role("link", name="Diagnostics").click()
    expect(page.get_by_text("Fit a severity model first").first).to_be_visible()
    assert page.get_by_text(MISMATCH_B).count() == 0  # retired V2 guard
    assert page.locator("[data-testid='stMetric']").count() == 0
    assert page.locator("[data-testid='stVegaLiteChart']").count() == 0
    assert page.get_by_text("Observed vs Predicted").count() == 0
    no_exception(page)

    page.get_by_role("link", name="Prediction").click()
    expect(page.get_by_text("Fit a severity model first").first).to_be_visible()
    assert page.get_by_text(MISMATCH_B).count() == 0  # retired V2 guard
    assert page.get_by_role("button", name="Predict", exact=True).count() == 0
    assert page.get_by_text("Single policy").count() == 0
    assert page.get_by_text("Single claim").count() == 0
    assert page.get_by_text("Total expected claims").count() == 0
    no_exception(page)
    print("TC5 PASS")

    # TC6 — severity fit
    page.get_by_role("link", name="Severity Model").click()
    expect(page.get_by_text("Model setup").first).to_be_visible()
    expect(page.get_by_text("ClaimAmount ~ Area").first).to_be_visible()
    page.get_by_role("button", name="Fit model").click()
    expect(page.get_by_text("Model fitted and recorded").first).to_be_visible(timeout=30000)
    no_exception(page)
    print("TC6 PASS")

    # TC7 — severity Diagnostics happy path
    page.get_by_role("link", name="Diagnostics").click()
    expect(page.get_by_text("Model summary").first).to_be_visible(timeout=60000)
    assert page.get_by_text("next slice").count() == 0
    assert page.get_by_text("loaded dataset is a").count() == 0
    metrics = page.locator("[data-testid='stMetric']")
    expect(metrics.first).to_be_visible()
    assert metrics.count() == 4, metrics.count()
    expect(page.get_by_text("ClaimAmount ~").first).to_be_visible()
    expect(page.get_by_text("gamma").first).to_be_visible()
    expect(page.get_by_text("Coefficients with confidence intervals").first).to_be_visible()
    expect(page.get_by_text("Coefficient table").first).to_be_visible()
    assert page.get_by_text("claim-size").count() + page.get_by_text("claim amount").count() >= 1
    expect(page.get_by_text("Residuals").first).to_be_visible()
    assert page.locator("[data-testid='stRadio']").count() >= 1
    assert page.get_by_text("mostly zero claims").count() == 0
    assert (
        page.get_by_text("heavy").count()
        + page.get_by_text("skew").count()
        + page.get_by_text("large claims").count()
    ) >= 1
    expect(page.get_by_text("QQ plot").first).to_be_visible()
    expect(page.get_by_text("Observed vs Predicted").first).to_be_visible()
    expect(page.get_by_text("Average claim amount").first).to_be_visible()
    expect(page.get_by_text("Predicted-claim-amount band").first).to_be_visible()
    expect(page.get_by_text("Calibration table").first).to_be_visible()
    assert page.locator("[data-testid='stVegaLiteChart']").count() >= 4
    assert page.get_by_text("claim frequency").count() == 0
    assert page.get_by_text("policy-year").count() == 0
    assert page.get_by_text("predicted-frequency band").count() == 0
    assert page.get_by_text("claim amount").count() >= 1
    no_exception(page)
    print("TC7 PASS")

    # TC8 — severity Prediction: single claim + batch + stale frequency batch hidden
    page.get_by_role("link", name="Prediction").click()
    expect(page.get_by_text("Single claim").first).to_be_visible()
    expect(page.get_by_text("Batch prediction").first).to_be_visible()
    assert page.get_by_text("Single policy").count() == 0
    assert page.locator("[data-testid='stSelectbox']").count() >= 4
    assert page.locator("[data-testid='stNumberInput']").count() >= 4
    assert page.get_by_text("policy-year").count() == 0
    assert page.get_by_text("Exposure (policy-years)").count() == 0
    assert page.get_by_text("Total expected claims").count() == 0  # stale freq batch hidden
    assert page.get_by_text("36,102").count() == 0
    assert page.get_by_text("Mean expected frequency").count() == 0
    assert page.get_by_text("next slice").count() == 0
    no_exception(page)

    page.get_by_role("button", name="Predict", exact=True).click()
    expect(page.get_by_text("Expected claim amount").first).to_be_visible()
    assert page.get_by_text("Expected claims").count() == 0
    assert page.get_by_text("Expected claim frequency").count() == 0
    single_metric = page.locator("[data-testid='stMetricValue']").first.inner_text()

    page.get_by_role("button", name="Predict for loaded claims").click()
    expect(page.get_by_text("Mean expected claim amount").first).to_be_visible(timeout=60000)
    expect(page.get_by_text("Total expected claim amount").first).to_be_visible()
    expect(page.get_by_text("Total observed claim amount").first).to_be_visible()
    assert page.locator("[data-testid='stMetric']").count() >= 3
    expect(page.get_by_text("does not reproduce").first).to_be_visible()
    assert page.get_by_text("by construction").count() == 0
    expect(page.locator("[data-testid='stDataFrame']").first).to_be_visible()
    expect(page.get_by_text("Download predictions CSV").first).to_be_visible()
    assert page.get_by_text("Total expected claims").count() == 0
    assert page.get_by_text("claim frequency").count() == 0
    assert page.get_by_text("policy-year").count() == 0
    assert page.get_by_text("next slice").count() == 0
    no_exception(page)
    batch_values = [el.inner_text() for el in page.locator("[data-testid='stMetricValue']").all()]
    print(f"TC8 PASS single-claim metric={single_metric!r} batch metrics={batch_values}")

    # TC9 — frequency dataset loaded again: with per-kind slots (V3 slice 1) the
    # Poisson model from TC4 is STILL ALIVE — frequency views render with NO refit
    # (in V2 this exact step showed the mismatch guard)
    load_builtin(page, "frequency", "678,013 rows")
    page.get_by_role("link", name="Diagnostics").click()
    expect(page.get_by_text("Model summary").first).to_be_visible(timeout=60000)
    assert page.get_by_text(MISMATCH_A).count() == 0  # retired V2 guard
    assert page.get_by_text("claim frequency").count() >= 1
    assert page.get_by_text("claim amount").count() == 0
    assert page.locator("[data-testid='stMetric']").count() >= 4
    no_exception(page)

    page.get_by_role("link", name="Prediction").click()
    expect(page.get_by_text("Single policy").first).to_be_visible()
    assert page.get_by_text(MISMATCH_A).count() == 0  # retired V2 guard
    assert page.get_by_text("Single claim").count() == 0
    assert page.get_by_text("Total expected claim amount").count() == 0  # stale sev batch hidden
    no_exception(page)
    print("TC9 PASS (frequency model survived the severity fit — per-kind slots)")

    # TC10 — refitting frequency updates its slot; views still render
    page.get_by_role("link", name="Frequency Model").click()
    page.get_by_role("button", name="Fit model").click()
    expect(page.get_by_text("Model fitted and recorded").first).to_be_visible(timeout=180000)

    page.get_by_role("link", name="Diagnostics").click()
    expect(page.get_by_text("Model summary").first).to_be_visible(timeout=60000)
    expect(page.get_by_text("Observed vs Predicted").first).to_be_visible()
    assert page.get_by_text("loaded dataset is a").count() == 0
    assert page.get_by_text("claim frequency").count() >= 1
    assert page.get_by_text("claim amount").count() == 0
    assert page.locator("[data-testid='stMetric']").count() >= 4
    no_exception(page)

    page.get_by_role("link", name="Prediction").click()
    expect(page.get_by_text("Single policy").first).to_be_visible()
    expect(page.get_by_text("Batch prediction").first).to_be_visible()
    assert page.get_by_text("Single claim").count() == 0
    assert page.get_by_text("Total expected claim amount").count() == 0  # stale sev batch hidden
    no_exception(page)
    print("TC10 PASS")

    browser.close()

print("ALL EXECUTED TCs PASSED (TC11 run separately from the shell; TC12 deferred/manual)")
