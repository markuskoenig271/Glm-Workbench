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
