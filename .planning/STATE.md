# Project State

Rolling "where I left off" file (committed). Overwritten each session.
Read this + `TODO.md` at the start of every session. See `PROJECT.md` for the spec.

---

## Last updated: 2026-08-25 (session 5 — V2 slice 3: kind-aware Diagnostics + Prediction)

## Headline

**V2 (severity workflow) is complete.** Slice 3 delivered through the full
Change Validation Workflow (BA agent → Test agent plan → TDD → committed
Playwright runner): `prediction.predict_severity`, and pages 05/06 rewritten
kind-aware from the single active-model slot. The interim "arrives with the
next slice" guards are gone, replaced by real guards for the dangerous
states (dataset kind ≠ model kind, row-count mismatch, stale batch from the
other kind). Everything is **uncommitted** (Markus decides commits). Next
main-app work: **V3 pure premium** (needs per-kind model slots — see TODO
notes) — confirm with Markus before starting.

## What was done this session

- **Engine:** `predict_severity(model, claims, spec)` → copy +
  `expected_claim_amount` (model mean, no exposure scaling; missing-predictor
  ValueError). `observed_vs_predicted` deliberately untouched — with
  `offset=None` its `exposure` column is the claim count and its
  `*_frequency` columns are per-claim averages; the page renames them for
  severity. 7 new unit tests + severity fixtures in conftest
  (`SEVERITY_SPEC`, `severity_portfolio`, `fitted_severity_model`); suite
  109 passed, 99.43% coverage; ruff + mypy clean.
- **UI:** `pages/05_Diagnostics.py` per-kind `WORDING` table (claim-size
  relativities, heavy-tail residual caption, average-claim-amount
  calibration, renamed calibration table columns); `pages/06_Prediction.py`
  severity mode ("Single claim" what-if without exposure → one metric
  "Expected claim amount"; "Predict for loaded claims" batch; honest caption
  that a log-link Gamma does NOT reproduce the observed total; kind-specific
  CSV filename); both pages: fresh-session guard names both model screens,
  **dataset-kind ≠ model-kind guard**, Diagnostics calibration row-count
  guard, batches tagged with `predictions_kind`.
- **E2E:** plan `.planning/e2e-tests/severity-diagnostics-prediction.md`
  (TC1–TC12) + committed runner `e2e/e2e_severity_diag_pred.py`. TC1–TC11
  PASSED first run (TC10 reverse slot-swap executed, not deferred); TC12
  manual (added to the manual-walkthrough backlog). Slice-2 runner
  `e2e_severity_model.py` TC7 inverted (05/06 now render for a severity
  model) + its plan annotated; `e2e_diag_pred.py` untouched and green.
- **Real-data findings (record for the teaching captions):** mean expected
  claim amount 2,230.9; batch total 58,995,121 vs observed 59,909,216 →
  **−1.53% gap** (log-link Gamma balance is not exact — unlike Poisson's
  36,102 = 36,102); calibration band observed averages 1,586–5,453;
  median-profile single claim 1,504.
- Docs: `docs/architecture.md` roadmap marks V2 complete (2026-08-25);
  `e2e/README.md` lists the new runner and its 3 appended history runs.

## Working agreements / lessons (keep honoring these)

- Change Validation Workflow every slice on the MAIN app (BA agent → Test
  agent plan in `.planning/e2e-tests/` → committed runner in `e2e/`).
- Commits only when Markus says so; conventional commits, no Co-Authored-By.
- Never delete `data/workbench.db`; runners append real runs by design.
- Playwright: one tab + sidebar links after loading; `expect` before
  `count`; full-phrase absence assertions (`get_by_text` is case-insensitive
  substring — bare `frequency` matches the sidebar); the combobox route
  (click + type fragment + Enter) now proven for BOTH `severity` and
  `frequency`. Bash heredocs choke on non-ASCII (—, μ) — use the Write tool
  for files containing them.

## Open / next steps

1. **Commit decision (Markus):** slice 3 (engine, pages, tests, e2e plan +
   runner, docs, TODO/STATE) — suggested `feat: kind-aware diagnostics +
   prediction, predict_severity (V2 slice 3)`. Still-untracked interview
   `.docx` at the repo root awaits his call (backlog item).
2. **V3 pure premium** — design step first (architecture-first rule): split
   the single active-model slot per kind (`models["frequency"]`,
   `models["severity"]`), pure premium = λ(x)·μ(x), then V3.x compound
   Poisson simulation (needs `model.scale` dispersion surfaced). Confirm
   scope with Markus before starting.
3. Backlog unchanged: manual walkthrough (now incl. slice-3 TC12),
   regularisation rediscussion, synthetic Chapter 27 generator, R feasibility
   follow-ups, V2.x notes (generalize stepwise beyond frequency; heavy-tail
   histogram binning).

## Architecture drift check (per CLAUDE.md save protocol)

No drift: `docs/architecture.md` "V2 — Severity design" slice 3 and
`docs/ui_screens.md` sections 6/7 describe exactly what was built
(kind-aware wording, single-claim what-if without exposure, batch per claim
row). Only the roadmap status line was updated. One design note worth
carrying into the V3 design (not drift): the diagnostics engine's
`observed_vs_predicted` column names are frequency-flavoured
(`observed_frequency`/`predicted_frequency`) while being reused for
severity averages — rename to kind-neutral names when V3 touches it.
