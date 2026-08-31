"""pricing_engine.prediction — expected claim frequency, single policy and batch."""

import numpy as np
import pandas as pd
import pytest

from pricing_engine import prediction
from pricing_engine.data import DatasetSpec
from tests.conftest import GROUP_SPEC, SEVERITY_SPEC


class TestPredictFrequency:
    def test_batch_adds_columns(self, fitted_model, group_portfolio: pd.DataFrame) -> None:  # type: ignore[no-untyped-def]
        result = prediction.predict_frequency(fitted_model, group_portfolio, GROUP_SPEC)
        assert "expected_frequency" in result.columns
        assert "expected_claims" in result.columns
        assert "expected_frequency" not in group_portfolio.columns  # copy, not mutation
        assert (result["expected_frequency"] > 0).all()
        assert np.isfinite(result["expected_frequency"]).all()

    def test_in_sample_balance(self, fitted_model, group_portfolio: pd.DataFrame) -> None:  # type: ignore[no-untyped-def]
        """Poisson with intercept reproduces total observed claims in-sample."""
        result = prediction.predict_frequency(fitted_model, group_portfolio, GROUP_SPEC)
        assert result["expected_claims"].sum() == pytest.approx(
            group_portfolio["ClaimNb"].sum(), rel=0.005
        )

    def test_expected_claims_scale_with_exposure(  # type: ignore[no-untyped-def]
        self, fitted_model, group_portfolio: pd.DataFrame
    ) -> None:
        result = prediction.predict_frequency(fitted_model, group_portfolio, GROUP_SPEC)
        assert np.allclose(
            result["expected_claims"],
            result["expected_frequency"] * result["Exposure"],
        )

    def test_single_policy(self, fitted_model, group_portfolio: pd.DataFrame) -> None:  # type: ignore[no-untyped-def]
        one = group_portfolio.head(1).copy()
        result = prediction.predict_frequency(fitted_model, one, GROUP_SPEC)
        assert len(result) == 1
        assert float(result["expected_claims"].iloc[0]) == pytest.approx(
            float(result["expected_frequency"].iloc[0] * one["Exposure"].iloc[0])
        )

    def test_without_offset_claims_equal_frequency(  # type: ignore[no-untyped-def]
        self, fitted_model, group_portfolio: pd.DataFrame
    ) -> None:
        no_offset_spec = DatasetSpec(
            name="t", label="T", target="ClaimNb", offset=None, predictors=("Group", "Noise")
        )
        result = prediction.predict_frequency(fitted_model, group_portfolio, no_offset_spec)
        assert np.allclose(result["expected_claims"], result["expected_frequency"])

    def test_missing_predictor_raises(self, fitted_model, group_portfolio: pd.DataFrame) -> None:  # type: ignore[no-untyped-def]
        broken = group_portfolio.drop(columns=["Group"])
        with pytest.raises(ValueError, match="Group"):
            prediction.predict_frequency(fitted_model, broken, GROUP_SPEC)


class TestPredictSeverity:
    def test_batch_adds_expected_claim_amount(  # type: ignore[no-untyped-def]
        self, fitted_severity_model, severity_portfolio: pd.DataFrame
    ) -> None:
        result = prediction.predict_severity(
            fitted_severity_model, severity_portfolio, SEVERITY_SPEC
        )
        assert "expected_claim_amount" in result.columns
        assert "expected_claim_amount" not in severity_portfolio.columns  # copy, not mutation
        assert len(result) == len(severity_portfolio)
        assert (result["expected_claim_amount"] > 0).all()
        assert np.isfinite(result["expected_claim_amount"]).all()
        # no frequency-style columns leak into the severity result
        assert "expected_frequency" not in result.columns
        assert "expected_claims" not in result.columns

    def test_no_exposure_scaling(  # type: ignore[no-untyped-def]
        self, fitted_severity_model, severity_portfolio: pd.DataFrame
    ) -> None:
        """Per-claim expected amount is the model mean itself — no offset, no scaling."""
        with_exposure = severity_portfolio.assign(Exposure=0.5)
        result = prediction.predict_severity(fitted_severity_model, with_exposure, SEVERITY_SPEC)
        assert np.allclose(
            result["expected_claim_amount"], np.asarray(fitted_severity_model.fittedvalues)
        )

    def test_recovers_group_means(  # type: ignore[no-untyped-def]
        self, fitted_severity_model, severity_portfolio: pd.DataFrame
    ) -> None:
        result = prediction.predict_severity(
            fitted_severity_model, severity_portfolio, SEVERITY_SPEC
        )
        by_group = result.groupby("Group")["expected_claim_amount"].mean()
        assert by_group["A"] == pytest.approx(1_000.0, rel=0.1)
        assert by_group["B"] == pytest.approx(3_000.0, rel=0.1)

    def test_single_claim(  # type: ignore[no-untyped-def]
        self, fitted_severity_model, severity_portfolio: pd.DataFrame
    ) -> None:
        one = severity_portfolio.head(1).copy()
        result = prediction.predict_severity(fitted_severity_model, one, SEVERITY_SPEC)
        assert len(result) == 1
        assert float(result["expected_claim_amount"].iloc[0]) > 0

    def test_missing_predictor_raises(  # type: ignore[no-untyped-def]
        self, fitted_severity_model, severity_portfolio: pd.DataFrame
    ) -> None:
        broken = severity_portfolio.drop(columns=["Group"])
        with pytest.raises(ValueError, match="Group"):
            prediction.predict_severity(fitted_severity_model, broken, SEVERITY_SPEC)


