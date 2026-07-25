"""pricing_engine.preprocessing — binning, log transforms, encoding, capping."""

import numpy as np
import pandas as pd
import pytest

from pricing_engine import preprocessing


class TestBinNumeric:
    def test_adds_band_column(self, fremtpl2_sample: pd.DataFrame) -> None:
        df, new_column = preprocessing.bin_numeric(fremtpl2_sample, "DrivAge", bins=2)
        assert new_column == "DrivAge_band"
        assert new_column in df.columns
        assert "DrivAge_band" not in fremtpl2_sample.columns  # original untouched
        assert df[new_column].nunique() <= 2
        assert all(isinstance(v, str) for v in df[new_column])

    def test_uniform_strategy(self, fremtpl2_sample: pd.DataFrame) -> None:
        df, new_column = preprocessing.bin_numeric(
            fremtpl2_sample, "DrivAge", bins=2, strategy="uniform"
        )
        assert df[new_column].nunique() <= 2

    def test_unknown_column_raises(self, fremtpl2_sample: pd.DataFrame) -> None:
        with pytest.raises(ValueError, match="nope"):
            preprocessing.bin_numeric(fremtpl2_sample, "nope")

    def test_non_numeric_column_raises(self, fremtpl2_sample: pd.DataFrame) -> None:
        with pytest.raises(ValueError, match="numeric"):
            preprocessing.bin_numeric(fremtpl2_sample, "VehGas")

    def test_bad_strategy_raises(self, fremtpl2_sample: pd.DataFrame) -> None:
        with pytest.raises(ValueError, match="strategy"):
            preprocessing.bin_numeric(fremtpl2_sample, "DrivAge", strategy="magic")


class TestLogTransform:
    def test_adds_log_columns(self, fremtpl2_sample: pd.DataFrame) -> None:
        df = preprocessing.log_transform(fremtpl2_sample, ["Density"])
        assert "Density_log" in df.columns
        assert np.isfinite(df["Density_log"]).all()
        assert df["Density_log"].iloc[0] == pytest.approx(np.log(1217.0))
        assert "Density_log" not in fremtpl2_sample.columns

    def test_non_positive_values_raise(self, fremtpl2_sample: pd.DataFrame) -> None:
        with pytest.raises(ValueError, match="ClaimNb"):
            preprocessing.log_transform(fremtpl2_sample, ["ClaimNb"])  # contains zeros

    def test_unknown_column_raises(self, fremtpl2_sample: pd.DataFrame) -> None:
        with pytest.raises(ValueError, match="nope"):
            preprocessing.log_transform(fremtpl2_sample, ["nope"])


class TestEncodeCategorical:
    def test_dummies_with_baseline_dropped(self, fremtpl2_sample: pd.DataFrame) -> None:
        df = preprocessing.encode_categorical(fremtpl2_sample, ["VehGas"])
        # 3 levels in the fixture (Diesel/Petrol/Regular) -> 2 dummies
        dummies = [c for c in df.columns if c.startswith("VehGas_")]
        assert len(dummies) == 2
        assert "VehGas" in df.columns  # original kept

    def test_unknown_column_raises(self, fremtpl2_sample: pd.DataFrame) -> None:
        with pytest.raises(ValueError, match="nope"):
            preprocessing.encode_categorical(fremtpl2_sample, ["nope"])


class TestCapColumn:
    def test_caps_and_counts(self, fremtpl2_sample: pd.DataFrame) -> None:
        df = fremtpl2_sample.assign(Exposure=[0.5, 1.4, 2.0, 1.0])
        capped, n_capped = preprocessing.cap_column(df, "Exposure", 1.0)
        assert n_capped == 2
        assert capped["Exposure"].max() == 1.0
        assert df["Exposure"].max() == 2.0  # original untouched

    def test_nothing_to_cap(self, fremtpl2_sample: pd.DataFrame) -> None:
        capped, n_capped = preprocessing.cap_column(fremtpl2_sample, "Exposure", 1.0)
        assert n_capped == 0
        assert (capped["Exposure"] == fremtpl2_sample["Exposure"]).all()

    def test_unknown_column_raises(self, fremtpl2_sample: pd.DataFrame) -> None:
        with pytest.raises(ValueError, match="nope"):
            preprocessing.cap_column(fremtpl2_sample, "nope", 1.0)
