#' glmworkbenchR: GLM Workbench as an R Shiny package
#'
#' Shiny port of the Python GLM Workbench. The app is an R package in the
#' usual "Shiny as a package" layout: `run_app()` is the single entry point,
#' every screen is a namespaced module (`mod_*_ui()` / `mod_*_server()`), the
#' data layer lives in `fct_*.R`, and all dependencies are declared in
#' `DESCRIPTION` / `NAMESPACE` instead of `library()` calls.
#'
#' Development loop (RStudio): `devtools::load_all()` (Ctrl+Shift+L) then
#' `run_app()`; `devtools::document()` regenerates `NAMESPACE` and `man/`;
#' `devtools::test()` and `devtools::check()` before sharing.
#'
#' @keywords internal
#' @import shiny
#' @importFrom rlang .data :=
#' @importFrom dplyr mutate select inner_join filter transmute summarise across
#'   everything all_of bind_rows slice_head
#' @importFrom tidyselect where
#' @importFrom tidyr pivot_longer
#' @importFrom purrr map_chr set_names
#' @importFrom tibble tibble as_tibble
#' @importFrom stats quantile
"_PACKAGE"
