"""Data layer: dataset specs, built-in dataset registry, loaders, validation.

Every dataset is described by a DatasetSpec (target, offset, predictors) so pages
and the engine never hardcode column names — see docs/architecture.md "Datasets".
The primary V1 dataset is freMTPL2 (real French motor TPL, CC0); the synthetic
Chapter 27 dataset (docs/car-insurance.md) is backlogged.
"""

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import IO

import pandas as pd

# --- Chapter 27 synthetic dataset (backlogged generator) --------------------

TARGET_COLUMN = "Claims"
OFFSET_COLUMN = "Exposure"
PREDICTOR_COLUMNS = [
    "Age",  # continuous
    "LocationType",  # urban / rural
    "Region",  # 5 categories
    "VehicleAge",  # continuous
    "FuelType",  # electric / diesel / petrol
    "NoClaimYears",  # ordinal
    "Dummy1",  # binary, no real effect
    "Dummy2",  # categorical, no real effect
]

# Minimum a portfolio must provide for V1 frequency modelling.
REQUIRED_COLUMNS = [TARGET_COLUMN, OFFSET_COLUMN]

DEFAULT_N_POLICIES = 20_000

# --- freMTPL2: real French motor TPL data (CC0, OpenML 41214/41215) ---------
# Parquet files in data/raw/ — see docs/architecture.md "Datasets". Native
# column names are kept; the DatasetSpec absorbs the difference.

FREMTPL2_FREQ_PATH = Path("data/raw/freMTPL2freq.parquet")
FREMTPL2_SEV_PATH = Path("data/raw/freMTPL2sev.parquet")
FREMTPL2_FREQ_URL = "https://data.openml.org/datasets/0004/41214/dataset_41214.pq"
FREMTPL2_SEV_URL = "https://data.openml.org/datasets/0004/41215/dataset_41215.pq"
FREMTPL2_TARGET_COLUMN = "ClaimNb"
FREMTPL2_OFFSET_COLUMN = "Exposure"
FREMTPL2_SEV_TARGET_COLUMN = "ClaimAmount"
FREMTPL2_PREDICTOR_COLUMNS = [
    "Area",  # density band A–F
    "VehPower",
    "VehAge",
    "DrivAge",
    "BonusMalus",
    "VehBrand",
    "VehGas",  # Diesel / Regular
    "Density",
    "Region",
]

# --- Dataset spec + registry ------------------------------------------------


@dataclass(frozen=True)
class DatasetSpec:
    """Generic description of a modelling dataset: what to predict, with what.

    `kind` ("frequency" or "severity") drives which model screen fits the
    dataset, UI wording, and validation strictness — see docs/architecture.md
    "Spec kind (V2)".
    """

    name: str
    label: str
    target: str
    offset: str | None
    predictors: tuple[str, ...]
    kind: str = "frequency"

    @property
    def required_columns(self) -> tuple[str, ...]:
        cols = [self.target]
        if self.offset is not None:
            cols.append(self.offset)
        cols.extend(self.predictors)
        return tuple(cols)


FREMTPL2_FREQ_SPEC = DatasetSpec(
    name="fremtpl2_freq",
    label="freMTPL2 — French motor TPL, frequency (678k policies)",
    target=FREMTPL2_TARGET_COLUMN,
    offset=FREMTPL2_OFFSET_COLUMN,
    predictors=tuple(FREMTPL2_PREDICTOR_COLUMNS),
)

FREMTPL2_SEV_SPEC = DatasetSpec(
    name="fremtpl2_sev",
    label="freMTPL2 — French motor TPL, severity (26.4k claims)",
    target=FREMTPL2_SEV_TARGET_COLUMN,
    offset=None,
    predictors=tuple(FREMTPL2_PREDICTOR_COLUMNS),
    kind="severity",
)

DATASET_REGISTRY: dict[str, DatasetSpec] = {
    FREMTPL2_FREQ_SPEC.name: FREMTPL2_FREQ_SPEC,
    FREMTPL2_SEV_SPEC.name: FREMTPL2_SEV_SPEC,
}


def list_datasets() -> list[DatasetSpec]:
    """Specs of all built-in datasets, in registry order."""
    return list(DATASET_REGISTRY.values())


def load_dataset(name: str) -> tuple[pd.DataFrame, DatasetSpec]:
    """Load a built-in dataset by registry name; returns (data, spec)."""
    if name not in DATASET_REGISTRY:
        available = ", ".join(DATASET_REGISTRY)
        raise KeyError(f"Unknown dataset {name!r} — available: {available}")
    return _LOADERS[name](), DATASET_REGISTRY[name]


# --- Loaders ----------------------------------------------------------------


