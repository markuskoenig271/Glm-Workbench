# Project State

Rolling "where I left off" file (committed). Overwritten each session.
Read this + `TODO.md` at the start of every session. See `PROJECT.md` for the spec.

---

## Last updated: 2026-08-31 (session 6 — V3 complete: per-kind slots, model persistence, pure-premium quote calculator; user manual)

## Headline

**V3 is complete** — designed, approved, built and E2E-verified in ONE session,
in three slices, each through the full Change Validation Workflow (BA agent →
test plan in `.planning/e2e-tests/` → committed runner in `e2e/`). Six commits,
all pushed to `origin/main`:

1. **5975c27** — interview `.docx` committed (Markus' decision; backlog item
   closed).
2. **54d595c — V3 design** in `docs/architecture.md` + `docs/ui_screens.md`
   (Markus' decisions via single questions: model selection on 05/06 by
   dataset kind, premium breakdown in the first cut, FULL model persistence).
3. **583652a — slice 1:** per-kind model slots `model_frequency`/
   `model_severity` (fitting no longer evicts the other kind); 05/06 select
   by `spec.kind` (V2 mismatch guard retired); `observed_vs_predicted`
   columns renamed kind-neutral (`observed_mean`/`predicted_mean` — the
   carried V2 note, resolved). Plan+runner `per-kind-model-slots` TC1–TC12
   green; 2 old runners updated for the retired behaviors.
4. **d52fc9d — slice 2:** fitted-model persistence. `model_runs.model_path`
   (idempotent ALTER TABLE migration; 31 old rows keep NULL),
   `storage.save_model`/`load_model`, pickles
   `models/run{id:04d}_{kind}_{family}.pickle` (gitignored), Load control in
   the run histories of 04/07, Diagnostics hint for data-stripped loaded
   models (summary() raises — guarded). KEY ENGINE FIND:
   `save(remove_data=True)` strips IN PLACE → `save_model` deep-copies first
   (unit-tested). Plan+runner `model-persistence` green; headline load 4.2s
   vs ~12s refit.
5. **c860279 — slice 3:** the quote calculator. Engine
   `predict_pure_premium` + `premium_breakdown` (union missing-predictor
   check over BOTH models' formulas; numeric baselines rebased at the
   portfolio MEDIAN — BA gap G4); `pages/08_Pure_Premium.py` (guard ladder
   incl. the G2 round-trip text, quote + breakdown + honest batch); Home
   model-status + "ready to quote". BA gap G1 HONESTY CORRECTION baked into
   docs+screen: no observed-cost comparison is possible (severity table
   covers only ~73% of the 36,102 claims). Plan+runner `pure-premium`
   TC1–TC10 green.
6. **2378750 — `manuals/glm-workbench_user_manual.docx`:** 8-chapter German
   walkthrough with VERIFIED reference values (generated via python-docx,
   ephemeral `uv run --with`; generator script lives in the session
   scratchpad only).

Quality: 132 unit tests, 99.11% coverage; ruff + mypy clean; full regression
battery green (all 9 UI/engine runners). Real-data anchors: median-policy
premium **€97.22/yr** (= the breakdown's reference premium; freq 0.0670 ×
amount €1,450), portfolio total expected loss **€79.8M**, average annual
premium **€243**, expected claims 36,102 (exact), BonusMalus monotone,
exposure scaling exact, loaded models quote identically.

Markus STARTED the manual walkthrough (ran the app, asked two good questions —
frequency QQ-plot interpretation, 36,102-vs-26,444 claims gap — both answered
in chat); the app was stopped at session end (taskkill of his
`uv run streamlit run app.py` tree). Working tree clean.

## What was done this session (details in TODO.md entries)

- Session language switched to German (Markus' request — memory saved).
- Context established: Markus will work at Swiss Life in reinsurance;
  a reinsurance-treaty feature was discussed and DROPPED (motor data) —
  the quote-calculator framing replaced it.
- V3 slices 1–3 as in the headline; ~35 new unit tests overall
  (109 → 132), 3 new E2E plans + 3 committed runners.
- Existing runners: retired-behavior inversions (slice 1), plus repeated
  Playwright timing hardenings — NEW LESSONS documented in `e2e/README.md`:
  metric LABELS mount after the metric element (assert via
  `stMetric.filter(has_text=…)`), widget counts need an expect on the LAST
  widget (`nth(n-1)`) or an element below the group; text that also appears
  in selectbox option labels ("AIC") does not wait.
- `app.py` Home refreshed (sidebar order incl. Severity Model + Pure
  Premium, roadmap markers, per-slot status).
- Design-doc corrections during the slices (documented in place): G1 batch
  metrics, G4 median baseline, G2 guard round trip, slice-2 Load-control
  mechanism + summary-expander guard.

## Working agreements / lessons (keep honoring these)

- Change Validation Workflow every slice on the MAIN app; decisions for
  Markus via AskUserQuestion ONE AT A TIME (his explicit preference).
- Commits only when Markus says so; conventional commits, no Co-Authored-By.
- Respond in German; code/commits/docs stay English.
- Never delete `data/workbench.db` OR the `models/` pickles; runners append
  real runs + pickles by design (~57 runs in the DB after this session).
- statsmodels: `save(remove_data=True)` mutates in place (deep-copy first);
  data-stripped results predict and report coefficients/criteria but have no
  resid/fittedvalues and `summary()` raises.
- Playwright/Streamlit lessons consolidated in `e2e/README.md` (mount-lag
  expects; the slice-3 additions above).
- Bash-tool heredocs can mangle non-ASCII — prefer Write/Edit; verify with
  `od -c` when a heredoc was unavoidable (worked this session, still check).
- python-docx via `uv run --with python-docx` for one-off docx generation —
  no project dependency added.

## Open / next steps

1. **Markus' manual walkthrough** along `manuals/glm-workbench_user_manual.docx`
   (started; severity/persistence/quote chapters remaining) + the
   deferred/manual E2E TCs (TODO list).
2. **Manual addendum (his call, offered, unanswered):** Feature Engineering
   on the severity dataset + the G6 rebuild-on-both-frames caveat.
3. **V3.x aggregate-loss simulation** — design exists in
   `docs/architecture.md` "Modeling"; prerequisites (predict_severity,
   per-kind slots) are now ALL delivered; needs the Gamma dispersion surfaced
   from the engine. Natural next milestone — confirm with Markus.
4. Educational side quest: Negative Binomial vs Poisson AIC comparison
   (overdispersion — prompted by his QQ-plot question).
5. Backlog unchanged otherwise (regularisation rediscussion, synthetic
   Chapter 27 generator, V2.x notes, R-package follow-ups on hold).

## Architecture drift check (per CLAUDE.md save protocol)

No drift: `docs/architecture.md` and `docs/ui_screens.md` were updated
in-session as part of each slice (V3 section marked "approved and delivered
2026-08-31", roadmap marks V3 complete, honesty/mechanism corrections
documented in place with dates). The V2 carried note (frequency-flavoured
calibration column names) was RESOLVED by slice 1. The R package
(`glmworkbench_in_r/`) was untouched and intentionally stays outside
`docs/architecture.md`. One documented-not-drifted corner: quantile bins
built on two different frames give different edges (G6 note in the
pure-premium E2E plan + TODO V3.x follow-ups).
