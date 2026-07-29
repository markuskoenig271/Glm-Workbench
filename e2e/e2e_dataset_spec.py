"""Executes TC1-TC8 from .planning/e2e-tests/dataset-spec-loaders.md verbatim.

Engine-only (no app). Run from the repo root:
    uv run python e2e/e2e_dataset_spec.py
"""

import time

import numpy as np

from pricing_engine.data import (
    DATASET_REGISTRY,
    DatasetSpec,
    list_datasets,
    load_dataset,
    load_fremtpl2_freq,
    load_fremtpl2_sev,
    validate_portfolio,
)

# TC1
df = load_fremtpl2_freq()
assert df.shape == (678013, 12), df.shape
for col in (
    "IDpol",
    "ClaimNb",
    "Exposure",
    "Area",
    "VehPower",
    "VehAge",
    "DrivAge",
    "BonusMalus",
    "VehBrand",
    "VehGas",
    "Density",
    "Region",
):
    assert col in df.columns, col
print("TC1 PASS", df.shape)

# TC2
df = load_fremtpl2_sev()
assert df.shape == (26639, 2), df.shape
assert "IDpol" in df.columns, df.columns
print("TC2 PASS", df.shape)

# TC3
names = [s.name for s in list_datasets()]
assert "fremtpl2_freq" in names, names
spec = DATASET_REGISTRY["fremtpl2_freq"]
assert isinstance(spec, DatasetSpec)
assert spec.target == "ClaimNb" and spec.offset == "Exposure"
assert set(spec.predictors) == {
    "Area",
    "VehPower",
    "VehAge",
    "DrivAge",
    "BonusMalus",
    "VehBrand",
    "VehGas",
    "Density",
    "Region",
}
assert set(spec.required_columns) == {spec.target, spec.offset, *spec.predictors}
try:
    spec.target = "x"  # type: ignore[misc]
    raise SystemExit("TC3 FAIL: spec not frozen")
except AttributeError:
    pass
print("TC3 PASS", spec.name, "|", spec.label)

# TC4
df, spec = load_dataset("fremtpl2_freq")
direct = load_fremtpl2_freq()
assert df.shape == direct.shape == (678013, 12)
missing = [c for c in spec.required_columns if c not in df.columns]
assert not missing, missing
print("TC4 PASS")

# TC5
t0 = time.perf_counter()
df, spec = load_dataset("fremtpl2_freq")
findings = validate_portfolio(df, spec)
elapsed = time.perf_counter() - t0
assert findings == [], findings
print(f"TC5 PASS (load+validate 678k rows in {elapsed:.2f}s)")

# TC6
full, spec = load_dataset("fremtpl2_freq")
df = full.head(1000).copy()
df["ClaimNb"] = df["ClaimNb"].astype("int64")
df["DrivAge"] = df["DrivAge"].astype("float64")
df = df.drop(columns=["Region"])
df.loc[df.index[0], "ClaimNb"] = -1
df.loc[df.index[1], "Exposure"] = 0.0
df.loc[df.index[2], "DrivAge"] = np.nan
findings = validate_portfolio(df, spec)
assert findings, "expected findings, got []"
text = " | ".join(findings).lower()
for token in ("region", "claimnb", "exposure", "drivage"):
    assert token in text, (token, findings)
print("TC6 PASS", len(findings), "findings:")
for f in findings:
    print("   -", f)

# TC7
try:
    load_fremtpl2_freq("data/raw/does_not_exist.parquet")
    raise SystemExit("TC7 FAIL: no exception raised")
except FileNotFoundError as e:
    msg = str(e)
    assert "curl" in msg, msg
    assert "data.openml.org" in msg, msg
    print("TC7 PASS:", msg.splitlines()[0], "...")

# TC8
try:
    load_dataset("no_such_dataset")
    raise SystemExit("TC8 FAIL: no exception raised")
except KeyError as e:
    msg = str(e)
    assert "no_such_dataset" in msg, msg
    assert "fremtpl2_freq" in msg, msg
    print("TC8 PASS:", msg)

print("ALL 8 TCs PASSED")
