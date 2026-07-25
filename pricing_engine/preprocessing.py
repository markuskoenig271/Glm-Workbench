"""Feature engineering: binning, encoding, transforms, interactions, offsets."""

import pandas as pd


def bin_numeric(df: pd.DataFrame, column: str, bins: int) -> pd.DataFrame:
    """Bin a numeric column into categorical bands."""
    raise NotImplementedError


def encode_categorical(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """One-hot encode categorical columns."""
    raise NotImplementedError


def log_transform(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Apply log transforms to numeric columns."""
    raise NotImplementedError
