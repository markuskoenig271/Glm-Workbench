"""Diagnostics (screen 6 in docs/ui_screens.md) — kind-aware since V2."""

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

from pricing_engine import diagnostics

ACCENT = "#4c78a8"
OBSERVED_COLOR = "#4c78a8"
PREDICTED_COLOR = "#f58518"

# Wording per model kind — the engine is kind-agnostic, only the labels change.
WORDING = {
    "frequency": {
        "relativity": "Risk relativities exp(coef)",
        "relativity_axis": "Relativity exp(coef)",
        "residual_note": (
            "Count data with mostly zero claims makes residuals look lumpy/banded — "
            "that is expected for Poisson models, not a defect."
        ),
        "residual_unit": "Policies",
        "calibration_note": (
            "Calibration by predicted-frequency band: observed vs predicted claim frequency "
            "per band — a trustworthy model keeps them close in every band."
        ),
        "band_axis": "Predicted-frequency band",
        "value_axis": "Claim frequency",
        "value_format": ".4f",
        "weight_label": "exposure",
    },
    "severity": {
        "relativity": "Claim-size relativities exp(coef)",
        "relativity_axis": "Claim-size relativity exp(coef)",
        "residual_note": (
            "Claim amounts are heavy-tailed: a few very large claims produce a long "
            "right tail of residuals — typical for Gamma severity models, not a defect."
        ),
        "residual_unit": "Claims",
        "calibration_note": (
            "Calibration by predicted-claim-amount band: observed vs predicted average "
            "claim amount per band — a trustworthy model keeps them close in every band."
        ),
        "band_axis": "Predicted-claim-amount band",
        "value_axis": "Average claim amount",
        "value_format": ",.0f",
        "weight_label": "claims",
    },
}

st.title("Diagnostics")

if "portfolio" not in st.session_state:
    st.info("Load a dataset first — go to Data Import.")
    st.stop()

portfolio = st.session_state["portfolio"]
spec = st.session_state["spec"]
# per-kind model slots (docs/architecture.md V3 slice 1): the loaded dataset's kind
# selects the model, so dataset and model always match by construction
kind = spec.kind
if f"model_{kind}" not in st.session_state:
    screen = "Frequency Model" if kind == "frequency" else "Severity Model"
    st.info(f"Fit a {kind} model first — go to {screen}.")
    st.stop()

model = st.session_state[f"model_{kind}"]
meta = st.session_state[f"model_{kind}_meta"]
words = WORDING[kind]

col1, col2, col3, col4 = st.columns(4)
col1.metric("AIC", f"{meta['aic']:,.0f}")
col2.metric("BIC", f"{meta['bic']:,.0f}")
col3.metric("Deviance", f"{meta['deviance']:,.0f}")
col4.metric("Parameters", f"{meta['n_params']:,}")
st.caption(f"Model: `{meta['formula']}` ({meta['family']}, {kind})")

st.subheader("Coefficients with confidence intervals")
table = diagnostics.coefficient_table(model)
non_intercept = table[table["term"] != "Intercept"].copy()
top = non_intercept.reindex(non_intercept["coef"].abs().sort_values(ascending=False).index).head(20)
top["exp_ci_low"] = np.exp(top["ci_low"])
top["exp_ci_high"] = np.exp(top["ci_high"])
st.caption(
    f"{words['relativity']} with 95% confidence whiskers; the dashed line at 1.0 "
    "is 'no effect'. Whiskers crossing 1.0 mean the effect is not significant."
)
base = alt.Chart(top)
whiskers = base.mark_rule(color=ACCENT).encode(
    y=alt.Y("term", type="nominal", sort=None, title=None),
    x=alt.X("exp_ci_low", type="quantitative", title=words["relativity_axis"]),
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

# a model loaded from the run history is data-stripped (saved with remove_data):
# it predicts and reports coefficients, but carries no residual/fitted arrays
if meta.get("source") == "loaded":
    st.info(
        "This model was loaded from the run history — the saved file predicts and "
        "reports coefficients, but carries no residual data. Refit in this session "
        "to see residuals, the QQ plot, calibration and the full summary."
    )
    st.stop()

st.subheader("Residuals")
residual_kind = st.radio("Residual kind", diagnostics.RESIDUAL_KINDS, horizontal=True)
hist = diagnostics.residual_histogram(model, kind=residual_kind)
st.caption(words["residual_note"])
hist_chart = (
    alt.Chart(hist)
    .mark_bar(color=ACCENT)
    .encode(
        x=alt.X("residual", type="quantitative", title=f"{residual_kind} residual"),
        y=alt.Y("count", type="quantitative", title=words["residual_unit"]),
        tooltip=[
            alt.Tooltip("residual", type="quantitative", format=".2f"),
            alt.Tooltip("count", type="quantitative", format=","),
        ],
    )
)
st.altair_chart(hist_chart, use_container_width=True)

st.subheader("QQ plot")
qq = diagnostics.qq_data(model, kind=residual_kind)
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
        y=alt.Y("sample", type="quantitative", title=f"Sample {residual_kind} residual quantile"),
    )
)
qq_line = (
    alt.Chart(qq_span)
    .mark_line(strokeDash=[4, 4], color="gray")
    .encode(x="theoretical", y="sample")
)
st.altair_chart(qq_points + qq_line, use_container_width=True)

st.subheader("Observed vs Predicted")
if meta["n_obs"] != len(portfolio):
    st.info(
        f"The loaded dataset has {len(portfolio):,} rows but the model was fitted on "
        f"{meta['n_obs']:,} — refit the model on the current data to see its calibration."
    )
else:
    st.caption(words["calibration_note"])
    ovp = diagnostics.observed_vs_predicted(portfolio, spec, model)
    # engine columns are means per unit of the offset (frequency); with no offset
    # (severity) they are per-claim averages, i.e. average claim amounts
    ovp_long = ovp.melt(
        id_vars=["group", "exposure"],
        value_vars=["observed_mean", "predicted_mean"],
        var_name="series",
        value_name="value",
    )
    ovp_long["series"] = ovp_long["series"].map(
        {"observed_mean": "Observed", "predicted_mean": "Predicted"}
    )
    ovp_chart = (
        alt.Chart(ovp_long)
        .mark_bar()
        .encode(
            x=alt.X("group", type="nominal", sort=None, title=words["band_axis"]),
            xOffset=alt.XOffset("series", type="nominal"),
            y=alt.Y("value", type="quantitative", title=words["value_axis"]),
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
                alt.Tooltip("value", type="quantitative", format=words["value_format"]),
                alt.Tooltip(
                    "exposure", type="quantitative", format=",.0f", title=words["weight_label"]
                ),
            ],
        )
    )
    st.altair_chart(ovp_chart, use_container_width=True)
    with st.expander("Calibration table"):
        if kind == "severity":
            ovp = ovp.rename(
                columns={
                    "exposure": "claims",
                    "observed_mean": "observed_avg_claim_amount",
                    "predicted_mean": "predicted_avg_claim_amount",
                }
            )
        st.dataframe(ovp.round(4))

st.subheader("Model summary")
with st.expander("Full statsmodels summary"):
    st.text(model.summary().as_text())
