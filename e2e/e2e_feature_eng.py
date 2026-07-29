"""Executes the E2E TCs from .planning/e2e-tests/feature-engineering.md.

Engine truths first, then UI TCs via Playwright. Run from the repo root:
    uv run python e2e/e2e_feature_eng.py
"""

import numpy as np
from harness import streamlit_app
from playwright.sync_api import expect, sync_playwright

from pricing_engine.data import load_dataset
from pricing_engine.preprocessing import (
    bin_numeric,
    cap_column,
    encode_categorical,
    log_transform,
)

# --- Engine-level TCs --------------------------------------------------------

df, spec = load_dataset("fremtpl2_freq")

# cap_column on real Exposure: known quirk, ~1,200 rows above 1.0
capped, n_capped = cap_column(df, "Exposure", 1.0)
assert 500 < n_capped < 5_000, n_capped
assert capped["Exposure"].max() == 1.0
assert df["Exposure"].max() > 1.0  # original untouched
# idempotence: capping again caps nothing
_, n_again = cap_column(capped, "Exposure", 1.0)
assert n_again == 0, n_again

# bin_numeric on DrivAge: <= 8 ordered bands covering every policy, string labels
banded, band_col = bin_numeric(df, "DrivAge", bins=8, strategy="quantile")
assert band_col == "DrivAge_band"
assert banded[band_col].nunique() <= 8
assert banded[band_col].notna().all()
assert len(banded) == 678_013
assert all(isinstance(v, str) for v in banded[band_col].unique())

# non-numeric column refuses to bin
try:
    bin_numeric(df, "Area")
    raise SystemExit("FAIL: no ValueError for non-numeric column")
except ValueError as e:
    assert "numeric" in str(e), e

# log_transform on Density: finite values
logged = log_transform(df, ["Density"])
assert np.isfinite(logged["Density_log"]).all()

# ValueError cases
try:
    bin_numeric(df, "NotAColumn")
    raise SystemExit("FAIL: no ValueError for unknown column")
except ValueError as e:
    assert "NotAColumn" in str(e), e
try:
    log_transform(df, ["ClaimNb"])  # contains zeros
    raise SystemExit("FAIL: no ValueError for non-positive column")
except ValueError as e:
    assert "ClaimNb" in str(e), e

# encode_categorical VehGas (2 levels in real data) -> exactly 1 dummy, original kept
encoded = encode_categorical(df, ["VehGas"])
dummies = [c for c in encoded.columns if c.startswith("VehGas_")]
assert len(dummies) == 1, dummies
assert "VehGas" in encoded.columns

print(f"ENGINE TCs PASS (Exposure rows capped: {n_capped:,})")

# --- UI TCs via Playwright ----------------------------------------------------

expect.set_options(timeout=20000)

with streamlit_app() as URL, sync_playwright() as p:
    browser = p.chromium.launch()
    context = browser.new_context()
    page = context.new_page()

    # Guard TC — fresh session straight to Feature Engineering
    page.goto(f"{URL}/Feature_Engineering")
    expect(page.get_by_text("Load a dataset first").first).to_be_visible()
    assert page.get_by_text("Current model specification").count() == 0
    assert page.locator("[data-testid='stException']").count() == 0
    print("GUARD TC PASS")

    # Setup — load dataset, navigate via sidebar
    page.get_by_role("link", name="Data Import").click()
    page.get_by_role("button", name="Load dataset").click()
    expect(page.get_by_text("Loaded freMTPL2")).to_be_visible()
    page.get_by_role("link", name="Feature Engineering").click()
    expect(page.get_by_text("Current model specification").first).to_be_visible()
    print("SETUP TC PASS")

    # Exposure cap TC — caption shows >1 count, button caps, caption shows 0
    expect(page.get_by_text(f"{n_capped:,} rows have Exposure above 1.0").first).to_be_visible()
    page.get_by_role("button", name="Cap Exposure at 1.0").click()
    expect(page.get_by_text(f"Capped {n_capped:,} value(s) of Exposure").first).to_be_visible()
    expect(page.get_by_text("0 rows have Exposure above 1.0").first).to_be_visible()
    print("EXPOSURE CAP TC PASS")

    # Binning TC — default selectbox (first numeric predictor: VehPower),
    # default 8 quantile bands; success message names the band variable
    page.get_by_role("button", name="Create banded variable").click()
    expect(page.get_by_text("Added banded variable 'VehPower_band'").first).to_be_visible()
    # spec section lists the new predictor as plain text
    expect(page.get_by_text("VehPower_band").first).to_be_visible()
    expect(page.get_by_text("Predictors (10)").first).to_be_visible()
    print("BINNING TC PASS")

    # Downstream integration — Data Exploration still renders after engineering
    page.get_by_role("link", name="Data Exploration").click()
    expect(page.get_by_text("One-way claim frequency").first).to_be_visible()
    assert page.locator("[data-testid='stException']").count() == 0
    print("DOWNSTREAM TC PASS")

    browser.close()

print("ALL EXECUTED TCs PASSED")
