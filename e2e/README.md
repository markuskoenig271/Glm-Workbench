# E2E runners

Executable form of the E2E test plans in `.planning/e2e-tests/*.md` (each script's
docstring names its plan). They run the real app against the real freMTPL2 data —
**manually, not via pytest** (`testpaths = ["tests"]` excludes this directory).

## Prerequisites

- `uv sync` done and the freMTPL2 parquet files present in `data/raw/`
  (download commands in the top-level README)
- Playwright Chromium for the UI scripts: `uv run playwright install chromium`
- Port 8598 free (the harness launches a headless Streamlit instance there)
- Windows (teardown uses `taskkill /T` to kill the Streamlit process tree)

## Running

From the **repo root**, one script at a time:

```bash
uv run python e2e/e2e_dataset_spec.py    # engine only, seconds
uv run python e2e/e2e_data_import.py     # + UI, ~1 min
uv run python e2e/e2e_exploration.py     # + UI, ~1 min
uv run python e2e/e2e_feature_eng.py     # + UI, ~1 min
uv run python e2e/e2e_freq_model.py      # + UI, ~2 min (three full GLM fits)
uv run python e2e/e2e_diag_pred.py       # + UI, ~2 min (two full GLM fits)
uv run python e2e/e2e_stepwise.py        # + UI, ~1 min (reduced 3-predictor spec)
uv run python e2e/e2e_stepwise_tc3b.py   # engine only, ~1 min
uv run python e2e/e2e_severity_dataset.py # + UI, ~1 min (V2 slice 1)
uv run python e2e/e2e_severity_model.py  # + UI, ~2 min (three Gamma fits, one IG attempt)
uv run python e2e/e2e_severity_diag_pred.py # + UI, ~3 min (two Poisson + two Gamma fits, V2 slice 3)
uv run python e2e/e2e_model_slots.py     # + UI, ~4 min (per-kind model slots, V3 slice 1)
uv run python e2e/e2e_model_persistence.py # + UI, ~5 min (save/load fitted models, V3 slice 2)
uv run python e2e/e2e_pure_premium.py    # + UI, ~8 min (quote calculator, V3 slice 3)
```

Each script prints `... PASS` per test case and exits non-zero on the first failure.

## Notes (hard-won Playwright/Streamlit lessons — keep honoring these)

- One tab + **sidebar navigation** after loading data: `page.goto()`/refresh starts
  a new Streamlit session and drops `st.session_state`.
- `expect(...).to_be_visible()` before any `.count()` assertion on progressively
  rendered pages — counts don't auto-wait.
- UI TCs use defaults-only widget interaction, plus ONE sanctioned BaseWeb
  selectbox route proven in the severity runners: click the combobox, type a
  distinctive fragment (e.g. `severity`), press Enter. Anything beyond that is
  deferred/manual (see the "deferred" notes in each plan).
- Numeric truths are asserted at the engine level, not scraped from the UI.
- `e2e_freq_model.py` appends two real runs, `e2e_severity_model.py` one real
  run, `e2e_severity_diag_pred.py` three real runs (two Poisson, one Gamma),
  `e2e_model_slots.py` three real runs (two Poisson, one Gamma) and
  `e2e_model_persistence.py` three real runs to the history in
  `data/workbench.db` (that behavior is under test). Since V3 slice 2 every
  UI fit ALSO writes a small pickle to `models/` (gitignored — leave them,
  they are the Load feature's data). **Never delete `data/workbench.db`.**
- Streamlit mounts metric/chart widgets asynchronously after their text
  deltas: `expect` the `stMetric`/`stVegaLiteChart` LOCATOR itself before any
  `.count()` on it — a nearby text expect is not enough (and beware text that
  also appears in selectbox option labels, e.g. "AIC"). Metric LABELS mount
  after the metric element — assert them via
  `expect(stMetric.filter(has_text=...))`, never a bare filtered count. For
  widget-count assertions, `expect` the LAST expected widget (`nth(n-1)`) or
  an element rendered below the whole group first.
- `e2e_model_persistence.py` and `e2e_pure_premium.py` append 3 real runs +
  3 gitignored pickles each.
