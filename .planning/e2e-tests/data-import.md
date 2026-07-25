# E2E — Data Import slice (load_portfolio + pages/01_Data_Import.py + Home status)

Change under test: the app's first real UI feature. Engine:
`load_portfolio(source)` in `pricing_engine/data.py` — CSV loader accepting a
path or a file-like object (Streamlit upload), missing path → friendly
`FileNotFoundError`. UI: `pages/01_Data_Import.py` with a source radio
("Built-in dataset" / "CSV upload"); built-in path loads via the registry into
`st.session_state["portfolio"]` / `st.session_state["spec"]` with a success
message "Loaded <label>: <n> rows"; CSV path goes upload → preview →
column-mapping widgets (target selectbox, optional offset selectbox with
"<none>", predictors multiselect) → "Use this dataset" builds an ad-hoc
`DatasetSpec` and stores it the same way. Once loaded (either path): Preview
section (`df.head(20)` dataframe + "N rows × M columns" caption) and a
Validation report section rendering `validate_portfolio` findings as
`st.warning` lines, or `st.success` "No issues found — portfolio is ready for
modelling." when empty. Home (`app.py`): workflow status shows the active
dataset label + row count when loaded, else "No dataset loaded yet — start
with Data Import." Errors from the engine (missing Parquet → curl hint) must
surface as `st.error`, never as a traceback.

BA scenarios (the user is an actuary learning GLMs, working through the
Chapter-27 frequency workflow on real data):

- As an actuary, I open Data Import, see the built-in freMTPL2 dataset already
  selected, click one button, and the full 678k-policy portfolio is loaded —
  no file paths, no code. The success message tells me what I got and how many
  rows, so I trust the load actually happened.
- As a learner, I immediately see WHAT I loaded: a preview of the first rows
  and a "rows × columns" caption, so I can sanity-check columns like ClaimNb
  and Exposure before modelling.
- As a learner, the validation verdict is unambiguous in both directions: the
  pristine built-in dataset tells me in green that the portfolio is ready for
  modelling; a broken portfolio tells me in yellow, per finding, exactly which
  column is wrong and why (negative claim count, missing values, bad
  exposure) — the report teaches, it doesn't just gatekeep.
- As an actuary with my own data, I upload a CSV, see a preview, map which
  column is the claim count (target), optionally which is the exposure
  (offset), pick predictors, and confirm — after which the app treats my
  portfolio exactly like the built-in one (same preview, same validation, same
  session state, same Home status).
- As a returning user, the Home page confirms what is currently active: after
  loading, it names the dataset and its row count; before loading anything it
  points me to the Data Import screen instead of showing a blank or broken
  status — I always know where I am in the workflow.
- As someone on a fresh clone without `data/raw/*.parquet`, clicking "Load
  dataset" shows a red error box containing the exact curl command to fetch
  the file — a Streamlit traceback here would be a failure of the whole
  "errors teach" principle.

Test Agent notes from the BA interview: a UI now exists, so per CLAUDE.md the
cases run via **Playwright (Python sync API)** against the running Streamlit
app. Assumptions and mechanics:

- App started headless on port 8598 before the run, e.g.
  `uv run streamlit run app.py --server.port 8598 --server.headless true`
  from the repo root (real `data/raw/*.parquet` files present). Pages are
  reachable directly by URL: Home `http://localhost:8598/`, Data Import
  `http://localhost:8598/Data_Import`.
- Streamlit renders `st.button` as a real `<button>` with its label text —
  `page.get_by_role("button", name="Load dataset")` works. Success / warning /
  error blocks contain their message text — assert with
  `expect(page.get_by_text(...)).to_be_visible()`. The sidebar link to the
  main page is labelled **"app"**.
- **Session state is per browser tab (websocket session).** TC3 (Home reflects
  the load) must navigate within the SAME page object used for TC2 — via the
  sidebar "app" link or `page.goto` in the same context/tab. A new context is
  a fresh session (which is exactly what TC1 exploits).
