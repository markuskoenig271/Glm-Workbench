"""pricing_engine.storage — SQLite model run history (decision 7) + model persistence (V3)."""

import json
import sqlite3
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pytest

from pricing_engine import diagnostics, storage
from tests.conftest import GROUP_SPEC

_OLD_SCHEMA = """
CREATE TABLE model_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    dataset TEXT NOT NULL,
    target TEXT NOT NULL,
    "offset" TEXT,
    formula TEXT NOT NULL,
    family TEXT NOT NULL,
    n_obs INTEGER NOT NULL,
    aic REAL NOT NULL,
    bic REAL NOT NULL,
    deviance REAL NOT NULL,
    log_likelihood REAL NOT NULL,
    coefficients_json TEXT NOT NULL
)
"""


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


def _record_run(conn: sqlite3.Connection, *, family: str = "poisson", **overrides: Any) -> int:
    storage.ensure_schema(conn)
    params: dict[str, Any] = dict(
        dataset="fremtpl2_freq",
        target="ClaimNb",
        offset="Exposure",
        formula="ClaimNb ~ Group + Noise",
        family=family,
        n_obs=2_000,
        aic=1.0,
        bic=2.0,
        deviance=3.0,
        log_likelihood=-0.5,
        coefficients={"Intercept": -2.3, "Group[T.B]": 1.1, "Noise": 0.0},
    )
    params.update(overrides)
    return storage.record_model_run(conn, **params)


class TestSchemaMigration:
    def test_old_db_gains_model_path_and_keeps_rows(self, tmp_path: Path) -> None:
        db = tmp_path / "old.db"
        with sqlite3.connect(db) as conn:
            conn.execute(_OLD_SCHEMA)
            conn.execute(
                """
                INSERT INTO model_runs
                    (dataset, target, "offset", formula, family, n_obs,
                     aic, bic, deviance, log_likelihood, coefficients_json)
                VALUES ('d', 't', NULL, 'f', 'poisson', 1, 0, 0, 0, 0, '{}')
                """
            )
            conn.commit()
        conn = storage.connect(db)
        runs = storage.list_model_runs(conn)
        assert "model_path" in runs.columns
        assert len(runs) == 1
        assert runs.iloc[0]["model_path"] is None or pd.isna(runs.iloc[0]["model_path"])
        conn.close()

    def test_fresh_db_has_model_path(self, tmp_db: sqlite3.Connection) -> None:
        storage.ensure_schema(tmp_db)
        cols = {row[1] for row in tmp_db.execute("PRAGMA table_info(model_runs)")}
        assert "model_path" in cols


class TestSaveLoadModel:
    @pytest.fixture(autouse=True)
    def _models_dir(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("GLM_MODELS_DIR", str(tmp_path / "models"))

    def test_save_writes_pickle_and_records_path(  # type: ignore[no-untyped-def]
        self, tmp_db: sqlite3.Connection, fitted_model
    ) -> None:
        run_id = _record_run(tmp_db)
        path = storage.save_model(tmp_db, run_id, fitted_model)
        assert path.exists()
        assert "frequency" in path.name and "poisson" in path.name
        row = storage.list_model_runs(tmp_db).iloc[0]
        assert row["model_path"] == str(path)

    def test_roundtrip_predicts_and_reports_like_the_original(  # type: ignore[no-untyped-def]
        self, tmp_db: sqlite3.Connection, fitted_model, group_portfolio: pd.DataFrame
    ) -> None:
        from pricing_engine.prediction import predict_frequency

        run_id = _record_run(tmp_db, aic=float(fitted_model.aic))
        storage.save_model(tmp_db, run_id, fitted_model)
        loaded, meta = storage.load_model(tmp_db, run_id)
        # the data-stripped pickle still predicts and reports coefficients
        assert np.allclose(loaded.params.to_numpy(), fitted_model.params.to_numpy())
        original = predict_frequency(fitted_model, group_portfolio, GROUP_SPEC)
        reloaded = predict_frequency(loaded, group_portfolio, GROUP_SPEC)
        assert np.allclose(
            reloaded["expected_frequency"].to_numpy(), original["expected_frequency"].to_numpy()
        )
        table = diagnostics.coefficient_table(loaded)
        assert {"term", "coef", "p_value", "ci_low", "ci_high"} <= set(table.columns)
        # meta reconstructed from the run row
        assert meta["source"] == "loaded"
        assert meta["kind"] == "frequency"
        assert meta["family"] == "poisson"
        assert meta["formula"] == "ClaimNb ~ Group + Noise"
        assert meta["aic"] == pytest.approx(float(fitted_model.aic))
        assert meta["n_params"] == 3
        assert meta["n_obs"] == 2_000

    def test_save_does_not_mutate_the_live_model(  # type: ignore[no-untyped-def]
        self, tmp_db: sqlite3.Connection, fitted_model
    ) -> None:
        # save(remove_data=True) strips in place unless storage copies first —
        # the session model must keep its residuals for Diagnostics after a fit+save
        run_id = _record_run(tmp_db)
        storage.save_model(tmp_db, run_id, fitted_model)
        assert len(np.asarray(fitted_model.fittedvalues)) == 2_000
        assert len(np.asarray(fitted_model.resid_deviance)) == 2_000
        assert float(fitted_model.aic) > 0

    def test_loaded_model_is_data_stripped(  # type: ignore[no-untyped-def]
        self, tmp_db: sqlite3.Connection, fitted_model
    ) -> None:
        run_id = _record_run(tmp_db)
        storage.save_model(tmp_db, run_id, fitted_model)
        loaded, _ = storage.load_model(tmp_db, run_id)
        # remove_data=True: the nobs-length arrays are gone — the documented
        # limitation behind the Diagnostics residual-section hint
        stripped = getattr(loaded, "fittedvalues", None)
        assert stripped is None or len(np.atleast_1d(stripped)) == 0

    def test_severity_model_kind(  # type: ignore[no-untyped-def]
        self, tmp_db: sqlite3.Connection, fitted_severity_model
    ) -> None:
        run_id = _record_run(
            tmp_db,
            dataset="fremtpl2_sev",
            target="ClaimAmount",
            offset=None,
            formula="ClaimAmount ~ Group + Noise",
            family="gamma",
        )
        path = storage.save_model(tmp_db, run_id, fitted_severity_model)
        assert "severity" in path.name and "gamma" in path.name
        _, meta = storage.load_model(tmp_db, run_id)
        assert meta["kind"] == "severity"

    def test_load_without_saved_file_raises(self, tmp_db: sqlite3.Connection) -> None:
        run_id = _record_run(tmp_db)  # no save_model call — model_path stays NULL
        with pytest.raises(ValueError, match="no saved model"):
            storage.load_model(tmp_db, run_id)

    def test_load_missing_pickle_raises(  # type: ignore[no-untyped-def]
        self, tmp_db: sqlite3.Connection, fitted_model
    ) -> None:
        run_id = _record_run(tmp_db)
        path = storage.save_model(tmp_db, run_id, fitted_model)
        path.unlink()
        with pytest.raises(FileNotFoundError):
            storage.load_model(tmp_db, run_id)

    def test_load_unknown_run_raises(self, tmp_db: sqlite3.Connection) -> None:
        storage.ensure_schema(tmp_db)
        with pytest.raises(ValueError, match="No model run"):
            storage.load_model(tmp_db, 999)
