"""Executes the TCs from .planning/e2e-tests/pure-premium.md (V3 slice 3).

Engine TCs (TC1-TC2, pure — no DB) and the TC10 snapshot first, then UI TCs
(TC3-TC9, two contexts). TC11 (pytest + the other runners) runs separately
from the shell; TC12 is deferred/manual. Run from the repo root:
    uv run python e2e/e2e_pure_premium.py
"""

import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd
from harness import streamlit_app
from playwright.sync_api import Page, expect, sync_playwright

from pricing_engine import prediction, storage
from pricing_engine.data import load_dataset
from pricing_engine.glm import build_formula, family_kind, fit_frequency_glm, fit_severity_glm

# --- TC1: real-data anchors — batch totals, exposure-halving, monotonicity ----

freq_df, freq_spec = load_dataset("fremtpl2_freq")
sev_df, sev_spec = load_dataset("fremtpl2_sev")
assert len(freq_df) == 678_013 and freq_spec.kind == "frequency"
assert len(sev_df) == 26_444 and sev_spec.kind == "severity"

freq_model = fit_frequency_glm(freq_df, build_formula(freq_spec), offset_column=freq_spec.offset)
sev_model = fit_severity_glm(sev_df, build_formula(sev_spec))  # gamma default

required = prediction.required_columns(freq_model, sev_model, freq_spec)
assert required == list(freq_spec.predictors), required
assert prediction.formula_columns(freq_model) == list(freq_spec.predictors)
numeric = [c for c in required if pd.api.types.is_numeric_dtype(freq_df[c])]
assert numeric == ["VehPower", "VehAge", "DrivAge", "BonusMalus", "Density"], numeric

batch = prediction.predict_pure_premium(freq_model, sev_model, freq_df, freq_spec)
for col in ("expected_frequency", "expected_claim_amount", "pure_premium", "expected_loss"):
    assert col in batch.columns and col not in freq_df.columns  # copy, not mutation
assert np.allclose(
    batch["pure_premium"], batch["expected_frequency"] * batch["expected_claim_amount"]
)
assert np.allclose(batch["expected_loss"], batch["pure_premium"] * batch["Exposure"])
assert (batch["pure_premium"] > 0).all() and np.isfinite(batch["pure_premium"]).all()

total_claims = float((batch["expected_frequency"] * batch["Exposure"]).sum())
assert abs(total_claims - 36_102) < 400, total_claims
mean_amount = float(batch["expected_claim_amount"].mean())
assert 2_100 < mean_amount < 2_400, mean_amount
total_loss = float(batch["expected_loss"].sum())
assert 6.5e7 < total_loss < 9.5e7, total_loss
spread = np.percentile(batch["pure_premium"], [25, 50, 75, 95, 99])
assert spread[0] > 0 and np.all(np.diff(spread) > 0)

profile: dict[str, object] = {}
for col in required:
    s = freq_df[col]
    profile[col] = (
        float(s.median())
        if pd.api.types.is_numeric_dtype(s)
        else sorted(str(v) for v in s.dropna().unique())[0]
    )
row = pd.DataFrame([profile]).assign(Exposure=1.0, ClaimNb=0)
quote = prediction.predict_pure_premium(freq_model, sev_model, row, freq_spec)
premium_1y = float(quote["expected_loss"].iloc[0])
assert premium_1y == float(quote["pure_premium"].iloc[0])  # exposure 1.0

half = prediction.predict_pure_premium(freq_model, sev_model, row.assign(Exposure=0.5), freq_spec)
assert float(half["pure_premium"].iloc[0]) == float(quote["pure_premium"].iloc[0])
assert float(half["expected_loss"].iloc[0]) == 0.5 * premium_1y

premiums = [
    float(
        prediction.predict_pure_premium(
            freq_model, sev_model, row.assign(BonusMalus=float(v)), freq_spec
        )["pure_premium"].iloc[0]
    )
    for v in (50, 75, 100, 150)
]
assert all(a < b for a, b in zip(premiums, premiums[1:], strict=False)), premiums
print(
    f"TC1 PASS total_claims={total_claims:,.0f} mean_amount={mean_amount:.1f} "
    f"total_loss={total_loss / 1e6:.1f}M median_premium={premium_1y:.2f}"
)

# --- TC2: breakdown identity + median baseline + union ValueError -------------