- `st.dataframe` renders as a canvas-based grid (glide-data-grid); asserting
  cell contents is unreliable. Assert the preview via the "rows × columns"
  caption text and the presence of the dataframe container instead.
- Selectbox / multiselect are BaseWeb widgets and fiddly to automate. All
  automated TCs are designed to work with **defaults**: the registry has one
  dataset (preselected), and the CSV fixture is built so the DEFAULT column
  mapping already exercises the validator. **Assumption:** the target
  selectbox defaults to the first CSV column; the offset selectbox defaults to
  "<none>"; the predictors multiselect defaults to empty. If the
  implementation's defaults differ, adjust the fixture column order first; if
  a selectbox interaction becomes unavoidable, click it and use keyboard
  (type + Enter) rather than hunting dropdown DOM. Full remapping is
  explicitly deferred to a manual case (TC5).
- File upload: `page.set_input_files("input[type=file]", <path>)` on the
  `st.file_uploader`'s hidden input. Write the CSV fixture to a temp path
  before the run.
- After any click/upload, Streamlit reruns asynchronously — rely on Playwright
  auto-waiting `expect(...)` assertions (generous timeout, e.g. 15 s for the
  678k-row load), never on fixed sleeps.
- The missing-data-file path (TC6) cannot be triggered from the UI without
  mutating the running app's working data, so it is split: a deterministic
  Python-level engine check (the UI wraps that exact exception in `st.error`),
  plus an OPTIONAL manual UI variant with a rename-the-parquet recipe.

## TC1 — Fresh session: Home shows the "no dataset" status

1. Open a **new browser context**, `page.goto("http://localhost:8598/")`,
   wait for the app to render.
2. Expected: the workflow status contains
   `No dataset loaded yet — start with Data Import.` and does NOT contain the
   freMTPL2 label or any row count. (Fresh context = fresh Streamlit session,
   so this also proves the status is session-driven, not hardcoded.)

## TC2 — Happy path: one-click built-in load, preview, clean validation

1. In the same context, `page.goto("http://localhost:8598/Data_Import")`.
2. Confirm the source radio shows "Built-in dataset" selected by default and
   the dataset selectbox already shows the freMTPL2 label (only registry
   entry — no selectbox interaction needed).
3. Click the button `Load dataset`.
4. Expected (allow up to ~15 s for the 678k-row load):
   - Success message visible containing
     `Loaded freMTPL2 — French motor TPL, frequency (678k policies)` and
     `678013` (per the spec'd format "Loaded <label>: <n> rows"; if the row
     count is thousands-separated, match `678` + `013` loosely and note it in
     Results).
   - Preview section visible: a dataframe grid plus a caption containing
     `678013 rows` and `12 columns` (same loose-match caveat).
   - Validation report shows the success message
     `No issues found — portfolio is ready for modelling.` and NO warning
     blocks.

## TC3 — Home reflects the active dataset (same session)

1. Immediately after TC2, in the SAME tab, click the sidebar link `app` (or
   `page.goto("http://localhost:8598/")` in the same tab).
2. Expected: the workflow status now names the active dataset — contains the
   freMTPL2 label and `678013` (row count) — and no longer shows
   `No dataset loaded yet`.

## TC4 — CSV upload of a deliberately broken file (default mapping)

1. Write this fixture to a temp path (e.g. scratchpad `broken_portfolio.csv`)
   — first column is the target under the default-mapping assumption; row 2
   has a negative claim count, row 3 an empty (NaN) claim count:

   ```csv
   ClaimNb,Exposure,DrivAge
   1,0.5,40
   -1,0.7,30
   ,0.3,55
   ```

2. `page.goto("http://localhost:8598/Data_Import")` in a fresh tab or the
   same one; select the radio option `CSV upload` (radio options are
   labelled text — click `page.get_by_text("CSV upload")` within the radio
   group).
