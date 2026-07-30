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

    def test_kind_defaults_to_frequency(self) -> None:
        spec = data.DatasetSpec(name="x", label="X", target="y", offset=None, predictors=("a",))
        assert spec.kind == "frequency"
        assert data.FREMTPL2_FREQ_SPEC.kind == "frequency"

    def test_fremtpl2_sev_spec(self) -> None:
        spec = data.FREMTPL2_SEV_SPEC
        assert spec.name == "fremtpl2_sev"
        assert spec.target == "ClaimAmount"
        assert spec.offset is None
        assert spec.kind == "severity"
        assert spec.predictors == tuple(data.FREMTPL2_PREDICTOR_COLUMNS)
        assert "severity" in spec.label.lower()


class TestRegistry:
    def test_registry_contains_both_fremtpl2_datasets(self) -> None:
        assert list(data.DATASET_REGISTRY) == ["fremtpl2_freq", "fremtpl2_sev"]

    def test_list_datasets(self) -> None:
        specs = data.list_datasets()
        assert [s.name for s in specs] == ["fremtpl2_freq", "fremtpl2_sev"]

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


class TestSeverityJoinLoader:
    @pytest.fixture(autouse=True)
    def _patch_paths(
        self,
        fremtpl2_sample: pd.DataFrame,
        fremtpl2_sev_sample: pd.DataFrame,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        freq_pq = tmp_path / "freq.parquet"
        sev_pq = tmp_path / "sev.parquet"
        fremtpl2_sample.to_parquet(freq_pq)
        fremtpl2_sev_sample.to_parquet(sev_pq)
        monkeypatch.setattr(data, "FREMTPL2_FREQ_PATH", freq_pq)
        monkeypatch.setattr(data, "FREMTPL2_SEV_PATH", sev_pq)

    def test_one_row_per_claim_with_rating_factors(self) -> None:
        df = data.load_fremtpl2_sev_joined()
        # policy 1 claimed twice -> two rows; orphan 99 dropped
        assert len(df) == 3
        assert (df["IDpol"] == [1, 1, 5]).all()
        for col in ("ClaimAmount", *data.FREMTPL2_PREDICTOR_COLUMNS):
            assert col in df.columns, col

    def test_frequency_columns_are_not_carried_over(self) -> None:
        df = data.load_fremtpl2_sev_joined()
        assert "ClaimNb" not in df.columns
        assert "Exposure" not in df.columns

    def test_rating_factors_come_from_the_matching_policy(self) -> None:
        df = data.load_fremtpl2_sev_joined()
        assert (df.loc[df["IDpol"] == 1, "Area"] == "D").all()
        assert (df.loc[df["IDpol"] == 5, "Area"] == "B").all()

    def test_load_dataset_dispatches_to_sev_loader(self) -> None:
        df, spec = data.load_dataset("fremtpl2_sev")
        assert spec is data.FREMTPL2_SEV_SPEC
        assert len(df) == 3
        assert data.validate_portfolio(df, spec) == []


class TestLoadPortfolio:
    def test_load_from_csv_path(self, fremtpl2_sample: pd.DataFrame, tmp_path: Path) -> None:
        csv = tmp_path / "portfolio.csv"
        fremtpl2_sample.to_csv(csv, index=False)
        df = data.load_portfolio(csv)
        assert list(df.columns) == list(fremtpl2_sample.columns)
        assert len(df) == len(fremtpl2_sample)

    def test_load_from_buffer(self, fremtpl2_sample: pd.DataFrame) -> None:
        import io

        buffer = io.BytesIO(fremtpl2_sample.to_csv(index=False).encode())
        df = data.load_portfolio(buffer)
        assert list(df.columns) == list(fremtpl2_sample.columns)
        assert len(df) == len(fremtpl2_sample)

    def test_missing_path_error_is_friendly(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError, match="Portfolio CSV"):
            data.load_portfolio(tmp_path / "nope.csv")


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

    def test_severity_target_must_be_strictly_positive(self) -> None:
        spec = data.DatasetSpec(
            name="s",
            label="S",
            target="ClaimAmount",
            offset=None,
            predictors=("DrivAge",),
            kind="severity",
        )
        df = pd.DataFrame({"ClaimAmount": [100.0, 0.0, -5.0], "DrivAge": [30, 40, 50]})
        findings = data.validate_portfolio(df, spec)
        assert any("ClaimAmount" in f and "positive" in f.lower() and "2" in f for f in findings)

    def test_severity_valid_frame_has_no_findings(self) -> None:
        spec = data.DatasetSpec(
            name="s",
            label="S",
            target="ClaimAmount",
            offset=None,
            predictors=("DrivAge",),
            kind="severity",
        )
        df = pd.DataFrame({"ClaimAmount": [100.0, 1204.0], "DrivAge": [30, 40]})
        assert data.validate_portfolio(df, spec) == []

    def test_frequency_zero_target_is_not_flagged(self, fremtpl2_sample: pd.DataFrame) -> None:
        # zero claim counts are normal for frequency data — only severity requires positive
        assert data.validate_portfolio(fremtpl2_sample, data.FREMTPL2_FREQ_SPEC) == []
