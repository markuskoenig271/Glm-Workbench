# Project State

Rolling "where I left off" file (committed). Overwritten each session.
Read this + `TODO.md` at the start of every session. See `PROJECT.md` for the spec.

---

## Last updated: 2026-07-29 (session 2 — e2e harness committed, V2 designed + slice 1 built)

## Headline

Two things happened: (1) the **E2E runner harness** was promoted from the old
session scratchpad into a committed `e2e/` directory and re-executed fully
green (`45d0621`, pushed to origin/main). (2) **V2 severity started**: design
approved by Markus (decision 8 in PROJECT.md — per-claim Gamma, full-workflow
scope) and written into docs/architecture.md + docs/ui_screens.md, and
**slice 1 (the severity dataset) is implemented and validated but
UNCOMMITTED** — suite 97 passed / 99.41% coverage, ruff + mypy clean, E2E
TC1–TC9 green. Waiting on Markus' commit word (suggested:
`feat: severity dataset as second registered dataset (V2 slice 1)`).

## What was done this session

- **e2e/ harness (committed `45d0621`, pushed):** shared `harness.py`
  (headless app on port 8598, taskkill teardown, FIXTURES path),
  `fixtures/broken_portfolio.csv`, README (run instructions + Playwright
  lessons), all eight V1 runners with repo-relative paths (freq-model storage
  TC on tempfile now). All eight re-executed green; V1 headline numbers
  reproduced exactly (AIC 286,703; freq 0.1007; balance 36,102 = 36,102).
  pytest does not collect e2e/ (`testpaths = ["tests"]`).
- **V2 design (decision 8):** per-claim severity GLM (Gamma default /
  Inverse Gaussian, log link, no offset) on `fremtpl2_sev` = sev table
  inner-joined with the 9 rating factors; `DatasetSpec.kind` drives guards,
  wording, validation. Three slices planned (see TODO V2 section). Markus
  chose per-claim over weighted per-policy, and full workflow over
  fit-screen-only.
- **V2 slice 1 (uncommitted):** engine (`kind` field, `FREMTPL2_SEV_SPEC`,
  `load_fremtpl2_sev_joined`, severity-aware validation) + UI (kind-aware
  Exploration metrics/labels, Frequency Model kind guard) + 10 unit tests +
  E2E doc `.planning/e2e-tests/severity-dataset.md` (BA/Test agent authored)
  executed via the new committed runner `e2e/e2e_severity_dataset.py`.
- Backlog decisions (Markus): regularisation rediscussion stays in backlog;
  manual walkthrough stays in backlog (now includes severity TC10).

## Key real-data facts learned (severity)

- Joined severity table: **26,444 rows × 11 cols** (26,639 claims − 195
  orphans); ClaimAmount min 1.0 / median 1,172 / **mean 2,265.51 joined**
  (raw table 2,278.5 — orphan drop shifts it) / max 4,075,400.56;
  fixed-compensation spikes 1204.00 → 4,792, 1128.12 → 3,056.
- ClaimAmount histogram: first bin > 90% (heavy tail) — expected artifact,
  UX improvement noted in TODO V2.x.
- freq parquet is sorted claims-first (head(1000) has no zero-claim rows).
- Playwright: combobox click + type-fragment + Enter DOES work for Streamlit
  selectboxes (first sanctioned success — used by severity-dataset TC6).

## Working agreements / lessons (keep honoring these)

- Change Validation Workflow every slice: BA/Test agent writes
  `.planning/e2e-tests/<slice>.md`, I execute + record Results. TDD first.
- Commits only when Markus says so; conventional commits, no Co-Authored-By.
- E2E runners now live in committed `e2e/` (see its README for the
  Playwright/Streamlit lessons; expect-before-count bit again this session).
- Never delete data/workbench.db (run history: 11 rows after today's runs).

## Open / next steps

1. **Commit slice 1** when Markus says so (code + docs + planning are all
   uncommitted in the working tree; see git status).
2. **V2 slice 2 — Severity Model screen:** `glm.fit_severity_glm` +
   `pages/07_Severity_Model.py` + reverse kind guard (details in TODO).
3. **V2 slice 3 — kind-aware Diagnostics + Prediction** (details in TODO).
4. Backlog (Markus' explicit calls today): manual walkthrough incl. severity
   TC10; regularisation rediscussion.

## Architecture drift check (per CLAUDE.md save protocol)

No drift. docs/architecture.md and docs/ui_screens.md were updated FIRST
(architecture-first) this session with the V2 design; slice 1 code matches
them. Note: the docs describe slices 2–3 (Severity Model screen, kind-aware
Diagnostics/Prediction) that are designed but not yet built — that is
forward-looking approved design, tracked in TODO, not drift.
