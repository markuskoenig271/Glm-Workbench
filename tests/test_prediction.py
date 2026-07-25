"""pricing_engine.prediction — expected claim frequency, single policy and batch."""

import numpy as np
import pandas as pd
import pytest

from pricing_engine import prediction
from pricing_engine.data import DatasetSpec
from tests.conftest import GROUP_SPEC


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
