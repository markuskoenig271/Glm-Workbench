# Project State

Rolling "where I left off" file (committed). Overwritten each session.
Read this + `TODO.md` at the start of every session. See `PROJECT.md` for the spec.

---

## Last updated: 2026-08-02 (session 4 — R Shiny EUC feasibility study, verified cross-laptop)

## Headline

Side-track session, no Streamlit/Python changes: built a complete **R Shiny
tech feasibility study** in a new top-level `R/` folder (Markus' request,
ahead of V2 slice 3). Template app mirrors all 7 Streamlit pages with the
standard Shiny module pattern; Data Import + Feature Engineering
implemented (tidyverse/pipe style), model pages are placeholders. Three
escalating EUC delivery variants all work: browser launcher, Edge
app-mode launcher, and an **Electron desktop exe that self-manages its R
packages** (end-user contract: install R once, the exe does the rest).
**Verified on Markus' second laptop.** Everything in `R/` is **untracked/
uncommitted**, as are the TODO/STATE updates. Next dev work on the main
app remains **V2 slice 3** (confirm with Markus before starting).

## What was done this session

- **R/ template app** (R 4.2.1 found at `C:\Program Files\R`, no RStudio
  needed): `app.R` (bslib `page_navbar`) + `core/datasets.R` (registry,
  nanoparquet parquet loaders incl. severity inner join, kind-aware
  `validate_portfolio`) + `core/preprocessing.R` (cap/bin/log) +
  `modules/` (`NS()` + `moduleServer` per page; shared `reactiveValues`
  state as the `st.session_state` analogue; placeholder module reused for
  pages 02/04–07). Headless checks (scratchpad `test_core.R`, 12/12 PASS)
  reproduce the Python facts: freq 678,013 rows, sev join 26,444 rows,
  mean claim 2,265.5.
- **Converted to tidyverse/pipe style** at Markus' request: native `|>`,
  dplyr verbs, `"{col}_band" :=` dynamic mutate, tidyr `pivot_longer`
  validation report, tibbles, readr CSV upload. All deps were already in
  his user library (dplyr 1.1.4 etc.); only **nanoparquet** was newly
  installed (user lib, compiled via his Rtools42).
- **Launchers:** `run_app.bat` (default browser tab) and
  `run_app_desktop.bat` (Edge/Chrome `--app=` mode on port 8613, native-
  window feel, closing the window kills the server via
  Get-NetTCPConnection→Stop-Process; verified headlessly).
- **Electron wrapper `R/desktop/`** (Node 24 was present): `main.js`
  spawns Rscript, parses Shiny's random "Listening on" port, native
  window, `taskkill /t` cleanup. **Self-managing per Markus' requirement:**
  preflight-checks 9 required packages, auto-installs missing ones into
  `R_LIBS_USER` with a live-log first-run window (resumes if interrupted);
  R-not-found and setup-failure show copy-pasteable self-help HTML pages.
  freMTPL2 parquet bundled (built-in datasets work on target machines).
  Builds via electron-builder: **portable `GLM Workbench 0.1.0.exe`
  (74.8 MB) + NSIS `GLM Workbench Setup 0.1.0.exe`** in `R/desktop/dist/`.
  Smoke tests all green (dev, packaged, and auto-install E2E via a
  junction-based scratch `R_LIBS_USER` with tibble removed — real library
  untouched). **Markus confirmed the portable exe works on his other
  laptop.**
- Feasibility Q&A captured in `R/README.md`: no RStudio needed; no true
  compiled .exe exists (options ranked: launcher / R-Portable /
  Electron / RInno-legacy / shinylive-WASM); winCodeSign build gotcha
  (extract manually without Dev Mode); golem/package conversion path.
- Memory saved: Markus' former-company background (golem-style Shiny-as-
  package, roxygen/DESCRIPTION/Rtools, Docker on OpenShift).

## Machine facts learned (dev laptop)

- R 4.2.1 (`C:\Program Files\R\R-4.2.1`, registry key present, not on
  PATH), Rtools42 present, tidyverse packages built under 4.2.3 (harmless
  warnings). Edge at `C:\Program Files (x86)\Microsoft\Edge`. Node 24 /
  npm 11. CRAN 4.2 binaries are frozen → nanoparquet compiles from source
  on 4.2 (why current-R advice is in the exe's failure page).

## Working agreements / lessons (keep honoring these)

- Change Validation Workflow every slice on the MAIN app. The R/ spike
  deliberately ran lighter (headless core checks + smoke tests instead of
  BA/Test-agent E2E docs) — it is a feasibility template, not product code.
  If R/ graduates, put it under the full workflow.
- Commits only when Markus says so; conventional commits, no Co-Authored-By.
- E2E runners live in committed `e2e/`; never delete data/workbench.db.

## Open / next steps

1. **Commit decisions:** `R/` folder (fully untracked; node_modules/dist/
   r-portable already gitignored via `R/desktop/.gitignore`), the
   TODO/STATE updates, and the still-untracked interview .docx.
2. **V2 slice 3 — kind-aware Diagnostics + Prediction** (finishes V2;
   details in TODO). Still the next main-app work; confirm start.
3. **R feasibility follow-ups** (TODO): icon, renv pinning, R-Portable
   bundle, model screens in R, golem conversion if server-side.
4. Then V3 pure premium, V3.x simulation; backlog unchanged
   (regularisation rediscussion, synthetic generator, manual walkthrough).

## Architecture drift check (per CLAUDE.md save protocol)

No drift in the approved design docs: nothing in the Streamlit app,
`pricing_engine/`, or the data layer changed this session.
`docs/architecture.md` intentionally does not cover the `R/` folder — it
is an experimental feasibility spike outside the product architecture,
tracked in TODO ("Tech feasibility — R Shiny EUC app"). If the R app is
ever promoted beyond a spike, it needs its own design doc under `docs/`
(flagged in the TODO follow-ups).