real = freq_df.iloc[[0]].copy()
base, factors = prediction.premium_breakdown(freq_model, sev_model, real, freq_df, freq_spec)
assert list(factors["predictor"]) == required
assert np.allclose(
    factors["combined_factor"], factors["frequency_factor"] * factors["severity_factor"]
)
premium = float(
    prediction.predict_pure_premium(freq_model, sev_model, real, freq_spec)["pure_premium"].iloc[0]
)
assert np.isclose(base * float(np.prod(factors["combined_factor"].to_numpy())), premium)

base2, f2 = prediction.premium_breakdown(freq_model, sev_model, row, freq_df, freq_spec)
assert np.allclose(f2["combined_factor"], 1.0), f2
assert np.isclose(base2, float(quote["pure_premium"].iloc[0]))

rng = np.random.default_rng(3)
sev_extra = fit_severity_glm(
    sev_df.assign(Extra=rng.uniform(size=len(sev_df))), "ClaimAmount ~ BonusMalus + Extra"
)
assert prediction.formula_columns(sev_extra) == ["BonusMalus", "Extra"]
assert prediction.required_columns(freq_model, sev_extra, freq_spec) == (
    list(freq_spec.predictors) + ["Extra"]
)
for fn in (
    lambda: prediction.predict_pure_premium(freq_model, sev_extra, freq_df, freq_spec),
    lambda: prediction.premium_breakdown(freq_model, sev_extra, real, freq_df, freq_spec),
):
    try:
        fn()
        raise AssertionError("expected ValueError")
    except ValueError as exc:
        assert "Extra" in str(exc) and "Missing predictor column" in str(exc), exc
print(f"TC2 PASS base={base:.2f} row0_premium={premium:.2f}")

# --- TC10 snapshot: real DB state BEFORE the UI flow ---------------------------

DB_PATH = Path("data") / "workbench.db"
storage.connect(DB_PATH).close()  # migrate before any raw read (slice-2 lesson)
with sqlite3.connect(DB_PATH) as raw:
    n0 = raw.execute("SELECT COUNT(*) FROM model_runs").fetchone()[0]
    max_id0 = raw.execute("SELECT COALESCE(MAX(id), 0) FROM model_runs").fetchone()[0]
    schema0 = [r[1] for r in raw.execute("PRAGMA table_info(model_runs)")]
    null_count0 = raw.execute(
        "SELECT COUNT(*) FROM model_runs WHERE model_path IS NULL"
    ).fetchone()[0]
print(f"TC10 snapshot: {n0} runs, max_id={max_id0}, {null_count0} NULL-path rows")

# --- UI TCs -------------------------------------------------------------------

GUARD_NO_DATASET = "Load a dataset first — go to Data Import."
GUARD_WRONG_KIND = (
    "The active dataset is a severity dataset (claim amounts) — pure premium "
    "is quoted per policy. Load the frequency dataset in Data Import."
)
GUARD_BOTH_MISSING = (
    "Pure premium needs both models in session. Fit or load a frequency model "
    "on Frequency Model, and a severity model on Severity Model (load the "
    "severity dataset there first, then reload the frequency dataset — model "
    "slots survive the switch)."
)
GUARD_NO_FREQ = "No frequency model in session — fit or load one on Frequency Model."
GUARD_NO_SEV = (
    "No severity model in session — load the severity dataset in Data Import, "
    "fit or load a severity model on Severity Model, then reload the frequency "
    "dataset (model slots survive the switch)."
)
TAKE_OUT = (
    "Take out a policy: defaults describe the median policy — change the inputs "
    "and get the annual risk premium."
)
HOME_NONE_FREQ = "Frequency model: none — fit or load one on Frequency Model."
HOME_NONE_SEV = "Severity model: none — fit or load one on Severity Model."
HOME_READY = "Both models in session — ready to quote on Pure Premium."


def no_exception(page: Page) -> None:
    assert page.get_by_text("Traceback").count() == 0
    assert page.locator("[data-testid='stException']").count() == 0


