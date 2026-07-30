"""Executes the TCs from .planning/e2e-tests/severity-dataset.md (TC10 deferred).

Engine TCs (TC1-TC4) first, then UI TCs (TC5-TC9) in one tab. TC6 uses the one
sanctioned BaseWeb interaction (click combobox, type, Enter) with a manual
fallback. Run from the repo root:
    uv run python e2e/e2e_severity_dataset.py
"""

import numpy as np
from harness import streamlit_app
from playwright.sync_api import expect, sync_playwright

from pricing_engine.data import (
    list_datasets,
    load_dataset,
    load_fremtpl2_sev,
    validate_portfolio,
)
from pricing_engine.exploration import (
    histogram,
    one_way_frequency,
    portfolio_frequency,
    summarize_portfolio,
)

# --- TC1: registry and spec truths -------------------------------------------

specs = {s.name: s for s in list_datasets()}
assert set(specs) >= {"fremtpl2_freq", "fremtpl2_sev"}, specs.keys()
freq_spec, sev_spec = specs["fremtpl2_freq"], specs["fremtpl2_sev"]
assert freq_spec.kind == "frequency", freq_spec.kind
assert sev_spec.kind == "severity", sev_spec.kind
assert sev_spec.target == "ClaimAmount", sev_spec.target
assert sev_spec.offset is None, sev_spec.offset
assert sev_spec.predictors == freq_spec.predictors
assert len(sev_spec.predictors) == 9
assert sev_spec.required_columns == ("ClaimAmount", *sev_spec.predictors)
assert freq_spec.target == "ClaimNb" and freq_spec.offset == "Exposure"
assert "severity" in sev_spec.label.lower(), sev_spec.label
print("TC1 PASS", sev_spec.label)

# --- TC2: severity load — join, orphan drop, ClaimAmount truths --------------

df, spec = load_dataset("fremtpl2_sev")
assert len(df) == 26_444, len(df)
assert df.shape[1] == 11, list(df.columns)  # IDpol + ClaimAmount + 9 factors
for col in spec.required_columns:
    assert col in df.columns, col
assert int(df[list(spec.required_columns)].isna().sum().sum()) == 0

ca = df["ClaimAmount"]
assert float(ca.min()) == 1.0, ca.min()
assert abs(float(ca.max()) - 4_075_400.56) < 0.01, ca.max()
assert 2_260 < float(ca.mean()) < 2_270, ca.mean()  # joined-table mean (raw: 2,278.5)
assert 1_150 < float(ca.median()) < 1_190, ca.median()
assert (ca > 0).all()
counts = ca.value_counts()
assert counts.loc[1204.00] == 4_792, counts.loc[1204.00]
assert counts.loc[1128.12] == 3_056, counts.loc[1128.12]

try:
    load_fremtpl2_sev("data/raw/does_not_exist.parquet")
    raise SystemExit("TC2 FAIL: no exception raised")
except FileNotFoundError as e:
    assert "curl" in str(e) and "41215" in str(e), e

df_f, spec_f = load_dataset("fremtpl2_freq")
assert len(df_f) == 678_013 and spec_f.kind == "frequency"
print("TC2 PASS", df.shape)

# --- TC3: severity-aware validation ------------------------------------------

assert validate_portfolio(df, spec) == [], validate_portfolio(df, spec)

broken = df.head(10).copy()
broken.iloc[0, broken.columns.get_loc("ClaimAmount")] = 0.0
broken.iloc[1, broken.columns.get_loc("ClaimAmount")] = -50.0
findings = validate_portfolio(broken, spec)
assert findings, "zero/negative ClaimAmount must be flagged for severity kind"
joined = " | ".join(findings)
assert "ClaimAmount" in joined, joined
assert "2" in joined or len(findings) >= 2, joined
assert "claim count" not in joined.lower(), joined
assert "positive" in joined.lower(), joined

# the freq parquet is sorted claims-first, so sample zero-count rows explicitly
sample = df_f[df_f["ClaimNb"] == 0].head(1000)
assert (sample["ClaimNb"] == 0).all() and len(sample) == 1000
zero_findings = [f for f in validate_portfolio(sample, spec_f) if "ClaimNb" in f]
assert zero_findings == [], zero_findings
print("TC3 PASS", findings)

# --- TC4: exploration aggregates are per-claim averages ----------------------

avg = portfolio_frequency(df, spec)
assert 2_260 < avg < 2_270, avg  # ≈ 2,265.5 (joined table)

summary = summarize_portfolio(df, spec)
assert len(summary) == len(spec.required_columns) == 10, len(summary)

ow = one_way_frequency(df, spec, "Area")
assert len(ow) == 6, ow
assert np.isfinite(ow["frequency"]).all() and (ow["frequency"] > 0).all(), ow
assert ow["frequency"].between(500, 20_000).all(), ow["frequency"]
assert not any("xposure" in c for c in ow.columns), ow.columns

assert len(one_way_frequency(df, spec, "DrivAge")) <= 12

