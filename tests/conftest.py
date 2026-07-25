"""Shared fixtures. tmp_db gives every test an isolated SQLite database."""

import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pandas as pd
import pytest


@pytest.fixture
def tmp_db(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    """An isolated SQLite database, deleted with the test's tmp_path."""
    conn = sqlite3.connect(tmp_path / "test.db")
    yield conn
    conn.close()


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