class TestPredictPurePremium:
    """V3: pure premium = expected frequency x expected claim amount, per policy."""

    def test_columns_and_products(  # type: ignore[no-untyped-def]
        self, fitted_model, fitted_severity_model, group_portfolio: pd.DataFrame
    ) -> None:
        result = prediction.predict_pure_premium(
            fitted_model, fitted_severity_model, group_portfolio, GROUP_SPEC
        )
        for column in (
            "expected_frequency",
            "expected_claim_amount",
            "pure_premium",
            "expected_loss",
        ):
            assert column in result.columns
            assert column not in group_portfolio.columns  # copy, not mutation
        assert np.allclose(
            result["pure_premium"],
            result["expected_frequency"] * result["expected_claim_amount"],
        )
        assert np.allclose(result["expected_loss"], result["pure_premium"] * result["Exposure"])
        assert (result["pure_premium"] > 0).all()
        assert np.isfinite(result["pure_premium"]).all()

    def test_matches_the_individual_predictors(  # type: ignore[no-untyped-def]
        self, fitted_model, fitted_severity_model, group_portfolio: pd.DataFrame
    ) -> None:
        combined = prediction.predict_pure_premium(
            fitted_model, fitted_severity_model, group_portfolio, GROUP_SPEC
        )
        freq = prediction.predict_frequency(fitted_model, group_portfolio, GROUP_SPEC)
        sev = fitted_severity_model.predict(group_portfolio)
        assert np.allclose(combined["expected_frequency"], freq["expected_frequency"])
        assert np.allclose(combined["expected_claim_amount"], np.asarray(sev))

    def test_riskier_group_pays_more(  # type: ignore[no-untyped-def]
        self, fitted_model, fitted_severity_model, group_portfolio: pd.DataFrame
    ) -> None:
        # Group B runs ~3x frequency AND ~3x severity — premium ~9x group A
        result = prediction.predict_pure_premium(
            fitted_model, fitted_severity_model, group_portfolio, GROUP_SPEC
        )
        by_group = result.groupby("Group")["pure_premium"].mean()
        assert by_group["B"] / by_group["A"] == pytest.approx(9.0, rel=0.3)

    def test_offset_free_spec(  # type: ignore[no-untyped-def]
        self, fitted_model, fitted_severity_model, group_portfolio: pd.DataFrame
    ) -> None:
        no_offset_spec = DatasetSpec(
            name="t", label="T", target="ClaimNb", offset=None, predictors=("Group", "Noise")
        )
        result = prediction.predict_pure_premium(
            fitted_model, fitted_severity_model, group_portfolio, no_offset_spec
        )
        assert np.allclose(result["expected_loss"], result["pure_premium"])

    def test_missing_predictor_raises(  # type: ignore[no-untyped-def]
        self, fitted_model, fitted_severity_model, group_portfolio: pd.DataFrame
    ) -> None:
        broken = group_portfolio.drop(columns=["Group"])
        with pytest.raises(ValueError, match="Group"):
            prediction.predict_pure_premium(fitted_model, fitted_severity_model, broken, GROUP_SPEC)

    def test_severity_model_column_outside_the_spec_raises(  # type: ignore[no-untyped-def]
        self, fitted_model, severity_portfolio: pd.DataFrame, group_portfolio: pd.DataFrame
    ) -> None:
        # the severity model's own formula may need columns the frequency spec
        # does not carry — the friendly error must cover the union, not fall
        # into a cryptic patsy failure
        from pricing_engine import glm

        rng = np.random.default_rng(3)
        with_extra = severity_portfolio.assign(Extra=rng.uniform(size=len(severity_portfolio)))
        sev_extra = glm.fit_severity_glm(with_extra, "ClaimAmount ~ Group + Extra")
        with pytest.raises(ValueError, match="Extra"):
            prediction.predict_pure_premium(fitted_model, sev_extra, group_portfolio, GROUP_SPEC)


