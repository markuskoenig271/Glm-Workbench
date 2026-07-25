"""GLM fitting: frequency (Poisson / Negative Binomial) and severity (Gamma / Inverse Gaussian).

Backed by statsmodels (key decision 4 in .planning/PROJECT.md). V1 implements the
frequency side only (Poisson, log link, exposure offset — docs/car-insurance.md);
Negative Binomial and the severity families follow in later versions.
"""

from typing import Any

import pandas as pd

FREQUENCY_FAMILIES = ["poisson", "negative_binomial"]
SEVERITY_FAMILIES = ["gamma", "inverse_gaussian"]


def fit_frequency_glm(
    df: pd.DataFrame,
    formula: str,
    family: str = "poisson",
    offset_column: str | None = "exposure",
) -> Any:
    """Fit a frequency GLM (claim counts, exposure as offset)."""
    raise NotImplementedError


def fit_severity_glm(
    df: pd.DataFrame,
    formula: str,
    family: str = "gamma",
) -> Any:
    """Fit a severity GLM on claims with positive amounts."""
    raise NotImplementedError
