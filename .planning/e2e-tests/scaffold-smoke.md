# E2E — Scaffold smoke test

Change under test: initial project scaffold, revised for the V1 scope
(Chapter 27 frequency-only — docs/car-insurance.md; no features yet).
BA scenarios: as a user I can start the app, land on Home (which states the V1
scope and roadmap), and see the six V1 workflow pages in the sidebar so I know
where each step of the frequency workflow will live.

## TC1 — App starts and serves the Home screen

1. `uv run streamlit run app.py --server.headless true --server.port 8599`
2. GET `http://localhost:8599` → HTTP 200
3. Home shows the title "GLM Workbench", the V1/Chapter-27 caption, workflow
   status, and the version roadmap

## TC2 — All 6 V1 workflow pages are registered

1. With the app from TC1 running, the sidebar lists, in order:
   Data Import, Data Exploration, Feature Engineering, Frequency Model,
   Diagnostics, Prediction
2. Severity Model, Pure Premium, and Reports do NOT appear (V2+ per roadmap)
3. Each page opens without error and shows its "Not yet implemented" notice

## Execution notes

- Streamlit renders client-side, so the HTTP check (TC1 step 2) verifies serving;
  page registration (TC2) is verified via the `pages/` file listing that Streamlit
  maps 1:1 into the sidebar. Full Playwright automation starts with the first real
  UI feature (browser tooling not yet part of the scaffold).

## Results

- 2026-07-25 (initial scaffold, 9 pages): TC1 PASS (HTTP 200, clean server log);
  TC2 PASS by construction.
- 2026-07-25 (V1 rescope, 6 pages): TC1 PASS (HTTP 200, server log clean — no
  errors/tracebacks); TC2 PASS by construction (exactly 6 files in `pages/`,
  numbered 01–06 in the workflow order above; Severity/Pure Premium/Reports
  files deleted).