h = histogram(df, "ClaimAmount")
assert len(h) <= 30
assert h["count"].max() / h["count"].sum() > 0.9  # the known heavy-tail artifact
print("TC4 PASS", round(avg, 1))

# --- UI TCs -------------------------------------------------------------------

expect.set_options(timeout=20000)

with streamlit_app() as URL, sync_playwright() as p:
    browser = p.chromium.launch()
    context = browser.new_context()
    page = context.new_page()
    page.set_default_timeout(20000)

    # TC5 — default (frequency) path unchanged with two datasets registered
    page.goto(f"{URL}/Data_Import")
    expect(page.get_by_text("Built-in dataset").first).to_be_visible()
    assert page.locator("[data-testid='stSelectbox']").count() >= 1
    page.get_by_role("button", name="Load dataset").click()
    expect(page.get_by_text("Loaded freMTPL2").first).to_be_visible()
    expect(page.get_by_text("frequency").first).to_be_visible()
    expect(page.get_by_text("678,013 rows").first).to_be_visible()
    expect(page.get_by_text("No issues found — portfolio is ready for modelling.")).to_be_visible()
    assert page.get_by_text("Traceback").count() == 0
    assert page.locator("[data-testid='stException']").count() == 0
    print("TC5 PASS")

    # TC6 — the ONE sanctioned BaseWeb interaction: click, type 'severity', Enter
    page.locator("[data-testid='stSelectbox']").first.click()
    page.keyboard.type("severity")
    page.keyboard.press("Enter")
    page.get_by_role("button", name="Load dataset").click()
    expect(page.get_by_text("severity (26.4k claims): 26,444 rows").first).to_be_visible()
    expect(page.get_by_text("26,444 rows × 11 columns").first).to_be_visible()
    expect(page.get_by_text("No issues found — portfolio is ready for modelling.")).to_be_visible()
    assert page.get_by_text("Traceback").count() == 0
    assert page.locator("[data-testid='stException']").count() == 0
    # optional follow-up: Home names the severity dataset
    page.get_by_role("link", name="app").click()
    expect(page.get_by_text("severity").first).to_be_visible()
    expect(page.get_by_text("26,444").first).to_be_visible()
    print("TC6 PASS (automated combobox route: click + type + Enter)")

    # TC7 — kind-aware Data Exploration
    page.get_by_role("link", name="Data Exploration").click()
    metrics = page.locator("[data-testid='stMetric']")
    expect(metrics.first).to_be_visible()
    assert metrics.count() >= 2, metrics.count()
    expect(page.get_by_text("Average claim amount").first).to_be_visible()
    expect(page.get_by_text("2,266").first).to_be_visible()
    expect(page.get_by_text("26,444").first).to_be_visible()
    assert page.get_by_text("Claim frequency").count() == 0
    assert page.get_by_text("Total exposure").count() == 0
    expect(page.get_by_text("One-way average claim amount").first).to_be_visible()
    assert page.get_by_text("One-way claim frequency").count() == 0
    expect(page.get_by_text("Summary statistics").first).to_be_visible()
    expect(page.get_by_text("Histograms").first).to_be_visible()
    expect(page.get_by_text("Correlations").first).to_be_visible()
    charts = page.locator("[data-testid='stVegaLiteChart'], [data-testid='stArrowVegaLiteChart']")
    expect(charts.first).to_be_visible()  # expect-before-count: charts mount late
    assert charts.count() >= 2, charts.count()
    assert page.locator("[data-testid='stDataFrame']").count() >= 3
    assert page.get_by_text("Traceback").count() == 0
    assert page.locator("[data-testid='stException']").count() == 0
    print("TC7 PASS")

    # TC8 — Feature Engineering unchanged, NO exposure-cap section
    page.get_by_role("link", name="Feature Engineering").click()
    expect(page.get_by_text("Current model specification").first).to_be_visible()
    expect(page.get_by_text("Variables").first).to_be_visible()
    expect(page.get_by_text("Binning").first).to_be_visible()
    expect(page.get_by_text("Log transform").first).to_be_visible()
    expect(page.get_by_text("Encoding").first).to_be_visible()
    assert page.get_by_text("Cap Exposure at 1.0").count() == 0
    assert page.get_by_text("rows have Exposure above 1.0").count() == 0
    assert page.locator("[data-testid='stException']").count() == 0
    print("TC8 PASS")

    # TC9 — Frequency Model guards against the severity dataset
    page.get_by_role("link", name="Frequency Model").click()
    expect(page.get_by_text("Severity Model").first).to_be_visible()
    expect(page.get_by_text("severity").first).to_be_visible()
    assert page.get_by_role("button", name="Fit model").count() == 0
    assert page.get_by_text("Model setup").count() == 0
    assert page.get_by_text("Variable selection").count() == 0
    assert page.locator("[data-testid='stException']").count() == 0
    print("TC9 PASS")

    browser.close()

print("ALL EXECUTED TCs PASSED (TC10 deferred/manual per plan)")
