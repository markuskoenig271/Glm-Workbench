# GLM Workbench

A local workbench to test out and learn Generalized Linear Models for actuarial
pricing, through a guided Streamlit UI. **Version 1 follows the Chapter 27
car-insurance frequency workflow** from *Pricing in General Insurance* (Parodi)
on the **real freMTPL2 dataset** (678k French motor TPL policies): explore the
portfolio, fit a Poisson GLM with exposure offset, inspect diagnostics, and
predict expected claim frequencies. Severity, pure premium, and a generic
workbench follow as V2–V4 (see `docs/car-insurance.md`).

## Quick start

```bash
uv sync
uv run streamlit run app.py
```

## Development

```bash
uv run pytest                      # tests (75%+ coverage gate)
uv run ruff check pricing_engine/ tests/
uv run mypy pricing_engine/
```

## Datasets

The workbench runs on the real **freMTPL2** French motor TPL data (CC0, from
OpenML / CASdatasets); the synthetic Chapter 27 dataset is backlogged. `data/`
is gitignored — fetch the Parquet files once:

```bash
curl -sL -o data/raw/freMTPL2freq.parquet https://data.openml.org/datasets/0004/41214/dataset_41214.pq
curl -sL -o data/raw/freMTPL2sev.parquet  https://data.openml.org/datasets/0004/41215/dataset_41215.pq
```

## Docs

- Spec: `.planning/PROJECT.md`
- Architecture: `docs/architecture.md`
- UI screens: `docs/ui_screens.md`
