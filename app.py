"""GLM Workbench — Home (screen 1 in docs/ui_screens.md)."""

import streamlit as st

import pricing_engine

st.set_page_config(page_title="GLM Workbench", page_icon="📊", layout="wide")

st.title("GLM Workbench")
st.caption(
    f"v{pricing_engine.__version__} — actuarial pricing experiments with GLMs, "
    "following the car-insurance workflow of Parodi, *Pricing in General "
    "Insurance* (Chapter 27): frequency × severity → pure premium."
)

st.markdown(
    """
    Welcome. Work through the pages in the sidebar in order:

    **Data Import → Data Exploration → Feature Engineering → Frequency Model /
    Severity Model → Diagnostics → Prediction → Pure Premium**
    """
)

st.subheader("Workflow status")
if "spec" in st.session_state:
    spec = st.session_state["spec"]
    portfolio = st.session_state["portfolio"]
    st.success(f"Active dataset: {spec.label} — {len(portfolio):,} rows")
else:
    st.info("No dataset loaded yet — start with Data Import.")

for kind, screen in (("frequency", "Frequency Model"), ("severity", "Severity Model")):
    meta = st.session_state.get(f"model_{kind}_meta")
    if meta is None:
        st.caption(f"{kind.title()} model: none — fit or load one on {screen}.")
    else:
        st.caption(
            f"{kind.title()} model: {meta['source']} ({meta['family']}, AIC {meta['aic']:,.0f})"
        )
if "model_frequency" in st.session_state and "model_severity" in st.session_state:
    st.success("Both models in session — ready to quote on Pure Premium.")

st.subheader("Roadmap")
st.markdown(
    """
    - **V1** — Frequency GLM — complete
    - **V2** — Severity GLM (Gamma) — complete
    - **V3** — Pure Premium (Frequency × Severity) — this version
    - **V4** — Generic pricing workbench
    """
)
