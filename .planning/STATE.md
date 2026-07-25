# Project State

Rolling "where I left off" file (committed). Overwritten each session.
Read this + `TODO.md` at the start of every session. See `PROJECT.md` for the spec.

---

## Last updated: 2026-07-25 (session 1 — from empty repo to V1 + stepwise, all pushed)

## Headline

**V1 is complete and live**: the full Chapter-27 frequency workflow on the real
freMTPL2 dataset (678,013 policies), all 7 screens working, plus the V1.x
stepwise-variable-selection enhancement. Everything through `89025e9` is on
`origin/main`; only a TODO.md edit (regularisation rediscuss note) is pending
commit. Suite **87 passed / 99.4% coverage**, ruff + mypy clean, six E2E slices
executed green against real data. Markus was testing the app at the session end
(`streamlit run app.py`, port 8501 — running in a background task).

## What exists (one session!)

- Bootstrap: cleaned copied-over planning files, CLAUDE.md, gitignore; spec'd
  PROJECT.md; scaffold; V1 rescope to Parodi Ch. 27 after Markus added
  docs/car-insurance.md; freMTPL2 chosen + downloaded (decision 6, CC0,
  data/raw/*.parquet, download commands in README).
- `pricing_engine/`: data (DatasetSpec/registry/loaders/validation),
  exploration (aggregate-only), preprocessing (bin/log/encode/cap),
  glm (fit + stepwise_selection), diagnostics (coeffs/CIs/residuals/QQ/
  calibration), prediction (frequency single+batch), storage (SQLite
  model_runs, decision 7; data/workbench.db, GLM_DB_PATH override).
- `pages/01–06` + Home: Import (built-in + CSV upload w/ column mapping) →
  Exploration → Feature Engineering → Frequency Model (fit + variable
  selection + run history) → Diagnostics → Prediction (what-if + batch + CSV).

## Verified headline numbers (E2E, real data)

- Overall frequency **0.1007**; full Poisson fit ~12s; AIC 286,703;
  BonusMalus +2.3%/point (p≪0.001); calibration weighted-pred = observed;
  in-sample balance EXACT (expected 36,102 = observed 36,102); stepwise
  forward adds BonusMalus → DrivAge → VehGas in strength order; Exposure
  quirk: 1,224 rows > 1.0, cap button in Feature Engineering.

## Working agreements / lessons (keep honoring these)

- Change Validation Workflow every slice: BA/Test agent writes
  `.planning/e2e-tests/<slice>.md`, I execute + record Results. TDD first.
- Playwright lessons live in the E2E docs' notes (one tab + sidebar nav —
  goto/refresh drops session state; expect-before-count on progressive
  renders; defaults-only widgets, changes deferred/manual; engine TCs for
  numeric truths; never delete data/workbench.db).
- Commits only when Markus says so; conventional commits, no Co-Authored-By.

## Open / next steps

1. Commit the pending TODO.md note (this save-session commit).
2. **Rediscuss regularisation with Markus** (TODO backlog item, his ask —
   wants it in "somehow"; settle the degraded-inference-view framing).
3. Markus' manual walkthrough: deferred/manual TCs incl. the full 9-predictor
   stepwise UI run (~5–10 min; expect all 9 to survive).
4. Housekeeping TODO: promote scratchpad Playwright runners into a committed
   `e2e/` dir.
5. Then V2 — Severity GLM (freMTPL2sev already in data/raw;
   `fit_severity_glm` is the last engine stub).

## Architecture drift check (per CLAUDE.md save protocol)

None open — architecture.md and ui_screens.md were updated in-session with
each slice (Datasets section, exploration/storage modules, stepwise section);
code and docs are in sync as of `89025e9`.
