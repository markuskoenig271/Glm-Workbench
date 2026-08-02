# Home page module — workflow status overview (mirrors app.py Home).

mod_home_ui <- function(id) {
  ns <- NS(id)
  div(
    class = "container-fluid py-3",
    h3("GLM Workbench — R Shiny feasibility study"),
    p(
      "Template mirroring the Streamlit app's screens with the standard Shiny",
      "module pattern (namespaced UI + server modules, shared reactive state).",
      "Feasibility scope: Data Import and Feature Engineering / cleansing;",
      "the modelling screens are namespaced placeholders."
    ),
    h4("Workflow status"),
    tableOutput(ns("status"))
  )
}

mod_home_server <- function(id, state) {
  moduleServer(id, function(input, output, session) {
    output$status <- renderTable({
      loaded <- !is.null(state$portfolio)
      data_status <- if (loaded) {
        sprintf(
          "Loaded: %s (%s rows)",
          state$spec$label, format(nrow(state$portfolio), big.mark = ",")
        )
      } else {
        "No dataset loaded"
      }
      tibble(
        Page = c(
          "01 Data Import", "02 Data Exploration", "03 Feature Engineering",
          "04 Frequency Model", "05 Diagnostics", "06 Prediction",
          "07 Severity Model"
        ),
        Status = c(
          data_status,
          "Placeholder (not in feasibility scope)",
          if (loaded) "Available" else "Load a dataset first",
          rep("Placeholder (not in feasibility scope)", 4)
        )
      )
    })
  })
}
