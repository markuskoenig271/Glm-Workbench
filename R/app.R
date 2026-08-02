# GLM Workbench — R Shiny feasibility study.
# Entry point: navbar UI over namespaced page modules sharing one reactiveValues
# state (portfolio + spec + single active model slot, mirroring the Streamlit
# session_state design). Run with:  Rscript -e "shiny::runApp('R')"
# or double-click run_app.bat.

library(shiny)
library(bslib)
suppressPackageStartupMessages({
  library(dplyr)   # also attached by core/, repeated here for explicitness
  library(tibble)
  library(readr)   # CSV upload in mod_data_import
})

source("core/datasets.R")
source("core/preprocessing.R")
for (f in list.files("modules", pattern = "\\.R$", full.names = TRUE)) {
  source(f)
}

ui <- page_navbar(
  title = "GLM Workbench (R)",
  theme = bs_theme(version = 5, bootswatch = "flatly"),
  nav_panel("Home", mod_home_ui("home")),
  nav_panel("01 Data Import", mod_data_import_ui("data_import")),
  nav_panel("02 Data Exploration", mod_placeholder_ui("exploration", "Data Exploration")),
  nav_panel("03 Feature Engineering", mod_feature_engineering_ui("feature_engineering")),
  nav_panel("04 Frequency Model", mod_placeholder_ui("frequency_model", "Frequency Model")),
  nav_panel("05 Diagnostics", mod_placeholder_ui("diagnostics", "Diagnostics")),
  nav_panel("06 Prediction", mod_placeholder_ui("prediction", "Prediction")),
  nav_panel("07 Severity Model", mod_placeholder_ui("severity_model", "Severity Model"))
)

server <- function(input, output, session) {
  # Shared app state — the Shiny analogue of st.session_state:
  # portfolio + spec from Data Import, model/model_meta = single active
  # model slot (kind-gated, as in the Streamlit app; unused until the
  # modelling modules arrive).
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

shinyApp(ui, server)
