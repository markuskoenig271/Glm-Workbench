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


@pytest.fixture
def gamma_claims() -> pd.DataFrame:
    """Per-claim severity data with a real Gamma signal: group B claims ~3x group A."""
    rng = np.random.default_rng(27)
    n = 2_000
    group = rng.choice(["A", "B"], size=n)
    mean = np.where(group == "A", 1_000.0, 3_000.0)
    shape = 2.0
    amounts = rng.gamma(shape, mean / shape)
    return pd.DataFrame({"ClaimAmount": amounts, "Group": group})


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


class TestStepwiseSelection:
    def test_backward_drops_noise_keeps_group(self, group_portfolio: pd.DataFrame) -> None:
        from tests.conftest import GROUP_SPEC

        selected, log = glm.stepwise_selection(group_portfolio, GROUP_SPEC)
        assert selected == ("Group",)
        assert list(log.columns) == ["step", "action", "n_predictors", "value"]
        assert log.iloc[0]["action"] == "start"
        assert "drop Noise" in list(log["action"])
        # every improving step lowers the criterion
        assert (log["value"].diff().dropna() <= 0).all()

    def test_forward_adds_group_only(self, group_portfolio: pd.DataFrame) -> None:
        from tests.conftest import GROUP_SPEC

        selected, log = glm.stepwise_selection(group_portfolio, GROUP_SPEC, direction="forward")
        assert selected == ("Group",)
        assert "add Group" in list(log["action"])

    def test_bic_criterion(self, group_portfolio: pd.DataFrame) -> None:
        from tests.conftest import GROUP_SPEC

        selected, _ = glm.stepwise_selection(group_portfolio, GROUP_SPEC, criterion="bic")
        assert "Group" in selected

    def test_on_fit_callback_called(self, group_portfolio: pd.DataFrame) -> None:
        from tests.conftest import GROUP_SPEC

        messages: list[str] = []
        glm.stepwise_selection(group_portfolio, GROUP_SPEC, on_fit=messages.append)
        # at least: 1 start fit + first-round candidates (2)
        assert len(messages) >= 3

    def test_bad_direction_raises(self, group_portfolio: pd.DataFrame) -> None:
        from tests.conftest import GROUP_SPEC

        with pytest.raises(ValueError, match="backward"):
            glm.stepwise_selection(group_portfolio, GROUP_SPEC, direction="sideways")

    def test_bad_criterion_raises(self, group_portfolio: pd.DataFrame) -> None:
        from tests.conftest import GROUP_SPEC

        with pytest.raises(ValueError, match="aic"):
            glm.stepwise_selection(group_portfolio, GROUP_SPEC, criterion="r2")


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


class TestFitSeverityGlm:
    def test_gamma_recovers_group_effect(self, gamma_claims: pd.DataFrame) -> None:
        model = glm.fit_severity_glm(gamma_claims, "ClaimAmount ~ Group")
        assert model.converged
        # log link: exp(intercept) ~ group A mean amount; exp(group B coef) ~ 3x relativity
        params = model.params
        assert np.exp(params["Intercept"]) == pytest.approx(1_000.0, rel=0.15)
        assert np.exp(params["Group[T.B]"]) == pytest.approx(3.0, rel=0.15)

    def test_log_link_not_statsmodels_default(self, gamma_claims: pd.DataFrame) -> None:
        # statsmodels' Gamma default link is inverse power — the fit must use log
        model = glm.fit_severity_glm(gamma_claims, "ClaimAmount ~ Group")
        import statsmodels.api as sm

        assert isinstance(model.model.family, sm.families.Gamma)
        assert isinstance(model.model.family.link, sm.families.links.Log)

    def test_inverse_gaussian_family(self, gamma_claims: pd.DataFrame) -> None:
        model = glm.fit_severity_glm(gamma_claims, "ClaimAmount ~ Group", family="inverse_gaussian")
        assert model.converged
        import statsmodels.api as sm

        assert isinstance(model.model.family, sm.families.InverseGaussian)
        assert isinstance(model.model.family.link, sm.families.links.Log)

    def test_unknown_family_raises(self, gamma_claims: pd.DataFrame) -> None:
        with pytest.raises(ValueError, match="gamma"):
            glm.fit_severity_glm(gamma_claims, "ClaimAmount ~ Group", family="poisson")

    def test_fitted_means_match_observed_by_group(self, gamma_claims: pd.DataFrame) -> None:
        # Gamma + log link with a saturated one-factor model reproduces group means
        model = glm.fit_severity_glm(gamma_claims, "ClaimAmount ~ Group")
        fitted = model.fittedvalues
        for level in ["A", "B"]:
            mask = gamma_claims["Group"] == level
            assert fitted[mask].mean() == pytest.approx(
                gamma_claims.loc[mask, "ClaimAmount"].mean(), rel=1e-6
            )
