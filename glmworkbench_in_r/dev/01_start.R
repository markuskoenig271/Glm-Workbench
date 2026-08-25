# Building a Prod-Ready, Robust Shiny Application.
#
# README: each step of the dev files is optional, and you don't have to
# fill every dev scripts before getting started.
# 01_start.R should be filled at start.
# 02_dev.R should be used to keep track of your development during the project.
# 03_deploy.R should be used once you need to deploy your app.
#
# glmworkbenchR: the package was golem-ified from an existing devtools
# package on 2026-08-25, so most of this file has already been applied
# (DESCRIPTION, LICENSE, README, tests). Kept for the standard golem layout.

## Fill the DESCRIPTION ----
golem::fill_desc(
  pkg_name = "glmworkbenchR",
  pkg_title = "GLM Workbench - R Shiny Port of the Actuarial Pricing Workbench",
  pkg_description = "Shiny application mirroring the Python GLM Workbench.",
  author_first_name = "Markus",
  author_last_name = "Koenig",
  author_email = "markuskoenig73@gmail.com",
  repo_url = NULL,
  pkg_version = "0.1.0"
)

## Set common files ----
# usethis::use_mit_license("Markus Koenig")  # LICENSE is "all rights reserved" for now
# usethis::use_readme_rmd(open = FALSE)      # README.md is maintained by hand
# usethis::use_code_of_conduct(contact = "Markus Koenig")
# usethis::use_lifecycle_badge("Experimental")
# usethis::use_news_md(open = FALSE)

## Init Testing Infrastructure ----
## Create a template for tests
golem::use_recommended_tests()

## Favicon ----
# golem::use_favicon()  # drop a favicon.ico into inst/app/www and enable golem::favicon() in app_ui.R
# golem::remove_favicon()

## Add helper functions ----
golem::use_utils_ui(with_test = TRUE)
golem::use_utils_server(with_test = TRUE)

## Use git ----
# usethis::use_git()  # the repo root (Python app) is already a git repo

# You're now set! ----

# go to dev/02_dev.R
rstudioapi::navigateToFile("dev/02_dev.R")
