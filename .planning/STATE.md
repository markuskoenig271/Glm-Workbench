# Project State

Rolling "where I left off" file (committed). Overwritten each session.
Read this + `TODO.md` at the start of every session. See `PROJECT.md` for the spec.

---

## Last updated: 2026-09-02 (session 7 — R prototype: architecture review vs. ChatGPT blueprint, CRAN snapshot pinning, renv decision closed)

## Headline

Short R-prototype session (Python app untouched). Two outcomes:

1. **Blueprint review:** Markus stored a ChatGPT-derived architecture
   blueprint for the LEGACY Swiss Life "Mortality Regression" rewrite at
   `docs/arch_reasonimg_rshiny/architecture_r_shiny_reasoning_blueprint.md`
   (UNTRACKED — his file, commit not requested). Assessment delivered in
   chat: its target architecture ("A+ — Modular Shiny with clean domain
   layer") matches glmworkbenchR almost 1:1 (modules orchestrate /
   `fct_*` domain layer / `reactiveValues` state / bslib / no API);
   glmworkbenchR is one maturity level AHEAD (package+golem from the
   start, config layer, EUC/Electron deployment — all absent from the
   blueprint). Flagged deltas: golem-first instead of "app.R now, package
   later"; runtime installs are fine as a controlled installer-shell
   preflight (vs. the blueprint's §10 ban, which targets install calls in
   app logic); renv → see 2. Offered (unanswered): fold these deltas into
   the blueprint doc as an addendum.

2. **CRAN snapshot pinning — the renv backlog point is CLOSED (Markus'
   decisions).** His hard end-user contract: "R installed (target 4.6) +
   CRAN access, NOTHING more, then run the exe." Package/golem is no
   problem for that (exe installs the bundled source, pure R, no Rtools —
   already E2E-proven). Instead of renv (restore of old versions often
   needs source compilation → would break the no-Rtools contract), the
   exe's auto-install now pins a **dated Posit Package Manager snapshot**:
   `CRAN_SNAPSHOT = 'https://packagemanager.posit.co/cran/2026-09-01'` in
   `desktop/main.js` (env override `GLM_WORKBENCH_CRAN` for
   proxies/internal mirrors; bump the date only deliberately + re-test).
   README: manual-install line uses the same URL; EUC section documents
   the decision + rationale; old renv recommendation replaced (renv =
   dev-machine-only option). TODO backlog entry resolved.

Verification chain (all green, 2026-09-02): snapshot serves 19,147 Windows
binaries even for dev R 4.2.1 (target R 4.6 a fortiori); scratch-lib
install through the exact installer steps (`INSTALL_OK praise 1.0.0`,
binary zip from the snapshot); `node --check` OK; Electron dev smoke
`SMOKE_OK`; **`npm run dist` rebuilt** portable (74.8 MB) + NSIS (75 MB);
packaged portable exe smoke exit 0, no orphan Rscript; snapshot URL
grep-confirmed inside the packaged `app.asar`.

**COMMITTED 2026-09-02 (Markus' call, right after the save):**
`e9fadbe feat(r-desktop): pin package installs to dated Posit CRAN
snapshot` (main.js + README) and the blueprint doc under
`docs/arch_reasonimg_rshiny/` (docs commit together with these planning
touch-ups). Working tree clean.

## Working agreements / lessons (keep honoring these)

- Change Validation Workflow every slice on the MAIN app; decisions for
  Markus via AskUserQuestion ONE AT A TIME (his explicit preference).
- Commits only when Markus says so; conventional commits, no Co-Authored-By.
  Session-save commit covers `.planning/` only (precedent 8a34b17).
- Respond in German; code/commits/docs stay English.
- Never delete `data/workbench.db` OR the `models/` pickles; runners append
  real runs + pickles by design (~57 runs in the DB).
- statsmodels: `save(remove_data=True)` mutates in place (deep-copy first);
  data-stripped results predict and report coefficients/criteria but have no
  resid/fittedvalues and `summary()` raises.
- Playwright/Streamlit lessons consolidated in `e2e/README.md`.
- Bash-tool heredocs can mangle non-ASCII — prefer Write/Edit.
- python-docx via `uv run --with python-docx` for one-off docx generation.
- R side: exe smoke = `GLM_WORKBENCH_SMOKE_TEST=1`, criterion exit 0 + no
  orphan Rscript; P3M snapshots serve Windows binaries even for older R.

## Open / next steps

1. **Blueprint addendum (offered, unanswered):** fold the glmworkbenchR
   deltas (golem-first, installer-shell preflight vs. §10, snapshot-pinning
   instead of renv, config layer, deployment chapter) into
   `docs/arch_reasonimg_rshiny/architecture_r_shiny_reasoning_blueprint.md`.
2. **Markus' manual walkthrough** along
   `manuals/glm-workbench_user_manual.docx` (started session 6; severity /
   persistence / quote chapters remaining) + deferred/manual E2E TCs.
3. **Manual addendum (his call, still unanswered):** Feature Engineering on
   the severity dataset + the G6 rebuild-on-both-frames caveat.
4. **V3.x aggregate-loss simulation** — design in `docs/architecture.md`
   "Modeling"; all prerequisites delivered; needs the Gamma dispersion
   surfaced from the engine. Natural next Python milestone — confirm.
5. Educational side quest: Negative Binomial vs Poisson AIC comparison.
6. Backlog unchanged otherwise (regularisation rediscussion, synthetic
   Chapter 27 generator, V2.x notes, remaining R follow-ups: custom icon,
   bundle R-Portable, extend template to model screens).

## Architecture drift check (per CLAUDE.md save protocol)

No drift: this session touched only `glmworkbench_in_r/` (deliberately
outside `docs/architecture.md`) and its own README, which was updated
in-session together with the code change. The new
`docs/arch_reasonimg_rshiny/` blueprint is a reference document for the
LEGACY-tool rewrite, not this repo's architecture — no sync needed.
