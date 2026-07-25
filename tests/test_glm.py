"""pricing_engine.glm — formula building and frequency GLM fitting."""

import numpy as np
import pandas as pd
import pytest

from pricing_engine import glm
from pricing_engine.data import FREMTPL2_FREQ_SPEC, DatasetSpec


@pytest.fixture
def poisson_portfolio() -> pd.DataFrame:
    """A small portfolio with a real Poisson signal: group B runs ~3x group A."""
    rng = np.random.default_rng(27)
    n = 2_000
    group = rng.choice(["A", "B"], size=n)
    exposure = rng.uniform(0.1, 1.0, size=n)
    rate = np.where(group == "A", 0.1, 0.3)
    claims = rng.poisson(rate * exposure)
    return pd.DataFrame({"ClaimNb": claims, "Exposure": exposure, "Group": group})


GROUP_SPEC = DatasetSpec(
    name="test", label="Test", target="ClaimNb", offset="Exposure", predictors=("Group",)
)


class TestBuildFormula:
    def test_from_spec(self) -> None:
        formula = glm.build_formula(FREMTPL2_FREQ_SPEC)
        assert formula.startswith("ClaimNb ~ ")
        assert "Area" in formula and "Region" in formula
        # offset is passed separately, never a formula term
        assert "Exposure" not in formula

    def test_no_predictors_raises(self) -> None:
        empty = DatasetSpec(name="x", label="X", target="y", offset=None, predictors=())
        with pytest.raises(ValueError, match="predictor"):
            glm.build_formula(empty)


class TestFitFrequencyGlm:
    def test_poisson_recovers_group_effect(self, poisson_portfolio: pd.DataFrame) -> None:
        model = glm.fit_frequency_glm(
            poisson_portfolio, "ClaimNb ~ Group", offset_column="Exposure"
        )
        assert model.converged
        # exp(intercept) ~ group A base rate; exp(group B coef) ~ 3x relativity
        params = model.params
        assert np.exp(params["Intercept"]) == pytest.approx(0.1, rel=0.35)
        assert np.exp(params["Group[T.B]"]) == pytest.approx(3.0, rel=0.35)

    def test_offset_matters(self, poisson_portfolio: pd.DataFrame) -> None:
        with_offset = glm.fit_frequency_glm(
            poisson_portfolio, "ClaimNb ~ Group", offset_column="Exposure"
        )
        without = glm.fit_frequency_glm(poisson_portfolio, "ClaimNb ~ Group", offset_column=None)
        assert with_offset.params["Intercept"] != pytest.approx(without.params["Intercept"])

    def test_negative_binomial_family(self, poisson_portfolio: pd.DataFrame) -> None:
        model = glm.fit_frequency_glm(
            poisson_portfolio,
            "ClaimNb ~ Group",
            family="negative_binomial",
            offset_column="Exposure",
        )
        assert model.converged

    def test_unknown_family_raises(self, poisson_portfolio: pd.DataFrame) -> None:
        with pytest.raises(ValueError, match="poisson"):
            glm.fit_frequency_glm(poisson_portfolio, "ClaimNb ~ Group", family="gaussian")
