"""Diagnostics: coefficients, residuals, calibration, AIC/BIC, true-model comparison.

Plot-feeding functions return small aggregated frames (bins, quantile points,
calibration bands) — never one row per policy (docs/architecture.md scale note).
"""

from typing import Any

import numpy as np
import pandas as pd
from scipy import stats

from pricing_engine.data import DatasetSpec

RESIDUAL_KINDS = ["deviance", "pearson"]

SIGNIFICANCE_LEVEL = 0.05


def coefficient_table(model: Any) -> pd.DataFrame:
    """Coefficients with std errors, p-values, CIs, and exp(coef) risk relativities."""
    confidence = model.conf_int()
    table = pd.DataFrame(
        {
            "term": model.params.index,
            "coef": model.params.to_numpy(),
            "std_err": model.bse.to_numpy(),
            "p_value": model.pvalues.to_numpy(),
            "ci_low": confidence[0].to_numpy(),
            "ci_high": confidence[1].to_numpy(),
        }
    )
    table["exp_coef"] = np.exp(table["coef"])
    table["significant"] = table["p_value"] < SIGNIFICANCE_LEVEL
    return table.reset_index(drop=True)


def residuals(model: Any, kind: str = "deviance") -> pd.Series:
    """Residuals of the given kind (see RESIDUAL_KINDS)."""
    if kind not in RESIDUAL_KINDS:
        raise ValueError(f"Unknown residual kind '{kind}' — valid: {', '.join(RESIDUAL_KINDS)}")
    return model.resid_deviance if kind == "deviance" else model.resid_pearson


def residual_histogram(model: Any, kind: str = "deviance", bins: int = 40) -> pd.DataFrame:
    """Binned residual distribution: (bin midpoint, count) per bin."""
    values = residuals(model, kind)
    counts, edges = np.histogram(values, bins=bins)
    midpoints = (edges[:-1] + edges[1:]) / 2
    return pd.DataFrame({"residual": midpoints, "count": counts})


def qq_data(model: Any, kind: str = "deviance", points: int = 100) -> pd.DataFrame:
    """Sample residual quantiles vs standard-normal theoretical quantiles."""
    values = residuals(model, kind)
    probabilities = (np.arange(1, points + 1) - 0.5) / points
    return pd.DataFrame(
        {
            "theoretical": stats.norm.ppf(probabilities),
            "sample": np.quantile(values, probabilities),
        }
    )


def observed_vs_predicted(
    df: pd.DataFrame, spec: DatasetSpec, model: Any, groups: int = 10
) -> pd.DataFrame:
    """Calibration by predicted-frequency band: observed vs predicted per band.

    Policies are grouped into quantile bands of predicted frequency; per band
    the exposure-weighted observed and predicted frequencies are compared.
    """
    fitted = np.asarray(model.fittedvalues)
    exposure = df[spec.offset].to_numpy() if spec.offset is not None else np.ones(len(df))
    rate = fitted / exposure
    bands = pd.qcut(pd.Series(rate, index=df.index), q=groups, duplicates="drop")

    working = pd.DataFrame(
        {
            "band": bands,
            "exposure": exposure,
            "observed": df[spec.target].to_numpy(),
            "predicted": fitted,
        }
    )
    grouped = working.groupby("band", observed=True, sort=True).agg(
        exposure=("exposure", "sum"),
        observed=("observed", "sum"),
        predicted=("predicted", "sum"),
    )
    result = pd.DataFrame(
        {
            "group": grouped.index.astype(str),
            "exposure": grouped["exposure"].to_numpy(),
            "observed_frequency": (grouped["observed"] / grouped["exposure"]).to_numpy(),
            "predicted_frequency": (grouped["predicted"] / grouped["exposure"]).to_numpy(),
        }
    )
    return result.reset_index(drop=True)


def information_criteria(model: Any) -> dict[str, float]:
    """AIC / BIC / deviance / log-likelihood plus model size, for comparison."""
    return {
        "aic": float(model.aic),
        "bic": float(model.bic_llf),
        "deviance": float(model.deviance),
        "log_likelihood": float(model.llf),
        "n_params": int(model.df_model) + 1,
        "n_obs": int(model.nobs),
    }


def compare_with_true_model(model: Any, true_coefficients: dict[str, float]) -> pd.DataFrame:
    """Estimated vs hidden data-generating coefficients (BACKLOGGED, Chapter 27)."""
    raise NotImplementedError
