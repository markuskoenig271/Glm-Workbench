# TODO

Active work items and technical debt. Check this at the start of every session.

---

## Project setup (not started — repo is spec-only)

- [ ] Scaffold the project: `uv init`, `pyproject.toml` (streamlit, pandas, statsmodels,
  pytest, ruff, mypy), layout per `docs/architecture.md` (`app.py`, `pricing_engine/`,
  `pages/`, `tests/`), `.env.example`
- [ ] Decide the GLM library (statsmodels is the natural candidate) and record it in
  `PROJECT.md` under Key decisions
- [ ] Decide what SQLite actually stores (projects? fitted model metadata? run history?)
  and add it to `docs/architecture.md` — the current doc doesn't mention the storage layer
- [ ] Pick / prepare a sample insurance dataset for the Home screen's "Load sample data" flow
- [ ] Fill in the Quick Start section of `CLAUDE.md` once the scaffold exists
