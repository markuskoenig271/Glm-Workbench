"""pricing_engine.exploration — aggregated portfolio exploration.

All functions return small aggregated frames (never raw rows) so the UI stays
fast on the 678k-row freMTPL2 portfolio (docs/architecture.md scale note).
"""

import pandas as pd
import pytest

from pricing_engine import exploration
from pricing_engine.data import FREMTPL2_FREQ_SPEC, DatasetSpec

NO_OFFSET_SPEC = DatasetSpec(
    name="t", label="T", target="ClaimNb", offset=None, predictors=("DrivAge",)
)


class TestPortfolioFrequency:
    def test_claims_per_policy_year(self, fremtpl2_sample: pd.DataFrame) -> None:
        # 3 claims over 2.62 policy-years
        freq = exploration.portfolio_frequency(fremtpl2_sample, FREMTPL2_FREQ_SPEC)
        assert freq == pytest.approx(3 / 2.62)

    def test_without_offset_falls_back_to_per_policy(self, fremtpl2_sample: pd.DataFrame) -> None:
        freq = exploration.portfolio_frequency(fremtpl2_sample, NO_OFFSET_SPEC)
        assert freq == pytest.approx(3 / 4)


class TestSummarizePortfolio:
    def test_one_row_per_required_column(self, fremtpl2_sample: pd.DataFrame) -> None:
        summary = exploration.summarize_portfolio(fremtpl2_sample, FREMTPL2_FREQ_SPEC)
        assert list(summary["column"]) == list(FREMTPL2_FREQ_SPEC.required_columns)

    def test_roles_and_kinds(self, fremtpl2_sample: pd.DataFrame) -> None:
        summary = exploration.summarize_portfolio(fremtpl2_sample, FREMTPL2_FREQ_SPEC)
        by_col = summary.set_index("column")
        assert by_col.loc["ClaimNb", "role"] == "target"
        assert by_col.loc["Exposure", "role"] == "offset"
        assert by_col.loc["Area", "role"] == "predictor"
        assert by_col.loc["DrivAge", "kind"] == "numeric"
        assert by_col.loc["VehGas", "kind"] == "categorical"

    def test_numeric_stats_and_missing(self, fremtpl2_sample: pd.DataFrame) -> None:
        df = fremtpl2_sample.copy()
        df["DrivAge"] = df["DrivAge"].astype("float64")
        df.loc[0, "DrivAge"] = None
        summary = exploration.summarize_portfolio(df, FREMTPL2_FREQ_SPEC)
        row = summary.set_index("column").loc["DrivAge"]
        assert row["missing"] == 1
        assert row["min"] == 30.0
        assert row["max"] == 55.0
        # categorical columns carry no numeric stats
        assert pd.isna(summary.set_index("column").loc["VehGas", "min"])


class TestOneWayFrequency:
    def test_categorical_predictor(self, fremtpl2_sample: pd.DataFrame) -> None:
        ow = exploration.one_way_frequency(fremtpl2_sample, FREMTPL2_FREQ_SPEC, "Area")
        assert list(ow.columns) == ["Area", "policies", "claims", "exposure", "frequency"]
        by_level = ow.set_index("Area")
        # Area D: rows 0+1 -> 1 claim over 0.87 policy-years
        assert by_level.loc["D", "policies"] == 2
        assert by_level.loc["D", "frequency"] == pytest.approx(1 / 0.87)

    def test_numeric_predictor_is_binned(self, fremtpl2_sample: pd.DataFrame) -> None:
        ow = exploration.one_way_frequency(
            fremtpl2_sample, FREMTPL2_FREQ_SPEC, "DrivAge", max_levels=2
        )
        assert len(ow) <= 2
        assert ow["policies"].sum() == 4
        # readable band labels, not Interval objects
        assert all(isinstance(level, str) for level in ow["DrivAge"])

    def test_numeric_predictor_with_few_levels_stays_discrete(
        self, fremtpl2_sample: pd.DataFrame
    ) -> None:
        ow = exploration.one_way_frequency(fremtpl2_sample, FREMTPL2_FREQ_SPEC, "VehPower")
        assert len(ow) == 3  # 5, 6, 7 as-is

    def test_without_offset_uses_policy_counts(self, fremtpl2_sample: pd.DataFrame) -> None:
        ow = exploration.one_way_frequency(fremtpl2_sample, NO_OFFSET_SPEC, "DrivAge")
        assert "exposure" not in ow.columns
        assert ow["frequency"].sum() > 0

    def test_unknown_predictor_raises(self, fremtpl2_sample: pd.DataFrame) -> None:
        with pytest.raises(ValueError, match="Area"):
            exploration.one_way_frequency(fremtpl2_sample, FREMTPL2_FREQ_SPEC, "nope")


class TestHistogram:
    def test_categorical_counts(self, fremtpl2_sample: pd.DataFrame) -> None:
        hist = exploration.histogram(fremtpl2_sample, "VehGas")
        assert list(hist.columns) == ["VehGas", "count"]
        assert dict(zip(hist["VehGas"], hist["count"], strict=True)) == {
            "Diesel": 1,
            "Petrol": 1,
            "Regular": 2,
        }

    def test_numeric_binned(self, fremtpl2_sample: pd.DataFrame) -> None:
        hist = exploration.histogram(fremtpl2_sample, "DrivAge", bins=2)
        assert len(hist) == 2
        assert hist["count"].sum() == 4

    def test_unknown_column_raises(self, fremtpl2_sample: pd.DataFrame) -> None:
        with pytest.raises(ValueError, match="nope"):
            exploration.histogram(fremtpl2_sample, "nope")


class TestCorrelationMatrix:
    def test_numeric_required_columns_only(self, fremtpl2_sample: pd.DataFrame) -> None:
        corr = exploration.correlation_matrix(fremtpl2_sample, FREMTPL2_FREQ_SPEC)
        expected = ["ClaimNb", "Exposure", "VehPower", "VehAge", "DrivAge", "BonusMalus", "Density"]
        assert list(corr.columns) == expected
        assert list(corr.index) == expected
        assert all(corr.loc[c, c] == pytest.approx(1.0) for c in expected)


SEV_SPEC = DatasetSpec(
    name="s",
    label="S",
    target="ClaimAmount",
    offset=None,
    predictors=("Area",),
    kind="severity",
)


class TestSeverityAverages:
    def test_one_way_is_average_claim_amount_without_offset(self) -> None:
        df = pd.DataFrame({"ClaimAmount": [100.0, 300.0, 500.0], "Area": ["A", "A", "B"]})
        ow = exploration.one_way_frequency(df, SEV_SPEC, "Area")
        # with no offset the "frequency" column divides by row count: per-claim average
        assert list(ow[ow["Area"] == "A"]["frequency"]) == [200.0]
        assert list(ow[ow["Area"] == "B"]["frequency"]) == [500.0]
