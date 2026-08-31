"""SQLite storage: model run history (decision 7 in .planning/PROJECT.md).

Stores workbench state and model runs — never portfolio data (that stays in
Parquet/CSV). Default database: data/workbench.db, overridable via GLM_DB_PATH.
Fitted models (V3 slice 2) are pickled to models/ (overridable via
GLM_MODELS_DIR) with `remove_data=True`: small files that predict and report
coefficients/criteria, but carry no residual/fitted-value arrays.
"""

import copy
import json
import os
import sqlite3
from pathlib import Path
from typing import Any

import pandas as pd
from statsmodels.iolib.smpickle import load_pickle

from pricing_engine.glm import family_kind

DEFAULT_DB_PATH = Path("data/workbench.db")
DEFAULT_MODELS_DIR = Path("models")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS model_runs (
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
    coefficients_json TEXT NOT NULL,
    model_path TEXT
)
"""


def connect(path: str | Path | None = None) -> sqlite3.Connection:
    """Open (creating if needed) the workbench database and ensure the schema."""
    if path is None:
        path = Path(os.environ.get("GLM_DB_PATH", DEFAULT_DB_PATH))
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    ensure_schema(conn)
    return conn


def ensure_schema(conn: sqlite3.Connection) -> None:
    """Create the tables if they do not exist; migrate older databases in place."""
    conn.execute(_SCHEMA)
    # V3 slice 2 migration: pre-existing databases lack model_path (rows keep NULL)
    columns = {row[1] for row in conn.execute("PRAGMA table_info(model_runs)")}
    if "model_path" not in columns:
        conn.execute("ALTER TABLE model_runs ADD COLUMN model_path TEXT")
    conn.commit()


def record_model_run(
    conn: sqlite3.Connection,
    *,
    dataset: str,
    target: str,
    offset: str | None,
    formula: str,
    family: str,
    n_obs: int,
    aic: float,
    bic: float,
    deviance: float,
    log_likelihood: float,
    coefficients: dict[str, float],
) -> int:
    """Insert a model run; returns its id."""
    cursor = conn.execute(
        """
        INSERT INTO model_runs
            (dataset, target, "offset", formula, family, n_obs,
             aic, bic, deviance, log_likelihood, coefficients_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            dataset,
            target,
            offset,
            formula,
            family,
            n_obs,
            aic,
            bic,
            deviance,
            log_likelihood,
            json.dumps(coefficients),
        ),
    )
    conn.commit()
    return int(cursor.lastrowid or 0)


def list_model_runs(conn: sqlite3.Connection) -> pd.DataFrame:
    """All recorded model runs, newest first."""
    return pd.read_sql_query("SELECT * FROM model_runs ORDER BY id DESC", conn)


def models_dir() -> Path:
    """Directory for pickled models (created if needed), overridable via GLM_MODELS_DIR."""
    directory = Path(os.environ.get("GLM_MODELS_DIR", DEFAULT_MODELS_DIR))
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def save_model(conn: sqlite3.Connection, run_id: int, model: Any) -> Path:
    """Pickle a fitted model (data-stripped) and record its path on the run row."""
    row = conn.execute("SELECT family FROM model_runs WHERE id = ?", (run_id,)).fetchone()
    if row is None:
        raise ValueError(f"No model run with id {run_id}")
    family = row[0]
    path = models_dir() / f"run{run_id:04d}_{family_kind(family)}_{family}.pickle"
    # save(remove_data=True) strips the data arrays IN PLACE — copy first so the
    # live session model keeps its residuals/fitted values for Diagnostics
    copy.deepcopy(model).save(str(path), remove_data=True)
    conn.execute("UPDATE model_runs SET model_path = ? WHERE id = ?", (str(path), run_id))
    conn.commit()
    return path


def load_model(conn: sqlite3.Connection, run_id: int) -> tuple[Any, dict[str, Any]]:
    """Load a saved model plus its meta (reconstructed from the run row).

    The meta mirrors the fit-time `model_meta` session entry, with
    `source="loaded"` marking the data-stripped pickle (no residual arrays).
    """
    run = conn.execute("SELECT * FROM model_runs WHERE id = ?", (run_id,)).fetchone()
    if run is None:
        raise ValueError(f"No model run with id {run_id}")
    columns = [d[0] for d in conn.execute("SELECT * FROM model_runs LIMIT 0").description]
    row = dict(zip(columns, run, strict=True))
    if not row["model_path"]:
        raise ValueError(
            f"Run {run_id} has no saved model file (recorded before model persistence)."
        )
    path = Path(row["model_path"])
    if not path.exists():
        raise FileNotFoundError(f"Saved model file missing: {path}")
    model = load_pickle(str(path))
    meta = {
        "formula": row["formula"],
        "family": row["family"],
        "kind": family_kind(row["family"]),
        "aic": float(row["aic"]),
        "bic": float(row["bic"]),
        "deviance": float(row["deviance"]),
        "log_likelihood": float(row["log_likelihood"]),
        "n_obs": int(row["n_obs"]),
        "n_params": len(json.loads(row["coefficients_json"])),
        "source": "loaded",
    }
    return model, meta
