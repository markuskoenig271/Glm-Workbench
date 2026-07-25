"""pricing_engine.storage — SQLite model run history (decision 7)."""

import json
import sqlite3
from pathlib import Path
from typing import Any

import pytest

from pricing_engine import storage


class TestConnect:
    def test_creates_schema(self, tmp_path: Path) -> None:
        conn = storage.connect(tmp_path / "wb.db")
        tables = {
            row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        assert "model_runs" in tables
        conn.close()

    def test_env_override(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        override = tmp_path / "custom.db"
        monkeypatch.setenv("GLM_DB_PATH", str(override))
        conn = storage.connect()
        conn.close()
        assert override.exists()


class TestModelRuns:
    def test_record_and_list_roundtrip(self, tmp_db: sqlite3.Connection) -> None:
        storage.ensure_schema(tmp_db)
        run_id = storage.record_model_run(
            tmp_db,
            dataset="fremtpl2_freq",
            target="ClaimNb",
            offset="Exposure",
            formula="ClaimNb ~ Area",
            family="poisson",
            n_obs=678_013,
            aic=1.5,
            bic=2.5,
            deviance=3.5,
            log_likelihood=-0.75,
            coefficients={"Intercept": -2.3, "Area[T.B]": 0.1},
        )
        assert run_id == 1
        runs = storage.list_model_runs(tmp_db)
        assert len(runs) == 1
        row = runs.iloc[0]
        assert row["formula"] == "ClaimNb ~ Area"
        assert row["family"] == "poisson"
        assert row["n_obs"] == 678_013
        assert row["aic"] == 1.5
        assert json.loads(row["coefficients_json"])["Intercept"] == -2.3

    def test_list_newest_first(self, tmp_db: sqlite3.Connection) -> None:
        storage.ensure_schema(tmp_db)
        common: dict[str, Any] = dict(
            dataset="d",
            target="t",
            offset=None,
            family="poisson",
            n_obs=1,
            aic=0.0,
            bic=0.0,
            deviance=0.0,
            log_likelihood=0.0,
            coefficients={},
        )
        storage.record_model_run(tmp_db, formula="first", **common)
        storage.record_model_run(tmp_db, formula="second", **common)
        runs = storage.list_model_runs(tmp_db)
        assert list(runs["formula"]) == ["second", "first"]

    def test_empty_history(self, tmp_db: sqlite3.Connection) -> None:
        storage.ensure_schema(tmp_db)
        assert storage.list_model_runs(tmp_db).empty
