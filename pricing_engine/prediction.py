"""Prediction: expected claim frequency (V1); pure premium arrives in V3."""

from typing import Any

import numpy as np
import pandas as pd

from pricing_engine.data import DatasetSpec


def predict_frequency(model: Any, policies: pd.DataFrame, spec: DatasetSpec) -> pd.DataFrame:
    """Return a copy of `policies` with expected_frequency and expected_claims.

    expected_frequency is per policy-year (offset-free rate); expected_claims
    scales it by the policy's exposure when the spec defines an offset.
    """
    missing = [p for p in spec.predictors if p not in policies.columns]
    if missing:
        raise ValueError(f"Missing predictor column(s): {', '.join(missing)}")

    result = policies.copy()
    # offset 0 -> the pure per-policy-year rate, independent of the row's exposure
    rate = np.asarray(model.predict(result, offset=np.zeros(len(result))))
    result["expected_frequency"] = rate
    if spec.offset is not None:
        result["expected_claims"] = rate * result[spec.offset].to_numpy()
    else:
        result["expected_claims"] = rate
    return result


def predict_pure_premium(
    frequency_model: Any,
    severity_model: Any,
    policies: pd.DataFrame,
) -> pd.DataFrame:
    """Return policies with predicted frequency, severity, and pure premium columns (V3)."""
    raise NotImplementedError
