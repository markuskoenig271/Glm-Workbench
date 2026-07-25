"""Prediction: expected claim frequency (V1); pure premium arrives in V3."""

from typing import Any

import pandas as pd


def predict_frequency(frequency_model: Any, policies: pd.DataFrame) -> pd.DataFrame:
    """Return policies with a predicted expected-claim-frequency column (V1)."""
    raise NotImplementedError


def predict_pure_premium(
    frequency_model: Any,
    severity_model: Any,
    policies: pd.DataFrame,
) -> pd.DataFrame:
    """Return policies with predicted frequency, severity, and pure premium columns (V3)."""
    raise NotImplementedError
