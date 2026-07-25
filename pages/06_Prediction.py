"""Prediction (screen 7 in docs/ui_screens.md)."""

import pandas as pd
import streamlit as st

from pricing_engine import prediction

st.title("Prediction")

if "freq_model" not in st.session_state:
    st.info("Fit a model first — go to Frequency Model.")
    st.stop()

model = st.session_state["freq_model"]
portfolio = st.session_state["portfolio"]
spec = st.session_state["spec"]

st.subheader("Single policy")
st.caption(
    "Defaults describe the median policy — change inputs to see how the expected "
    "claim frequency reacts."
)
inputs: dict[str, object] = {}
columns = st.columns(3)
for i, predictor in enumerate(spec.predictors):
    holder = columns[i % 3]
    series = portfolio[predictor]
    if pd.api.types.is_numeric_dtype(series):
        inputs[predictor] = holder.number_input(
            predictor, value=float(series.median()), key=f"sp_{predictor}"
        )
    else:
        levels = sorted(str(v) for v in series.dropna().unique())
        inputs[predictor] = holder.selectbox(predictor, levels, key=f"sp_{predictor}")

exposure_value = 1.0
if spec.offset is not None:
    exposure_value = st.number_input(
        f"{spec.offset} (policy-years)", value=1.0, min_value=0.01, key="sp_exposure"
    )

if st.button("Predict", type="primary"):
    policy = pd.DataFrame([inputs])
    if spec.offset is not None:
        policy[spec.offset] = exposure_value
    policy[spec.target] = 0
    result = prediction.predict_frequency(model, policy, spec)
    frequency = float(result["expected_frequency"].iloc[0])
    claims = float(result["expected_claims"].iloc[0])
    col1, col2 = st.columns(2)
    col1.metric("Expected claim frequency", f"{frequency:.4f}", help="Claims per policy-year")
    col2.metric(
        "Expected claims",
        f"{claims:.4f}",
        help=f"For the entered exposure of {exposure_value:g} policy-years",
    )

st.subheader("Batch prediction")
if st.button("Predict for loaded portfolio"):
    with st.spinner(f"Predicting for {len(portfolio):,} policies..."):
        batch = prediction.predict_frequency(model, portfolio, spec)
    st.session_state["predictions"] = batch
    st.session_state["predictions_csv"] = batch.to_csv(index=False).encode()

if "predictions" in st.session_state:
    batch = st.session_state["predictions"]
    observed_total = int(batch[spec.target].sum())
    expected_total = float(batch["expected_claims"].sum())
    col1, col2, col3 = st.columns(3)
    col1.metric("Mean expected frequency", f"{batch['expected_frequency'].mean():.4f}")
    col2.metric("Total expected claims", f"{expected_total:,.0f}")
    col3.metric("Total observed claims", f"{observed_total:,}")
    st.caption(
        "In-sample, a Poisson GLM with an intercept reproduces the observed claim "
        "total by construction — expected and observed totals should match closely."
    )
    st.dataframe(batch.head(20))
    st.download_button(
        "Download predictions CSV",
        data=st.session_state["predictions_csv"],
        file_name="predictions.csv",
        mime="text/csv",
    )
