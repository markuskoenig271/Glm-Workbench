# TODO

Active work items and technical debt. Check this at the start of every session.

---

## V1 — frequency workbench on freMTPL2 (workflow per docs/car-insurance.md)

Primary V1 dataset is now **freMTPL2** (real data, decision 6); the synthetic
Chapter 27 generator moved to the backlog (2026-07-25, Markus' call).

- [x] **Dataset spec + registry — DONE 2026-07-25.** `DatasetSpec` frozen dataclass
  (name/label/target/offset/predictors, `required_columns`), `DATASET_REGISTRY`
  (fremtpl2_freq), `list_datasets()`, `load_dataset()` in `pricing_engine/data.py`.
- [x] **freMTPL2 loaders — DONE 2026-07-25.** `load_fremtpl2_freq`/`_sev` (Parquet,
  IDpol→int64, module-level default paths so tests can monkeypatch); missing file
  → FileNotFoundError with the curl command. **`validate_portfolio(df, spec)`
  implemented too** (missing columns, non-numeric/negative target, non-positive
  offset, NaN counts). TDD: 18 new unit tests (suite 26); E2E 8/8 PASSED against
  real data (`.planning/e2e-tests/dataset-spec-loaders.md` — load+validate 678k
  rows in 0.04s).
- [x] **Data Import slice — DONE 2026-07-25.** `load_portfolio` (CSV path or
  file-like upload, friendly missing-file error; 3 unit tests, suite 29) +
  `pages/01_Data_Import.py` (source radio; registry-driven built-in load into
  `st.session_state["portfolio"]`/`["spec"]`; CSV upload with column-mapping
  widgets building an ad-hoc DatasetSpec; preview + validation report) + Home
  workflow status reflects the active dataset. Playwright installed (first UI
  E2E): `.planning/e2e-tests/data-import.md` — TC1–TC4, TC6, TC7 PASSED, TC5
  deferred/manual. Known Streamlit behavior: browser refresh = new session =
  dataset must be reloaded.
- [x] **E2E runner harness — DONE 2026-07-29.** All eight scratchpad runners
  promoted to a committed `e2e/` directory: shared `harness.py` (headless app
  launch/teardown on port 8598, `FIXTURES` path), `fixtures/broken_portfolio.csv`,
  README with run instructions + the Playwright/Streamlit lessons. Scratchpad
  paths made repo-relative; freq-model storage TC now uses `tempfile` instead of
  scratchpad DBs. Run manually from the repo root, not collected by pytest
  (`testpaths = ["tests"]`). Ruff clean; all eight re-executed green 2026-07-29.
- [x] **Data Exploration slice — DONE 2026-07-25.** New module
  `pricing_engine/exploration.py` (aggregate-only: `portfolio_frequency`,
  `summarize_portfolio`, `one_way_frequency` with quantile binning,
  `histogram`, `correlation_matrix`; 14 unit tests, suite 43) +
  `pages/02_Data_Exploration.py` (guard, metric row, summary table, one-way
  Altair chart + expander table, histogram chart, correlation matrix).
  E2E `.planning/e2e-tests/data-exploration.md`: TC1–TC8 PASSED (freMTPL2
  frequency 0.1007; all-predictor aggregation in 0.32s), TC9 deferred/manual.
  architecture.md module diagram synced (exploration.py added).
- [x] **Feature Engineering slice — DONE 2026-07-25.**
  `pricing_engine/preprocessing.py` implemented (bin_numeric quantile/uniform →
  `<col>_band`, log_transform → `<col>_log`, encode_categorical drop_first,
  cap_column; 13 unit tests, suite 56) + `pages/03_Feature_Engineering.py`
  (variables multiselect wired to spec, exposure cap at 1.0 — real data: 1,224
  rows, binning + log-transform builders appending to spec predictors, encoding
  info note, live spec summary; all mutations via callbacks). E2E
  `.planning/e2e-tests/feature-engineering.md`: all executed TCs PASSED,
  TC8 deferred/manual.
- [x] **Frequency Model slice — DONE 2026-07-25.** `glm.build_formula` +
  `fit_frequency_glm` (Poisson/NegBin, log link, log-exposure offset),
  `diagnostics.coefficient_table` (exp_coef relativities, significance flag) +
  `information_criteria`, NEW `pricing_engine/storage.py` (decision 7 delivered:
  SQLite model_runs at data/workbench.db, GLM_DB_PATH override) +
  `pages/04_Frequency_Model.py` (family select, formula preview, spinner fit,
  metrics, coefficient table, plain-language strongest-effects + insignificance
  warning, persistent run history). 14 new unit tests (suite 70). E2E
  `.planning/e2e-tests/frequency-model.md`: all executed TCs PASSED (real fit
  11.5s, BonusMalus +2.3%/point p≪0.001, AIC 286,703), TC8 deferred/manual.
- [x] **Diagnostics slice — DONE 2026-07-25.** Engine: `residuals` (deviance/
  pearson), `residual_histogram`, `qq_data`, `observed_vs_predicted` (decile
  calibration, aggregate-only) + shared fitted-model fixtures in conftest.
  UI `pages/05_Diagnostics.py`: model guard, metrics, exp(coef) CI-whisker
  chart with 1.0 reference, residual histogram + kind radio, QQ plot,
  observed-vs-predicted grouped bars (2 series + legend), statsmodels summary
  expander. E2E `.planning/e2e-tests/diagnostics.md`: all executed TCs PASSED
  (4 diagnostics on 678k in 0.15s; weighted predicted freq 0.1007 == observed).
- [x] **Prediction slice — DONE 2026-07-25.** Engine: `predict_frequency`
  (offset-free rate + exposure-scaled claims, copy semantics, missing-predictor
  ValueError). UI `pages/06_Prediction.py`: model guard, single-policy what-if
  (median-default widgets per predictor + exposure input), batch prediction
  with summary metrics + preview + CSV download. E2E
  `.planning/e2e-tests/prediction.md`: all executed TCs PASSED (full predict
  2.0s; **in-sample balance exact: expected 36,102 = observed 36,102**).
  **→ V1 workflow complete: all 7 screens functional.**

## V1.x — enhancements (next up)

- [x] **Stepwise variable selection — DONE 2026-07-25** (as designed: no new
  tab). `glm.stepwise_selection` (backward/forward, AIC/BIC, on_fit progress
  callback, step log; candidate fits NOT recorded in run history) + "Variable
  selection" section on `pages/04_Frequency_Model.py` (radios, st.status
  progress, step-log table, Adopt button → shared spec). 6 unit tests (the
  synthetic Noise factor is correctly dropped; suite 87). E2E
  `.planning/e2e-tests/stepwise-selection.md`: engine TC on real data with a
  reduced 3-predictor spec — all three kept (all genuine effects; stops after
  round 1, 4 fits/9s), guard + section-render UI TCs passed; full UI run
  manual/deferred (minutes by design).
