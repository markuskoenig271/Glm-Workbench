"""Executes the TCs from .planning/e2e-tests/severity-model.md (TC9 deferred).

Engine TCs (TC1-TC3) first, then UI TCs (TC4-TC7) in one tab. TC8 (pytest +
slice-1 runner) is run separately from the shell — this script must not hold
port 8598 while the slice-1 runner launches its own app. Run from the repo root:
    uv run python e2e/e2e_severity_model.py
"""

import inspect
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from harness import streamlit_app
from playwright.sync_api import expect, sync_playwright

from pricing_engine import storage
from pricing_engine.data import DATASET_REGISTRY, load_dataset
from pricing_engine.diagnostics import coefficient_table, information_criteria
from pricing_engine.glm import (
    FREQUENCY_FAMILIES,
    SEVERITY_FAMILIES,
    build_formula,
    fit_severity_glm,
)

# --- TC1: severity family contract — log link, no offset, error wording -------

assert SEVERITY_FAMILIES == ["gamma", "inverse_gaussian"], SEVERITY_FAMILIES
assert FREQUENCY_FAMILIES == ["poisson", "negative_binomial"], FREQUENCY_FAMILIES

params = inspect.signature(fit_severity_glm).parameters
assert "offset" not in params and "offset_column" not in params, list(params)

try:
    fit_severity_glm(pd.DataFrame({"y": [1.0], "x": [1.0]}), "y ~ x", family="poisson")
    raise SystemExit("TC1 FAIL: no ValueError for family='poisson'")
except ValueError as e:
    assert "Unknown severity family 'poisson'" in str(e), e
    assert "gamma, inverse_gaussian" in str(e), e

rng = np.random.default_rng(42)
tiny = pd.DataFrame({"y": rng.gamma(2.0, 500.0, 400) + 1.0, "x": rng.normal(size=400)})
for name, fam_cls in [
    ("gamma", sm.families.Gamma),
    ("inverse_gaussian", sm.families.InverseGaussian),
]:
    m = fit_severity_glm(tiny, "y ~ x", family=name)
    fam = m.model.family
    assert isinstance(fam, fam_cls), (name, type(fam))
    assert isinstance(fam.link, sm.families.links.Log), (name, type(fam.link))
    assert getattr(m.model, "offset", None) is None, (name, m.model.offset)
    assert (np.asarray(m.fittedvalues) > 0).all(), name

assert isinstance(fit_severity_glm(tiny, "y ~ x").model.family, sm.families.Gamma)

sev_spec = DATASET_REGISTRY["fremtpl2_sev"]
assert build_formula(sev_spec) == (
    "ClaimAmount ~ Area + VehPower + VehAge + DrivAge + BonusMalus"
    " + VehBrand + VehGas + Density + Region"
), build_formula(sev_spec)
print("TC1 PASS")

# --- TC2: real-data Gamma fit calibration + IG fit attempt --------------------

df, spec = load_dataset("fremtpl2_sev")
formula = build_formula(spec)
model = fit_severity_glm(df, formula)  # gamma default

fitted = np.asarray(model.fittedvalues)
assert (fitted > 0).all()
mean_fitted = float(fitted.mean())
assert abs(mean_fitted - 2_265.5) / 2_265.5 < 0.05, mean_fitted

info = information_criteria(model)
assert info["n_obs"] == 26_444, info["n_obs"]
for key in ("aic", "bic", "deviance", "log_likelihood"):
    assert np.isfinite(info[key]), (key, info[key])
assert info["n_params"] > 20

table = coefficient_table(model)
non_int = table[table["term"] != "Intercept"]
rel = np.exp(non_int["coef"])
assert rel.between(0.1, 10).all(), non_int.loc[~rel.between(0.1, 10), "term"].tolist()

insig = non_int[~non_int["significant"]]
assert len(insig) > 0, "expected insignificant terms on real severity data"

try:
    m_ig = fit_severity_glm(df, formula, family="inverse_gaussian")
    assert isinstance(m_ig.model.family.link, sm.families.links.Log)
    assert (np.asarray(m_ig.fittedvalues) > 0).all()
    ig_outcome = f"IG fitted, AIC {float(m_ig.aic):,.0f}"
