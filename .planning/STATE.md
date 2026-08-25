# Project State

Rolling "where I left off" file (committed). Overwritten each session.
Read this + `TODO.md` at the start of every session. See `PROJECT.md` for the spec.

---

## Last updated: 2026-08-25 (session 5, part 2 — R app converted to the `glmworkbenchR` **golem** package)

## Headline

Two things happened today. **Part 1 (committed 98c091f, pushed): V2 slice 3**
— kind-aware Diagnostics + Prediction, `predict_severity`; V2 is complete.
**Part 2 (uncommitted): the R Shiny feasibility app became a proper R
package, then a golem app.** Markus' decisions: rename `R/` →
`glmworkbench_in_r/` (folder name says "everything else is Python"),
package name `glmworkbenchR` (underscores are illegal in R package names);
first built plain usethis/devtools, then — "für langfristige Wartbarkeit"
— **golem-ified in place** (dev/ scripts, golem-config.yml, app_config.R,
`with_golem_options`, `inst/app/www`). Everything verified twice (check
clean, 54 tests, smokes, first-run auto-install E2E, dist rebuilt). Next
main-app work: **V3 pure premium** (design first) — confirm with Markus.

## golem specifics (part 2b)

- Dev loop = `dev/run_dev.R` (`golem::document_and_reload(); run_app()`);
  `dev/02_dev.R` carries ready-made `golem::add_module()` lines for the
  five placeholder screens and `add_fct("glm")` for the modelling engine.
- `run_app(..., data_dir)` returns the app via `with_golem_options()`; Shiny
  run options go through `options = list(port =, launch.browser =)`. Rscript
  callers wrap it in `print()` (launchers, main.js) so it runs regardless of
  autoprint. `data_dir()` order: golem opt → env var → golem-config →
  `inst/extdata` → `../data/raw`.
- New runtime deps golem + config (also in the exe's `REQUIRED_PACKAGES`;
  the first-run E2E installed them into the scratch lib fine).
- Dist rebuilt 14:55 (golem version, 78 MB each); packaged portable exe
  smoke exit 0, no orphan Rscript, `resources/pkg` now also carries
  `inst/golem-config.yml` + `inst/app/www`.

## What was done in part 2 (R package)

- `glmworkbench_in_r/`: `DESCRIPTION` (Imports: shiny, bslib, DT,
  nanoparquet, dplyr, tidyr, tidyselect, purrr, readr, tibble, rlang;
  Suggests devtools/testthat/withr; `Depends: R >= 4.1` for `|>`),
  roxygen-generated `NAMESPACE`/`man/` (8 Rd), `LICENSE` (all rights
  reserved — Markus never picked a licence; check shows no NOTE for it),
  `.Rbuildignore`, `.gitignore`, `glmworkbenchR.Rproj`.
- `R/`: `glmworkbenchR-package.R` (all `@import`/`@importFrom`; no
  `library()`/`source()` anywhere), `app_ui.R`, `app_server.R`, exported
  `run_app(data_dir, port, launch.browser, ...)`, `fct_datasets.R`
  (registry, loaders, `validate_portfolio`, exported `data_dir()` resolving
  env `GLM_WORKBENCH_DATA_DIR` → option `glmworkbenchR.data_dir` →
  `inst/extdata` → `../data/raw`), `fct_preprocessing.R`, `mod_*.R`
  (`@noRd`). Non-ASCII in strings escaped as `\uXXXX` (check portability).
- `tests/testthat/`: 41 tests (preprocessing on toy tibbles; registry,
  validation incl. kind-awareness; real-data facts 678,013 / 26,444 /
  mean 2,265.5 — skipped when parquet not reachable, e.g. inside
  `R CMD check`'s temp copy unless `GLM_WORKBENCH_DATA_DIR` is set).
- Launchers `run_app.bat` / `run_app_desktop.bat`: use the installed
  package, else `pkgload::load_all()` of the source folder; call
  `glmworkbenchR::run_app(data_dir = '<pkg>/../data/raw', ...)`.
- Electron `desktop/main.js`: bundles the package source as
  `resources/pkg` (electron-builder `extraResources`), version-checks the
  installed `glmworkbenchR` against the bundled `DESCRIPTION` and installs
  it from source into `R_LIBS_USER` when missing/outdated (pure R, no
  Rtools), CRAN deps auto-installed as before, runs
  `glmworkbenchR::run_app(launch.browser = FALSE)` with
  `GLM_WORKBENCH_DATA_DIR` pointing at the bundled parquet.
- README rewritten: layout, `data_dir()` resolution, **"Development in
  RStudio"** loop (load_all → run_app; document; test; check; install),
  conventions for adding modules/deps, running without RStudio, EUC findings.
- Verification: `devtools::test()` 41 pass / 0 skip; `devtools::check()`
  0 errors, 0 warnings, 1 NOTE ("unable to verify current time" — harmless);
  `devtools::install()`; headless smoke via installed package (HTTP 200,
  3 s) and via the `load_all` fallback (1 s); Electron dev `npm start`
  smoke `SMOKE_OK`; **first-run E2E**: package removed from the real
  library → exe installed it from the bundled source into a scratch
  `R_LIBS_USER` → `SMOKE_OK`; real library untouched, then reinstalled.
  `npm run dist` rebuilt the portable + NSIS exes (78 MB each,
  `desktop/dist/`, gitignored); packaged smoke of the portable exe: exit 0,
  no orphan Rscript, `resources/pkg` holds DESCRIPTION/NAMESPACE/R/man and
  `resources/data/raw` both parquet files.

## Working agreements / lessons (keep honoring these)

- Commits only when Markus says so; conventional commits, no Co-Authored-By.
- R package hygiene: roxygen headers, `@importFrom` in
  `R/glmworkbenchR-package.R`, `.data[[col]]` / `all_of()` for columns,
  `\uXXXX` for non-ASCII, `devtools::document()` after editing headers,
  never edit `NAMESPACE`/`man/` by hand.
- Tooling gotcha: the Bash tool's heredocs mangle non-ASCII characters AND
  backslash escapes — use the Write/Edit tools (or a script file) for any
  content with `—`, `\u…`, etc.
- Playwright/Streamlit lessons unchanged (see part-1 STATE in git history
  98c091f and `e2e/README.md`).

## Open / next steps

1. **Commit decision (Markus):** the package conversion (rename + new
   files + TODO/STATE). Suggested:
   `refactor(r): convert Shiny app to the glmworkbenchR package (glmworkbench_in_r/)`.
   Still-untracked interview `.docx` at the repo root awaits his call.
2. Optional R follow-ups (TODO): `renv` pinning; custom icon; R-Portable
   bundle; model screens in R (`glm()` Poisson/Gamma); if server-side, the
   package is already golem-shaped.
3. **V3 pure premium** — design step first (per-kind model slots,
   λ(x)·μ(x)), then V3.x simulation. Confirm scope with Markus.
4. Backlog unchanged (manual walkthrough incl. slice-3 TC12, regularisation
   rediscussion, synthetic Chapter 27 generator, V2.x notes).

## Architecture drift check (per CLAUDE.md save protocol)

No drift in the Python design docs (nothing in `pricing_engine/`, `pages/`
or the data layer changed in part 2). `docs/architecture.md` intentionally
does not cover the R package — it is an experimental feasibility spike
outside the product architecture, tracked in TODO; its own design lives in
`glmworkbench_in_r/README.md`. If the R app is promoted beyond a spike it
needs a design doc under `docs/`.
