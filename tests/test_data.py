"""Dataset spec, registry, freMTPL2 loaders, and portfolio validation.

TDD for the "dataset spec + loaders" slice (docs/architecture.md "Datasets").
Unit tests run on small fixture frames / tmp parquet files; the E2E cases in
.planning/e2e-tests/dataset-spec-loaders.md cover the real downloaded data.
"""

from pathlib import Path

import pandas as pd
import pytest

from pricing_engine import data


class TestDatasetSpec:
    def test_fremtpl2_freq_spec(self) -> None:
        spec = data.FREMTPL2_FREQ_SPEC
        assert spec.name == "fremtpl2_freq"
        assert spec.target == "ClaimNb"
        assert spec.offset == "Exposure"
        assert spec.predictors == tuple(data.FREMTPL2_PREDICTOR_COLUMNS)
        assert "freMTPL2" in spec.label

    def test_required_columns(self) -> None:
        spec = data.FREMTPL2_FREQ_SPEC
        assert spec.required_columns == ("ClaimNb", "Exposure", *data.FREMTPL2_PREDICTOR_COLUMNS)

    def test_required_columns_without_offset(self) -> None:
        spec = data.DatasetSpec(name="x", label="X", target="y", offset=None, predictors=("a", "b"))
        assert spec.required_columns == ("y", "a", "b")

    def test_spec_is_immutable(self) -> None:
        with pytest.raises(AttributeError):
            data.FREMTPL2_FREQ_SPEC.target = "other"  # type: ignore[misc]


class TestRegistry:
    def test_registry_contains_fremtpl2_freq_only(self) -> None:
        assert list(data.DATASET_REGISTRY) == ["fremtpl2_freq"]

    def test_list_datasets(self) -> None:
        specs = data.list_datasets()
        assert [s.name for s in specs] == ["fremtpl2_freq"]

    def test_load_dataset_unknown_name(self) -> None:
        with pytest.raises(KeyError, match="fremtpl2_freq"):
            data.load_dataset("nope")

    def test_load_dataset_dispatches_to_loader(
        self, fremtpl2_sample: pd.DataFrame, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        pq = tmp_path / "freq.parquet"
        fremtpl2_sample.to_parquet(pq)
        monkeypatch.setattr(data, "FREMTPL2_FREQ_PATH", pq)
        df, spec = data.load_dataset("fremtpl2_freq")
        assert spec is data.FREMTPL2_FREQ_SPEC
        assert len(df) == len(fremtpl2_sample)


class TestFremtpl2Loaders:
    def test_load_freq_from_parquet(self, fremtpl2_sample: pd.DataFrame, tmp_path: Path) -> None:
        pq = tmp_path / "freq.parquet"
        fremtpl2_sample.to_parquet(pq)
        df = data.load_fremtpl2_freq(pq)
        assert list(df.columns) == list(fremtpl2_sample.columns)
        assert df["IDpol"].dtype == "int64"
        assert (df["ClaimNb"] == [1, 0, 2, 0]).all()

    def test_load_sev_from_parquet(self, tmp_path: Path) -> None:
        sev = pd.DataFrame({"IDpol": [1552.0, 1010996.0], "ClaimAmount": [995.20, 1128.12]})
        pq = tmp_path / "sev.parquet"
        sev.to_parquet(pq)
        df = data.load_fremtpl2_sev(pq)
        assert df["IDpol"].dtype == "int64"
        assert (df["ClaimAmount"] == [995.20, 1128.12]).all()

    def test_missing_file_error_is_friendly(self, tmp_path: Path) -> None:
        missing = tmp_path / "nope.parquet"
        with pytest.raises(FileNotFoundError, match="curl"):
            data.load_fremtpl2_freq(missing)
        with pytest.raises(FileNotFoundError, match="curl"):
            data.load_fremtpl2_sev(missing)


class TestValidatePortfolio:
    def test_valid_frame_has_no_findings(self, fremtpl2_sample: pd.DataFrame) -> None:
        assert data.validate_portfolio(fremtpl2_sample, data.FREMTPL2_FREQ_SPEC) == []

    def test_missing_columns_reported(self, fremtpl2_sample: pd.DataFrame) -> None:
        df = fremtpl2_sample.drop(columns=["ClaimNb", "Region"])
        findings = data.validate_portfolio(df, data.FREMTPL2_FREQ_SPEC)
        assert any("ClaimNb" in f for f in findings)
        assert any("Region" in f for f in findings)

    def test_negative_target_reported(self, fremtpl2_sample: pd.DataFrame) -> None:
        df = fremtpl2_sample.assign(ClaimNb=[1, -1, 2, 0])
        findings = data.validate_portfolio(df, data.FREMTPL2_FREQ_SPEC)
        assert any("negative" in f.lower() for f in findings)

    def test_non_numeric_target_reported(self, fremtpl2_sample: pd.DataFrame) -> None:
        df = fremtpl2_sample.assign(ClaimNb=["a", "b", "c", "d"])
        findings = data.validate_portfolio(df, data.FREMTPL2_FREQ_SPEC)
        assert any("numeric" in f.lower() for f in findings)

    def test_non_positive_offset_reported(self, fremtpl2_sample: pd.DataFrame) -> None:
        df = fremtpl2_sample.assign(Exposure=[0.5, 0.0, -0.1, 1.0])
        findings = data.validate_portfolio(df, data.FREMTPL2_FREQ_SPEC)
        assert any("Exposure" in f and "positive" in f.lower() for f in findings)

    def test_nan_counts_reported(self, fremtpl2_sample: pd.DataFrame) -> None:
        df = fremtpl2_sample.copy()
        df.loc[0, "DrivAge"] = None
        df.loc[[1, 2], "Region"] = None
        findings = data.validate_portfolio(df, data.FREMTPL2_FREQ_SPEC)
        assert any("DrivAge" in f and "1" in f for f in findings)
        assert any("Region" in f and "2" in f for f in findings)

    def test_offset_none_spec_skips_offset_checks(self, fremtpl2_sample: pd.DataFrame) -> None:
        spec = data.DatasetSpec(
            name="t", label="T", target="ClaimNb", offset=None, predictors=("DrivAge",)
        )
        df = fremtpl2_sample.drop(columns=["Exposure"])
        assert data.validate_portfolio(df, spec) == []
