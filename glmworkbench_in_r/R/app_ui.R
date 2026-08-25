#' The application User-Interface
#'
#' Navbar over the namespaced page modules, mirroring the Streamlit app's
#' `pages/` order.
#'
#' @param request Internal parameter for `{shiny}`.
#'     DO NOT REMOVE.
#' @import shiny
#' @noRd
app_ui <- function(request) {
  tagList(
    # Leave this function for adding external resources
    golem_add_external_resources(),
    # Your application UI logic
    bslib::page_navbar(
      title = "GLM Workbench (R)",
      theme = bslib::bs_theme(version = 5, bootswatch = "flatly"),
      bslib::nav_panel("Home", mod_home_ui("home")),
      bslib::nav_panel("01 Data Import", mod_data_import_ui("data_import")),
      bslib::nav_panel(
        "02 Data Exploration", mod_placeholder_ui("exploration", "Data Exploration")
      ),
      bslib::nav_panel(
        "03 Feature Engineering", mod_feature_engineering_ui("feature_engineering")
      ),
      bslib::nav_panel(
        "04 Frequency Model", mod_placeholder_ui("frequency_model", "Frequency Model")
      ),
      bslib::nav_panel("05 Diagnostics", mod_placeholder_ui("diagnostics", "Diagnostics")),
      bslib::nav_panel("06 Prediction", mod_placeholder_ui("prediction", "Prediction")),
      bslib::nav_panel(
        "07 Severity Model", mod_placeholder_ui("severity_model", "Severity Model")
      )
    )
  )
}

#' Add external Resources to the Application
#'
#' This function is internally used to add external
#' resources inside the Shiny application.
#'
#' @import shiny
#' @importFrom golem add_resource_path activate_js favicon bundle_resources
#' @noRd
golem_add_external_resources <- function() {
  add_resource_path(
    "www",
    app_sys("app/www")
  )

  tags$head(
    bundle_resources(
      path = app_sys("app/www"),
      app_title = "GLM Workbench (R)"
    )
    # Add here other external resources
    # for example, you can add shinyalert::useShinyalert()
  )
}
