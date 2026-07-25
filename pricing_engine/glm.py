"""GLM fitting: frequency (Poisson / Negative Binomial) and severity (Gamma / Inverse Gaussian).

Backed by statsmodels (key decision 4 in .planning/PROJECT.md). V1 implements the
frequency side (Poisson default, log link, log-exposure offset — docs/car-insurance.md);
the severity families follow in V2. Categorical predictors are treatment-coded
automatically by the formula interface.
"""

from typing import Any

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf

from pricing_engine.data import DatasetSpec

FREQUENCY_FAMILIES = ["poisson", "negative_binomial"]
SEVERITY_FAMILIES = ["gamma", "inverse_gaussian"]

_FREQUENCY_FAMILY_BUILDERS = {
    "poisson": sm.families.Poisson,
    "negative_binomial": sm.families.NegativeBinomial,
}


def build_formula(spec: DatasetSpec) -> str:
    """Model formula from a dataset spec: target ~ predictors.

    The offset is passed to the fit separately (log-exposure), never as a term.
    """
    if not spec.predictors:
        raise ValueError("The spec has no predictors — select at least one variable")
    return f"{spec.target} ~ {' + '.join(spec.predictors)}"


def fit_frequency_glm(
    df: pd.DataFrame,
    formula: str,
    family: str = "poisson",
    offset_column: str | None = "Exposure",
) -> Any:
    """Fit a frequency GLM (log link) with an optional log-exposure offset."""
    if family not in _FREQUENCY_FAMILY_BUILDERS:
        raise ValueError(
            f"Unknown frequency family '{family}' — valid: {', '.join(FREQUENCY_FAMILIES)}"
        )
    offset = np.log(df[offset_column]) if offset_column is not None else None
    model = smf.glm(formula, data=df, family=_FREQUENCY_FAMILY_BUILDERS[family](), offset=offset)
    return model.fit()


def fit_severity_glm(
    df: pd.DataFrame,
    formula: str,
    family: str = "gamma",
) -> Any:
    """Fit a severity GLM on claims with positive amounts (V2)."""
    raise NotImplementedError
