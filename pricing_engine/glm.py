"""GLM fitting: frequency (Poisson / Negative Binomial) and severity (Gamma / Inverse Gaussian).

Backed by statsmodels (key decision 4 in .planning/PROJECT.md). V1 implements the
frequency side (Poisson default, log link, log-exposure offset — docs/car-insurance.md);
the severity families follow in V2. Categorical predictors are treatment-coded
automatically by the formula interface.
"""

from collections.abc import Callable
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


SELECTION_DIRECTIONS = ["backward", "forward"]
SELECTION_CRITERIA = ["aic", "bic"]


def _criterion_value(model: Any, criterion: str) -> float:
    return float(model.aic) if criterion == "aic" else float(model.bic_llf)


def stepwise_selection(
    df: pd.DataFrame,
    spec: DatasetSpec,
    family: str = "poisson",
    direction: str = "backward",
    criterion: str = "aic",
    on_fit: Callable[[str], None] | None = None,
) -> tuple[tuple[str, ...], pd.DataFrame]:
    """Stepwise variable selection by information criterion.

    Backward: drop the predictor whose removal most improves the criterion,
    repeat until no removal improves. Forward: start from intercept-only and
    add the best-improving predictor until none improves. Returns the selected
    predictors and a step log (one row per accepted step, "start" first).

    On large portfolios select by AIC/BIC, not p-values — at this scale nearly
    every term is "significant".
    """
    if direction not in SELECTION_DIRECTIONS:
        raise ValueError(
            f"Unknown direction '{direction}' — valid: {', '.join(SELECTION_DIRECTIONS)}"
        )
    if criterion not in SELECTION_CRITERIA:
        raise ValueError(
            f"Unknown criterion '{criterion}' — valid: {', '.join(SELECTION_CRITERIA)}"
        )

    def fit_score(predictors: list[str], label: str) -> float:
        if on_fit is not None:
            on_fit(label)
        terms = " + ".join(predictors) if predictors else "1"
        model = fit_frequency_glm(
            df, f"{spec.target} ~ {terms}", family=family, offset_column=spec.offset
        )
        return _criterion_value(model, criterion)

    current = list(spec.predictors) if direction == "backward" else []
    remaining = [] if direction == "backward" else list(spec.predictors)
    current_value = fit_score(current, "start: fitting the starting model")

    log_rows: list[dict[str, object]] = [
        {"step": 0, "action": "start", "n_predictors": len(current), "value": current_value}
    ]
    step = 0
    while True:
        candidates = current if direction == "backward" else remaining
        if not candidates:
            break
        best_term: str | None = None
        best_value = current_value
        for term in candidates:
            if direction == "backward":
                trial = [p for p in current if p != term]
                label = f"trying without {term}"
            else:
                trial = [*current, term]
                label = f"trying with {term}"
            value = fit_score(trial, label)
            if value < best_value:
                best_term, best_value = term, value
        if best_term is None:
            break
        step += 1
        if direction == "backward":
            current = [p for p in current if p != best_term]
            action = f"drop {best_term}"
        else:
            current = [*current, best_term]
            remaining = [p for p in remaining if p != best_term]
            action = f"add {best_term}"
        current_value = best_value
        log_rows.append(
            {
                "step": step,
                "action": action,
                "n_predictors": len(current),
                "value": current_value,
            }
        )

    return tuple(current), pd.DataFrame(log_rows)


def _severity_family(name: str) -> sm.families.Family:
    # log link explicitly: statsmodels' Gamma/InverseGaussian defaults are inverse
    # power links, but multiplicative claim-size relativities need exp(beta)
    builders = {
        "gamma": sm.families.Gamma,
        "inverse_gaussian": sm.families.InverseGaussian,
    }
    return builders[name](link=sm.families.links.Log())


def fit_severity_glm(
    df: pd.DataFrame,
    formula: str,
    family: str = "gamma",
) -> Any:
    """Fit a per-claim severity GLM (log link, no offset) on positive amounts (V2)."""
    if family not in SEVERITY_FAMILIES:
        raise ValueError(
            f"Unknown severity family '{family}' — valid: {', '.join(SEVERITY_FAMILIES)}"
        )
    model = smf.glm(formula, data=df, family=_severity_family(family))
    return model.fit()
