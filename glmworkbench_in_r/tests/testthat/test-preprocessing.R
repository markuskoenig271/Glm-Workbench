# fct_preprocessing.R -- mirrors tests/test_preprocessing.py on tiny tibbles.

toy <- tibble::tibble(
  Exposure = c(0.5, 1.0, 1.5, 2.0, 0.25, 0.75),
  Age = c(20, 30, 40, 50, 60, 70),
  Region = c("A", "B", "A", "B", "A", "B")
)

test_that("cap_column caps values above the cap and keeps the rest", {
  capped <- cap_column(toy, "Exposure", 1.0)
  expect_equal(capped$Exposure, c(0.5, 1.0, 1.0, 1.0, 0.25, 0.75))
  expect_equal(toy$Exposure[3], 1.5) # input untouched (copy semantics)
})

test_that("cap_column rejects non-numeric columns", {
  expect_error(cap_column(toy, "Region", 1), "not numeric")
})

test_that("bin_numeric adds a <col>_band factor with quantile or uniform breaks", {
  q <- bin_numeric(toy, "Age", n_bins = 3, method = "quantile")
  expect_true("Age_band" %in% names(q))
  expect_s3_class(q$Age_band, "factor")
  expect_equal(nlevels(q$Age_band), 3)

  u <- bin_numeric(toy, "Age", n_bins = 2, method = "uniform")
  expect_equal(nlevels(u$Age_band), 2)
  expect_equal(as.integer(u$Age_band), c(1L, 1L, 1L, 2L, 2L, 2L))
})

test_that("bin_numeric fails loudly on too few distinct values or non-numeric input", {
  constant <- tibble::tibble(x = rep(1, 10))
  expect_error(bin_numeric(constant, "x", n_bins = 5), "too few distinct values")
  expect_error(bin_numeric(toy, "Region", n_bins = 2), "not numeric")
})

test_that("log_transform adds <col>_log and requires strictly positive values", {
  logged <- log_transform(toy, "Exposure")
  expect_equal(logged$Exposure_log, log(toy$Exposure))
  with_zero <- toy
  with_zero$Exposure[1] <- 0
  expect_error(log_transform(with_zero, "Exposure"), "strictly positive")
})
