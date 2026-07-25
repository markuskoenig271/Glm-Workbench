"""Feature engineering: binning, log transforms, encoding, capping.

All functions return a copy; the input frame is never mutated. New columns are
named after their source (`<column>_band`, `<column>_log`, `<column>_<level>`)
so they read naturally in specs, one-way analyses, and model formulas.
"""

import numpy as np
import pandas as pd

BIN_STRATEGIES = ["quantile", "uniform"]


def _require_column(df: pd.DataFrame, column: str) -> None:
    if column not in df.columns:
        raise ValueError(f"Unknown column '{column}' — available: {', '.join(df.columns)}")


def bin_numeric(
    df: pd.DataFrame, column: str, bins: int = 8, strategy: str = "quantile"
) -> tuple[pd.DataFrame, str]:
    """Add a banded categorical `<column>_band` with readable ordered labels.

    Returns (frame copy, new column name). `quantile` gives equal-exposure
    bands (actuarial default); `uniform` gives equal-width bands.
    """
    _require_column(df, column)
    if not pd.api.types.is_numeric_dtype(df[column]):
        raise ValueError(f"Column '{column}' is not numeric — binning needs a numeric column")
    if strategy not in BIN_STRATEGIES:
        raise ValueError(f"Unknown strategy '{strategy}' — valid: {', '.join(BIN_STRATEGIES)}")

    result = df.copy()
    if strategy == "quantile":
        bands = pd.qcut(result[column], q=bins, duplicates="drop")
    else:
        bands = pd.cut(result[column], bins=bins)

    new_column = f"{column}_band"
    result[new_column] = bands.astype(str)
    return result, new_column


def log_transform(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Add `<column>_log` (natural log) per column; requires strictly positive values."""
    result = df.copy()
    for column in columns:
        _require_column(df, column)
        series = df[column]
        if not pd.api.types.is_numeric_dtype(series) or (series <= 0).any():
            raise ValueError(
                f"Column '{column}' has non-positive or non-numeric values — "
                "log transform needs strictly positive numbers"
            )
        result[f"{column}_log"] = np.log(series)
    return result


def encode_categorical(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Add one-hot dummies (`<column>_<level>`, baseline level dropped); originals kept.

    Note: the GLM formula interface encodes categoricals automatically at fit
    time — this exists for exports and non-formula workflows.
    """
    for column in columns:
        _require_column(df, column)
    dummies = pd.get_dummies(df[columns], prefix=columns, drop_first=True)
    return pd.concat([df.copy(), dummies], axis=1)


def cap_column(df: pd.DataFrame, column: str, cap: float) -> tuple[pd.DataFrame, int]:
    """Clip values above `cap`; returns (frame copy, number of capped rows).

    freMTPL2's Exposure runs up to ~2 policy-years; the literature caps it at 1.
    """
    _require_column(df, column)
    n_capped = int((df[column] > cap).sum())
    result = df.copy()
    result[column] = result[column].clip(upper=cap)
    return result, n_capped
