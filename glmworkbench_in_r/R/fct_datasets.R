# Dataset registry, loaders and validation -- mirrors pricing_engine/data.py.
# Tidyverse style: native |> pipe, dplyr verbs, tibbles.

#' Registered datasets
#'
#' Same specs as `DATASET_REGISTRY` in `pricing_engine/data.py`: name, label,
#' kind (frequency / severity), target, offset and predictors.
#' @noRd
DATASET_REGISTRY <- list(
  fremtpl2_freq = list(
    name = "fremtpl2_freq",
    label = "freMTPL2 \u2014 claim frequency (678k policies)",
    kind = "frequency",
    target = "ClaimNb",
    offset = "Exposure",
    predictors = c(
      "VehPower", "VehAge", "DrivAge", "BonusMalus",
      "VehBrand", "VehGas", "Area", "Density", "Region"
    )
  ),
  fremtpl2_sev = list(
    name = "fremtpl2_sev",
    label = "freMTPL2 \u2014 claim severity (26k claims, joined rating factors)",
    kind = "severity",
    target = "ClaimAmount",
    offset = NULL,
    predictors = c(
      "VehPower", "VehAge", "DrivAge", "BonusMalus",
      "VehBrand", "VehGas", "Area", "Density", "Region"
    )
  )
)

#' Where the parquet files live
#'
#' Resolution order: the golem option `data_dir` (set by [run_app()]'s
#' `data_dir` argument, available while the app runs), the
#' `GLM_WORKBENCH_DATA_DIR` environment variable (set by the Electron desktop
#' shell to its bundled copy), `data_dir` in `inst/golem-config.yml` for the
#' active `GOLEM_CONFIG_ACTIVE` environment, the package's own `inst/extdata`
#' if it contains parquet files, and finally `../data/raw` relative to the
#' working directory -- the Python repo layout when the RStudio project is
#' open.
#'
#' @return A directory path (not guaranteed to exist).
#' @export
data_dir <- function() {
  opt <- tryCatch(golem::get_golem_options("data_dir"), error = function(e) NULL)
  if (!is.null(opt)) {
    return(opt)
  }
  env <- Sys.getenv("GLM_WORKBENCH_DATA_DIR", unset = "")
  if (nzchar(env)) {
    return(env)
  }
  configured <- tryCatch(get_golem_config("data_dir"), error = function(e) NULL)
  if (!is.null(configured)) {
    return(configured)
  }
  bundled <- app_sys("extdata")
  if (nzchar(bundled) && length(list.files(bundled, pattern = "\\.parquet$")) > 0) {
    return(bundled)
  }
  normalizePath(file.path(getwd(), "..", "data", "raw"), mustWork = FALSE)
}

#' Named choices for a selectInput: labels as names, registry keys as values.
#' @noRd
dataset_choices <- function() {
  set_names(names(DATASET_REGISTRY), map_chr(DATASET_REGISTRY, "label"))
}

#' Columns a spec needs in the portfolio (target, offset, predictors).
#' @noRd
required_columns <- function(spec) {
  unique(c(spec$target, spec$offset, spec$predictors))
}

read_parquet_checked <- function(file) {
  path <- file.path(data_dir(), file)
  if (!file.exists(path)) {
    stop(
      "Data file not found: ", path,
      "\nDownload the freMTPL2 parquet files first (see the Python app / project docs)."
    )
  }
  nanoparquet::read_parquet(path) |> as_tibble()
}

load_fremtpl2_freq <- function() {
  read_parquet_checked("freMTPL2freq.parquet") |>
    mutate(IDpol = as.numeric(.data$IDpol))
}

# Inner join severity claims onto the frequency rating factors (orphan claims
# without a matching policy are dropped) -- same semantics as
# load_fremtpl2_sev_joined() in pricing_engine/data.py.
load_fremtpl2_sev_joined <- function() {
  rating <- load_fremtpl2_freq() |>
    select("IDpol", all_of(DATASET_REGISTRY$fremtpl2_sev$predictors))
  read_parquet_checked("freMTPL2sev.parquet") |>
    mutate(IDpol = as.numeric(.data$IDpol)) |>
    inner_join(rating, by = "IDpol")
}

#' Load a registered dataset
#'
#' @param key Registry key: `"fremtpl2_freq"` or `"fremtpl2_sev"`.
#' @return A list with `portfolio` (tibble) and `spec` (the registry entry).
#' @export
load_dataset <- function(key) {
  spec <- DATASET_REGISTRY[[key]]
  if (is.null(spec)) stop("Unknown dataset: ", key)
  portfolio <- switch(key,
    fremtpl2_freq = load_fremtpl2_freq(),
    fremtpl2_sev = load_fremtpl2_sev_joined()
  )
  list(portfolio = portfolio, spec = spec)
}

#' Kind-aware portfolio validation
#'
#' Mirrors `validate_portfolio()` in `pricing_engine/data.py`: missing
#' columns, non-numeric / invalid target (severity targets must be strictly
#' positive, frequency targets non-negative), non-positive offsets, and
#' missing-value counts.
#'
#' @param df Portfolio tibble.
#' @param spec Dataset spec (registry entry or ad-hoc CSV spec).
#' @return A tibble with columns `level` (error / warning / ok) and `message`.
#' @export
validate_portfolio <- function(df, spec) {
  req_cols <- required_columns(spec)

  missing_cols <- setdiff(req_cols, names(df))
  if (length(missing_cols) > 0) {
    return(tibble(
      level = "error",
      message = paste("Missing columns:", paste(missing_cols, collapse = ", "))
    ))
  }

  target <- df[[spec$target]]
  target_msgs <- if (!is.numeric(target)) {
    tibble(level = "error", message = sprintf("Target '%s' is not numeric", spec$target))
  } else if (identical(spec$kind, "severity")) {
    n_bad <- sum(target <= 0, na.rm = TRUE)
    if (n_bad > 0) {
      tibble(
        level = "error",
        message = sprintf("%d claim amounts are not strictly positive", n_bad)
      )
    } else {
      tibble()
    }
  } else {
    n_bad <- sum(target < 0, na.rm = TRUE)
    if (n_bad > 0) {
      tibble(level = "error", message = sprintf("%d target values are negative", n_bad))
    } else {
      tibble()
    }
  }

  offset_msgs <- if (is.null(spec$offset)) {
    tibble()
  } else if (!is.numeric(df[[spec$offset]])) {
    tibble(level = "error", message = sprintf("Offset '%s' is not numeric", spec$offset))
  } else {
    n_bad <- sum(df[[spec$offset]] <= 0, na.rm = TRUE)
    if (n_bad > 0) {
      tibble(
        level = "error",
        message = sprintf("%d offset values are not strictly positive", n_bad)
      )
    } else {
      tibble()
    }
  }

  na_msgs <- df |>
    select(all_of(req_cols)) |>
    summarise(across(everything(), ~ sum(is.na(.x)))) |>
    pivot_longer(everything(), names_to = "column", values_to = "n_missing") |>
    filter(.data$n_missing > 0) |>
    transmute(
      level = "warning",
      message = sprintf("%s: %d missing values", .data$column, .data$n_missing)
    )

  msgs <- bind_rows(target_msgs, offset_msgs, na_msgs)
  if (nrow(msgs) > 0) {
    return(msgs)
  }
  tibble(
    level = "ok",
    message = sprintf(
      "Validation passed: %s rows \u00d7 %d columns, no issues found",
      format(nrow(df), big.mark = ","), ncol(df)
    )
  )
}
