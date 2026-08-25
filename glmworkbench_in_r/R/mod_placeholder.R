# Generic placeholder module for screens outside the feasibility scope
# (Data Exploration, Frequency Model, Diagnostics, Prediction, Severity Model).
# Instantiated once per page with its own namespace id -- demonstrates module
# reuse; each placeholder is later replaced by a real module file.

#' Placeholder module UI
#' @param id Module id.
#' @param title Page title.
#' @noRd
mod_placeholder_ui <- function(id, title) {
  ns <- NS(id)
  div(
    class = "container-fluid py-3",
    h3(title),
    div(
      class = "alert alert-secondary",
      "Not part of the feasibility slice \u2014 this screen exists to mirror the",
      "Streamlit app's page structure and will be implemented as its own",
      "module if the feasibility study is taken further."
    ),
    uiOutput(ns("context"))
  )
}

#' Placeholder module server
#' @param id Module id.
#' @param state Shared `reactiveValues` app state.
#' @noRd
mod_placeholder_server <- function(id, state) {
  moduleServer(id, function(input, output, session) {
    output$context <- renderUI({
      if (is.null(state$portfolio)) {
        p(em("No dataset loaded."))
      } else {
        p(em(sprintf(
          "Active dataset: %s (%s rows, kind: %s)",
          state$spec$label,
          format(nrow(state$portfolio), big.mark = ","),
          state$spec$kind
        )))
      }
    })
  })
}