except Exception as e:  # numerical fragility on the heavy tail is documented
    ig_outcome = f"IG raised {type(e).__name__}: {e}"
print(
    f"TC2 PASS mean_fitted={mean_fitted:.1f} aic={info['aic']:.0f} "
    f"insig={len(insig)}/{len(non_int)} | {ig_outcome}"
)

# --- TC3: storage row correctness on a TEMPFILE db ----------------------------
# connect(path) keeps the override in-process — nothing leaks into the app
# subprocess, and the real data/workbench.db is never touched by this TC.

tc3_db = Path(tempfile.mkdtemp()) / "e2e_sev_model.db"
assert spec.offset is None, spec.offset
with storage.connect(tc3_db) as conn:
    storage.record_model_run(
        conn,
        dataset=spec.name,
        target=spec.target,
        offset=spec.offset,
        formula=formula,
        family="gamma",
        n_obs=info["n_obs"],
        aic=info["aic"],
        bic=info["bic"],
        deviance=info["deviance"],
        log_likelihood=info["log_likelihood"],
        coefficients=model.params.to_dict(),
    )
with storage.connect(tc3_db) as conn:
    runs = storage.list_model_runs(conn)

assert len(runs) == 1, len(runs)
row = runs.iloc[0]
assert row["dataset"] == "fremtpl2_sev", row["dataset"]
assert row["target"] == "ClaimAmount", row["target"]
assert row["family"] == "gamma", row["family"]
assert row["formula"].startswith("ClaimAmount ~"), row["formula"]
assert int(row["n_obs"]) == 26_444, row["n_obs"]
assert row["offset"] is None or pd.isna(row["offset"]), row["offset"]
print("TC3 PASS", row["family"], row["offset"])

# --- UI TCs -------------------------------------------------------------------

expect.set_options(timeout=20000)

