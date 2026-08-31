"""Pure Premium (screen 9 in docs/ui_screens.md, V3) — the quote calculator."""

import numpy as np
import pandas as pd
import streamlit as st

from pricing_engine import prediction

st.title("Pure Premium")

if "portfolio" not in st.session_state:
    st.info("Load a dataset first — go to Data Import.")
    st.stop()

portfolio = st.session_state["portfolio"]
spec = st.session_state["spec"]

if spec.kind != "frequency":
    st.info(
        "The active dataset is a severity dataset (claim amounts) — pure premium "
        "is quoted per policy. Load the frequency dataset in Data Import."
    )
    st.stop()

missing_models = [k for k in ("frequency", "severity") if f"model_{k}" not in st.session_state]
if missing_models == ["frequency", "severity"]:
    st.info(
        "Pure premium needs both models in session. Fit or load a frequency model "
        "on Frequency Model, and a severity model on Severity Model (load the "
        "severity dataset there first, then reload the frequency dataset — model "
        "slots survive the switch)."
    )
    st.stop()
if missing_models == ["frequency"]:
    st.info("No frequency model in session — fit or load one on Frequency Model.")
    st.stop()
if missing_models == ["severity"]:
    st.info(
        "No severity model in session — load the severity dataset in Data Import, "
        "fit or load a severity model on Severity Model, then reload the frequency "
        "dataset (model slots survive the switch)."
    )
    st.stop()

freq_model = st.session_state["model_frequency"]
sev_model = st.session_state["model_severity"]
freq_meta = st.session_state["model_frequency_meta"]
sev_meta = st.session_state["model_severity_meta"]

required = prediction.required_columns(freq_model, sev_model, spec)
missing_columns = [c for c in required if c not in portfolio.columns]
if missing_columns:
    st.info(
        f"The models need column(s) not present in the loaded portfolio: "
        f"{', '.join(missing_columns)} — rebuild them on Feature Engineering, or "
        "refit the models on predictors the portfolio carries."
    )
    st.stop()

st.caption(
    f"Frequency model: {freq_meta['family']} ({freq_meta['source']}) · "
    f"Severity model: {sev_meta['family']} ({sev_meta['source']}) — "
    "pure premium = expected claim frequency × expected claim amount."
)

# --- quote a policy -----------------------------------------------------------

st.subheader("Quote a policy")
st.caption(
    "Take out a policy: defaults describe the median policy — change the inputs "
    "and get the annual risk premium."
)

inputs: dict[str, object] = {}
columns = st.columns(3)
for i, column in enumerate(required):
    holder = columns[i % 3]
    series = portfolio[column]
    if pd.api.types.is_numeric_dtype(series):
        inputs[column] = holder.number_input(
            column, value=float(series.median()), key=f"pp_{column}"
        )
    else:
        levels = sorted(str(v) for v in series.dropna().unique())
        inputs[column] = holder.selectbox(column, levels, key=f"pp_{column}")

exposure_value = 1.0
if spec.offset is not None:
    exposure_value = st.number_input(
        f"{spec.offset} (policy-years)", value=1.0, min_value=0.01, key="pp_exposure"
    )

if st.button("Get quote", type="primary"):
    row = pd.DataFrame([inputs])
    if spec.offset is not None:
        row[spec.offset] = exposure_value
    row[spec.target] = 0
    quote = prediction.predict_pure_premium(freq_model, sev_model, row, spec)
    frequency = float(quote["expected_frequency"].iloc[0])
    amount = float(quote["expected_claim_amount"].iloc[0])
    premium = float(quote["expected_loss"].iloc[0])
    col1, col2, col3 = st.columns(3)
    col1.metric("Expected claim frequency", f"{frequency:.4f}", help="Claims per policy-year")
    col2.metric(
        "Expected claim amount",
        f"{amount:,.0f}",
        help="Expected size of one claim with these characteristics (model mean)",
    )
    col3.metric(
        "Risk premium",
        f"{premium:,.2f}",
        help=(
            f"Expected loss for the entered exposure of {exposure_value:g} "
            "policy-years = frequency × claim amount × exposure"
        ),
    )
    st.caption(
        "Risk premium only — no expenses, loadings, or profit. Assumes claim "
        "counts and claim sizes are independent given the rating factors."
    )

    st.markdown("**Premium breakdown**")
    base, factors = prediction.premium_breakdown(freq_model, sev_model, row, portfolio, spec)
    st.caption(
        f"Reference premium {base:,.2f} × the combined factors below × exposure "
        "reproduces the quote exactly (both models are log-link with no "
        "interactions, so the premium is multiplicative). The reference policy "
        "is artificial: every categorical at its baseline level, every numeric "
        "at the portfolio median. Severity factors hover near 1.00 on this data "
        "(BonusMalus is its only significant term) — most tariff "
        "differentiation comes from the frequency column."
    )
    display = factors.rename(
        columns={
            "predictor": "Rating factor",
            "value": "Your value",
            "frequency_factor": "Frequency relativity",
            "severity_factor": "Severity relativity",
            "combined_factor": "Combined",
        }
    )
    st.dataframe(display.round(3))

# --- portfolio batch ----------------------------------------------------------

st.subheader("Portfolio premiums")
if st.button("Compute premiums for loaded portfolio"):
    with st.spinner(f"Pricing {len(portfolio):,} policies..."):
        batch = prediction.predict_pure_premium(freq_model, sev_model, portfolio, spec)
    st.session_state["premium_batch"] = batch
    st.session_state["premium_batch_csv"] = batch.to_csv(index=False).encode()

if "premium_batch" in st.session_state:
    batch = st.session_state["premium_batch"]
    if spec.offset is not None and spec.offset in batch.columns:
        expected_claims = float((batch["expected_frequency"] * batch[spec.offset]).sum())
    else:
        expected_claims = float(batch["expected_frequency"].sum())
    col1, col2, col3 = st.columns(3)
    col1.metric("Total expected loss", f"{batch['expected_loss'].sum():,.0f}")
    col2.metric("Total expected claims", f"{expected_claims:,.0f}")
    col3.metric("Average annual premium", f"{batch['pure_premium'].mean():,.2f}")
    st.caption(
        "No observed-cost comparison is shown: a frequency portfolio records "
        "claim counts, not amounts — on freMTPL2 the severity table covers only "
        "~73% of the claims, so a like-for-like observed total does not exist "
        "in this data. Cross-check the expected-claims total on the Prediction "
        "screen instead. On the default freMTPL2 Gamma fit the log-link "
        "severity model runs about −1.5% below the observed claim total, and "
        "that gap propagates into the expected-loss total."
    )
    percentiles = [25, 50, 75, 95, 99]
    spread = pd.DataFrame(
        {
            "percentile": [f"p{p}" for p in percentiles],
            "annual premium": np.percentile(batch["pure_premium"], percentiles),
        }
    )
    st.caption("Tariff spread — annual premium percentiles across the portfolio:")
    st.dataframe(spread.round(2))
    st.dataframe(batch.head(20))
    st.download_button(
        "Download premiums CSV",
        data=st.session_state["premium_batch_csv"],
        file_name="pure_premium_predictions.csv",
        mime="text/csv",
    )
