"""GLM Workbench — Home (screen 1 in docs/ui_screens.md)."""

import streamlit as st

import pricing_engine

st.set_page_config(page_title="GLM Workbench", page_icon="📊", layout="wide")

st.title("GLM Workbench")
st.caption(
    f"v{pricing_engine.__version__} — actuarial pricing experiments with GLMs. "
    "V1 reproduces the Chapter 27 car-insurance frequency example "
    "(Parodi, *Pricing in General Insurance*)."
)

st.markdown(
    """
    Welcome. Work through the pages in the sidebar in order:

    **Data Import → Data Exploration → Feature Engineering → Frequency Model →
    Diagnostics → Prediction**
    """
)

st.subheader("Workflow status")
if "spec" in st.session_state:
    spec = st.session_state["spec"]
    portfolio = st.session_state["portfolio"]
    st.success(f"Active dataset: {spec.label} — {len(portfolio):,} rows")
else:
    st.info("No dataset loaded yet — start with Data Import.")

st.subheader("Roadmap")
st.markdown(
    """
    - **V1** — Frequency GLM (this version)
    - **V2** — Severity GLM (Gamma)
    - **V3** — Pure Premium (Frequency × Severity)
    - **V4** — Generic pricing workbench
    """
)