class TestPremiumBreakdown:
    """The quote's multiplicative decomposition: premium = base x product of factors."""

    def test_factors_multiply_to_the_premium(  # type: ignore[no-untyped-def]
        self, fitted_model, fitted_severity_model, group_portfolio: pd.DataFrame
    ) -> None:
        profile = group_portfolio.head(1)[list(GROUP_SPEC.predictors)].copy()
        base, factors = prediction.premium_breakdown(
            fitted_model, fitted_severity_model, profile, group_portfolio, GROUP_SPEC
        )
        assert list(factors["predictor"]) == list(GROUP_SPEC.predictors)
        assert np.allclose(
            factors["combined_factor"],
            factors["frequency_factor"] * factors["severity_factor"],
        )
        premium = float(
            prediction.predict_pure_premium(
                fitted_model, fitted_severity_model, group_portfolio.head(1), GROUP_SPEC
            )["pure_premium"].to_numpy()[0]
        )
        combined_product = float(np.prod(factors["combined_factor"].to_numpy()))
        assert base * combined_product == pytest.approx(premium)

    def test_baseline_profile_has_unit_factors(  # type: ignore[no-untyped-def]
        self, fitted_model, fitted_severity_model, group_portfolio: pd.DataFrame
    ) -> None:
        baseline_profile = pd.DataFrame([{"Group": "A", "Noise": "X"}])
        base, factors = prediction.premium_breakdown(
            fitted_model, fitted_severity_model, baseline_profile, group_portfolio, GROUP_SPEC
        )
        assert np.allclose(factors["frequency_factor"], 1.0)
        assert np.allclose(factors["severity_factor"], 1.0)
        assert base > 0

    def test_group_factor_matches_the_relativities(  # type: ignore[no-untyped-def]
        self, fitted_model, fitted_severity_model, group_portfolio: pd.DataFrame
    ) -> None:
        profile = pd.DataFrame([{"Group": "B", "Noise": "X"}])
        _, factors = prediction.premium_breakdown(
            fitted_model, fitted_severity_model, profile, group_portfolio, GROUP_SPEC
        )
        group_row = factors[factors["predictor"] == "Group"].iloc[0]
        expected_freq = float(np.exp(fitted_model.params["Group[T.B]"]))
        expected_sev = float(np.exp(fitted_severity_model.params["Group[T.B]"]))
        assert group_row["frequency_factor"] == pytest.approx(expected_freq)
        assert group_row["severity_factor"] == pytest.approx(expected_sev)

    def test_missing_predictor_raises(  # type: ignore[no-untyped-def]
        self, fitted_model, fitted_severity_model, group_portfolio: pd.DataFrame
    ) -> None:
        with pytest.raises(ValueError, match="Noise"):
            prediction.premium_breakdown(
                fitted_model,
                fitted_severity_model,
                pd.DataFrame([{"Group": "A"}]),
                group_portfolio,
                GROUP_SPEC,
            )

    def test_numeric_baseline_is_the_portfolio_median(self) -> None:
        # numeric predictors rebase at the portfolio median (not 0): the base
        # premium is a plausible reference policy, and the median profile's
        # factor is exactly 1.0
        from pricing_engine import glm
        from pricing_engine.data import DatasetSpec

        rng = np.random.default_rng(11)
        n = 2_000
        x = rng.uniform(50, 150, size=n)
        exposure = np.ones(n)
        claims = rng.poisson(np.exp(-3 + 0.01 * x) * exposure)
        freq_df = pd.DataFrame({"ClaimNb": claims, "Exposure": exposure, "x": x})
        spec = DatasetSpec(
            name="n", label="N", target="ClaimNb", offset="Exposure", predictors=("x",)
        )
        freq_model = glm.fit_frequency_glm(freq_df, "ClaimNb ~ x", offset_column="Exposure")

        amounts = rng.gamma(shape=2.0, scale=np.exp(6 + 0.005 * x) / 2.0)
        sev_model = glm.fit_severity_glm(
            pd.DataFrame({"ClaimAmount": amounts, "x": x}), "ClaimAmount ~ x"
        )

        median_x = float(freq_df["x"].median())
        base, factors = prediction.premium_breakdown(
            freq_model, sev_model, pd.DataFrame([{"x": median_x}]), freq_df, spec
        )
        assert factors["combined_factor"].iloc[0] == pytest.approx(1.0)

        shifted = pd.DataFrame([{"x": median_x + 10.0}])
        _, shifted_factors = prediction.premium_breakdown(
            freq_model, sev_model, shifted, freq_df, spec
        )
        beta_f = float(freq_model.params["x"])
        beta_s = float(sev_model.params["x"])
        assert shifted_factors["frequency_factor"].iloc[0] == pytest.approx(np.exp(beta_f * 10.0))
        assert shifted_factors["severity_factor"].iloc[0] == pytest.approx(np.exp(beta_s * 10.0))
        # base x factor still reproduces the premium exactly
        premium = prediction.predict_pure_premium(
            freq_model, sev_model, shifted.assign(Exposure=1.0, ClaimNb=0), spec
        )["pure_premium"].iloc[0]
        assert base * float(shifted_factors["combined_factor"].iloc[0]) == pytest.approx(
            float(premium)
        )
