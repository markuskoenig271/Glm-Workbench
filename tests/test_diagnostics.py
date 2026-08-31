"""pricing_engine.diagnostics — coefficient table, criteria, residuals, calibration.

Uses the shared group_portfolio / fitted_model fixtures from conftest.
"""

import numpy as np
import pandas as pd
import pytest

from pricing_engine import diagnostics
from tests.conftest import GROUP_SPEC, SEVERITY_SPEC


class TestCoefficientTable:
    def test_columns_and_relativities(self, fitted_model) -> None:  # type: ignore[no-untyped-def]
        table = diagnostics.coefficient_table(fitted_model)
        assert list(table.columns) == [
            "term",
            "coef",
            "std_err",
            "p_value",
            "ci_low",
            "ci_high",
            "exp_coef",
            "significant",
        ]
        assert len(table) == 3  # Intercept, Group[T.B], Noise[T.Y]
        assert np.allclose(table["exp_coef"], np.exp(table["coef"]))

    def test_significance_flag(self, fitted_model) -> None:  # type: ignore[no-untyped-def]
        table = diagnostics.coefficient_table(fitted_model).set_index("term")
        assert (table["significant"] == (table["p_value"] < 0.05)).all()
        assert bool(table.loc["Group[T.B]", "significant"])
        assert not bool(table.loc["Noise[T.Y]", "significant"])


class TestInformationCriteria:
    def test_keys_and_finiteness(self, fitted_model) -> None:  # type: ignore[no-untyped-def]
        info = diagnostics.information_criteria(fitted_model)
        assert set(info) == {"aic", "bic", "deviance", "log_likelihood", "n_params", "n_obs"}
        assert all(np.isfinite(v) for v in info.values())
        assert info["n_obs"] == 2_000
        assert info["n_params"] == 3


class TestResiduals:
    def test_deviance_and_pearson(self, fitted_model) -> None:  # type: ignore[no-untyped-def]
        for kind in diagnostics.RESIDUAL_KINDS:
            res = diagnostics.residuals(fitted_model, kind)
            assert isinstance(res, pd.Series)
            assert len(res) == 2_000
            assert np.isfinite(res).all()

    def test_unknown_kind_raises(self, fitted_model) -> None:  # type: ignore[no-untyped-def]
        with pytest.raises(ValueError, match="deviance"):
            diagnostics.residuals(fitted_model, "studentized")


class TestResidualHistogram:
    def test_binned_counts(self, fitted_model) -> None:  # type: ignore[no-untyped-def]
        hist = diagnostics.residual_histogram(fitted_model, bins=20)
        assert list(hist.columns) == ["residual", "count"]
        assert len(hist) <= 20
        assert hist["count"].sum() == 2_000
        assert pd.api.types.is_float_dtype(hist["residual"])  # bin midpoints


class TestQqData:
    def test_shape_and_ordering(self, fitted_model) -> None:  # type: ignore[no-untyped-def]
        qq = diagnostics.qq_data(fitted_model, points=50)
        assert list(qq.columns) == ["theoretical", "sample"]
        assert len(qq) == 50
        assert (np.diff(qq["theoretical"]) > 0).all()
        assert (np.diff(qq["sample"]) >= 0).all()


class TestObservedVsPredicted:
    def test_calibration_bands(self, fitted_model, group_portfolio: pd.DataFrame) -> None:  # type: ignore[no-untyped-def]
        ovp = diagnostics.observed_vs_predicted(group_portfolio, GROUP_SPEC, fitted_model, groups=5)
        assert list(ovp.columns) == [
            "group",
            "exposure",
            "observed_mean",
            "predicted_mean",
        ]
        assert len(ovp) <= 5
        assert ovp["exposure"].sum() == pytest.approx(group_portfolio["Exposure"].sum(), rel=0.01)
        # in-sample Poisson with intercept: exposure-weighted predicted == observed overall
        total_pred = (ovp["predicted_mean"] * ovp["exposure"]).sum()
        total_obs = (ovp["observed_mean"] * ovp["exposure"]).sum()
        assert total_pred == pytest.approx(total_obs, rel=0.01)
        # bands are ordered by predicted frequency
        assert (np.diff(ovp["predicted_mean"]) >= 0).all()


class TestSeverityDiagnostics:
    """The diagnostics engine is offset-None-safe: a severity model needs no special path."""

    def test_calibration_is_average_claim_amount(  # type: ignore[no-untyped-def]
        self, fitted_severity_model, severity_portfolio: pd.DataFrame
    ) -> None:
        ovp = diagnostics.observed_vs_predicted(
            severity_portfolio, SEVERITY_SPEC, fitted_severity_model, groups=4
        )
        # offset None -> exposure is the row count -> the mean columns are
        # per-claim averages, i.e. observed vs predicted average claim amount
        assert ovp["exposure"].sum() == 2_000
        weighted_pred = (ovp["predicted_mean"] * ovp["exposure"]).sum() / 2_000
        assert weighted_pred == pytest.approx(
            float(np.asarray(fitted_severity_model.fittedvalues).mean())
        )
        assert (np.diff(ovp["predicted_mean"]) >= 0).all()
        assert ovp["observed_mean"].iloc[-1] > ovp["observed_mean"].iloc[0]

    def test_residuals_and_criteria(self, fitted_severity_model) -> None:  # type: ignore[no-untyped-def]
        for kind in diagnostics.RESIDUAL_KINDS:
            res = diagnostics.residuals(fitted_severity_model, kind)
            assert len(res) == 2_000
            assert np.isfinite(res).all()
        info = diagnostics.information_criteria(fitted_severity_model)
        assert info["n_obs"] == 2_000
        assert info["n_params"] == 3
        table = diagnostics.coefficient_table(fitted_severity_model).set_index("term")
        assert bool(table.loc["Group[T.B]", "significant"])
        assert table.loc["Group[T.B]", "exp_coef"] == pytest.approx(3.0, rel=0.15)