def metric(page: Page, label: str):  # noqa: ANN201 — Playwright locator
    return page.locator("[data-testid='stMetric']").filter(has_text=label)


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

    # --- context A: TC3-TC8 ---------------------------------------------------
    ctx_a = browser.new_context()
    page = ctx_a.new_page()
    page.set_default_timeout(20000)

    # TC3 — guard ladder + Home none-state
    page.goto(f"{URL}/Pure_Premium")
    expect(page.get_by_text(GUARD_NO_DATASET).first).to_be_visible()
    assert page.get_by_text("Quote a policy").count() == 0
    no_exception(page)

    page.get_by_role("link", name="app").click()
    expect(page.get_by_text(HOME_NONE_FREQ).first).to_be_visible()
    expect(page.get_by_text(HOME_NONE_SEV).first).to_be_visible()
    assert page.get_by_text(HOME_READY).count() == 0
    no_exception(page)

    load_builtin(page, "severity", "26,444")
    page.get_by_role("link", name="Pure Premium").click()
    expect(page.get_by_text(GUARD_WRONG_KIND).first).to_be_visible()
    assert page.get_by_text("Quote a policy").count() == 0
    no_exception(page)

    load_builtin(page, "frequency", "678,013")
    page.get_by_role("link", name="Pure Premium").click()
    expect(page.get_by_text(GUARD_BOTH_MISSING).first).to_be_visible()
    assert page.get_by_text("Quote a policy").count() == 0
    no_exception(page)
    print("TC3 PASS")

    # TC4 — frequency fit → the severity-missing ROUND-TRIP guard (G2)
    page.get_by_role("link", name="Frequency Model").click()
    page.get_by_role("button", name="Fit model").click()
    expect(page.get_by_text("Model fitted and recorded").first).to_be_visible(timeout=180000)
    assert page.get_by_text("saved for reuse").count() >= 1

    page.get_by_role("link", name="Pure Premium").click()
    expect(page.get_by_text(GUARD_NO_SEV).first).to_be_visible()
    assert page.get_by_text("Pure premium needs both models").count() == 0
    assert page.get_by_text("Quote a policy").count() == 0
    no_exception(page)

    page.get_by_role("link", name="app").click()
    expect(page.get_by_text("Frequency model: fitted (poisson, AIC").first).to_be_visible()
    expect(page.get_by_text(HOME_NONE_SEV).first).to_be_visible()
    assert page.get_by_text(HOME_READY).count() == 0
    print("TC4 PASS (round-trip guard, no dead end)")

    # TC5 — severity fit; kind guard precedes; ready to quote
    load_builtin(page, "severity", "26,444")
    page.get_by_role("link", name="Severity Model").click()
    page.get_by_role("button", name="Fit model").click()
    expect(page.get_by_text("Model fitted and recorded").first).to_be_visible(timeout=30000)
    assert page.get_by_text("saved for reuse").count() >= 1  # TC9's Load precondition

    page.get_by_role("link", name="Pure Premium").click()
    expect(page.get_by_text(GUARD_WRONG_KIND).first).to_be_visible()  # kind guard first
    assert page.get_by_text("Quote a policy").count() == 0
    no_exception(page)

    load_builtin(page, "frequency", "678,013")
    page.get_by_role("link", name="app").click()
    expect(page.get_by_text("Frequency model: fitted (poisson, AIC").first).to_be_visible()
    expect(page.get_by_text("Severity model: fitted (gamma, AIC").first).to_be_visible()
    expect(page.get_by_text(HOME_READY).first).to_be_visible()

    page.get_by_role("link", name="Pure Premium").click()
    expect(page.get_by_text(TAKE_OUT).first).to_be_visible()
    for fragment in (
        GUARD_NO_DATASET,
        "severity dataset (claim amounts)",
        "Pure premium needs both models",
        "No frequency model in session",
        "No severity model in session",
        "The models need column(s)",
    ):
        assert page.get_by_text(fragment).count() == 0, fragment
    model_caption = "Frequency model: poisson (fitted) · Severity model: gamma (fitted)"
    expect(page.get_by_text(model_caption).first).to_be_visible()
    expect(page.get_by_text("Quote a policy").first).to_be_visible()
    # wait for the BOTTOM of the form before counting widgets (mounts lag)
    expect(page.get_by_text("Portfolio premiums").first).to_be_visible()
    expect(page.get_by_role("button", name="Get quote")).to_be_visible()
    batch_button = page.get_by_role("button", name="Compute premiums for loaded portfolio")
    expect(batch_button).to_be_visible()
    expect(page.get_by_text("Exposure (policy-years)").first).to_be_visible()
    expect(page.locator("[data-testid='stNumberInput']").nth(5)).to_be_visible()
    assert page.locator("[data-testid='stNumberInput']").count() == 6  # 5 numerics + exposure
    expect(page.locator("[data-testid='stSelectbox']").nth(3)).to_be_visible()
    assert page.locator("[data-testid='stSelectbox']").count() == 4
    assert page.locator("[data-testid='stMetric']").count() == 0
    no_exception(page)
    print("TC5 PASS (ready to quote)")

    # TC6 — happy-path quote with the default (median) profile
    page.get_by_role("button", name="Get quote").click()
    expect(page.locator("[data-testid='stMetric']").first).to_be_visible()
    assert page.locator("[data-testid='stMetric']").count() == 3
    for label in ("Expected claim frequency", "Expected claim amount", "Risk premium"):
        expect(metric(page, label).first).to_be_visible()
        assert metric(page, label).count() == 1, label
    honesty = page.get_by_text("Risk premium only — no expenses, loadings, or profit.")
    expect(honesty.first).to_be_visible()
    independence = page.get_by_text("Assumes claim counts and claim sizes are independent")
    expect(independence.first).to_be_visible()
    expect(page.get_by_text("Premium breakdown").first).to_be_visible()
    expect(page.get_by_text("reproduces the quote exactly").first).to_be_visible()
    expect(page.get_by_text("The reference policy is artificial").first).to_be_visible()
    expect(page.locator("[data-testid='stDataFrame']").first).to_be_visible()
    assert page.locator("[data-testid='stDataFrame']").count() == 1
    no_exception(page)
    print("TC6 PASS (quote + breakdown)")

    # TC7 — screen 06's batch must NOT leak into 08
    page.get_by_role("link", name="Prediction").click()
    expect(page.get_by_text("Single policy").first).to_be_visible()
    expect(page.get_by_text("Batch prediction").first).to_be_visible()
    page.get_by_role("button", name="Predict for loaded portfolio").click()
    expect(page.get_by_text("Total expected claims").first).to_be_visible(timeout=120000)
    expect(page.get_by_text("36,102").first).to_be_visible()

    page.get_by_role("link", name="Pure Premium").click()
    expect(page.get_by_text("Portfolio premiums").first).to_be_visible()
    assert page.get_by_text("Total expected loss").count() == 0
    assert page.get_by_text("Average annual premium").count() == 0
    assert page.get_by_text("36,102").count() == 0
    assert page.locator("[data-testid='stMetric']").count() == 0
    no_exception(page)
    print("TC7 PASS (no leak from 06)")

    # TC8 — premium batch: honest summary + isolation direction 2
    page.get_by_role("button", name="Compute premiums for loaded portfolio").click()
    expect(page.locator("[data-testid='stMetric']").first).to_be_visible(timeout=120000)
    assert page.locator("[data-testid='stMetric']").count() == 3
    for label in ("Total expected loss", "Total expected claims", "Average annual premium"):
        expect(metric(page, label).first).to_be_visible()
        assert metric(page, label).count() == 1, label
    expect(page.get_by_text("No observed-cost comparison is shown").first).to_be_visible()
    expect(page.get_by_text("covers only ~73% of the claims").first).to_be_visible()
    expect(page.get_by_text("about −1.5% below the observed claim total").first).to_be_visible()
    cross_check = page.get_by_text("Cross-check the expected-claims total on the Prediction screen")
    expect(cross_check.first).to_be_visible()
    assert page.get_by_text("Total observed").count() == 0  # G1 negative
    expect(page.get_by_text("Tariff spread").first).to_be_visible()
    expect(page.locator("[data-testid='stDataFrame']").first).to_be_visible()
    assert page.locator("[data-testid='stDataFrame']").count() == 2  # spread + preview
    expect(page.get_by_text("Download premiums CSV").first).to_be_visible()
    no_exception(page)

    page.get_by_role("link", name="Prediction").click()
    expect(page.get_by_text("Total expected claims").first).to_be_visible()
    expect(page.get_by_text("36,102").first).to_be_visible()
    expect(page.get_by_text("Total observed claims").first).to_be_visible()
    assert page.get_by_text("Total expected loss").count() == 0
    assert page.get_by_text("Average annual premium").count() == 0
    no_exception(page)

    page.get_by_role("link", name="Pure Premium").click()
    expect(page.locator("[data-testid='stMetric']").first).to_be_visible()
    assert page.locator("[data-testid='stMetric']").count() == 3  # batch persists
    expect(metric(page, "Total expected loss").first).to_be_visible()
    assert metric(page, "Total expected loss").count() == 1
    no_exception(page)
    ctx_a.close()
    print("TC8 PASS (honest batch, isolation both ways, persists)")

    # --- context B: TC9 — fresh session, LOADED severity model ---------------
    ctx_b = browser.new_context()
    page = ctx_b.new_page()
    page.set_default_timeout(20000)

    page.goto(f"{URL}/Data_Import")
    expect(page.get_by_text("Built-in dataset").first).to_be_visible()
    page.locator("[data-testid='stSelectbox']").first.click()
    page.keyboard.type("severity")
    page.keyboard.press("Enter")
    page.get_by_role("button", name="Load dataset").click()
    expect(page.get_by_text("26,444").first).to_be_visible()

    page.get_by_role("link", name="Severity Model").click()
    expect(page.get_by_text("Load a saved severity model").first).to_be_visible()
    page.get_by_role("button", name="Load saved model").click()
    expect(page.get_by_text("no refit needed").first).to_be_visible(timeout=30000)

    load_builtin(page, "frequency", "678,013")
    page.get_by_role("link", name="Pure Premium").click()
    expect(page.get_by_text(GUARD_NO_FREQ).first).to_be_visible()
    assert page.get_by_text("Quote a policy").count() == 0
    assert page.get_by_text("Pure premium needs both models").count() == 0
    assert page.get_by_text("No severity model in session").count() == 0
    no_exception(page)

    page.get_by_role("link", name="app").click()
    expect(page.get_by_text("Severity model: loaded (gamma, AIC").first).to_be_visible()
    expect(page.get_by_text(HOME_NONE_FREQ).first).to_be_visible()
    assert page.get_by_text(HOME_READY).count() == 0

    page.get_by_role("link", name="Frequency Model").click()
    page.get_by_role("button", name="Fit model").click()
    expect(page.get_by_text("Model fitted and recorded").first).to_be_visible(timeout=180000)

    page.get_by_role("link", name="Pure Premium").click()
    expect(page.get_by_text("Severity model: gamma (loaded)").first).to_be_visible()
    expect(page.get_by_role("button", name="Get quote")).to_be_visible()
    page.get_by_role("button", name="Get quote").click()
    expect(page.locator("[data-testid='stMetric']").first).to_be_visible()
    assert page.locator("[data-testid='stMetric']").count() == 3
    expect(page.get_by_text("Premium breakdown").first).to_be_visible()
    expect(page.locator("[data-testid='stDataFrame']").first).to_be_visible()
    assert page.locator("[data-testid='stDataFrame']").count() == 1
    no_exception(page)
    ctx_b.close()
    print("TC9 PASS (loaded severity model quotes like a fitted one)")

    browser.close()

# --- TC10: bracket — 3 new saved runs, nothing else written --------------------

with sqlite3.connect(DB_PATH) as raw:
    n1 = raw.execute("SELECT COUNT(*) FROM model_runs").fetchone()[0]
    schema1 = [r[1] for r in raw.execute("PRAGMA table_info(model_runs)")]
    null_count1 = raw.execute(
        "SELECT COUNT(*) FROM model_runs WHERE model_path IS NULL"
    ).fetchone()[0]
    new_rows = raw.execute(
        "SELECT id, family, model_path FROM model_runs WHERE id > ?", (max_id0,)
    ).fetchall()
assert n1 - n0 == 3, (n0, n1)  # TC4 poisson, TC5 gamma, TC9 poisson
assert schema1 == schema0, (schema0, schema1)
assert null_count1 == null_count0, (null_count0, null_count1)
for rid, fam, mpath in new_rows:
    assert mpath is not None and Path(mpath).exists(), rid
    assert Path(mpath).name == f"run{rid:04d}_{family_kind(fam)}_{fam}.pickle", mpath
print(f"TC10 PASS ({n0} -> {n1} runs, schema + NULL count unchanged)")

print("ALL EXECUTED TCs PASSED (TC11 run separately from the shell; TC12 deferred/manual)")
