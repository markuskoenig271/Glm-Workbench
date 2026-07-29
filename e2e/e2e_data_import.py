"""Executes TC1-TC4, TC6, TC7 from .planning/e2e-tests/data-import.md.

TC5 is manual/deferred per the plan. Run from the repo root:
    uv run python e2e/e2e_data_import.py
"""

import io

from harness import FIXTURES, streamlit_app
from playwright.sync_api import expect, sync_playwright

from pricing_engine.data import load_fremtpl2_freq, load_portfolio

FIXTURE = str(FIXTURES / "broken_portfolio.csv")

# --- Engine-level TCs (no app needed) ---------------------------------------

# TC6
try:
    load_fremtpl2_freq("data/raw/does_not_exist.parquet")
    raise SystemExit("TC6 FAIL: no exception raised")
except FileNotFoundError as e:
    msg = str(e)
    assert "curl" in msg and "data.openml.org" in msg, msg
try:
    load_portfolio("data/does_not_exist.csv")
    raise SystemExit("TC6 FAIL: no exception raised")
except FileNotFoundError as e:
    msg = str(e)
    assert "does_not_exist.csv" in msg, msg
    assert "Traceback" not in msg
print("TC6 PASS (engine-level; UI variant not run — would disturb the app)")

# TC7
df_path = load_portfolio(FIXTURE)
assert df_path.shape[0] == 3, df_path.shape
assert "ClaimNb" in df_path.columns, df_path.columns
with open(FIXTURE, "rb") as fh:
    df_file = load_portfolio(io.BytesIO(fh.read()))
assert df_file.shape == df_path.shape
print("TC7 PASS", df_path.shape)

# --- UI TCs via Playwright ---------------------------------------------------

expect.set_options(timeout=20000)

with streamlit_app() as URL, sync_playwright() as p:
    browser = p.chromium.launch()
    context = browser.new_context()
    page = context.new_page()
    page.set_default_timeout(20000)

    # TC1 — fresh session Home
    page.goto(URL)
    expect(page.get_by_text("No dataset loaded yet — start with Data Import.")).to_be_visible()
    assert page.get_by_text("Active dataset").count() == 0
    print("TC1 PASS")

    # TC2 — one-click built-in load (same tab)
    page.goto(f"{URL}/Data_Import")
    expect(page.get_by_text("Built-in dataset").first).to_be_visible()
    # dataset preselection is proven by the post-click success message naming
    # the full label with zero selectbox interaction (see Results note)
    page.get_by_role("button", name="Load dataset").click()
    expect(page.get_by_text("Loaded freMTPL2")).to_be_visible()
    expect(page.get_by_text("678,013 rows").first).to_be_visible()
    expect(page.get_by_text("12 columns")).to_be_visible()
    expect(page.get_by_text("No issues found — portfolio is ready for modelling.")).to_be_visible()
    print("TC2 PASS (row count rendered thousands-separated: '678,013')")

    # TC3 — Home reflects the load (same tab, sidebar navigation — a full
    # page.goto reload would start a NEW Streamlit session and drop state)
    page.get_by_role("link", name="app").click()
    expect(page.get_by_text("Active dataset: freMTPL2")).to_be_visible()
    expect(page.get_by_text("678,013 rows").first).to_be_visible()
    assert page.get_by_text("No dataset loaded yet").count() == 0
    print("TC3 PASS")

    # TC4 — broken CSV upload with default mapping (sidebar navigation)
    page.get_by_role("link", name="Data Import").click()
    page.get_by_text("CSV upload").click()
    page.set_input_files("input[type=file]", FIXTURE)
    expect(page.get_by_text("Uploaded 'broken_portfolio.csv'")).to_be_visible()
    # Default mapping is proven by OUTCOME below: a "Target 'ClaimNb' ..."
    # finding can only appear if the target defaulted to the first column.
    page.get_by_role("button", name="Use this dataset").click()
    expect(page.get_by_text("Upload: broken_portfolio.csv").first).to_be_visible()
    expect(page.get_by_text("3 rows × 3 columns")).to_be_visible()
    expect(page.get_by_text("Target 'ClaimNb' has 1 negative value(s)")).to_be_visible()
    expect(page.get_by_text("Column 'ClaimNb' has 1 missing value(s)")).to_be_visible()
    assert page.get_by_text("No issues found").count() == 0
    # optional follow-up: Home shows the ad-hoc dataset (sidebar navigation)
    page.get_by_role("link", name="app").click()
    expect(page.get_by_text("Active dataset: Upload: broken_portfolio.csv")).to_be_visible()
    print("TC4 PASS (incl. optional Home follow-up)")

    browser.close()

print("ALL EXECUTED TCs PASSED (TC5 deferred/manual per plan)")
