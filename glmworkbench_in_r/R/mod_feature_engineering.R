# Feature Engineering / cleansing module -- mirrors pages/03_Feature_Engineering.py.
# Cap a column (e.g. Exposure at 1.0), quantile/uniform binning to <col>_band,
# log transform to <col>_log. Mutations write back to the shared state; new
# engineered columns are appended to the spec's predictor list.

#' Feature Engineering module UI
#' @param id Module id.
#' @noRd
mod_feature_engineering_ui <- function(id) {
  ns <- NS(id)
  div(class = "container-fluid py-3", uiOutput(ns("page")))
}

#' Feature Engineering module server
#' @param id Module id.
#' @param state Shared `reactiveValues` app state.
#' @noRd
mod_feature_engineering_server <- function(id, state) {
  moduleServer(id, function(input, output, session) {
    ns <- session$ns

    numeric_cols <- reactive({
      req(state$portfolio)
      state$portfolio |>
        select(where(is.numeric)) |>
        names()
    })

    output$page <- renderUI({
      if (is.null(state$portfolio)) {
        return(tagList(
          h3("Feature Engineering"),
          div(class = "alert alert-info", "Load a dataset on the Data Import page first.")
        ))
      }
      offset_default <- if (!is.null(state$spec$offset) &&
        state$spec$offset %in% numeric_cols()) {
        state$spec$offset
      } else {
        numeric_cols()[1]
      }
      tagList(
        h3("Feature Engineering"),
        fluidRow(
          column(
            4,
            h4("Cap a column"),
            p(em("e.g. cap Exposure at 1.0 policy-years")),
            selectInput(ns("cap_col"), "Column",
              choices = numeric_cols(),
              selected = offset_default
            ),
            numericInput(ns("cap_value"), "Cap at", value = 1, step = 0.1),
            actionButton(ns("apply_cap"), "Apply cap", class = "btn btn-primary")
          ),
          column(
            4,
            h4("Bin a numeric variable"),
            p(em("creates <column>_band and adds it to the predictors")),
            selectInput(ns("bin_col"), "Column", choices = numeric_cols()),
            numericInput(ns("bin_n"), "Number of bins", value = 5, min = 2, max = 20),
            radioButtons(ns("bin_method"), "Method",
              choices = c("quantile", "uniform"), inline = TRUE
            ),
            actionButton(ns("apply_bin"), "Create band", class = "btn btn-primary")
          ),
          column(
            4,
            h4("Log transform"),
            p(em("creates <column>_log and adds it to the predictors")),
            selectInput(ns("log_col"), "Column", choices = numeric_cols()),
            actionButton(ns("apply_log"), "Create log column", class = "btn btn-primary")
          )
        ),
        hr(),
        h4("Active spec"),
        tableOutput(ns("spec_summary")),
        h4("Portfolio preview (first 50 rows)"),
        DT::DTOutput(ns("preview"))
      )
    })

    append_predictor <- function(new_col) {
      spec <- state$spec
      if (!new_col %in% spec$predictors) {
        spec$predictors <- c(spec$predictors, new_col)
        state$spec <- spec
      }
    }

    observeEvent(input$apply_cap, {
      result <- tryCatch(
        cap_column(state$portfolio, input$cap_col, input$cap_value),
        error = function(e) e
      )
      if (inherits(result, "error")) {
        showNotification(conditionMessage(result), type = "error")
        return(invisible(NULL))
      }
      state$portfolio <- result
      showNotification(
        sprintf("Capped %s at %s", input$cap_col, input$cap_value),
        type = "message"
      )
    })

    observeEvent(input$apply_bin, {
      result <- tryCatch(
        bin_numeric(state$portfolio, input$bin_col, input$bin_n, input$bin_method),
        error = function(e) e
      )
      if (inherits(result, "error")) {
        showNotification(conditionMessage(result), type = "error")
        return(invisible(NULL))
      }
      state$portfolio <- result
      append_predictor(paste0(input$bin_col, "_band"))
      showNotification(
        sprintf(
          "Created %s_band (%s, %d bins)",
          input$bin_col, input$bin_method, input$bin_n
        ),
        type = "message"
      )
    })

    observeEvent(input$apply_log, {
      result <- tryCatch(
        log_transform(state$portfolio, input$log_col),
        error = function(e) e
      )
      if (inherits(result, "error")) {
        showNotification(conditionMessage(result), type = "error")
        return(invisible(NULL))
      }
      state$portfolio <- result
      append_predictor(paste0(input$log_col, "_log"))
      showNotification(sprintf("Created %s_log", input$log_col), type = "message")
    })

    output$spec_summary <- renderTable({
      req(state$spec)
      spec <- state$spec
      tibble(
        Field = c("Dataset", "Kind", "Target", "Offset", "Predictors", "Rows"),
        Value = c(
          spec$label,
          spec$kind,
          spec$target,
          if (is.null(spec$offset)) "none" else spec$offset,
          paste(spec$predictors, collapse = ", "),
          format(nrow(state$portfolio), big.mark = ",")
        )
      )
    })

    output$preview <- DT::renderDT({
      req(state$portfolio)
      state$portfolio |>
        slice_head(n = 50) |>
        DT::datatable(options = list(scrollX = TRUE, pageLength = 10), rownames = FALSE)
    })
  })
}
