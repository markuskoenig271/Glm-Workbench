# Project State

Rolling "where I left off" file (committed). Overwritten each session.
Read this + `TODO.md` at the start of every session. See `PROJECT.md` for the spec.

---

## Last updated: 2026-07-30 (session 3 — slice 1 committed, V2 slice 2 built + validated)

## Headline

Two things happened: (1) **V2 slice 1 was committed and pushed** (`3518e96`,
"feat: severity dataset as second registered dataset (V2 slice 1)" — Markus'
"continue" taken as the commit word the previous session was waiting for).
(2) **V2 slice 2 (Severity Model screen) is implemented and fully validated
but UNCOMMITTED** — suite 102 passed / 99.42% coverage, ruff + mypy clean,
E2E severity-model TC1–TC8 green via the new committed runner
`e2e/e2e_severity_model.py`, slice-1 runner re-executed green. Waiting on
Markus' commit word (suggested:
`feat: severity model screen with Gamma/IG GLM (V2 slice 2)`).

## What was done this session

- **Slice 1 commit:** verified green (97 tests, ruff/mypy clean), committed
  `3518e96`, pushed to origin/main.
- **Slice 2 through the full Change Validation Workflow:** BA-Agent report
  (scenarios S1–S8, AC-S1–S8, 12 traps) → Test Agent wrote
  `.planning/e2e-tests/severity-model.md` (9 TCs) → TDD → execution.
- **Engine:** `glm.fit_severity_glm` — Gamma default / Inverse Gaussian,
  BOTH with explicit `links.Log()` (statsmodels defaults are inverse-power —
  the headline trap), no offset parameter, friendly unknown-family
  ValueError. 5 new unit tests incl. link-class assertions and
  fitted-means-match-observed. The `fit_severity_glm` stub line was removed
  from `test_scaffold.py::test_stubs_fail_loudly` (per that file's contract;
  the stale stub test also triggered a pytest INTERNALERROR via patsy frame
  introspection — resolved by the removal).
- **Single active-model slot implemented** (approved architecture, "V2 keeps
  the single active-model slot"): session keys renamed `freq_model`/
  `freq_model_meta` → `model`/`model_meta` with `meta["kind"]`. Screen 04
  writes kind "frequency", new screen 07 kind "severity"; each results
  section renders only on kind match; pages 05/06 read the new key and show
  an interim "arrives with the next slice" guard when the active model is a
  severity model (slice 3 replaces these guards with real kind-awareness).
- **UI:** `pages/07_Severity_Model.py` mirroring screen 04 (family select,
  formula preview, "Log link, no offset" caption, fit → metrics /
  claim-size-relativity coefficient table / strongest-effects bullets /
  insignificance warning + "Severity signal is usually weaker" teaching
  caption, shared run history; NO stepwise section; reverse kind guard).
  Fit wrapped in try/except → friendly `st.error` (added mid-execution when
  TC2 proved the IG fit raises on the real data).
- **E2E:** committed runner `e2e/e2e_severity_model.py` (TC1–TC7 inline,
  engine TCs first); TC8 = pytest + slice-1 runner re-run, all green;
  TC9 deferred/manual. e2e/README.md updated (new runners, sanctioned
  combobox lesson, workbench.db append note).

## Key real-data facts learned (severity model)

- Gamma/log fit on 26,444 claims: **AIC 573,121**, mean fitted **2,230.9**
  vs observed 2,265.5 (−1.5%, within the ±5% calibration bound).
- **Only BonusMalus is significant — 41 of 42 non-intercept terms are
  insignificant.** The weak-severity-signal teaching moment in its most
  extreme form; the strongest-effects section renders exactly one bullet.
- **Inverse Gaussian is numerically infeasible on the real heavy tail**
  (`ValueError: NaN, inf or invalid value detected in weights`) — the UI
  catches it and suggests Gamma. Manual TC9 should expect that message.
- Run 12 appended to data/workbench.db by the TC6 UI fit (now 12+ rows).

## Working agreements / lessons (keep honoring these)

- Change Validation Workflow every slice: BA/Test agent writes
  `.planning/e2e-tests/<slice>.md`, I execute + record Results. TDD first.
- Commits only when Markus says so; conventional commits, no Co-Authored-By.
- E2E runners live in committed `e2e/` (README has the Playwright lessons).
- Never delete data/workbench.db.

## Open / next steps

1. **Commit slice 2** when Markus says so (all changes uncommitted in the
   working tree; suggested message above).
2. **V2 slice 3 — kind-aware Diagnostics + Prediction:**
   `prediction.predict_severity`, severity wording on Diagnostics, severity
   mode on Prediction; replaces the interim guards on pages 05/06 (details
   in TODO).
3. Backlog: manual walkthrough (now incl. severity-model TC9);
   regularisation rediscussion.

## Architecture drift check (per CLAUDE.md save protocol)

No drift. Slice 2 was built exactly to the approved "V2 — Severity design"
in docs/architecture.md (including the single active-model slot sentence)
and screen 8 in docs/ui_screens.md. The interim guards on Diagnostics/
Prediction are the designed slice-2→3 boundary state, tracked in TODO. The
docs' slice-3 description (kind-aware Diagnostics/Prediction) remains
forward-looking approved design, not drift.