3. `page.set_input_files("input[type=file]", <fixture path>)`.
4. Expected: an upload preview appears (dataframe grid for the 3-row file);
   the mapping widgets render — verify target selectbox shows `ClaimNb`
   (default = first column, per assumption), offset shows `<none>`,
   predictors empty. If the target default is a different column, note it in
   Results and select `ClaimNb` via click + type + Enter before proceeding.
5. Click the button `Use this dataset`.
6. Expected:
   - The dataset is stored: Preview section shows the data with a caption
     containing `3 rows` (columns count per implementation — the CSV has 3).
   - Validation report shows **warning** lines (not success), including one
     containing `ClaimNb` and `negative value(s)` and one containing
     `ClaimNb` and `missing value(s)` — the exact wording produced by
     `validate_portfolio` ("Target 'ClaimNb' has 1 negative value(s)",
     "Column 'ClaimNb' has 1 missing value(s)").
   - The clean-success message is NOT shown.
7. Optional follow-up (same tab): navigate to Home via the sidebar `app`
   link — the status should now reflect the ad-hoc CSV dataset (its label and
   `3` rows), proving both paths store state identically.

## TC5 — Full CSV column remapping (target + offset + predictors) — MANUAL / DEFERRED

Automating three BaseWeb widgets (change target away from the default, pick a
real offset instead of `<none>`, multi-select predictors) is brittle in
Playwright, so this case is **specified for manual execution** (or a later
dedicated widget-automation harness):

1. Upload a well-formed CSV (e.g. the TC4 fixture with the negative/blank rows
   fixed).
2. Map: target = `ClaimNb`, offset = `Exposure`, predictors = [`DrivAge`].
3. Click `Use this dataset`.
4. Expected: validation is clean ("No issues found…"); preview caption matches
   the file; Home shows the dataset. Then re-upload with the `DrivAge` column
   deleted from the file after mapping it as a predictor is NOT reachable
   (mapping widgets only offer existing columns) — the "missing required
   column" finding therefore stays an engine-level guarantee (covered by the
   previous slice's TC6 in `dataset-spec-loaders.md`), which is acceptable:
   the UI can only build specs from columns that exist at mapping time.

Record in Results whether this was executed manually or deferred.

## TC6 — Missing data file: the curl hint surfaces as an error, not a traceback

Engine-level (deterministic, automated — this is the exact exception the page
wraps in `st.error`):

1. Run via `uv run python <tempfile.py>` (or `.venv\Scripts\python.exe` in
   the sandbox) from the repo root:

   ```python
   from pricing_engine.data import load_fremtpl2_freq, load_portfolio
   try:
       load_fremtpl2_freq("data/raw/does_not_exist.parquet")
       raise SystemExit("FAIL: no exception raised")
   except FileNotFoundError as e:
       msg = str(e)
       assert "curl" in msg and "data.openml.org" in msg, msg
   try:
       load_portfolio("data/does_not_exist.csv")
       raise SystemExit("FAIL: no exception raised")
   except FileNotFoundError as e:
       msg = str(e)
       assert "does_not_exist.csv" in msg, msg
       assert "Traceback" not in msg
   print("PASS")
   ```

2. Expected: prints `PASS` — both the Parquet loader (curl +
   data.openml.org hint) and the new CSV `load_portfolio` raise friendly
   `FileNotFoundError`s naming the path.

OPTIONAL manual UI variant (only if safe to disturb the running app): stop
the app, rename `data/raw/freMTPL2freq.parquet` to `.bak`, restart the app,
open Data Import, click `Load dataset` — expected: a red `st.error` box whose
text contains `curl` and `data.openml.org`, and NO Streamlit exception
traceback ("Traceback" must not appear on the page). Rename the file back and
restart afterwards. Record in Results whether the UI variant was run or only
the engine-level check.

## TC7 — load_portfolio round-trip: CSV path and file-like both work (engine)

