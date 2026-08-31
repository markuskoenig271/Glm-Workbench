"""Prediction: expected claim frequency (V1), expected claim amount (V2); pure premium in V3."""

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


def predict_severity(model: Any, claims: pd.DataFrame, spec: DatasetSpec) -> pd.DataFrame:
    """Return a copy of `claims` with expected_claim_amount per row.

    Severity models are fitted per claim with no offset, so the expected claim
    amount is the model mean exp(X beta) itself — no exposure scaling applies.
    """
    missing = [p for p in spec.predictors if p not in claims.columns]
    if missing:
        raise ValueError(f"Missing predictor column(s): {', '.join(missing)}")

    result = claims.copy()
    result["expected_claim_amount"] = np.asarray(model.predict(result))
    return result


def predict_pure_premium(
    frequency_model: Any,
    severity_model: Any,
    policies: pd.DataFrame,
    spec: DatasetSpec,
) -> pd.DataFrame:
    """Return a copy of `policies` with the pure-premium columns (V3).

    pure_premium = expected_frequency (annual, offset-free rate) x
    expected_claim_amount — the expected yearly loss per unit of exposure;
    expected_loss scales it by the offset column when the spec defines one.
    Both models are applied to the same policy rating factors; the check
    covers the union of the spec and BOTH models' formula columns (the two
    models may have been fitted on different predictor sets).
    """
    required = required_columns(frequency_model, severity_model, spec)
    missing = [p for p in required if p not in policies.columns]
    if missing:
        raise ValueError(f"Missing predictor column(s): {', '.join(missing)}")

    result = policies.copy()
    rate = np.asarray(frequency_model.predict(result, offset=np.zeros(len(result))))
    amount = np.asarray(severity_model.predict(result))
    result["expected_frequency"] = rate
    result["expected_claim_amount"] = amount
    result["pure_premium"] = rate * amount
    if spec.offset is not None:
        result["expected_loss"] = result["pure_premium"] * result[spec.offset].to_numpy()
    else:
        result["expected_loss"] = result["pure_premium"]
    return result


def formula_columns(model: Any) -> list[str]:
    """Input columns a formula-fitted model needs, in formula order.

    Formulas in this app are always plain main effects (`build_formula`),
    so the RHS terms ARE the column names. Returns [] when the model carries
    no formula (non-formula fit).
    """
    formula = getattr(getattr(model, "model", None), "formula", None)
    if not formula or "~" not in formula:
        return []
    return [term.strip() for term in formula.split("~", 1)[1].split("+") if term.strip()]


def required_columns(frequency_model: Any, severity_model: Any, spec: DatasetSpec) -> list[str]:
    """Union of the spec's predictors and both models' formula columns."""
    required = list(spec.predictors)
    for column in formula_columns(frequency_model) + formula_columns(severity_model):
        if column not in required:
            required.append(column)
    return required


def premium_breakdown(
    frequency_model: Any,
    severity_model: Any,
    profile: pd.DataFrame,
    portfolio: pd.DataFrame,
    spec: DatasetSpec,
) -> tuple[float, pd.DataFrame]:
    """Multiplicative decomposition of a single profile's pure premium (V3).

    With log links and no interactions, premium = base x product of one factor
    per predictor, where each factor compares the profile against a reference
    value for that predictor alone (categorical: the reference level, i.e. the
    first sorted level in `portfolio` — patsy's ordering; numeric: the
    portfolio median, so the base reads as a plausible reference policy and a
    median profile's factor is exactly 1.0). `base` is the all-reference
    profile's premium. Returns (base_premium, factors) with per-model and
    combined factors.
    """
    predictors = [p for p in required_columns(frequency_model, severity_model, spec)]
    missing = [p for p in predictors if p not in profile.columns]
    if missing:
        raise ValueError(f"Missing predictor column(s): {', '.join(missing)}")

    def premium_of(row: pd.DataFrame) -> float:
        rate = float(np.asarray(frequency_model.predict(row, offset=np.zeros(1)))[0])
        amount = float(np.asarray(severity_model.predict(row))[0])
        return rate * amount

    def rate_of(row: pd.DataFrame) -> float:
        return float(np.asarray(frequency_model.predict(row, offset=np.zeros(1)))[0])

    def amount_of(row: pd.DataFrame) -> float:
        return float(np.asarray(severity_model.predict(row))[0])

    row = profile.iloc[[0]].copy()
    baselines: dict[str, str | float] = {}
    for predictor in predictors:
        series = portfolio[predictor]
        if pd.api.types.is_numeric_dtype(series):
            baselines[predictor] = float(series.median())
        else:
            baselines[predictor] = sorted(str(v) for v in series.dropna().unique())[0]

    base_row = row.copy()
    for predictor, baseline in baselines.items():
        base_row[predictor] = baseline
    base_premium = premium_of(base_row)

    records = []
    for predictor in predictors:
        swapped = row.copy()
        swapped[predictor] = baselines[predictor]
        records.append(
            {
                "predictor": predictor,
                "value": row[predictor].iloc[0],
                "frequency_factor": rate_of(row) / rate_of(swapped),
                "severity_factor": amount_of(row) / amount_of(swapped),
            }
        )
    factors = pd.DataFrame(records)
    factors["combined_factor"] = factors["frequency_factor"] * factors["severity_factor"]
    return base_premium, factors
