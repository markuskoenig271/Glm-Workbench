# Dataset registry, loaders and validation — mirrors pricing_engine/data.py.
# Tidyverse style: native |> pipe, dplyr verbs, tibbles.
# DATA_DIR is resolved when this file is sourced by app.R (working directory
# is the app directory, i.e. the repo's R/ folder).

suppressPackageStartupMessages({
  library(dplyr)
  library(tidyr)
  library(purrr)
  library(tibble)
})

DATA_DIR <- normalizePath(file.path(getwd(), "..", "data", "raw"), mustWork = FALSE)

DATASET_REGISTRY <- list(
  fremtpl2_freq = list(
    name = "fremtpl2_freq",
    label = "freMTPL2 — claim frequency (678k policies)",
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
    label = "freMTPL2 — claim severity (26k claims, joined rating factors)",
    kind = "severity",
    target = "ClaimAmount",
    offset = NULL,
    predictors = c(
      "VehPower", "VehAge", "DrivAge", "BonusMalus",
      "VehBrand", "VehGas", "Area", "Density", "Region"
    )
  )
)

dataset_choices <- function() {
  set_names(names(DATASET_REGISTRY), map_chr(DATASET_REGISTRY, "label"))
}

required_columns <- function(spec) {
  unique(c(spec$target, spec$offset, spec$predictors))
}

read_parquet_checked <- function(file) {
  path <- file.path(DATA_DIR, file)
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
    mutate(IDpol = as.numeric(IDpol))
}

# Inner join severity claims onto the frequency rating factors (orphan claims
# without a matching policy are dropped) — same semantics as
# load_fremtpl2_sev_joined() in pricing_engine/data.py.
load_fremtpl2_sev_joined <- function() {
  rating <- load_fremtpl2_freq() |>
    select(IDpol, all_of(DATASET_REGISTRY$fremtpl2_sev$predictors))
  read_parquet_checked("freMTPL2sev.parquet") |>
    mutate(IDpol = as.numeric(IDpol)) |>
    inner_join(rating, by = "IDpol")
}

load_dataset <- function(key) {
  spec <- DATASET_REGISTRY[[key]]
  if (is.null(spec)) stop("Unknown dataset: ", key)
  portfolio <- switch(key,
    fremtpl2_freq = load_fremtpl2_freq(),
    fremtpl2_sev = load_fremtpl2_sev_joined()
  )
  list(portfolio = portfolio, spec = spec)
}

# Kind-aware validation, returns a tibble(level, message) for display.
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
      tibble(level = "error", message = sprintf("%d claim amounts are not strictly positive", n_bad))
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
      tibble(level = "error", message = sprintf("%d offset values are not strictly positive", n_bad))
    } else {
      tibble()
    }
  }

  na_msgs <- df |>
    select(all_of(req_cols)) |>
    summarise(across(everything(), ~ sum(is.na(.x)))) |>
    pivot_longer(everything(), names_to = "column", values_to = "n_missing") |>
    filter(n_missing > 0) |>
    transmute(
      level = "warning",
      message = sprintf("%s: %d missing values", column, n_missing)
    )

  bind_rows(target_msgs, offset_msgs, na_msgs) |>
    (\(msgs) if (nrow(msgs) > 0) msgs else tibble(
      level = "ok",
      message = sprintf(
        "Validation passed: %s rows × %d columns, no issues found",
        format(nrow(df), big.mark = ","), ncol(df)
      )
    ))()
}
