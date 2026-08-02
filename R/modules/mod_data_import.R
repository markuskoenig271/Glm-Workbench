# Data Import module — mirrors pages/01_Data_Import.py.
# Built-in registry datasets or ad-hoc CSV upload with column mapping;
# writes state$portfolio + state$spec shared with all other pages.

mod_data_import_ui <- function(id) {
  ns <- NS(id)
  div(
    class = "container-fluid py-3",
    h3("Data Import"),
    p(
      "Load a built-in dataset or upload a CSV. The loaded portfolio and its",
      "dataset spec are shared with every other page via the app-level state."
    ),
    radioButtons(
      ns("source"), "Source",
      choices = c("Built-in dataset" = "builtin", "CSV upload" = "csv"),
      inline = TRUE
    ),
    conditionalPanel(
      condition = "input.source == 'builtin'", ns = ns,
      selectInput(ns("dataset"), "Dataset", choices = dataset_choices(), width = "480px"),
      actionButton(ns("load_builtin"), "Load dataset", class = "btn btn-primary")
    ),
    conditionalPanel(
      condition = "input.source == 'csv'", ns = ns,
      fileInput(ns("csv_file"), "CSV file", accept = ".csv"),
      uiOutput(ns("mapping_ui"))
    ),
    hr(),
    uiOutput(ns("active_dataset")),
    h4("Validation report"),
    tableOutput(ns("validation")),
    h4("Preview (first 100 rows)"),
    DT::DTOutput(ns("preview"))
  )
}

mod_data_import_server <- function(id, state) {
  moduleServer(id, function(input, output, session) {
    ns <- session$ns

    observeEvent(input$load_builtin, {
      result <- withProgress(message = "Loading dataset…", value = 0.5, {
        tryCatch(load_dataset(input$dataset), error = function(e) e)
      })
      if (inherits(result, "error")) {
        showNotification(conditionMessage(result), type = "error", duration = 12)
        return(invisible(NULL))
      }
      state$portfolio <- result$portfolio
      state$spec <- result$spec
      showNotification(
        sprintf(
          "Loaded %s (%s rows)",
          result$spec$label, format(nrow(result$portfolio), big.mark = ",")
        ),
        type = "message"
      )
    })

    csv_raw <- reactive({
      req(input$csv_file)
      readr::read_csv(input$csv_file$datapath, show_col_types = FALSE)
    })

    output$mapping_ui <- renderUI({
      cols <- names(csv_raw())
      tagList(
        p(em("Map the CSV columns onto an ad-hoc dataset spec:")),
        selectInput(ns("map_target"), "Target column", choices = cols),
        selectInput(
          ns("map_offset"), "Offset / exposure column (optional)",
          choices = c("(none)", cols)
        ),
        selectizeInput(ns("map_predictors"), "Predictors", choices = cols, multiple = TRUE),
        radioButtons(
          ns("map_kind"), "Model kind",
          choices = c("frequency", "severity"), inline = TRUE
        ),
        actionButton(ns("load_csv"), "Load CSV as portfolio", class = "btn btn-primary")
      )
    })

    observeEvent(input$load_csv, {
      if (length(input$map_predictors) == 0) {
        showNotification("Select at least one predictor.", type = "warning")
        return(invisible(NULL))
      }
      offset <- if (identical(input$map_offset, "(none)")) NULL else input$map_offset
      state$portfolio <- csv_raw()
      state$spec <- list(
        name = "adhoc_csv",
        label = paste("CSV upload:", input$csv_file$name),
        kind = input$map_kind,
        target = input$map_target,
        offset = offset,
        predictors = input$map_predictors
      )
      showNotification(
        sprintf("Loaded %s (%s rows)", input$csv_file$name,
                format(nrow(state$portfolio), big.mark = ",")),
        type = "message"
      )
    })

    output$active_dataset <- renderUI({
      if (is.null(state$portfolio)) {
        return(p(em("No dataset loaded yet.")))
      }
      spec <- state$spec
      tagList(
        h4("Active dataset"),
        p(
          strong(spec$label),
          sprintf(
            " — %s rows × %d columns | kind: %s | target: %s | offset: %s",
            format(nrow(state$portfolio), big.mark = ","),
            ncol(state$portfolio), spec$kind, spec$target,
            if (is.null(spec$offset)) "none" else spec$offset
          )
        )
      )
    })

    output$validation <- renderTable({
      req(state$portfolio)
      validate_portfolio(state$portfolio, state$spec)
    })

    output$preview <- DT::renderDT({
      req(state$portfolio)
      state$portfolio |>
        slice_head(n = 100) |>
        DT::datatable(options = list(scrollX = TRUE, pageLength = 10), rownames = FALSE)
    })
  })
}