- [ ] Manual walkthrough by Markus + the deferred/manual TCs from the E2E docs
  (selectbox/radio changes, CSV save, F5 history persistence; severity-dataset
  TC10: one-way/histogram switches on the severity data, bin/log on it, and
  the switch-back-to-frequency check; now also severity-model TC9: Inverse
  Gaussian via the UI — expect the friendly infeasible-fit error, reverse
  frequency slot-swap, run-history family/offset visual check; now also
  severity-diagnostics-prediction TC12: single-claim widget variations
  (BonusMalus up → expected claim amount up), pearson radio on the Gamma
  model, severity CSV contents, IG failure keeps the previous Gamma model
  in the slot). Kept in backlog 2026-07-29 (Markus).
- [x] SQLite scope — DECIDED 2026-07-25 (decision 7 in `PROJECT.md`, storage
  section in `docs/architecture.md`): workbench state + model run history,
  never portfolio data; implemented lazily.
- [x] SQLite schema + `storage` module — DONE 2026-07-25 with the Frequency
  Model slice (model_runs table; workbench-state/"projects" tables follow when
  a consumer needs them)

## V2 — severity workbench (decision 8 in PROJECT.md; design in docs/architecture.md "V2 — Severity design")

Approved 2026-07-29 (Markus): per-claim grain, full-workflow scope. Three
slices, each through the Change Validation Workflow.

