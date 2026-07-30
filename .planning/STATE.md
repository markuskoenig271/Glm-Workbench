# Project State

Rolling "where I left off" file (committed). Overwritten each session.
Read this + `TODO.md` at the start of every session. See `PROJECT.md` for the spec.

---

## Last updated: 2026-07-30 (session 3 — slices 1+2 committed, V3.x simulation on roadmap, interview doc)

## Headline

V2 slice 1 committed (`3518e96`) and **slice 2 (Severity Model screen) built
through the full Change Validation Workflow, validated, committed + pushed
(`43ca260`)**. A roadmap discussion added **V3.x aggregate loss simulation**
(compound Poisson Monte Carlo) to docs/architecture.md, docs/ui_screens.md
and TODO.md — those planning/doc updates are **uncommitted** at save
(suggested: `docs: session save + V3.x aggregate loss simulation on the
roadmap`). Side quest: an interview prep doc
`Shiny-to-React-R-Backend-Migration.docx` sits untracked in the repo root
awaiting Markus' commit/gitignore/local call. Next dev work: **V2 slice 3**
(Markus explicitly said "do not start yet with V3" — slice 3 finishes V2 and
was not vetoed, but confirm before starting).

## What was done this session

- **Slice 1 committed** `3518e96` (severity dataset) and pushed.
- **Slice 2 through the full Change Validation Workflow:** BA-Agent report
  (scenarios S1–S8, 12 traps) → Test Agent wrote
  `.planning/e2e-tests/severity-model.md` (9 TCs) → TDD → execution via the
  committed runner `e2e/e2e_severity_model.py` (TC1–TC8 PASSED, TC9
  deferred/manual) → **committed `43ca260` + pushed**. Suite 102 passed /
  99.42% coverage, ruff + mypy clean; slice-1 runner re-executed green.
  Engine: `glm.fit_severity_glm` (Gamma default / Inverse Gaussian, BOTH
  explicit `links.Log()`, no offset, friendly unknown-family ValueError; 5
  new unit tests; stub line removed from test_scaffold per its contract —
  the stale stub also caused a pytest INTERNALERROR via patsy frame
  introspection). **Single active-model slot implemented**: session keys
  `model`/`model_meta` with `kind`; screens 04/07 gate results on kind;
  pages 05/06 show interim "arrives with the next slice" guards (slice 3
  replaces them). UI `pages/07_Severity_Model.py` mirrors screen 04 (no
  stepwise section; reverse kind guard; fit in try/except → friendly error,
  added when E2E proved IG raises on the real data).
- **App started for Markus** (port 8501, background task in this session —
  will not survive the session; restart with
  `uv run streamlit run app.py`). Walked him through the kind guard: load
  the severity dataset via Data Import selectbox to use screen 07.
- **Roadmap discussion (compound Poisson / yearly losses):** missing = V3
  per-kind slots + slice-3 `predict_severity` + NEW simulation machinery.
  λ·μ IS the V3 pure premium (no simulation); simulation adds the
  distribution and needs the Gamma dispersion (`model.scale`) surfaced;
  independence + light-tail caveats must be UI captions. **Written into
  docs/architecture.md (Modeling + module diagram + roadmap),
  docs/ui_screens.md (V3.x Simulation screen), TODO.md — at Markus'
  request, uncommitted at save.**
- **Interview side quest (not project code):** discussed R Shiny →
  React/Angular SPA + R(plumber) backend target architecture and
  strangler-fig migration path; delivered
  `Shiny-to-React-R-Backend-Migration.docx` to the repo root (python-docx
  via ephemeral `uv run --with` — project deps untouched). Untracked;
  TODO item added for its fate.

## Key real-data facts learned (severity model)

- Gamma/log fit on 26,444 claims: **AIC 573,121**, mean fitted **2,230.9**
  vs observed 2,265.5 (−1.5%, within the ±5% calibration bound).
- **Only BonusMalus is significant — 41 of 42 non-intercept terms
  insignificant** (weak-severity-signal teaching moment; exactly one
  strongest-effects bullet renders).
- **Inverse Gaussian is numerically infeasible on the real heavy tail**
  (`ValueError: … estimation infeasible`) — UI catches it, suggests Gamma;
  manual TC9 should expect that message.
- Run 12 appended to data/workbench.db by the TC6 UI fit.

## Working agreements / lessons (keep honoring these)

- Change Validation Workflow every slice: BA/Test agent writes
  `.planning/e2e-tests/<slice>.md`, I execute + record Results. TDD first.
- Commits only when Markus says so; conventional commits, no Co-Authored-By.
- E2E runners live in committed `e2e/` (README has the Playwright lessons).
- Never delete data/workbench.db.

## Open / next steps

1. **Commit the planning/docs updates** when Markus says so (STATE, TODO,
   architecture.md, ui_screens.md — suggested message above; the .docx is a
   separate decision, see TODO backlog).
2. **V2 slice 3 — kind-aware Diagnostics + Prediction:**
   `prediction.predict_severity`, severity wording on Diagnostics, severity
   mode on Prediction; replaces the interim guards on pages 05/06 (details
   in TODO). Finishes V2. (Confirm start with Markus — his "not V3 yet" was
   about V3, but he then pivoted to interview prep.)
3. Then **V3 — Pure Premium** (per-kind slots, λ·μ) and **V3.x aggregate
   loss simulation** (backlog; design in docs/architecture.md "Modeling").
4. Backlog: manual walkthrough (incl. severity-model TC9); regularisation
   rediscussion; .docx fate.

## Architecture drift check (per CLAUDE.md save protocol)

No drift. Slice 2 code matches the approved V2 design (committed with it in
`43ca260`). The V3.x simulation additions to docs/architecture.md and
docs/ui_screens.md were made explicitly at Markus' request (forward-looking
approved design, tracked in TODO) — not silent drift. Interim guards on
pages 05/06 remain the designed slice-2→3 boundary state. The interview
.docx is not a design doc and does not touch the architecture baseline.
