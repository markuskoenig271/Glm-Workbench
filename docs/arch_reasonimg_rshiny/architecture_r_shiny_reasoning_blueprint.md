# Architecture Blueprint — Mortality Regression Shiny Rewrite

## 1. Goal

Rewrite the legacy **Mortality Regression** desktop application as a modern, maintainable **R Shiny application** while preserving the proven actuarial workflow and calculation logic.

The selected target architecture is **A+**:

> **Modular Shiny with a clean domain layer**

This deliberately avoids an unnecessary API or microservice layer for the initial implementation, while keeping the calculation logic independent enough that an API could be added later if needed.

---

## 2. Legacy Architecture

The current application is embedded into a local R installation.

```text
Rgui.exe
   ↓
Rprofile.site
   ↓
Custom "Swiss Life" menu
   ├── Reinsurance Simulations
   └── Mortality Regression
              ↓
      source("MortalityRegression.R")
```

Relevant files currently live inside the R installation:

```text
C:\Tools\R-4.6.1\
│
├── etc\
│   └── Rprofile.site
│
└── bin\x64\
    ├── Rgui.exe
    ├── MortalityRegression.R
    └── DeathSimulations.R
```

The legacy UI uses:

- `gWidgets2tcltk`
- `tkrplot`
- `sendmailR`
- `Rgui`
- global application state via `<<-`
- runtime package installation
- UI, state management, data preparation and GLM logic in one script

The existing application is therefore a **monolithic event-driven desktop R application**.

---

## 3. Existing Functional Workflow

The current user workflow is useful and should largely be preserved.

```text
Load mortality data
        ↓
Prepare data
        ↓
Define / transform variables
        ↓
Define exclusions
        ↓
Configure regression
        ↓
Run Poisson GLM
        ↓
Inspect results and plots
        ↓
Optimise / adjust groups
        ↓
Save factors / model results
```

Current main tabs:

```text
Mortality Regression
├── Data
├── Regression
├── Feedback
└── Log
```

### Data functions

- Load mortality data
- Load additional mortality data
- Define new model variables
- Center numeric variables
- Define data exclusions
- Remove rows with expected claims = 0
- Remove data fields
- Save prepared dataset
- Show raw / model / excluded data summaries

### Regression functions

- Update variable selection
- Define baseline values
- Run mortality regression
- Optimise groups
- Save regression factors
- Save model results
- Display regression table
- Display summary
- Select plots
- Display model plots

### Other functions

- Feedback / email
- Data transformation log

---

## 4. Target Architecture

The target architecture is intentionally simple:

```text
                Shiny Application
                       │
        ┌──────────────┴──────────────┐
        │                             │
     Data Module                Regression Module
        │                             │
        └──────────────┬──────────────┘
                       │
                Application State
                       │
                Domain Functions
                       │
        ┌──────────────┴──────────────┐
        │                             │
 Data Preparation              GLM / Optimisation
        │                             │
        └──────────────┬──────────────┘
                       │
                 R / stats::glm
```

The architecture has four conceptual layers.

### 4.1 UI Layer

Responsibilities:

- page layout
- navigation
- user inputs
- buttons
- tables
- plots
- notifications
- modal dialogs

Technology:

- Shiny
- `bslib`
- Bootstrap 5
- Shiny Modules

The UI layer must not contain actuarial calculation logic.

---

### 4.2 Shiny Module / Workflow Layer

Responsibilities:

- react to user events
- validate UI input
- call domain functions
- update application state
- render results

Typical pattern:

```r
observeEvent(input$run_model, {

  model <- fit_mortality_model(
    data = state$model_data,
    formula = model_formula()
  )

  state$model <- model
})
```

Modules should orchestrate work, not implement the calculations themselves.

---

### 4.3 Application State

The legacy application uses global variables and `<<-`.

The Shiny application should replace this with explicit session state.

Example:

```r
state <- reactiveValues(
  raw_data = NULL,
  model_data = NULL,
  excluded_data = NULL,
  model = NULL,
  model_results = NULL,
  model_list = list(),
  transformation_log = character()
)
```

Benefits:

- no hidden global state
- state is scoped to the user session
- easier debugging
- easier testing
- clearer dependencies

---

### 4.4 Domain Layer

The domain layer contains all reusable calculation and transformation logic.

It must be independent of Shiny.

It must not reference:

```r
input$
output$
session
observeEvent()
renderPlot()
renderTable()
gButton()
gGroup()
gFrame()
```

Example:

```r
fit_mortality_model <- function(data, formula) {

  glm(
    formula = formula,
    data = data,
    family = poisson(link = "log")
  )
}
```

Other likely domain functions:

```text
read_mortality_data()
validate_mortality_data()

create_derived_variable()
center_variable()
define_exclusions()
remove_zero_expected_rows()
remove_data_field()

fit_mortality_model()
define_baseline()
optimise_groups()

extract_regression_results()
calculate_regression_factors()
prepare_model_plot()

save_dataset()
save_model_results()
```

---

## 5. Proposed Project Structure

A pragmatic initial structure:

```text
mortality-regression/
│
├── app.R
│
├── R/
│   ├── mod_data.R
│   ├── mod_regression.R
│   ├── mod_results.R
│   ├── mod_log.R
│   │
│   ├── data_io.R
│   ├── data_preparation.R
│   ├── exclusions.R
│   ├── variables.R
│   ├── mortality_model.R
│   ├── group_optimization.R
│   ├── regression_results.R
│   └── persistence.R
│
├── tests/
│   └── testthat/
│
├── www/
│
├── renv.lock
└── README.md
```

If the project grows, the domain files can later be moved into a dedicated package.

---

## 6. Suggested Shiny Modules

### `mod_data`

Responsibilities:

```text
Import
Prepare
Transform
Exclude
Review dataset
```

Possible sub-sections:

```text
Data
├── Import
├── Transformations
├── Exclusions
└── Dataset Preview
```

---

### `mod_regression`

Responsibilities:

```text
Variable selection
Baseline selection
Model configuration
Run regression
Optimise groups
```

---

### `mod_results`

Responsibilities:

```text
Coefficient table
Model summary
Plots
Saved factors
Saved model results
```

This may initially remain part of `mod_regression` if the implementation remains compact.

---

### `mod_log`

Responsibilities:

- display transformation log
- display warnings
- optionally display model execution history

---

### Feedback

Feedback should probably no longer require a dedicated main tab unless business users consider it important.

It can instead be placed under:

```text
Help / About / Feedback
```

---

## 7. Mapping Legacy Code to New Architecture

| Legacy element | Classification | New location |
|---|---|---|
| `mainWin` | UI | `app.R` |
| `gnotebook()` | UI | Shiny navigation |
| `ggroup()` | UI | Shiny layout / cards |
| `gFrame()` | UI | `bslib::card()` |
| `gButton()` | UI | `actionButton()` |
| `gtable()` | UI | table output |
| `tkrplot()` | UI adapter | removed |
| `loadFile()` | mixed | module + `data_io.R` |
| `showData()` | mixed | module / presentation |
| `defineNewVariable()` | mixed | domain + modal UI |
| `centerVariable()` | domain | `variables.R` |
| `defineExclusions()` | mixed | domain + UI |
| `removeZeroRows()` | domain | `data_preparation.R` |
| `removeDataField()` | domain | `data_preparation.R` |
| `runRegression()` | heavily mixed | module + `mortality_model.R` |
| `glm(...)` | domain | `mortality_model.R` |
| `optimizeGroups()` | domain | `group_optimization.R` |
| `defineBaseline()` | domain / workflow | regression module + domain |
| regression plots | mixed | domain preparation + Shiny rendering |
| `sendmailR` | infrastructure | optional dedicated helper |
| `<<-` state | global state | `reactiveValues()` |
| runtime `install.packages()` | environment | removed |
| `Rprofile.site` startup | infrastructure | removed |

---

## 8. Refactoring Principle

The rewrite should **not** be performed as a mechanical Tcl/Tk-to-Shiny translation.

For example, this is not the main objective:

```text
gButton()
   ↓
actionButton()
```

The important transformation is:

```text
Legacy function
    │
    ├── UI code
    ├── global state
    ├── validation
    ├── calculation
    └── rendering

                ↓ refactor

Shiny module
    ├── user event
    ├── validation
    └── state update

Domain function
    └── calculation
```

---

## 9. Example: `runRegression()`

Legacy concept:

```r
runRegression <- function(...) {

  mod <<- glm(
    as.formula(modFormula),
    data = MODELDATA,
    family = poisson(link = "log")
  )

  # delete old GUI objects
  # create result table
  # create summary
  # create combobox
  # create plots
}
```

