"""Data layer: portfolio import, validation, and the synthetic Chapter 27 dataset.

Dataset schema per docs/car-insurance.md (Parodi, Chapter 27): ~20,000 policies,
claim counts as target, exposure as offset, and eight predictors — two of which
(Dummy1, Dummy2) are intentionally unrelated to the response.
"""

from pathlib import Path

import pandas as pd

TARGET_COLUMN = "Claims"
OFFSET_COLUMN = "Exposure"
PREDICTOR_COLUMNS = [
    "Age",  # continuous
    "LocationType",  # urban / rural
    "Region",  # 5 categories
    "VehicleAge",  # continuous
    "FuelType",  # electric / diesel / petrol
    "NoClaimYears",  # ordinal
    "Dummy1",  # binary, no real effect
    "Dummy2",  # categorical, no real effect
]

# Minimum a portfolio must provide for V1 frequency modelling.
REQUIRED_COLUMNS = [TARGET_COLUMN, OFFSET_COLUMN]

DEFAULT_N_POLICIES = 20_000

# freMTPL2: real French motor TPL data (CC0, OpenML 41214/41215), Parquet files
# in data/raw/ — see docs/architecture.md "Datasets". Native column names are
# kept; the dataset spec (target/offset/predictors) absorbs the difference.
FREMTPL2_FREQ_PATH = Path("data/raw/freMTPL2freq.parquet")
FREMTPL2_SEV_PATH = Path("data/raw/freMTPL2sev.parquet")
FREMTPL2_TARGET_COLUMN = "ClaimNb"
FREMTPL2_OFFSET_COLUMN = "Exposure"
FREMTPL2_PREDICTOR_COLUMNS = [
    "Area",  # density band A–F
    "VehPower",
    "VehAge",
    "DrivAge",
    "BonusMalus",
    "VehBrand",
    "VehGas",  # Diesel / Regular
    "Density",
    "Region",
]


def load_fremtpl2_freq(path: str | Path = FREMTPL2_FREQ_PATH) -> pd.DataFrame:
    """Load the freMTPL2 frequency table (678k policies)."""
    raise NotImplementedError


def load_fremtpl2_sev(path: str | Path = FREMTPL2_SEV_PATH) -> pd.DataFrame:
    """Load the freMTPL2 severity table (26.6k claim amounts; V2)."""
    raise NotImplementedError


def generate_chapter27_portfolio(
    n_policies: int = DEFAULT_N_POLICIES, seed: int = 27
) -> tuple[pd.DataFrame, dict[str, float]]:
    """Generate the synthetic Chapter 27 portfolio.

    Returns the portfolio and the hidden data-generating coefficients, kept for
    the educational estimated-vs-true comparison on the Diagnostics screen.
    """
    raise NotImplementedError


def load_portfolio(path: str | Path) -> pd.DataFrame:
    """Load a portfolio CSV into a DataFrame."""
    raise NotImplementedError


def validate_portfolio(df: pd.DataFrame) -> list[str]:
    """Validate a portfolio; return a list of human-readable findings (empty = valid)."""
    raise NotImplementedError
