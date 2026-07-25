# E2E — Dataset spec, registry, freMTPL2 loaders, portfolio validation

Change under test: engine-level dataset foundation in `pricing_engine/data.py`
(no UI wiring yet — Data Import screen is a later slice):
`DatasetSpec` frozen dataclass, `DATASET_REGISTRY` (single entry
`"fremtpl2_freq"`), `list_datasets()` / `load_dataset(name)`,
`load_fremtpl2_freq` / `load_fremtpl2_sev` (Parquet via pyarrow, real files in
`data/raw/`), and `validate_portfolio(df, spec) -> list[str]`.

BA scenarios (the "user" is the next-slice developer and, indirectly, the
actuary the future Data Import screen serves):

- As the developer of the Data Import slice, I can ask the registry which
  datasets exist and get a spec (target / offset / predictors /
  required_columns) so pages never hardcode freMTPL2 column names
  (architecture decision 6).
- As a learner, `load_dataset("fremtpl2_freq")` hands me the real 678k-policy
  portfolio ready for the Chapter-27 frequency workflow — correct shape, the
  target `ClaimNb`, the offset `Exposure`, and all nine predictors present.
- As a future V2 user, the severity table (26,639 claim amounts keyed by
  `IDpol`) loads the same way today, so nothing blocks the severity slice.
- When something is wrong, errors teach instead of confuse: a missing Parquet
  file tells me the exact curl command to fetch it (mirroring README
  "Datasets"); an unknown dataset name tells me which names ARE registered.
- The validation report is trustworthy in both directions: the pristine
  built-in dataset validates clean (empty list), and a broken portfolio
  (missing column, negative target, bad offset) yields human-readable findings
  — this is exactly what the Data Import screen will render.

Test Agent notes from the BA interview: no UI exists, so per CLAUDE.md the
cases run as Python invocations (`uv run python -c "..."`) against the REAL
downloaded Parquet files at `data/raw/freMTPL2freq.parquet` and
`data/raw/freMTPL2sev.parquet`. Each snippet prints `PASS`/values or raises;
a traceback or missing `PASS` marker = FAIL. Run all commands from the repo
root. On Windows PowerShell, prefer writing the snippet to a temp `.py` file
and running `uv run python <file>` if `-c` quoting gets awkward — the snippet
text is the contract, not the quoting.

## TC1 — Real freq file loads with expected shape and columns

1. Run:

   ```python
   from pricing_engine.data import load_fremtpl2_freq
   df = load_fremtpl2_freq()
   assert df.shape == (678013, 12), df.shape
   for col in ("IDpol", "ClaimNb", "Exposure", "Area", "VehPower", "VehAge",
               "DrivAge", "BonusMalus", "VehBrand", "VehGas", "Density", "Region"):
       assert col in df.columns, col
   print("PASS", df.shape)
   ```

2. Expected: prints `PASS (678013, 12)`; no exception. Default path resolves
   to `data/raw/freMTPL2freq.parquet` without any argument.

## TC2 — Real sev file loads (V2 groundwork)

1. Run:

   ```python
   from pricing_engine.data import load_fremtpl2_sev
   df = load_fremtpl2_sev()
   assert df.shape == (26639, 2), df.shape
   assert "IDpol" in df.columns, df.columns
   print("PASS", df.shape)
   ```

2. Expected: prints `PASS (26639, 2)`; `IDpol` (the join key to freq) is one
   of the two columns.

## TC3 — Registry exposes exactly the fremtpl2_freq spec

1. Run:

   ```python
   from pricing_engine.data import DATASET_REGISTRY, DatasetSpec, list_datasets
   names = list_datasets()
   assert "fremtpl2_freq" in names, names
   spec = DATASET_REGISTRY["fremtpl2_freq"]
   assert isinstance(spec, DatasetSpec)
   assert spec.target == "ClaimNb" and spec.offset == "Exposure"
   assert set(spec.predictors) == {"Area", "VehPower", "VehAge", "DrivAge",
                                   "BonusMalus", "VehBrand", "VehGas",
                                   "Density", "Region"}
   assert set(spec.required_columns) == {spec.target, spec.offset, *spec.predictors}
   print("PASS", spec.name, spec.label)
   ```

2. Expected: prints `PASS fremtpl2_freq <label>`. `required_columns` covers
   target + offset + all 9 predictors (11 columns; `IDpol` is an identifier,
   not required by the spec). The spec is frozen: as an optional extra check,
   assigning `spec.target = "x"` raises `dataclasses.FrozenInstanceError`.

## TC4 — load_dataset round-trip matches the direct loader

1. Run:

   ```python
   from pricing_engine.data import load_dataset, load_fremtpl2_freq
   df, spec = load_dataset("fremtpl2_freq")   # returns (data, spec)
   direct = load_fremtpl2_freq()
   assert df.shape == direct.shape == (678013, 12)
   missing = [c for c in spec.required_columns if c not in df.columns]
   assert not missing, missing
   print("PASS")
   ```

2. Expected: prints `PASS` — the registry route and the direct loader return
   the same real data, and every spec-required column exists in it, so pages
   can rely on spec + `load_dataset` alone.

## TC5 — Real freq data validates clean against its spec

