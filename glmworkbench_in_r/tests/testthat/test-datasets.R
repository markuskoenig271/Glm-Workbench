# fct_datasets.R -- registry, validation on tiny frames, real-data facts.
# The real-data tests need the Python repo's data/raw parquet files; they are
# skipped when those are not reachable (e.g. inside R CMD check's temp copy
# unless GLM_WORKBENCH_DATA_DIR points at them).

repo_data_dir <- function() {
  env <- Sys.getenv("GLM_WORKBENCH_DATA_DIR", unset = "")
  if (nzchar(env)) {
    return(env)
  }
  testthat::test_path("..", "..", "..", "data", "raw")
}

skip_if_no_data <- function() {
  dir <- repo_data_dir()
  testthat::skip_if_not(
    file.exists(file.path(dir, "freMTPL2freq.parquet")) &&
      file.exists(file.path(dir, "freMTPL2sev.parquet")),
    "freMTPL2 parquet files not available"
  )
  withr::local_options(list(glmworkbenchR.data_dir = dir), .local_envir = parent.frame())
}

test_that("registry exposes both freMTPL2 datasets with the Python specs", {
  expect_setequal(names(DATASET_REGISTRY), c("fremtpl2_freq", "fremtpl2_sev"))
  freq <- DATASET_REGISTRY$fremtpl2_freq
  sev <- DATASET_REGISTRY$fremtpl2_sev
  expect_equal(freq$kind, "frequency")
  expect_equal(freq$target, "ClaimNb")
  expect_equal(freq$offset, "Exposure")
  expect_equal(sev$kind, "severity")
  expect_equal(sev$target, "ClaimAmount")
  expect_null(sev$offset)
  expect_length(freq$predictors, 9)
  expect_equal(sev$predictors, freq$predictors)

  choices <- dataset_choices()
  expect_equal(unname(choices), c("fremtpl2_freq", "fremtpl2_sev"))
  expect_match(names(choices)[2], "severity")
  expect_equal(
    required_columns(freq),
    c("ClaimNb", "Exposure", freq$predictors)
  )
  expect_error(load_dataset("nope"), "Unknown dataset")
})

toy_spec <- list(
  name = "toy", label = "Toy", kind = "frequency",
  target = "ClaimNb", offset = "Exposure", predictors = c("Age")
)
toy <- tibble::tibble(ClaimNb = c(0, 1, 2), Exposure = c(0.5, 1, 1), Age = c(20, 30, 40))

test_that("validate_portfolio passes a clean frequency portfolio", {
  report <- validate_portfolio(toy, toy_spec)
  expect_equal(report$level, "ok")
  expect_match(report$message, "3 rows")
})

test_that("validate_portfolio reports missing columns, bad target/offset and NAs", {
  expect_match(validate_portfolio(toy[, c("ClaimNb", "Age")], toy_spec)$message, "Exposure")

  neg <- toy
  neg$ClaimNb[1] <- -1
  expect_match(validate_portfolio(neg, toy_spec)$message, "negative")

  zero_offset <- toy
  zero_offset$Exposure[2] <- 0
  expect_match(validate_portfolio(zero_offset, toy_spec)$message, "offset values")

  with_na <- toy
  with_na$Age[3] <- NA
  report <- validate_portfolio(with_na, toy_spec)
  expect_equal(report$level, "warning")
  expect_match(report$message, "Age: 1 missing")
})

test_that("validate_portfolio is kind-aware: severity targets must be strictly positive", {
  sev_spec <- list(
    name = "toy_sev", label = "Toy sev", kind = "severity",
    target = "ClaimAmount", offset = NULL, predictors = c("Age")
  )
  claims <- tibble::tibble(ClaimAmount = c(100, 0, 250), Age = c(20, 30, 40))
  report <- validate_portfolio(claims, sev_spec)
  expect_equal(report$level, "error")
  expect_match(report$message, "1 claim amounts are not strictly positive")
  # zero counts are fine for frequency data
  expect_equal(validate_portfolio(toy, toy_spec)$level, "ok")
})

test_that("real data: frequency portfolio loads with the Python row count", {
  skip_if_no_data()
  result <- load_dataset("fremtpl2_freq")
  expect_equal(nrow(result$portfolio), 678013)
  expect_true(all(required_columns(result$spec) %in% names(result$portfolio)))
  expect_equal(validate_portfolio(result$portfolio, result$spec)$level, "ok")
})

test_that("real data: severity join drops orphans and matches the Python mean", {
  skip_if_no_data()
  result <- load_dataset("fremtpl2_sev")
  expect_equal(nrow(result$portfolio), 26444)
  expect_equal(mean(result$portfolio$ClaimAmount), 2265.5, tolerance = 1e-4)
  expect_equal(validate_portfolio(result$portfolio, result$spec)$level, "ok")
})
