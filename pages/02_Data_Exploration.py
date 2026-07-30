"""Data Exploration (screen 3 in docs/ui_screens.md)."""

import altair as alt
import streamlit as st

from pricing_engine import exploration

# Single-series charts: one hue, no legend, natural level order, hover tooltips.
ACCENT = "#4c78a8"

st.title("Data Exploration")

if "portfolio" not in st.session_state:
    st.info("Load a dataset first — go to Data Import.")
    st.stop()

portfolio = st.session_state["portfolio"]
spec = st.session_state["spec"]

severity = spec.kind == "severity"

frequency = exploration.portfolio_frequency(portfolio, spec)
if severity:
    col1, col2, col3 = st.columns(3)
    col1.metric("Claims", f"{len(portfolio):,}")
    col2.metric("Total claim amount", f"{portfolio[spec.target].sum():,.0f}")
    col3.metric("Average claim amount", f"{frequency:,.0f}")
    st.caption("Average claim amount = total claim amount / number of claims (severity).")
else:
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Policies", f"{len(portfolio):,}")
    if spec.offset is not None:
        col2.metric("Total exposure", f"{portfolio[spec.offset].sum():,.0f}")
    else:
        col2.metric("Total exposure", "n/a")
    col3.metric("Total claims", f"{int(portfolio[spec.target].sum()):,}")
    col4.metric("Claim frequency", f"{frequency:.4f}")
    st.caption(
        "Claim frequency = total claims / total exposure (claims per policy-year)."
        if spec.offset is not None
        else "Claim frequency = total claims / policies (no exposure offset in this dataset)."
    )

st.subheader("Summary statistics")
st.dataframe(exploration.summarize_portfolio(portfolio, spec))

one_way_title = "Average claim amount" if severity else "Claim frequency"
st.subheader(f"One-way {one_way_title.lower()}")
predictor = st.selectbox("Predictor", list(spec.predictors))
one_way = exploration.one_way_frequency(portfolio, spec, predictor)
one_way_chart = (
    alt.Chart(one_way)
    .mark_bar(color=ACCENT)
    .encode(
        x=alt.X(predictor, type="nominal", sort=None, title=predictor),
        y=alt.Y("frequency", type="quantitative", title=one_way_title),
        tooltip=[
            alt.Tooltip(predictor, type="nominal"),
            alt.Tooltip("policies", type="quantitative", format=","),
            alt.Tooltip("claims", type="quantitative", format=","),
            *(
                [alt.Tooltip("exposure", type="quantitative", format=",.0f")]
                if spec.offset is not None
                else []
            ),
            alt.Tooltip("frequency", type="quantitative", format=",.0f" if severity else ".4f"),
        ],
    )
)
st.altair_chart(one_way_chart, use_container_width=True)
with st.expander("One-way table"):
    st.dataframe(one_way)

st.subheader("Histograms")
column = st.selectbox("Column", list(spec.required_columns))
hist = exploration.histogram(portfolio, column)
hist_chart = (
    alt.Chart(hist)
    .mark_bar(color=ACCENT)
    .encode(
        x=alt.X(column, type="nominal", sort=None, title=column),
        y=alt.Y("count", type="quantitative", title="Claims" if severity else "Policies"),
        tooltip=[
            alt.Tooltip(column, type="nominal"),
            alt.Tooltip("count", type="quantitative", format=","),
        ],
    )
)
st.altair_chart(hist_chart, use_container_width=True)

st.subheader("Correlations")
st.caption("Pearson correlations of the numeric columns.")
st.dataframe(exploration.correlation_matrix(portfolio, spec).round(3))
