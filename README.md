# GLM Workbench

A local workbench to test out and learn Generalized Linear Models for actuarial
pricing, through a guided Streamlit UI. **Version 1 reproduces the Chapter 27
car-insurance frequency example** from *Pricing in General Insurance* (Parodi):
load the synthetic ~20k-policy portfolio, explore it, fit a Poisson GLM with
exposure offset, inspect diagnostics, and predict expected claim frequencies.
Severity, pure premium, and a generic workbench follow as V2–V4
(see `docs/car-insurance.md`).

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

Besides the built-in synthetic Chapter 27 dataset, the workbench uses the real
**freMTPL2** French motor TPL data (CC0, from OpenML / CASdatasets). `data/` is
gitignored — fetch the Parquet files once:

```bash
curl -sL -o data/raw/freMTPL2freq.parquet https://data.openml.org/datasets/0004/41214/dataset_41214.pq
curl -sL -o data/raw/freMTPL2sev.parquet  https://data.openml.org/datasets/0004/41215/dataset_41215.pq
```

## Docs

- Spec: `.planning/PROJECT.md`
- Architecture: `docs/architecture.md`
- UI screens: `docs/ui_screens.md`