1. Run:

   ```python
   from pricing_engine.data import load_dataset, validate_portfolio
   df, spec = load_dataset("fremtpl2_freq")
   findings = validate_portfolio(df, spec)
   assert findings == [], findings
   print("PASS")
   ```

2. Expected: prints `PASS` — the pristine built-in dataset produces an empty
   findings list (empty = valid). If this fails, print the findings: either
   the validator is over-strict or the data assumptions are wrong; both are
   ship-blockers for the Data Import slice.

## TC6 — validate_portfolio reports problems in plain language

1. Run (deliberately broken portfolio):

   ```python
   import numpy as np
   from pricing_engine.data import load_dataset, validate_portfolio
   full, spec = load_dataset("fremtpl2_freq")
   df = full.head(1000).copy()
   # The real data uses uint8 for counts/ages (cannot hold -1/NaN) — cast to
   # the plain dtypes a CSV upload would have before injecting bad values.
   df["ClaimNb"] = df["ClaimNb"].astype("int64")
   df["DrivAge"] = df["DrivAge"].astype("float64")
   df = df.drop(columns=["Region"])          # missing required column
   df.loc[df.index[0], "ClaimNb"] = -1       # negative target
   df.loc[df.index[1], "Exposure"] = 0.0     # non-positive offset
   df.loc[df.index[2], "DrivAge"] = np.nan   # NaN in a required column
   findings = validate_portfolio(df, spec)
   assert findings, "expected findings, got []"
   text = " | ".join(findings).lower()
   for token in ("region", "claimnb", "exposure", "drivage"):
       assert token in text, (token, findings)
   print("PASS", len(findings), "findings")
   ```

2. Expected: prints `PASS <n> findings` with n >= 4-ish; each finding is a
   human-readable string naming the offending column (missing `Region`,
   negative `ClaimNb`, non-positive `Exposure`, NaN count in `DrivAge`) —
   suitable for direct rendering in the future validation report.

## TC7 — Missing Parquet file gives the curl-command error

1. Run:

   ```python
   from pricing_engine.data import load_fremtpl2_freq
   try:
       load_fremtpl2_freq("data/raw/does_not_exist.parquet")
       raise SystemExit("FAIL: no exception raised")
   except FileNotFoundError as e:
       msg = str(e)
       assert "curl" in msg, msg
       assert "data.openml.org" in msg, msg
       print("PASS:", msg)
   ```

2. Expected: prints `PASS: ...` — a `FileNotFoundError` (not a raw pyarrow
   error) whose message contains the curl download command from README
   "Datasets" (`curl -sL -o data/raw/freMTPL2freq.parquet https://data.openml.org/datasets/0004/41214/dataset_41214.pq`),
   so a fresh clone knows exactly how to fetch the data.

## TC8 — Unknown registry name gives a helpful KeyError

1. Run:

   ```python
   from pricing_engine.data import load_dataset
   try:
       load_dataset("no_such_dataset")
       raise SystemExit("FAIL: no exception raised")
   except KeyError as e:
       msg = str(e)
       assert "no_such_dataset" in msg, msg
       assert "fremtpl2_freq" in msg, msg
       print("PASS:", msg)
   ```

2. Expected: prints `PASS: ...` — a `KeyError` naming the bad input AND
   listing the available dataset name(s), so the caller (or a future upload
   flow) can self-correct without reading source code.

## Execution notes

- TC1/TC2/TC4/TC5 require the real files in `data/raw/` (7.5 MB / 277 KB,
  downloaded 2026-07-25). If absent, fetch them with the README curl commands
  first — do NOT stub them; these cases exist to exercise real data.
- TC5 on 678k rows should still complete in seconds; if it is slow, note the
  timing in Results (scale note in `docs/architecture.md` applies to the
  engine too).
- Run each snippet via `uv run python -c "<snippet>"` or from a temp file with
  `uv run python <file>`; inside the Claude Code sandbox use
  `.venv/bin/python` / `.venv\Scripts\python.exe` if `uv run` is blocked
  (see CLAUDE.md).

## Results

- 2026-07-25 — **ALL 8 TCs PASSED** (executed via `uv run python <script>` from
  repo root against the real Parquet files):
  - TC1 PASS (678013, 12); TC2 PASS (26639, 2); TC3 PASS (spec frozen,
    11 required columns); TC4 PASS (registry route ≡ direct loader).
  - TC5 PASS — load + validate of all 678k rows in **0.04 s** (scale is a
    non-issue at the engine level).
  - TC6 PASS — 4 findings, each naming its column ("Missing required column
    'Region'", "Target 'ClaimNb' has 1 negative value(s)", "Offset 'Exposure'
    has 1 non-positive value(s) — exposure must be positive", "Column 'DrivAge'
    has 1 missing value(s)").
  - TC7 PASS (FileNotFoundError with the curl + data.openml.org command);
    TC8 PASS (KeyError names 'no_such_dataset' and lists 'fremtpl2_freq').
- Adjustments made during execution (doc updated in place): TC4–TC6 snippets
  aligned to the actual API — `load_dataset` returns `(df, spec)`; TC6 casts
  `ClaimNb`/`DrivAge` from the real data's uint8 to int64/float64 before
  injecting bad values (uint8 physically cannot hold −1/NaN; the cast mirrors
  what a CSV upload would contain anyway).
