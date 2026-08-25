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