Target architecture:

### Domain

```r
fit_mortality_model <- function(data, formula) {

  glm(
    formula = formula,
    data = data,
    family = poisson(link = "log")
  )
}
```

### Result transformation

```r
extract_regression_results <- function(model) {
  ...
}
```

### Shiny orchestration

```r
observeEvent(input$run_regression, {

  state$model <- fit_mortality_model(
    data = state$model_data,
    formula = model_formula()
  )

})
```

### Rendering

```r
output$coefficients <- renderTable({
  req(state$model)
  extract_regression_results(state$model)
})
```

This separation is one of the central goals of the rewrite.

---

## 10. Dependency Management

The legacy application installs packages at runtime.

Example:

```r
if (!"tkrplot" %in% installed.packages()[,"Package"]) {
  install.packages("tkrplot")
}
```

This should be removed.

Use controlled dependency management instead, preferably:

```text
renv
```

The deployed application should have deterministic package versions.

---

## 11. Testing Strategy

Testing should focus especially on preserving calculation behaviour.

### Unit tests

For pure functions:

```text
data transformations
variable creation
exclusions
baseline handling
GLM setup
factor extraction
group optimisation
```

### Regression tests

For selected known datasets:

```text
Legacy result
      ≈
New application result
```

Important outputs to compare:

- coefficients
- fitted values
- regression factors
- model summaries
- exclusions
- saved model results

### Shiny tests

Only critical user flows need end-to-end tests:

```text
Load data
→ Prepare data
→ Configure model
→ Run regression
→ View result
```

---

## 12. Migration Strategy

A staged migration is preferable to rewriting everything at once.

### Phase 1 — Understand

Create a function inventory for `MortalityRegression.R`.

Classify every function as:

```text
UI
STATE
DOMAIN
IO
INFRASTRUCTURE
```

Identify dependencies and global variables.

---

### Phase 2 — Extract domain logic

Move pure calculation code into standalone functions without changing its behaviour.

First candidates:

```text
centerVariable
removeZeroRows
removeDataField
GLM fitting
result extraction
group optimisation
factor calculation
```

---

### Phase 3 — Connect to Shiny template

Implement the first vertical slice:

```text
Load data
→ Preview data
→ Select variables
→ Run regression
→ Display result
```

This provides an early working application.

---

### Phase 4 — Add remaining workflow

Add:

```text
derived variables
centering
exclusions
baseline definition
group optimisation
save factors
save model results
logging
```

---

### Phase 5 — Validate against legacy application

Run identical datasets through both systems.

Check functional equivalence before changing actuarial logic.

---

## 13. What Is Explicitly Out of Scope Initially

The first version should not introduce complexity without a concrete requirement.

Therefore do **not** initially require:

- React
- Angular
- separate JavaScript frontend
- REST API
- `plumber`
- microservices
- separate calculation deployment
- distributed processing

These remain possible future extensions.

---

## 14. Future Extension Path

Because domain logic is independent of Shiny, a future API can be added without rewriting the calculation engine.

Possible later architecture:

```text
Shiny
   ↓
plumber API
   ↓
Mortality domain functions
```

or:

```text
Shiny ─┐
       ├── Mortality calculation package
Batch ─┤
       │
API ───┘
```

This is why separating domain logic from Shiny is worthwhile even though no API is required today.

---

## 15. Architectural Decision

### Selected approach

> **A+ — Modular Shiny with clean domain functions and explicit application state**

### Rationale

The application is:

- relatively small
- used by a limited internal specialist audience
- based on an existing R calculation workflow
- not currently required to serve multiple external clients
- suitable for a direct Shiny implementation

A dedicated service or API layer would currently add deployment, debugging and maintenance overhead without a clear benefit.

At the same time, domain logic will remain independent of Shiny so that future reuse remains possible.

---

## 16. Guiding Principle

The central principle for the rewrite is:

> **Preserve the actuarial workflow and calculation behaviour, replace the technical coupling.**

The legacy application already has a useful business workflow.

The rewrite should therefore focus on:

```text
Legacy UI          → modern Shiny UI
Global variables   → explicit session state
Mixed functions    → separated domain functions
R installation     → self-contained application
Runtime installs   → controlled dependencies
Untested logic     → regression-tested calculation kernel
```

The result should be a compact, maintainable Shiny application rather than a larger platform architecture.
