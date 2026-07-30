"""Diagnostics (screen 6 in docs/ui_screens.md)."""

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

from pricing_engine import diagnostics

ACCENT = "#4c78a8"
OBSERVED_COLOR = "#4c78a8"
PREDICTED_COLOR = "#f58518"

st.title("Diagnostics")

if "model" not in st.session_state:
    st.info("Fit a model first — go to Frequency Model.")
    st.stop()

model = st.session_state["model"]
meta = st.session_state["model_meta"]

if meta["kind"] != "frequency":
    st.info(
        "The active model is a severity model — severity-aware diagnostics arrive "
        "with the next slice. Fit a frequency model to use this screen."
    )
    st.stop()
portfolio = st.session_state["portfolio"]
spec = st.session_state["spec"]

col1, col2, col3, col4 = st.columns(4)
col1.metric("AIC", f"{meta['aic']:,.0f}")
col2.metric("BIC", f"{meta['bic']:,.0f}")
col3.metric("Deviance", f"{meta['deviance']:,.0f}")
col4.metric("Parameters", f"{meta['n_params']:,}")
st.caption(f"Model: `{meta['formula']}` ({meta['family']})")

st.subheader("Coefficients with confidence intervals")
table = diagnostics.coefficient_table(model)
non_intercept = table[table["term"] != "Intercept"].copy()
top = non_intercept.reindex(non_intercept["coef"].abs().sort_values(ascending=False).index).head(20)
top["exp_ci_low"] = np.exp(top["ci_low"])
top["exp_ci_high"] = np.exp(top["ci_high"])
st.caption(
    "Risk relativities exp(coef) with 95% confidence whiskers; the dashed line at 1.0 "
    "is 'no effect'. Whiskers crossing 1.0 mean the effect is not significant."
)
base = alt.Chart(top)
whiskers = base.mark_rule(color=ACCENT).encode(
    y=alt.Y("term", type="nominal", sort=None, title=None),
    x=alt.X("exp_ci_low", type="quantitative", title="Relativity exp(coef)"),
    x2="exp_ci_high",
)
points = base.mark_point(filled=True, size=60, color=ACCENT).encode(
    y=alt.Y("term", type="nominal", sort=None),
    x=alt.X("exp_coef", type="quantitative"),
    tooltip=[
        alt.Tooltip("term", type="nominal"),
        alt.Tooltip("exp_coef", type="quantitative", format=".3f"),
        alt.Tooltip("p_value", type="quantitative", format=".2g"),
    ],
)
reference = (
    alt.Chart(pd.DataFrame({"x": [1.0]})).mark_rule(strokeDash=[4, 4], color="gray").encode(x="x")
)
st.altair_chart(whiskers + points + reference, use_container_width=True)
with st.expander("Coefficient table"):
    st.dataframe(table.round(4))

st.subheader("Residuals")
kind = st.radio("Residual kind", diagnostics.RESIDUAL_KINDS, horizontal=True)
hist = diagnostics.residual_histogram(model, kind=kind)
st.caption(
    "Count data with mostly zero claims makes residuals look lumpy/banded — "
    "that is expected for Poisson models, not a defect."
)
hist_chart = (
    alt.Chart(hist)
    .mark_bar(color=ACCENT)
    .encode(
        x=alt.X("residual", type="quantitative", title=f"{kind} residual"),
        y=alt.Y("count", type="quantitative", title="Policies"),
        tooltip=[
            alt.Tooltip("residual", type="quantitative", format=".2f"),
            alt.Tooltip("count", type="quantitative", format=","),
        ],
    )
)
st.altair_chart(hist_chart, use_container_width=True)

st.subheader("QQ plot")
qq = diagnostics.qq_data(model, kind=kind)
qq_span = pd.DataFrame(
    {
        "theoretical": [qq["theoretical"].min(), qq["theoretical"].max()],
        "sample": [qq["theoretical"].min(), qq["theoretical"].max()],
    }
)
qq_points = (
    alt.Chart(qq)
    .mark_point(color=ACCENT, size=25)
    .encode(
        x=alt.X("theoretical", type="quantitative", title="Theoretical normal quantile"),
        y=alt.Y("sample", type="quantitative", title=f"Sample {kind} residual quantile"),
    )
)
qq_line = (
    alt.Chart(qq_span)
    .mark_line(strokeDash=[4, 4], color="gray")
    .encode(x="theoretical", y="sample")
)
st.altair_chart(qq_points + qq_line, use_container_width=True)

st.subheader("Observed vs Predicted")
st.caption(
    "Calibration by predicted-frequency band: a trustworthy model keeps observed and "
    "predicted close in every band."
)
ovp = diagnostics.observed_vs_predicted(portfolio, spec, model)
ovp_long = ovp.melt(
    id_vars=["group", "exposure"],
    value_vars=["observed_frequency", "predicted_frequency"],
    var_name="series",
    value_name="frequency",
)
ovp_long["series"] = ovp_long["series"].map(
    {"observed_frequency": "Observed", "predicted_frequency": "Predicted"}
)
ovp_chart = (
    alt.Chart(ovp_long)
    .mark_bar()
    .encode(
        x=alt.X("group", type="nominal", sort=None, title="Predicted-frequency band"),
        xOffset=alt.XOffset("series", type="nominal"),
        y=alt.Y("frequency", type="quantitative", title="Claim frequency"),
        color=alt.Color(
            "series",
            type="nominal",
            scale=alt.Scale(
                domain=["Observed", "Predicted"], range=[OBSERVED_COLOR, PREDICTED_COLOR]
            ),
            title=None,
        ),
        tooltip=[
            alt.Tooltip("group", type="nominal"),
            alt.Tooltip("series", type="nominal"),
            alt.Tooltip("frequency", type="quantitative", format=".4f"),
            alt.Tooltip("exposure", type="quantitative", format=",.0f"),
        ],
    )
)
st.altair_chart(ovp_chart, use_container_width=True)
with st.expander("Calibration table"):
    st.dataframe(ovp.round(4))

st.subheader("Model summary")
with st.expander("Full statsmodels summary"):
    st.text(model.summary().as_text())
