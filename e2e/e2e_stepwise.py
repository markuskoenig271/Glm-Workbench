"""Executes the TCs from .planning/e2e-tests/stepwise-selection.md.

Engine TC on the real data with a reduced 3-predictor spec (timing constraint);
UI TC verifies the section renders — the full UI run is manual/deferred.
Run from the repo root:
    uv run python e2e/e2e_stepwise.py
"""

import time
from dataclasses import replace

from harness import streamlit_app
from playwright.sync_api import expect, sync_playwright

from pricing_engine.data import load_dataset
from pricing_engine.glm import stepwise_selection

# --- Engine TC: backward selection on real data, reduced spec ----------------

df, spec = load_dataset("fremtpl2_freq")
reduced = replace(spec, predictors=("BonusMalus", "DrivAge", "VehGas"))

fits: list[str] = []
t0 = time.perf_counter()
selected, log = stepwise_selection(df, reduced, on_fit=fits.append)
elapsed = time.perf_counter() - t0

assert set(selected) <= {"BonusMalus", "DrivAge", "VehGas"}, selected
assert "BonusMalus" in selected, selected  # strongest real effect must survive
assert log.iloc[0]["action"] == "start"
assert (log["value"].diff().dropna() <= 0).all()  # improving steps only
assert len(fits) >= 4  # start + at least first-round candidates
print(
    f"ENGINE TC PASS ({elapsed:.0f}s, {len(fits)} fits, selected={selected}, "
    f"log actions={list(log['action'])})"
)

# --- UI TCs -------------------------------------------------------------------

expect.set_options(timeout=20000)

with streamlit_app() as URL, sync_playwright() as p:
    browser = p.chromium.launch()

    # Guard: section must not appear before a dataset is loaded
    ctx = browser.new_context()
    pg = ctx.new_page()
    pg.goto(f"{URL}/Frequency_Model")
    expect(pg.get_by_text("Load a dataset first").first).to_be_visible()
    assert pg.get_by_text("Variable selection").count() == 0
    ctx.close()
    print("GUARD TC PASS")

    # Section renders after setup
    context = browser.new_context()
    page = context.new_page()
    page.goto(f"{URL}/Data_Import")
    page.get_by_role("button", name="Load dataset").click()
    expect(page.get_by_text("Loaded freMTPL2")).to_be_visible()
    page.get_by_role("link", name="Frequency Model").click()
    # "Run history" renders after the selection section — await it first
    expect(page.get_by_text("Run history").first).to_be_visible()
    expect(page.get_by_text("Variable selection").first).to_be_visible()
    expect(page.get_by_text("Direction").first).to_be_visible()
    expect(page.get_by_text("Criterion").first).to_be_visible()
    expect(page.get_by_role("button", name="Run selection")).to_be_visible()
    assert page.locator("[data-testid='stException']").count() == 0
    print("SECTION TC PASS (full UI run is manual/deferred — ~45 fits, minutes)")

    browser.close()

print("ALL EXECUTED TCs PASSED")
