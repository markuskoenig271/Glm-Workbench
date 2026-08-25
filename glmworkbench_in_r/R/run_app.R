#' Run the Shiny Application
#'
#' Single entry point for every way of starting the app: RStudio
#' (`dev/run_dev.R` or `devtools::load_all(); run_app()`), the command line
#' (`Rscript -e "glmworkbenchR::run_app()"`), the EUC launchers and the
#' Electron desktop shell. Shiny run options (port, host, launch.browser)
#' go through `options`, e.g.
#' `run_app(options = list(port = 8613, launch.browser = FALSE))`.
#'
#' @param ... arguments to pass to golem_opts.
#' See `?golem::get_golem_options` for more details.
#' @param data_dir Directory holding the `freMTPL2*.parquet` files; `NULL`
#'   (default) keeps the resolution of [data_dir()] (golem option →
#'   `GLM_WORKBENCH_DATA_DIR` env var → `golem-config.yml` → `inst/extdata`
#'   → `../data/raw` relative to the working directory).
#' @inheritParams shiny::shinyApp
#'
#' @export
#' @importFrom shiny shinyApp
#' @importFrom golem with_golem_options
run_app <- function(
  onStart = NULL,
  options = list(),
  enableBookmarking = NULL,
  uiPattern = "/",
  data_dir = NULL,
  ...
) {
  with_golem_options(
    app = shinyApp(
      ui = app_ui,
      server = app_server,
      onStart = onStart,
      options = options,
      enableBookmarking = enableBookmarking,
      uiPattern = uiPattern
    ),
    golem_opts = list(data_dir = data_dir, ...)
  )
}
