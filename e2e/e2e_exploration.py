"""Executes TC1-TC8 from .planning/e2e-tests/data-exploration.md (TC9 deferred).

Run from the repo root:
    uv run python e2e/e2e_exploration.py
"""

import time

import numpy as np
from harness import streamlit_app
from playwright.sync_api import expect, sync_playwright

from pricing_engine.data import load_dataset
from pricing_engine.exploration import (
    correlation_matrix,
    histogram,
    one_way_frequency,
    portfolio_frequency,
    summarize_portfolio,
)

# --- Engine-level TCs (TC7, TC8) --------------------------------------------

df, spec = load_dataset("fremtpl2_freq")
assert len(df) == 678_013, len(df)

f = portfolio_frequency(df, spec)
assert 0.09 < f < 0.11, f

summary = summarize_portfolio(df, spec)
assert len(summary) == len(spec.required_columns), (len(summary), spec.required_columns)

ow = one_way_frequency(df, spec, "Area")
assert len(ow) == 6, ow
assert (ow["exposure"] > 0).all(), ow
assert np.isfinite(ow["frequency"]).all(), ow

ow_age = one_way_frequency(df, spec, "DrivAge")
assert len(ow_age) <= 12, len(ow_age)
assert (ow_age["exposure"] > 0).all()

try:
    one_way_frequency(df, spec, "NotAColumn")
    raise SystemExit("TC7 FAIL: no ValueError raised")
except ValueError as e:
    assert "Area" in str(e), e

h_num = histogram(df, "DrivAge")
h_cat = histogram(df, "Area")
assert len(h_num) <= 30 and len(h_cat) == 6, (len(h_num), len(h_cat))
corr = correlation_matrix(df, spec)
assert corr.shape[0] == corr.shape[1] and corr.shape[0] >= 2, corr.shape
assert np.allclose(np.diag(corr), 1.0)
print("TC7 PASS", round(f, 4))

t0 = time.perf_counter()
summarize_portfolio(df, spec)
for p in spec.predictors:
    one_way_frequency(df, spec, p)
elapsed = time.perf_counter() - t0
assert elapsed < 5.0, f"too slow: {elapsed:.2f}s"
print(f"TC8 PASS {elapsed:.2f}s")

# --- UI TCs via Playwright ----------------------------------------------------

expect.set_options(timeout=20000)

with streamlit_app() as URL, sync_playwright() as p:
    browser = p.chromium.launch()
    context = browser.new_context()
    page = context.new_page()

    # TC1 — guard in a fresh session (direct goto is correct here)
    page.goto(f"{URL}/Data_Exploration")
    expect(page.get_by_text("Load a dataset first").first).to_be_visible()
    assert page.get_by_text("678").count() == 0
    assert page.locator("[data-testid='stMetric']").count() == 0
    assert page.get_by_text("Summary statistics").count() == 0
    assert page.get_by_text("Traceback").count() == 0
    assert page.locator("[data-testid='stException']").count() == 0
    print("TC1 PASS")

    # TC2 — load dataset, then sidebar to Data Exploration
    page.get_by_role("link", name="Data Import").click()
    page.get_by_role("button", name="Load dataset").click()
    expect(page.get_by_text("Loaded freMTPL2")).to_be_visible()
    page.get_by_role("link", name="Data Exploration").click()
    expect(page.get_by_text("Data Exploration").first).to_be_visible()
    assert page.get_by_text("Load a dataset first").count() == 0
    print("TC2 PASS")

    # TC3 — headline metrics
    metrics = page.locator("[data-testid='stMetric']")
    expect(metrics.first).to_be_visible()
    assert metrics.count() >= 4, metrics.count()
    expect(page.get_by_text("Policies").first).to_be_visible()
    expect(page.get_by_text("Total exposure").first).to_be_visible()
    expect(page.get_by_text("Total claims").first).to_be_visible()
    expect(page.get_by_text("Claim frequency").first).to_be_visible()
    expect(page.get_by_text("678,013").first).to_be_visible()
    expect(page.get_by_text("36,102").first).to_be_visible()
    expect(page.get_by_text("0.10").first).to_be_visible()
    print("TC3 PASS (labels: Policies / Total exposure / Total claims / Claim frequency)")

    # TC4 — summary statistics
    expect(page.get_by_text("Summary statistics").first).to_be_visible()
    assert page.locator("[data-testid='stDataFrame']").count() >= 1
    print("TC4 PASS")

    # TC5 — one-way section: header, selectbox, chart, table
    expect(page.get_by_text("One-way claim frequency").first).to_be_visible()
    assert page.locator("[data-testid='stSelectbox']").count() >= 1
    charts = page.locator("[data-testid='stVegaLiteChart'], [data-testid='stArrowVegaLiteChart']")
    expect(charts.first).to_be_visible()
    assert page.locator("[data-testid='stDataFrame']").count() >= 1
    assert page.locator("[data-testid='stException']").count() == 0
    print(f"TC5 PASS (chart containers so far: {charts.count()})")

    # TC6 — histograms + correlations
    expect(page.get_by_text("Histograms").first).to_be_visible()
    assert page.locator("[data-testid='stSelectbox']").count() >= 2
    assert charts.count() >= 2, charts.count()
    expect(page.get_by_text("Correlations").first).to_be_visible()
    assert page.locator("[data-testid='stDataFrame']").count() >= 2
    assert page.get_by_text("Traceback").count() == 0
    assert page.locator("[data-testid='stException']").count() == 0
    print(f"TC6 PASS (dataframes: {page.locator('[data-testid="stDataFrame"]').count()})")

    browser.close()

print("ALL EXECUTED TCs PASSED (TC9 deferred/manual per plan)")
