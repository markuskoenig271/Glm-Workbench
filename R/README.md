# GLM Workbench — R Shiny feasibility study

A template Shiny app mirroring the Streamlit app's screens, built with the
standard Shiny architecture: namespaced UI/server **modules** (`NS()` +
`moduleServer()`), one module file per screen, and a shared `reactiveValues`
state that plays the role of `st.session_state`.

**Feasibility scope:** Data Import (built-in registry datasets + CSV upload
with column mapping, kind-aware validation report) and Feature Engineering /
cleansing (cap, quantile/uniform binning, log transform). The modelling
screens (02, 04–07) are namespaced placeholders so the page structure matches
the real app 1:1.

## Layout

```
R/
├── app.R                          # entry point: navbar UI + module wiring
├── core/
│   ├── datasets.R                 # registry, parquet loaders, validate_portfolio
│   └── preprocessing.R            # cap_column, bin_numeric, log_transform
├── modules/
│   ├── mod_home.R                 # workflow status
│   ├── mod_data_import.R          # 01 — implemented
│   ├── mod_feature_engineering.R  # 03 — implemented
│   └── mod_placeholder.R          # 02, 04–07 — one instance per page
├── run_app.bat                    # EUC launcher — browser tab variant
├── run_app_desktop.bat            # EUC launcher — native-window variant (Edge/Chrome app mode)
├── desktop/                       # Electron wrapper — real desktop app + distributable .exe
│   ├── main.js                    # spawns the R server, native window, kills R on close
│   └── package.json               # electron-builder config (portable .exe + NSIS installer)
└── README.md
```

The data loaders read the same `data/raw/freMTPL2*.parquet` files the Python
app uses (via the dependency-free `nanoparquet` package), including the
severity inner join onto the frequency rating factors.

`core/` and the module data handling are written in **tidyverse style**: the
native `|>` pipe, dplyr verbs (`mutate`, `select`, `inner_join`,
`slice_head`, dynamic column names via `"{col}_band" :=`), tidyr
(`pivot_longer` in the validation report), purrr, tibbles, and `readr` for
CSV upload — the direct R analogue of the pandas code in `pricing_engine/`.

## Running it

Requirements: **R only — RStudio is NOT needed** (RStudio is just an IDE; the
Shiny runtime ships with the `shiny` package and serves the app to any
browser). One-time package install:

```
Rscript -e "install.packages(c('shiny','bslib','DT','nanoparquet','dplyr','tidyr','purrr','readr','tibble'), repos='https://cloud.r-project.org')"
```

Then double-click one of the launchers (both find the installed R via the
registry, with a Program Files fallback):

- **`run_app.bat`** — opens the app as a tab in the default browser. Stop it
  with Ctrl+C in the console window (or close the console).
- **`run_app_desktop.bat`** — starts the server headless on port 8613 and
  opens it in Edge/Chrome **app mode** (`--app=URL`): an own window without
  tabs or address bar, so it looks and feels like a native desktop
  application. **Closing that window shuts the R server down again** (the
  launcher waits on the window, then kills whatever process is listening on
  the port). Uses a dedicated browser profile in `%TEMP%` so it works even
  when a normal Edge/Chrome session is already open.

Or from the repo root without any launcher:

```
Rscript -e "shiny::runApp('R', launch.browser = TRUE)"
```

## EUC deployment findings ("can we ship an executable?")

There is **no true compiled .exe** for R/Shiny — R is an interpreted runtime,
like Python. What exists, in increasing order of packaging effort:

1. **Installed R + launcher script** (what `run_app.bat` does). Users need R
   installed once (plain R, no RStudio, no admin-share issues if IT deploys
   it); the app itself is just a folder. Simplest and the usual EUC pattern.
2. **R-Portable bundled with the app** — a zero-install folder on a network
   share or USB: copy `R-Portable/` next to the app, point the launcher's
   `RSCRIPT` at it. Nothing to install on the user's machine at all.
3. **Electron wrapper** — implemented in `desktop/`. A Node/Electron shell
   that finds R (bundled `r-portable/` in resources → `r-portable/` next to
   the portable .exe → `GLM_WORKBENCH_RSCRIPT` env var → registry → Program
   Files), spawns the Shiny server on a random free port (parsed from
   Shiny's "Listening on" line), shows the app in its own native window
   with taskbar identity, and taskkills the R process tree on close.
   **End-user contract: install R once — everything else is managed by the
   exe.** On every start the shell checks the required R packages and, if
   any are missing, installs them automatically into the user's R library
   (first-run setup window with live progress log; resumes if interrupted).
   If R itself is missing, a self-help page with copy-pasteable
   instructions is shown instead of the app. The freMTPL2 parquet files are
   bundled, so the built-in datasets work on target machines. Dev run:
   `npm install` then `npm start` inside `desktop/`. Distributables:
   `npm run dist` → `desktop/dist/` with a **portable single-file .exe**
   and an **NSIS Setup.exe installer**. Heavyweight (hundreds of MB with
   Chromium) and needs Node.js to build. Caveat: auto-install uses CRAN
   binaries; on outdated R versions some packages may only exist as source
   (needs Rtools) — the failure page then advises installing a current R. Build gotcha: without Windows Developer Mode, electron-builder's
   winCodeSign cache fails to extract (macOS symlinks); fix by extracting
   `winCodeSign-2.6.0.7z` manually with 7za into
   `%LOCALAPPDATA%\electron-builder\Cache\winCodeSign\winCodeSign-2.6.0`
   and ignoring the two darwin symlink errors.
4. **RInno** — generates an Inno Setup Windows installer that bundles
   R-Portable + the app + a desktop shortcut. Historically the standard
   answer, but the package is no longer actively maintained; treat as legacy.
5. **shinylive / webR (WASM)** — exports the app to static files that run
   **entirely in the browser with no R installed anywhere**. Genuinely
   zero-install, but package support is limited to WASM builds and there is
   no local file-system/SQLite access — good for demos, not for a workbench
   that reads local parquet and writes a local DB.

Recommended for a real EUC rollout: **option 2** (R-Portable + launcher) for
zero-install, or option 1 if a managed R install is acceptable. Pin package
versions with `renv` (`renv::init()` in this folder) before sharing.

## Deliberate parallels to the Streamlit app

| Streamlit | Shiny equivalent here |
| --- | --- |
| `st.session_state["portfolio"]/["spec"]` | `reactiveValues` state passed to every module |
| one file per page in `pages/` | one module file per page in `modules/` |
| `pricing_engine.data` registry/loaders | `core/datasets.R` |
| `pricing_engine.preprocessing` | `core/preprocessing.R` |
| single active model slot + kind gate | `state$model` / `state$model_meta` (reserved) |

One behavioural difference to note for the study: browser refresh starts a
new Shiny session (dataset must be reloaded) — same as Streamlit.
