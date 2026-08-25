#' Application server
#'
#' Creates the shared app state (the Shiny analogue of Streamlit's
#' `st.session_state`: portfolio + spec from Data Import, `model` /
#' `model_meta` = single active model slot, kind-gated as in the Python app
#' and unused until the modelling modules arrive) and wires every page module
#' to it.
#'
#' @param input,output,session Standard Shiny server arguments.
#' @noRd
app_server <- function(input, output, session) {
  state <- reactiveValues(portfolio = NULL, spec = NULL, model = NULL, model_meta = NULL)

  mod_home_server("home", state)
  mod_data_import_server("data_import", state)
  mod_placeholder_server("exploration", state)
  mod_feature_engineering_server("feature_engineering", state)
  mod_placeholder_server("frequency_model", state)
  mod_placeholder_server("diagnostics", state)
  mod_placeholder_server("prediction", state)
  mod_placeholder_server("severity_model", state)
}
