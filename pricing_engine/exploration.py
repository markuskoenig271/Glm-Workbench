"""Portfolio exploration: summary stats, one-way frequencies, histograms, correlations.

Every function AGGREGATES — it returns a small frame, never raw rows — so the UI
stays fast on the 678k-row freMTPL2 portfolio (docs/architecture.md scale note).
"""

import numpy as np
import pandas as pd

from pricing_engine.data import DatasetSpec


def portfolio_frequency(df: pd.DataFrame, spec: DatasetSpec) -> float:
    """Overall claim frequency: claims per policy-year (per policy without offset)."""
    claims = float(df[spec.target].sum())
    if spec.offset is not None:
        return claims / float(df[spec.offset].sum())
    return claims / len(df)


def summarize_portfolio(df: pd.DataFrame, spec: DatasetSpec) -> pd.DataFrame:
    """One row per required column: role, kind, missing/unique counts, numeric stats."""
    roles = {spec.target: "target"}
    if spec.offset is not None:
        roles[spec.offset] = "offset"
    rows = []
    for column in spec.required_columns:
        series = df[column]
        numeric = pd.api.types.is_numeric_dtype(series)
        rows.append(
            {
                "column": column,
                "role": roles.get(column, "predictor"),
                "kind": "numeric" if numeric else "categorical",
                "missing": int(series.isna().sum()),
                "unique": int(series.nunique()),
                "min": float(series.min()) if numeric else None,
                "mean": float(series.mean()) if numeric else None,
                "max": float(series.max()) if numeric else None,
            }
        )
    return pd.DataFrame(rows)


def one_way_frequency(
    df: pd.DataFrame, spec: DatasetSpec, predictor: str, max_levels: int = 12
) -> pd.DataFrame:
    """The classic actuarial one-way: claim frequency per predictor level.

    Numeric predictors with more than max_levels distinct values are
    quantile-binned; level labels are plain strings in natural order.
    """
    if predictor not in spec.predictors:
        valid = ", ".join(spec.predictors)
        raise ValueError(f"Unknown predictor '{predictor}' — valid predictors: {valid}")

    series = df[predictor]
    if pd.api.types.is_numeric_dtype(series) and series.nunique() > max_levels:
        groups = pd.qcut(series, q=max_levels, duplicates="drop")
    else:
        groups = series

    aggregations: dict[str, tuple[str, str]] = {
        "policies": (spec.target, "size"),
        "claims": (spec.target, "sum"),
    }
    if spec.offset is not None:
        aggregations["exposure"] = (spec.offset, "sum")

    grouped = df.groupby(groups, observed=True, sort=True).agg(**aggregations)
    denominator = grouped["exposure"] if spec.offset is not None else grouped["policies"]
    grouped["frequency"] = grouped["claims"] / denominator

    result = grouped.reset_index(names=predictor)
    result[predictor] = result[predictor].astype(str)
    return result


def histogram(df: pd.DataFrame, column: str, bins: int = 30) -> pd.DataFrame:
    """Aggregated distribution: binned counts for numerics, value counts otherwise."""
    if column not in df.columns:
        raise ValueError(f"Unknown column '{column}' — available: {', '.join(df.columns)}")

    series = df[column].dropna()
    if pd.api.types.is_numeric_dtype(series) and series.nunique() > bins:
        counts, edges = np.histogram(series, bins=bins)
        labels = [f"{edges[i]:.4g} – {edges[i + 1]:.4g}" for i in range(len(counts))]
        return pd.DataFrame({column: labels, "count": counts})

    value_counts = series.value_counts().sort_index()
    return pd.DataFrame({column: value_counts.index.astype(str), "count": value_counts.to_numpy()})


def correlation_matrix(df: pd.DataFrame, spec: DatasetSpec) -> pd.DataFrame:
    """Pearson correlations of the numeric required columns."""
    numeric = [
        column for column in spec.required_columns if pd.api.types.is_numeric_dtype(df[column])
    ]
    return df[numeric].corr()