1. Run via `uv run python <tempfile.py>` from the repo root, using the TC4
   fixture CSV:

   ```python
   import io
   from pricing_engine.data import load_portfolio
   path = r"<fixture path>\broken_portfolio.csv"
   df_path = load_portfolio(path)
   assert df_path.shape[0] == 3, df_path.shape
   assert "ClaimNb" in df_path.columns, df_path.columns
   with open(path, "rb") as fh:
       df_file = load_portfolio(io.BytesIO(fh.read()))  # what st.file_uploader hands over
   assert df_file.shape == df_path.shape
   print("PASS", df_path.shape)
   ```

2. Expected: prints `PASS (3, 3)` — the same loader serves both the
   path-based and the upload (file-like) route, so the UI needs no special
   casing.

## Execution notes

- Prerequisites: real `data/raw/freMTPL2freq.parquet` present (7.5 MB;
  otherwise fetch via the README curl command first — TC2/TC3 exercise real
  data by design); Playwright for Python installed with a Chromium browser
  (`uv run playwright install chromium` if missing).
- Start the app once for the whole run:
  `uv run streamlit run app.py --server.port 8598 --server.headless true`
  (background process; kill it after the run). Give it a few seconds to boot
  before the first `goto`.
- Run TC1→TC2→TC3 in ONE browser context/tab in that order (TC3 depends on
  TC2's session state; TC1 must come first while the session is fresh — or
  use a separate fresh context for TC1). TC4 may reuse the tab (its upload
  replaces the session dataset) or use a fresh one.
- Write the Playwright script(s) and the CSV fixture to the session
  scratchpad, not the repo. Use `playwright.sync_api` with
  `expect(...)`-style auto-waiting assertions; set a default timeout of
  ~15000 ms for the post-click assertions in TC2.
- Exact-text caveats: the spec'd messages are
  "Loaded <label>: <n> rows", "N rows × M columns",
  "No issues found — portfolio is ready for modelling.",
  "No dataset loaded yet — start with Data Import." If the implementation's
  final wording differs trivially (punctuation, thousands separators), match
  loosely on the distinctive fragments and record the actual text in Results;
  a MISSING message or a traceback on the page is a FAIL, wording drift is
  not.
- TC4's default-mapping assumption (target = first column, offset = <none>,
  predictors = empty) must be verified in step 4 before clicking — if it does
  not hold, either adjust the fixture column order or do the minimal
  click+type+Enter selectbox interaction, and document which in Results.

## Results

- 2026-07-25 — **executed TCs ALL PASSED** (Playwright 1.61 / Chromium headless,
  app on port 8598, real data): TC1, TC2, TC3, TC4 (incl. optional Home
  follow-up) via UI; TC6, TC7 engine-level. **TC5 DEFERRED/manual** per plan
  (BaseWeb remapping automation); TC6's optional manual UI variant not run
  (engine check covers the wrapped exception; the page renders it via
  `st.error`).
- Wording observations (loose-match per Execution notes, no drift failures):
  row counts render thousands-separated ("678,013 rows"); preview caption is
  "Active dataset: <label> — N rows × M columns".
- Deviations from the plan's assumptions, found during execution:
  - **Predictors multiselect defaults to ALL remaining columns**, not empty
    (implementation choice — friendlier default). TC4 unaffected: the
    "Target 'ClaimNb' has 1 negative value(s)" finding proves the target
    defaulted to the first column; the mapping-widget DOM pre-checks were
    dropped as redundant (BaseWeb combobox values are not readable via
    `get_by_text`; hidden glide-data-grid header cells shadow column names).
  - **TC3 MUST navigate via the sidebar link, not `page.goto`** — confirmed
    live: a full reload opens a new Streamlit session and drops
    `st.session_state` (the plan's warning was correct; goto variant fails).
    UX consequence worth knowing: a browser refresh clears the loaded dataset.
  - Strict-mode: text fragments appearing in both the success message and the
    caption need `.first`.