- [x] **Slice 1: severity dataset — DONE 2026-07-29 (uncommitted at save).**
  `DatasetSpec.kind` ("frequency" default / "severity"); registered dataset
  `fremtpl2_sev` (`load_fremtpl2_sev_joined`: inner join sev × freq rating
  factors on IDpol → 26,444 rows × 11 cols, 195 orphans dropped); kind-aware
  `validate_portfolio` (severity target strictly positive, "claim amounts"
  wording); kind-aware Data Exploration (Claims / Total claim amount /
  Average claim amount 2,266; one-way average claim amount); Frequency Model
  kind guard. Feature Engineering + Data Import needed zero changes
  (spec-driven). 10 new unit tests (suite 97, 99.41% cov). E2E
  `.planning/e2e-tests/severity-dataset.md` TC1–TC9 PASSED via committed
  runner `e2e/e2e_severity_dataset.py` (combobox click+type+Enter automation
  worked); TC10 deferred/manual. Findings recorded: joined mean 2,265.5 (raw
  2,278.5); freq parquet sorted claims-first.
- [x] **Slice 2: severity model screen — DONE 2026-07-30 (uncommitted at
  save).** `glm.fit_severity_glm` (Gamma default / Inverse Gaussian, BOTH
  with explicit log link; no offset parameter; friendly unknown-family
  ValueError) + `pages/07_Severity_Model.py` mirroring screen 04 (family
  select, formula preview, fit with try/except → friendly error on numerical
  failure, claim-size relativities, plain-language aids, insignificance
  warning + weaker-severity-signal teaching caption, shared run history; NO
  stepwise section) + reverse kind guard. **Single active-model slot
  implemented** (session keys `model`/`model_meta` with `kind`; screens
  04/07 write their kind, results gated by kind; Diagnostics/Prediction read
  the new key and show an interim guard for severity models until slice 3).
  5 new unit tests (suite 102, 99.42% cov; `fit_severity_glm` stub line
  removed from test_scaffold per its contract). E2E
  `.planning/e2e-tests/severity-model.md` TC1–TC8 PASSED via committed
  runner `e2e/e2e_severity_model.py`; TC9 deferred/manual. Real-data
  findings: mean fitted 2,230.9 (obs 2,265.5), AIC 573,121, **only
  BonusMalus significant (41/42 terms insignificant)**, IG fit numerically
  infeasible on the heavy tail (now caught with a friendly error).
