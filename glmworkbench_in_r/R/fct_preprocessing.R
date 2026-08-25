# Cleansing / feature-engineering helpers -- mirrors pricing_engine/preprocessing.py.
# Tidyverse style: dplyr mutate with dynamic column names ("{col}_band" :=).

#' Cap a numeric column
#'
#' @param df Portfolio tibble.
#' @param col Column name.
#' @param cap Upper bound; values above it are set to `cap`.
#' @return `df` with the column capped.
#' @export
cap_column <- function(df, col, cap) {
  if (!is.numeric(df[[col]])) stop("Column '", col, "' is not numeric")
  df |> mutate("{col}" := pmin(.data[[col]], cap))
}

#' Bin a numeric column into `<col>_band`
#'
#' @param df Portfolio tibble.
#' @param col Column name.
#' @param n_bins Number of bins.
#' @param method `"quantile"` (equal counts) or `"uniform"` (equal widths).
#' @return `df` with an added factor column `<col>_band`.
#' @export
bin_numeric <- function(df, col, n_bins = 5, method = c("quantile", "uniform")) {
  method <- match.arg(method)
  x <- df[[col]]
  if (!is.numeric(x)) stop("Column '", col, "' is not numeric")
  breaks <- switch(method,
    quantile = x |>
      quantile(probs = seq(0, 1, length.out = n_bins + 1), na.rm = TRUE) |>
      unique(),
    uniform = seq(min(x, na.rm = TRUE), max(x, na.rm = TRUE), length.out = n_bins + 1)
  )
  if (length(breaks) < 3) {
    stop("Column '", col, "' has too few distinct values for ", n_bins, " bins")
  }
  df |> mutate("{col}_band" := cut(.data[[col]], breaks = breaks, include.lowest = TRUE))
}

#' Log-transform a strictly positive column into `<col>_log`
#'
#' @param df Portfolio tibble.
#' @param col Column name.
#' @return `df` with an added column `<col>_log`.
#' @export
log_transform <- function(df, col) {
  x <- df[[col]]
  if (!is.numeric(x)) stop("Column '", col, "' is not numeric")
  if (any(x <= 0, na.rm = TRUE)) {
    stop("Log transform requires strictly positive values in '", col, "'")
  }
  df |> mutate("{col}_log" := log(.data[[col]]))
}
