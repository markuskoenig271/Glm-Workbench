"""Diagnostics: coefficients, residuals, calibration, AIC/BIC, true-model comparison."""

from typing import Any

import pandas as pd

RESIDUAL_KINDS = ["deviance", "pearson"]


def coefficient_table(model: Any) -> pd.DataFrame:
    """Coefficients with std errors, p-values, confidence intervals, and exp(coef) relativities."""
    raise NotImplementedError


def residuals(model: Any, kind: str = "deviance") -> pd.Series:
    """Residuals of the given kind (see RESIDUAL_KINDS)."""
    raise NotImplementedError


def information_criteria(model: Any) -> dict[str, float]:
    """AIC / BIC / deviance for model comparison."""
    raise NotImplementedError


def compare_with_true_model(model: Any, true_coefficients: dict[str, float]) -> pd.DataFrame:
    """Estimated vs hidden data-generating coefficients (educational, Chapter 27)."""
    raise NotImplementedError
