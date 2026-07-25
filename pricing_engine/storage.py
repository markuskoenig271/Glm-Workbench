"""SQLite storage: model run history (decision 7 in .planning/PROJECT.md).

Stores workbench state and model runs — never portfolio data (that stays in
Parquet/CSV). Default database: data/workbench.db, overridable via GLM_DB_PATH.
"""

import json
import os
import sqlite3
from pathlib import Path

import pandas as pd

DEFAULT_DB_PATH = Path("data/workbench.db")

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
    coefficients_json TEXT NOT NULL
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
    """Create the tables if they do not exist."""
    conn.execute(_SCHEMA)
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
