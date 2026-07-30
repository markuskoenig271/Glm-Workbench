"""Shared fixtures. tmp_db gives every test an isolated SQLite database."""

import sqlite3
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pytest

from pricing_engine import glm
from pricing_engine.data import DatasetSpec


@pytest.fixture
def tmp_db(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    """An isolated SQLite database, deleted with the test's tmp_path."""
    conn = sqlite3.connect(tmp_path / "test.db")
    yield conn
    conn.close()


@pytest.fixture
def fremtpl2_sample() -> pd.DataFrame:
    """A tiny frame in the freMTPL2freq schema (native column names, all 12 columns)."""
    return pd.DataFrame(
        {
            "IDpol": [1, 3, 5, 10],
            "ClaimNb": [1, 0, 2, 0],
            "Exposure": [0.10, 0.77, 0.75, 1.0],
            "Area": ["D", "D", "B", "A"],
            "VehPower": [5, 5, 6, 7],
            "VehAge": [0, 2, 2, 12],
            "DrivAge": [55, 55, 52, 30],
            "BonusMalus": [50, 50, 50, 68],
            "VehBrand": ["B12", "B12", "B12", "B3"],
            "VehGas": ["Regular", "Regular", "Diesel", "Petrol"],
            "Density": [1217.0, 1217.0, 54.0, 3000.0],
            "Region": ["R82", "R82", "R22", "R11"],
        }
    )


@pytest.fixture
def fremtpl2_sev_sample() -> pd.DataFrame:
    """A tiny frame in the freMTPL2sev schema: policy 1 claims twice, 99 is an orphan."""
    return pd.DataFrame(
        {
            "IDpol": [1, 1, 5, 99],
            "ClaimAmount": [1204.00, 1128.12, 500.0, 999.0],
        }
    )


GROUP_SPEC = DatasetSpec(
    name="test_group",
    label="Test group portfolio",
    target="ClaimNb",
    offset="Exposure",
    predictors=("Group", "Noise"),
)


@pytest.fixture
def group_portfolio() -> pd.DataFrame:
    """2k-row portfolio with a real Poisson signal (B ~3x A) and a no-effect Noise factor."""
    rng = np.random.default_rng(7)
    n = 2_000
    group = rng.choice(["A", "B"], size=n)
    exposure = rng.uniform(0.1, 1.0, size=n)
    rate = np.where(group == "A", 0.1, 0.3)
    return pd.DataFrame(
        {
            "ClaimNb": rng.poisson(rate * exposure),
            "Exposure": exposure,
            "Group": group,
            "Noise": rng.choice(["X", "Y"], size=n),
        }
    )


@pytest.fixture
def fitted_model(group_portfolio: pd.DataFrame) -> Any:
    """A converged Poisson GLM on the group portfolio (offset log Exposure)."""
    return glm.fit_frequency_glm(
        group_portfolio, "ClaimNb ~ Group + Noise", offset_column="Exposure"
    )


@pytest.fixture
def sample_portfolio() -> pd.DataFrame:
    """A tiny portfolio in the Chapter 27 schema (docs/car-insurance.md)."""
    return pd.DataFrame(
        {
            "Age": [25, 47, 33, 61],
            "LocationType": ["Urban", "Rural", "Urban", "Rural"],
            "Region": ["R1", "R3", "R2", "R5"],
            "VehicleAge": [3, 10, 7, 1],
            "FuelType": ["Petrol", "Diesel", "Electric", "Petrol"],
            "NoClaimYears": [0, 5, 2, 9],
            "Dummy1": [0, 1, 0, 1],
            "Dummy2": ["A", "B", "A", "C"],
            "Exposure": [1.0, 0.5, 1.0, 0.25],
            "Claims": [0, 1, 2, 0],
        }
    )
