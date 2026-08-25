# golem's recommended tests (trimmed to what applies here).

test_that("app ui", {
  ui <- app_ui(request = NULL)
  golem::expect_shinytaglist(ui)
  # Check that formals have not been removed
  fmls <- formals(app_ui)
  for (i in c("request")) {
    expect_true(i %in% names(fmls))
  }
})

test_that("app server", {
  server <- app_server
  expect_type(server, "closure")
  # Check that formals have not been removed
  fmls <- formals(app_server)
  for (i in c("input", "output", "session")) {
    expect_true(i %in% names(fmls))
  }
})

test_that("app_sys works", {
  expect_true(
    app_sys("golem-config.yml") != ""
  )
})

test_that("golem-config works", {
  config_file <- app_sys("golem-config.yml")
  skip_if(config_file == "")
  expect_true(
    get_golem_config("app_prod", config = "production", file = config_file)
  )
  expect_false(
    get_golem_config("app_prod", config = "dev", file = config_file)
  )
  expect_equal(get_golem_config("golem_name", file = config_file), "glmworkbenchR")
  expect_null(get_golem_config("data_dir", file = config_file))
})

test_that("run_app returns a shiny app object carrying the golem options", {
  app <- run_app(data_dir = "some/dir", options = list(launch.browser = FALSE))
  expect_s3_class(app, "shiny.appobj")
  expect_equal(app$appOptions$golem_options$data_dir, "some/dir")
})