def _read_openml_parquet(path: str | Path, what: str, url: str) -> pd.DataFrame:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(
            f"{what} not found at '{path}'. Download it once with:\n"
            f"  curl -sL -o {path.as_posix()} {url}\n"
            f"(see README 'Datasets')."
        )
    df = pd.read_parquet(path)
    df["IDpol"] = df["IDpol"].astype("int64")
    return df


def load_fremtpl2_freq(path: str | Path | None = None) -> pd.DataFrame:
    """Load the freMTPL2 frequency table (678k policies)."""
    return _read_openml_parquet(
        path if path is not None else FREMTPL2_FREQ_PATH,
        "freMTPL2 frequency data",
        FREMTPL2_FREQ_URL,
    )


def load_fremtpl2_sev(path: str | Path | None = None) -> pd.DataFrame:
    """Load the freMTPL2 severity table (26.6k claim amounts; V2)."""
    return _read_openml_parquet(
        path if path is not None else FREMTPL2_SEV_PATH,
        "freMTPL2 severity data",
        FREMTPL2_SEV_URL,
    )


def load_fremtpl2_sev_joined(
    freq_path: str | Path | None = None, sev_path: str | Path | None = None
) -> pd.DataFrame:
    """The V2 severity modelling table: one row per claim with its rating factors.

    Inner-joins each severity row (IDpol, ClaimAmount) with the frequency
    table's predictors on IDpol; orphan claims (no matching policy — a known
    freMTPL2 quirk, ~0.7%) are dropped. ClaimNb/Exposure are not carried over:
    severity is modelled per claim, without an offset.
    """
    sev = load_fremtpl2_sev(sev_path)
    freq = load_fremtpl2_freq(freq_path)
    factors = freq[["IDpol", *FREMTPL2_PREDICTOR_COLUMNS]]
    return sev.merge(factors, on="IDpol", how="inner")


_LOADERS: dict[str, Callable[[], pd.DataFrame]] = {
    "fremtpl2_freq": load_fremtpl2_freq,
    "fremtpl2_sev": load_fremtpl2_sev_joined,
}

# --- Validation -------------------------------------------------------------


def validate_portfolio(df: pd.DataFrame, spec: DatasetSpec) -> list[str]:
    """Validate a portfolio against a dataset spec.

    Returns human-readable findings; an empty list means the portfolio is usable
    for frequency modelling.
    """
    findings: list[str] = []

    present = [c for c in spec.required_columns if c in df.columns]
    findings.extend(
        f"Missing required column '{c}'" for c in spec.required_columns if c not in df.columns
    )

    if spec.target in df.columns:
        target = df[spec.target]
        target_meaning = "claim amounts" if spec.kind == "severity" else "claim counts"
        if not pd.api.types.is_numeric_dtype(target):
            findings.append(f"Target '{spec.target}' must be numeric ({target_meaning})")
        elif spec.kind == "severity":
            # Gamma/Inverse Gaussian require strictly positive amounts
            non_positive = int((target <= 0).sum())
            if non_positive:
                findings.append(
                    f"Target '{spec.target}' has {non_positive} non-positive value(s) — "
                    "claim amounts must be positive"
                )
        else:
            negative = int((target < 0).sum())
            if negative:
                findings.append(f"Target '{spec.target}' has {negative} negative value(s)")

    if spec.offset is not None and spec.offset in df.columns:
        offset = df[spec.offset]
        if not pd.api.types.is_numeric_dtype(offset):
            findings.append(f"Offset '{spec.offset}' must be numeric (exposure)")
        else:
            non_positive = int((offset <= 0).sum())
            if non_positive:
                findings.append(
                    f"Offset '{spec.offset}' has {non_positive} non-positive value(s) — "
                    "exposure must be positive"
                )

    for column in present:
        missing = int(df[column].isna().sum())
        if missing:
            findings.append(f"Column '{column}' has {missing} missing value(s)")

    return findings


# --- Stubs for later slices -------------------------------------------------


def generate_chapter27_portfolio(
    n_policies: int = DEFAULT_N_POLICIES, seed: int = 27
) -> tuple[pd.DataFrame, dict[str, float]]:
    """Generate the synthetic Chapter 27 portfolio (BACKLOGGED — see TODO.md).

    Returns the portfolio and the hidden data-generating coefficients, kept for
    the educational estimated-vs-true comparison on the Diagnostics screen.
    """
    raise NotImplementedError


def load_portfolio(source: str | Path | IO[bytes]) -> pd.DataFrame:
    """Load a portfolio CSV from a path or a file-like object (e.g. an upload)."""
    if isinstance(source, str | Path):
        path = Path(source)
        if not path.exists():
            raise FileNotFoundError(f"Portfolio CSV not found at '{path}'.")
        return pd.read_csv(path)
    return pd.read_csv(source)
