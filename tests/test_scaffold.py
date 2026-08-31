"""Scaffold contract tests: the package imports, exposes its API, and stubs fail loudly.

These pin the pricing_engine surface agreed in docs/architecture.md and the
Chapter 27 dataset schema from docs/car-insurance.md; each stub test is replaced
by real tests (written first, per TDD) when the feature is implemented.
"""

import sqlite3

import pandas as pd
import pytest

import pricing_engine
from pricing_engine import data, diagnostics, glm, report


def test_version() -> None:
    assert pricing_engine.__version__ == "0.1.0"


def test_chapter27_schema() -> None:
    assert data.TARGET_COLUMN == "Claims"
    assert data.OFFSET_COLUMN == "Exposure"
    assert data.PREDICTOR_COLUMNS == [
        "Age",
        "LocationType",
        "Region",
        "VehicleAge",
        "FuelType",
        "NoClaimYears",
        "Dummy1",
        "Dummy2",
    ]
    assert data.REQUIRED_COLUMNS == ["Claims", "Exposure"]
    assert data.DEFAULT_N_POLICIES == 20_000


def test_fremtpl2_schema() -> None:
    assert data.FREMTPL2_TARGET_COLUMN == "ClaimNb"
    assert data.FREMTPL2_OFFSET_COLUMN == "Exposure"
    assert data.FREMTPL2_PREDICTOR_COLUMNS == [
        "Area",
        "VehPower",
        "VehAge",
        "DrivAge",
        "BonusMalus",
        "VehBrand",
        "VehGas",
        "Density",
        "Region",
    ]
    assert data.FREMTPL2_FREQ_PATH.name == "freMTPL2freq.parquet"
    assert data.FREMTPL2_SEV_PATH.name == "freMTPL2sev.parquet"


def test_glm_families() -> None:
    assert glm.FREQUENCY_FAMILIES == ["poisson", "negative_binomial"]
    assert glm.SEVERITY_FAMILIES == ["gamma", "inverse_gaussian"]


def test_residual_kinds() -> None:
    assert diagnostics.RESIDUAL_KINDS == ["deviance", "pearson"]


def test_stubs_fail_loudly(sample_portfolio: pd.DataFrame) -> None:
    """Unimplemented engine functions must raise, never silently return."""
    with pytest.raises(NotImplementedError):
        data.generate_chapter27_portfolio()
    with pytest.raises(NotImplementedError):
        diagnostics.compare_with_true_model(None, {})
    with pytest.raises(NotImplementedError):
        report.export_html(None, "report.html")


def test_tmp_db_fixture(tmp_db: sqlite3.Connection) -> None:
    tmp_db.execute("CREATE TABLE t (x INTEGER)")
    tmp_db.execute("INSERT INTO t VALUES (1)")
    assert tmp_db.execute("SELECT x FROM t").fetchone() == (1,)


def test_sample_portfolio_fixture(sample_portfolio: pd.DataFrame) -> None:
    expected = set(data.PREDICTOR_COLUMNS) | set(data.REQUIRED_COLUMNS)
    assert expected <= set(sample_portfolio.columns)
    assert (sample_portfolio[data.OFFSET_COLUMN] > 0).all()
