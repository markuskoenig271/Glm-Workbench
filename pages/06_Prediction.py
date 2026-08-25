"""Prediction (screen 7 in docs/ui_screens.md) — kind-aware since V2."""

import pandas as pd
import streamlit as st

from pricing_engine import prediction

st.title("Prediction")

if "model" not in st.session_state:
    st.info("Fit a model first — go to Frequency Model or Severity Model.")
    st.stop()

model = st.session_state["model"]
meta = st.session_state["model_meta"]
kind = meta["kind"]
portfolio = st.session_state["portfolio"]
spec = st.session_state["spec"]

if spec.kind != kind:
    other = "Severity Model" if spec.kind == "severity" else "Frequency Model"
    st.info(
        f"The active model is a {kind} model but the loaded dataset is a {spec.kind} "
        f"dataset — fit a {spec.kind} model on it first (go to {other}) or reload the "
        f"{kind} dataset."
    )
    st.stop()

# --- single what-if ------------------------------------------------------------

if kind == "frequency":
    st.subheader("Single policy")
    st.caption(
        "Defaults describe the median policy — change inputs to see how the expected "
        "claim frequency reacts."
    )
else:
    st.subheader("Single claim")
    st.caption(
        "Defaults describe the median claim — change inputs to see how the expected "
        "claim amount reacts. One row per claim: there is no exposure to enter."
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
if kind == "frequency" and spec.offset is not None:
    exposure_value = st.number_input(
        f"{spec.offset} (policy-years)", value=1.0, min_value=0.01, key="sp_exposure"
    )

if st.button("Predict", type="primary"):
    row = pd.DataFrame([inputs])
    if kind == "frequency":
        if spec.offset is not None:
            row[spec.offset] = exposure_value
        row[spec.target] = 0
        result = prediction.predict_frequency(model, row, spec)
        frequency = float(result["expected_frequency"].iloc[0])
        claims = float(result["expected_claims"].iloc[0])
        col1, col2 = st.columns(2)
        col1.metric("Expected claim frequency", f"{frequency:.4f}", help="Claims per policy-year")
        col2.metric(
            "Expected claims",
            f"{claims:.4f}",
            help=f"For the entered exposure of {exposure_value:g} policy-years",
        )
    else:
        result = prediction.predict_severity(model, row, spec)
        amount = float(result["expected_claim_amount"].iloc[0])
        st.metric(
            "Expected claim amount",
            f"{amount:,.0f}",
            help="Expected size of one claim with these characteristics (model mean)",
        )

# --- batch -------------------------------------------------------------------

st.subheader("Batch prediction")
batch_label = "Predict for loaded portfolio" if kind == "frequency" else "Predict for loaded claims"
if st.button(batch_label):
    unit = "policies" if kind == "frequency" else "claims"
    with st.spinner(f"Predicting for {len(portfolio):,} {unit}..."):
        if kind == "frequency":
            batch = prediction.predict_frequency(model, portfolio, spec)
        else:
            batch = prediction.predict_severity(model, portfolio, spec)
    st.session_state["predictions"] = batch
    st.session_state["predictions_kind"] = kind
    st.session_state["predictions_csv"] = batch.to_csv(index=False).encode()

# a batch from the other model kind (single active-model slot) is never shown here
if "predictions" in st.session_state and st.session_state.get("predictions_kind") == kind:
    batch = st.session_state["predictions"]
    col1, col2, col3 = st.columns(3)
    if kind == "frequency":
        observed_total = int(batch[spec.target].sum())
        expected_total = float(batch["expected_claims"].sum())
        col1.metric("Mean expected frequency", f"{batch['expected_frequency'].mean():.4f}")
        col2.metric("Total expected claims", f"{expected_total:,.0f}")
        col3.metric("Total observed claims", f"{observed_total:,}")
        st.caption(
            "In-sample, a Poisson GLM with an intercept reproduces the observed claim "
            "total by construction — expected and observed totals should match closely."
        )
    else:
        observed_total = float(batch[spec.target].sum())
        expected_total = float(batch["expected_claim_amount"].sum())
        col1.metric("Mean expected claim amount", f"{batch['expected_claim_amount'].mean():,.0f}")
        col2.metric("Total expected claim amount", f"{expected_total:,.0f}")
        col3.metric("Total observed claim amount", f"{observed_total:,.0f}")
        st.caption(
            "Unlike Poisson, a log-link Gamma GLM does not reproduce the observed total "
            "exactly — its balance condition weights each claim by 1/mean, so a small "
            "in-sample gap between expected and observed totals is normal."
        )
    st.dataframe(batch.head(20))
    st.download_button(
        "Download predictions CSV",
        data=st.session_state["predictions_csv"],
        file_name=f"{kind}_predictions.csv",
        mime="text/csv",
    )