with streamlit_app() as URL, sync_playwright() as p:
    browser = p.chromium.launch()
    context = browser.new_context()
    page = context.new_page()
    page.set_default_timeout(20000)

    # TC4 — no-dataset guard on a fresh session (direct goto is the point here)
    page.goto(f"{URL}/Severity_Model")
    expect(page.get_by_text("Load a dataset first — go to Data Import.")).to_be_visible()
    assert page.get_by_role("button", name="Fit model").count() == 0
    assert page.get_by_text("Model setup").count() == 0
    assert page.locator("[data-testid='stSelectbox']").count() == 0
    assert page.get_by_text("Traceback").count() == 0
    assert page.locator("[data-testid='stException']").count() == 0
    print("TC4 PASS")

    # TC5 — reverse guard (frequency dataset active) + screen-04 regression
    page.get_by_role("link", name="Data Import").click()
    expect(page.get_by_text("Built-in dataset").first).to_be_visible()
    page.get_by_role("button", name="Load dataset").click()
    expect(page.get_by_text("678,013 rows").first).to_be_visible()

    page.get_by_role("link", name="Severity Model").click()
    expect(page.get_by_text("frequency dataset").first).to_be_visible()
    expect(page.get_by_text("Frequency Model screen").first).to_be_visible()
    assert page.get_by_role("button", name="Fit model").count() == 0
    assert page.get_by_text("Model setup").count() == 0
    assert page.get_by_text("Distribution").count() == 0
    assert page.get_by_text("ClaimAmount ~").count() == 0
    assert page.locator("[data-testid='stException']").count() == 0

    page.get_by_role("link", name="Frequency Model").click()
    expect(page.get_by_text("Model setup").first).to_be_visible()
    expect(page.get_by_text("ClaimNb ~").first).to_be_visible()
    expect(page.get_by_role("button", name="Fit model")).to_be_visible()
    expect(page.get_by_text("Variable selection").first).to_be_visible()
    assert page.locator("[data-testid='stException']").count() == 0
    print("TC5 PASS")

    # TC6 — severity happy path: sanctioned combobox route, fit, results, wording
    page.get_by_role("link", name="Data Import").click()
    expect(page.get_by_text("Built-in dataset").first).to_be_visible()
    page.locator("[data-testid='stSelectbox']").first.click()
    page.keyboard.type("severity")
    page.keyboard.press("Enter")
    page.get_by_role("button", name="Load dataset").click()
    expect(page.get_by_text("26,444 rows").first).to_be_visible()

    page.get_by_role("link", name="Severity Model").click()
    expect(page.get_by_text("Model setup").first).to_be_visible()
    expect(page.get_by_text("Distribution").first).to_be_visible()
    assert page.locator("[data-testid='stSelectbox']").count() >= 1
    expect(page.get_by_text("ClaimAmount ~ Area").first).to_be_visible()
    assert page.get_by_text("ClaimNb").count() == 0
    expect(page.get_by_text("Log link, no offset").first).to_be_visible()
    assert page.get_by_text("Variable selection").count() == 0
    assert page.get_by_text("claim frequency").count() == 0
    assert page.get_by_text("per policy-year").count() == 0
    assert page.get_by_text("Exposure").count() == 0

    page.get_by_role("button", name="Fit model").click()
    expect(page.get_by_text("Model fitted and recorded").first).to_be_visible(timeout=30000)
    metrics = page.locator("[data-testid='stMetric']")
    expect(metrics.first).to_be_visible()
    assert metrics.count() == 4, metrics.count()
    for label in ["AIC", "BIC", "Deviance", "Parameters"]:
        expect(page.get_by_text(label).first).to_be_visible()
    expect(page.get_by_text("Coefficients").first).to_be_visible()
    expect(page.get_by_text("claim-size relativity").first).to_be_visible()
    grids = page.locator("[data-testid='stDataFrame']")
    expect(grids.first).to_be_visible()
    assert grids.count() >= 2  # coefficient table + run history
    expect(page.get_by_text("What the strongest effects mean").first).to_be_visible()
    expect(page.get_by_text("Statistically insignificant terms").first).to_be_visible()
    expect(page.get_by_text("Severity signal is usually weaker").first).to_be_visible()
    expect(page.get_by_text("Run history").first).to_be_visible()
    # whole-page wording re-check after fitting
    assert page.get_by_text("claim frequency").count() == 0
    assert page.get_by_text("per policy-year").count() == 0
    assert page.get_by_text("Exposure").count() == 0
    assert page.get_by_text("Variable selection").count() == 0
    assert page.get_by_text("Traceback").count() == 0
    assert page.locator("[data-testid='stException']").count() == 0
    print("TC6 PASS (automated combobox route: click + type + Enter)")

    # TC7 — single-slot stale state: interim guards on 05/06, no crash on 04
    page.get_by_role("link", name="Diagnostics").click()
    expect(page.get_by_text("severity model").first).to_be_visible()
    expect(page.get_by_text("next slice").first).to_be_visible()
    assert page.locator("[data-testid='stMetric']").count() == 0
    assert page.get_by_text("Traceback").count() == 0
    assert page.locator("[data-testid='stException']").count() == 0

    page.get_by_role("link", name="Prediction").click()
    expect(page.get_by_text("severity model").first).to_be_visible()
    expect(page.get_by_text("next slice").first).to_be_visible()
    assert page.get_by_role("button", name="Predict", exact=True).count() == 0
    assert page.get_by_text("Traceback").count() == 0
    assert page.locator("[data-testid='stException']").count() == 0

    page.get_by_role("link", name="Frequency Model").click()
    expect(page.get_by_text("severity dataset").first).to_be_visible()
    expect(page.get_by_text("Severity Model screen").first).to_be_visible()
    assert page.get_by_role("button", name="Fit model").count() == 0
    assert page.get_by_text("Model setup").count() == 0
    assert page.get_by_text("Traceback").count() == 0
    assert page.locator("[data-testid='stException']").count() == 0
    print("TC7 PASS")

    browser.close()

print("ALL EXECUTED TCs PASSED (TC8 run separately from the shell; TC9 deferred/manual)")
