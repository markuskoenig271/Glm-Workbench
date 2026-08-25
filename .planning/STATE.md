# Project State

Rolling "where I left off" file (committed). Overwritten each session.
Read this + `TODO.md` at the start of every session. See `PROJECT.md` for the spec.

---

## Last updated: 2026-08-25 (session 5 — V2 complete; R app is now the `glmworkbenchR` golem package)

## Headline

Four commits today, all pushed to `origin/main`:

1. **98c091f — V2 slice 3** (kind-aware Diagnostics + Prediction,
   `predict_severity`) → **V2 severity workflow complete.**
2. **21b0571 — R app converted to an R package, golem style**: `R/` renamed
   to `glmworkbench_in_r/`, package `glmworkbenchR`, dev/ scripts,
   golem-config, `run_app()` via `with_golem_options()`, testthat suite,
   launchers + Electron exe updated, README with an RStudio guide.
3. **9049c6c — README**: binary-only install hints (R 4.2's frozen CRAN
   binaries trigger a "compile from source?" prompt → answer Nein).
4. **4266edd — session save** after Markus confirmed the README walkthrough
   in RStudio worked ("R studio hat geklappt"); includes RStudio's own
   housekeeping edits (`.Rproj.user` in the root `.gitignore`, rewritten
   `glmworkbenchR.Rproj`).

Working tree is clean except the interview `.docx` at the repo root
(untracked; Markus was asked: commit / gitignore / leave — no answer yet).
Next main-app work: **V3 pure premium** (design first) — confirm with Markus.

## What was done this session (details in TODO.md entries)

- **Python (slice 3):** `prediction.predict_severity`; pages 05/06 rewritten
  kind-aware with dataset-kind ≠ model-kind guard, calibration row-count
  guard, `predictions_kind` tagging; honest Gamma total-balance caption.
  109 unit tests, 99.43% cov; E2E plan
  `.planning/e2e-tests/severity-diagnostics-prediction.md` + runner
  `e2e/e2e_severity_diag_pred.py` TC1–TC11 green; slice-2 runner TC7
  inverted. Real-data: mean expected claim amount 2,230.9, total gap −1.53%.
- **R package:** DESCRIPTION/NAMESPACE/man, `R/` = app_ui/app_server/
  run_app/app_config/fct_datasets/fct_preprocessing/mod_*; `inst/
  golem-config.yml`, `inst/app/www/custom.css`; `dev/01_start.R`,
  `02_dev.R` (ready-made `add_module()` lines for the 5 placeholder
  screens), `03_deploy.R`, `run_dev.R`; 54 testthat tests; `check()`
  0 errors / 0 warnings / 1 harmless NOTE; headless + Electron smokes;
  first-run E2E (exe installs the bundled package source into a scratch
  library); dist rebuilt (`desktop/dist/`, 78 MB each, gitignored).
  golem 1.0.1 + config 0.3.2 newly installed on the dev laptop.
- **Docs for Markus (in chat, not in repo):** golem explained; what "Ja"
  on the compile prompt would do and how to revert
  (`install.packages(c("rlang","roxygen2","pkgload"), type = "binary")`);
  debugging in RStudio (`browser()` after `load_all()`, editor breakpoints,
  `options(shiny.error = browser)`, reactlog, `debugonce()` on `fct_*`,
  `testServer()` for modules); stopping the app (stop button / Esc, `Q` in
  the debugger, `shiny::stopApp()`).

## Working agreements / lessons (keep honoring these)

- Change Validation Workflow every slice on the MAIN app (BA agent → Test
  agent plan in `.planning/e2e-tests/` → committed runner in `e2e/`). The
  R package runs lighter: `devtools::test()` + `check()` + smokes.
- Commits only when Markus says so; conventional commits, no Co-Authored-By.
- Never delete `data/workbench.db`; runners append real runs by design.
- R package hygiene: roxygen headers, `@importFrom` in
  `R/glmworkbenchR-package.R`, `.data[[col]]` / `all_of()`, `\uXXXX` for
  non-ASCII, `document()` after header edits, never hand-edit
  `NAMESPACE`/`man/`; new CRAN deps also go into `desktop/main.js`
  `REQUIRED_PACKAGES`. Rscript callers wrap `run_app()` in `print()`.
- R 4.2.1 on the dev laptop: CRAN binaries frozen → prefer
  `type = "binary"` / `upgrade = "never"`, answer "Nein" to source-compile
  prompts.
- Tooling gotcha: the Bash tool's heredocs mangle non-ASCII characters and
  backslash escapes — use Write/Edit (or a script file) for such content.
- Playwright/Streamlit lessons unchanged (`e2e/README.md`).

## Open / next steps

1. **Decide the `.docx`** at the repo root (commit / gitignore / leave).
2. **R follow-ups (his call):** `golem::add_module("frequency_model")` with
   `glm()` Poisson/Gamma as the first real modelling screen; `renv` pinning
   / current R; custom icon; R-Portable bundle.
3. **V3 pure premium** — design step first (per-kind model slots,
   λ(x)·μ(x)), then V3.x compound-Poisson simulation. Confirm scope.
4. Backlog unchanged (manual walkthrough incl. slice-3 TC12, regularisation
   rediscussion, synthetic Chapter 27 generator, V2.x notes).

## Architecture drift check (per CLAUDE.md save protocol)

No drift in the Python design docs: `docs/architecture.md` "V2 — Severity
design" and `docs/ui_screens.md` 6/7 describe what slice 3 built; the
roadmap line was updated to "V2 complete 2026-08-25". One note carried for
the V3 design (not drift): `diagnostics.observed_vs_predicted` column names
are frequency-flavoured while reused for severity averages — rename to
kind-neutral names when V3 touches it. `docs/architecture.md` intentionally
does not cover the R package (feasibility spike; its design lives in
`glmworkbench_in_r/README.md`); it needs a `docs/` design doc only if
promoted beyond a spike.