- [x] **Slice 3: kind-aware Diagnostics + Prediction — DONE 2026-08-25
  (commit 98c091f, pushed). → V2 severity workflow complete.**
  `prediction.predict_severity(model, claims, spec)` (copy + `expected_claim_amount`,
  no exposure scaling, missing-predictor ValueError). `pages/05_Diagnostics.py`
  + `pages/06_Prediction.py` rewritten kind-aware from `model_meta["kind"]`:
  per-kind WORDING table on 05 (claim-size relativities, heavy-tail residual
  caption, calibration = observed vs predicted average claim amount per
  predicted-claim-amount band, severity calibration table columns renamed);
  06 gets a "Single claim" what-if (no exposure input, one metric "Expected
  claim amount"), "Predict for loaded claims" batch with the HONEST caption
  that a log-link Gamma does NOT reproduce the observed total (freq keeps
  its Poisson by-construction caption), kind-specific CSV filename. New
  guards replacing the interim "next slice" ones: fresh session ("Fit a model
  first — go to Frequency Model or Severity Model."), **dataset-kind ≠
  model-kind guard on both pages** (the reverse slot-swap crash trap: a
  678k-fitted model against a 26k frame), row-count guard on the calibration
  section, and batches tagged with `predictions_kind` so a stale batch from
  the other kind is never rendered. Engine `observed_vs_predicted` untouched
  (offset None → per-claim averages; its `*_frequency` column names are now
  documented as "per unit of offset" on the page). 7 new unit tests (severity
  fixtures `SEVERITY_SPEC`/`severity_portfolio`/`fitted_severity_model` in
  conftest; suite 109, 99.43% cov). E2E
  `.planning/e2e-tests/severity-diagnostics-prediction.md` TC1–TC10 PASSED
  via committed runner `e2e/e2e_severity_diag_pred.py` (incl. TC10 reverse
  swap, executed); TC12 deferred/manual. Real-data findings: mean expected
  claim amount 2,230.9; batch total 58,995,121 vs observed 59,909,216
  (**−1.53% gap — the log-link Gamma balance teaching point**); calibration
  bands' observed averages 1,586–5,453; median-profile single claim 1,504.
  Slice-2 runner TC7 inverted (05/06 now render for a severity model);
  regression runners `e2e_diag_pred.py` + `e2e_severity_model.py` re-executed
  green (TC11). Docs: architecture roadmap marks V2 complete; e2e README lists
  the new runner (appends 3 real runs to data/workbench.db).
- [ ] V2.x notes: generalize `stepwise_selection` beyond the frequency
  fitter; consider a log-scale/binning improvement for the heavy-tailed
  ClaimAmount histogram (first bin holds >90% — known artifact, TC4).

## V3 — pure premium (design approved 2026-08-31; docs/architecture.md "V3 — Pure premium design")

Markus' decisions 2026-08-31: quote-calculator framing for the new screen;
model selection on 05/06 by the loaded dataset's kind (no picker); premium
breakdown in the first cut; FULL fitted-model persistence (save on fit, load
from run history) as its own slice. Three slices, each through the Change
Validation Workflow.

- [x] **Slice 1: per-kind model slots — DONE 2026-08-31 (uncommitted at
  first save).** Session slots `model_frequency`/`model_severity` (+`_meta`)
  replace `model`/`model_meta`; 04/07 write their own slot (fitting no longer
  evicts the other kind); 05/06 select the model by `spec.kind` with the new
  guard order (dataset-first `Load a dataset first — go to Data Import.`,
  then `Fit a <kind> model first — go to <screen>.`) — the V2 kind-mismatch
  guard is retired (impossible by construction). Engine rename
  `observed_vs_predicted`: `observed_frequency`/`predicted_frequency` →
  `observed_mean`/`predicted_mean` (value-neutral; anchors 0.1007 / 2,230.9 /
  bands 1,586–5,453 unchanged). 109 unit tests, 99.43% cov; ruff + mypy
  clean. E2E `.planning/e2e-tests/per-kind-model-slots.md` TC1–TC12 PASSED
  via committed runner `e2e/e2e_model_slots.py` (TC9 headline: dataset switch
  flips 05/06 between both live models without refits); regression runners
  updated for the retired behaviors (`e2e_diag_pred.py` 2 updates,
  `e2e_severity_diag_pred.py` 4 inversions — noted in that plan's Results)
  and re-executed green; `e2e_severity_model.py` unchanged. TC14
  deferred/manual (folded into the manual-walkthrough backlog item).
- [ ] **Slice 2: fitted-model persistence** — `model_runs.model_path`
  (ALTER TABLE migration), pickles in `models/` via
  `results.save(remove_data=True)`, per-row "Load" action in the run-history
  tables on 04/07 filling the kind's slot (`model_meta["source"]="loaded"`);
  Diagnostics residual/QQ/calibration sections show an info hint for loaded
  (data-stripped) models. See architecture slice 2 for the documented
  `remove_data` limitation.
- [ ] **Slice 3: `predict_pure_premium` + Pure Premium screen** — quote
  calculator (rating-factor widgets + exposure → expected frequency, expected
  claim amount, annual risk premium), premium breakdown table (freq × sev
  relativities), portfolio batch with honest captions (risk premium only;
  freq ⊥ sev; −1.53% Gamma gap propagates; severity nearly flat).

## Tech feasibility — R Shiny EUC app (started 2026-08-02)

(History below refers to the original `R/` folder; it was renamed to
`glmworkbench_in_r/` on 2026-08-25 when the app became the R package
`glmworkbenchR` — see the last DONE entry of this section.)

- [x] **R Shiny template app — DONE 2026-08-02 (uncommitted).** `R/` folder
  mirroring all 7 Streamlit pages with the standard Shiny module pattern
  (`NS()` + `moduleServer()`, one module per page, shared `reactiveValues`
  state as the `st.session_state` analogue). Implemented per feasibility
  scope: Data Import (registry datasets via `nanoparquet` parquet loaders
  incl. the severity inner join, CSV upload with column mapping, kind-aware
  `validate_portfolio`) + Feature Engineering (cap/bin/log, spec-predictor
  append); pages 02, 04–07 are namespaced placeholders. Headless core checks
  reproduce the Python facts (freq 678,013 rows; sev join 26,444 rows, mean
  2,265.5); app smoke-tested on R 4.2.1 (HTTP 200, all tabs render).
  `R/run_app.bat` = EUC launcher (registry lookup → Program Files fallback);
  `R/README.md` documents the executable/packaging findings (no true .exe;
  R-Portable bundle recommended). New R user-library dep: `nanoparquet`.
  **Converted to tidyverse/pipe style 2026-08-02** (native `|>`, dplyr verbs,
  dynamic `"{col}_band" :=` mutate, tidyr pivot in validation, tibbles,
  readr CSV upload; deps dplyr/tidyr/purrr/readr/tibble were already
  installed). Core checks re-passed 12/12, app smoke re-passed.
  **Second launcher added 2026-08-02:** `R/run_app_desktop.bat` runs the
  server headless on port 8613 and opens Edge/Chrome app mode (`--app=`,
  native-window look); closing the window kills the server via
  Get-NetTCPConnection on the port (kill logic verified headlessly; the
  actual Edge window is Markus' manual check).
  **Electron wrapper added 2026-08-02** (`R/desktop/`): main.js spawns the R
  server (R lookup: bundled r-portable → env var → registry → Program
  Files), parses Shiny's random "Listening on" port, native BrowserWindow,
  taskkill /t on close; electron-builder targets portable .exe + NSIS
  installer, Shiny sources bundled via extraResources (R itself NOT bundled
  unless r-portable/ is dropped in). node_modules/dist/r-portable
  gitignored. **Built + verified 2026-08-02:** dev smoke (npm start) and
  packaged smoke both PASS (exit 0, no orphan Rscript); artifacts in
  `R/desktop/dist/`: portable `GLM Workbench 0.1.0.exe` (70.8 MB) + NSIS
  `GLM Workbench Setup 0.1.0.exe` (71 MB). Build gotcha documented: the
  winCodeSign cache had to be extracted manually (7za, symlink errors on
  darwin dylibs are ignorable) because Windows Developer Mode is off.
  Polish follow-ups: custom icon (default Electron icon used), decide
  whether to bundle R-Portable for zero-install.
  **Self-managing exe 2026-08-02** (after Markus' other-laptop test hit "R
  not found"): end-user contract is now "install R once, the exe manages
  the rest" — main.js preflight-checks the 9 required packages and
  auto-installs missing ones into R_LIBS_USER (first-run progress window
  with live log, resumes on rerun); R-not-found and setup-failure cases
  show copy-pasteable self-help HTML pages (links open externally);
  freMTPL2 parquet now bundled via extraResources so built-in datasets
  work on target machines; r-portable is also searched next to the
  portable exe (PORTABLE_EXECUTABLE_DIR). Auto-install flow E2E-tested via
  junction-based scratch R_LIBS_USER with tibble removed (installed,
  app booted, SMOKE_OK; real library untouched).
- [x] **Cross-machine verification — DONE 2026-08-02.** Markus copied the
  portable exe to his other laptop: first hit "R not found" (old dialog),
  then after the self-managing rebuild **confirmed it works there** (R
  installed by him once; packages auto-installed by the exe; bundled
  built-in datasets load).
- [x] **Converted to an R package `glmworkbenchR` — DONE 2026-08-25
  (commit 21b0571 together with the golem-ification, pushed; README install
  hints 9049c6c).** Markus' decisions: folder renamed `R/` →
  `glmworkbench_in_r/` (makes clear everything above/next to it is Python;
  underscores are illegal in R package names, so the package is
  `glmworkbenchR`), plain usethis/devtools workflow (roxygen, `load_all()`),
  NOT golem. Layout: `DESCRIPTION` (Imports declared, no `library()`/`source()`
  anywhere), roxygen-generated `NAMESPACE` + `man/`, `R/app_ui.R` +
  `R/app_server.R` + exported `run_app(data_dir, port, launch.browser)`,
  `R/fct_datasets.R` (+ `data_dir()` resolution: env
  `GLM_WORKBENCH_DATA_DIR` → option → `inst/extdata` → `../data/raw`),
  `R/fct_preprocessing.R`, `R/mod_*.R` (`@noRd`), `.Rproj`, `.Rbuildignore`,
  LICENSE (all rights reserved), testthat 3e suite (41 tests incl. real-data
  facts, skipped without parquet). Verified: `devtools::check()` 0 errors /
  0 warnings / 1 harmless NOTE (future timestamps), `devtools::install()`,
  headless smoke via the installed package AND via the launchers'
  `pkgload::load_all()` fallback, Electron dev smoke `SMOKE_OK`, and the
  first-run E2E (package removed → exe installs `glmworkbenchR` from the
  bundled source into a scratch `R_LIBS_USER` → app boots; real library
  untouched). Electron `main.js` now runs `glmworkbenchR::run_app()`, bundles
  the package source under `resources/pkg`, version-checks it against the
  installed one (reinstalls on version bump), sets `GLM_WORKBENCH_DATA_DIR`
  to the bundled parquet; launchers call `run_app()` (installed pkg or
  `load_all` fallback). README rewritten with a "Development in RStudio"
  section (load_all / document / test / check / install loop). Non-ASCII in
  R strings must be `\uXXXX` escapes (R CMD check portability) — done via a
  scratch helper script. Distributables rebuilt with `npm run dist`
  (portable + NSIS, 78 MB each); packaged portable exe smoke: exit 0, no
  orphan Rscript, package source + parquet present under `resources/`.
- [x] **golem-ified — DONE 2026-08-25 (same session, in commit 21b0571).** Markus
  reconsidered ("für langfristige Wartbarkeit ist golem ein guter
  Standard"): the package now follows the golem layout without a restart —
  `dev/01_start.R`, `02_dev.R` (ready-made `add_module()` lines for the five
  placeholder screens), `03_deploy.R`, `run_dev.R`; `R/app_config.R`
  (`app_sys()`, `get_golem_config()`); `inst/golem-config.yml`
  (default/production/dev, `data_dir` per env); `inst/app/www/custom.css`
  bundled via `golem_add_external_resources()` in `app_ui(request)`;
  `run_app(onStart, options, enableBookmarking, uiPattern, data_dir, ...)`
  via `golem::with_golem_options()` — Shiny run options now go through
  `options = list(port=, launch.browser=)`, `data_dir` is a golem opt read
  first by `data_dir()` (then env var → golem-config → extdata →
  ../data/raw). golem (>= 0.4.0) + config in Imports and in the exe's
  `REQUIRED_PACKAGES`; launchers/main.js call
  `print(glmworkbenchR::run_app(options = list(...)))`. golem 1.0.1 + config
  0.3.2 installed on the dev laptop. Verified again: 54 tests (13 golem
  recommended tests added), `check` 0/0/1 NOTE, headless smokes (installed +
  load_all), Electron dev smoke, first-run E2E (scratch lib install incl.
  golem deps) — all green; dist rebuilt (see STATE for the packaged smoke).
- [x] **RStudio walkthrough by Markus — DONE 2026-08-25 ("R studio hat
  geklappt").** He opened `glmworkbenchR.Rproj` and followed the README;
  R 4.2.1 asked to compile newer sources (frozen 4.2 CRAN binaries) →
  "Nein" (documented in README, commit 9049c6c). RStudio added
  `.Rproj.user` to the root `.gitignore` and rewrote `glmworkbenchR.Rproj`
  (harmless, committed with the session save). Longer-term: a current R
  (4.4/4.5) + `renv` pinning would remove the source-compile prompts.
- [ ] Feasibility follow-ups when Markus decides: custom app icon; `renv`
  (or DESCRIPTION-style) version pinning before wider sharing; bundle
  R-Portable for true zero-install (lookup order already prefers it);
  whether to extend the template to the model screens (`glm()`
  Poisson/Gamma equivalents); whether `R/` gets committed (currently fully
  untracked); if it ever goes server-side, convert to golem/package
  structure (modules are already golem-shaped — Markus knows this workflow
  from his former company).

## Backlog

- [ ] **Decide fate of `Shiny-to-React-R-Backend-Migration.docx`** (repo root,
  untracked, created 2026-07-30): interview material, not project code —
  Markus to say commit / gitignore / keep local. Source outline lives in the
  session transcript only.
- [ ] **Chapter 27 synthetic dataset generator** (`generate_chapter27_portfolio`,
  ~20k policies) + the educational features that need its hidden data-generating
  model: `compare_with_true_model` diagnostic, Dummy1/Dummy2 insignificance demo.
  Slots in behind the dataset spec as a second registered dataset (stubs already
  in `pricing_engine/`). Deferred 2026-07-25 in favour of real-data-first.
- [ ] **Regularisation (lasso/ridge/elastic net) — REDISCUSS with Markus**
  (2026-07-25: he wants to revisit this and eventually put it in somehow, ahead
  of the original V4 deferral; 2026-07-29: confirmed keep in backlog for now). Sketch when discussing: a "Regularisation"
  option on the Frequency Model page (none default / lasso / ridge / elastic
  net + alpha input) via statsmodels `fit_regularized`; lasso's zeroed
  coefficients would complement stepwise as a second selection lens. The
  trade-off to settle in the discussion: penalised fits return no std
  errors/p-values/CIs → needs a degraded coefficient view (coefficients +
  relativities only, explicit note about missing inference; Diagnostics
  CI-whisker chart and significance highlighting don't apply). Typical
  actuarial practice keeps pricing GLMs unpenalised for interpretability —
  decide framing (educational comparison feature vs. modelling tool).
- [ ] **Aggregate loss simulation (V3.x) — compound Poisson Monte Carlo**
  (discussed with Markus 2026-07-30; design written into
  `docs/architecture.md` "Modeling" + `docs/ui_screens.md` roadmap). Yearly
  loss DISTRIBUTION (percentiles, exceedance) on top of the two fitted
  models: N ~ Poisson(λ(x)), N Gamma severity draws per profile
  (mean exp(Xβ) + dispersion φ = `model.scale` → shape 1/φ, scale μφ), sum,
  repeat. Engine must surface the Gamma dispersion (today only the mean).
  Prerequisites: V2 slice 3 (`predict_severity`) + V3 per-kind model slots.
  Honest-caption requirements: freq⊥sev independence assumption; Gamma
  light tail understates extreme years (method demo, not a 1-in-200);
  spliced Pareto tail = further-future idea. Note: the EXPECTED yearly loss
  needs no simulation — λ·μ is the V3 pure premium itself.
- [ ] V2+ roadmap items (severity, pure premium, generic workbench, reports) —
  tracked in `PROJECT.md` / `docs/architecture.md`

## Project setup (done)

- [x] Scaffold — DONE 2026-07-25 (see STATE.md); revised same day for the V1
  rescope (pages 01–06) and again for freMTPL2 + dataset-spec design
- [x] GLM library decision — statsmodels (decision 4 in `PROJECT.md`)
- [x] V1 scope decision — Chapter 27 frequency-only (decision 5)
- [x] freMTPL2 as real dataset + generic dataset spec (decision 6); data
  downloaded + verified, pyarrow added
- [x] CLAUDE.md Quick Start filled
- [x] Doc drift (architecture.md repo layout) — fixed 2026-07-25
