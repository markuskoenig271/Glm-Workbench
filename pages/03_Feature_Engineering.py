"""Feature Engineering (screen 4 in docs/ui_screens.md)."""

from dataclasses import replace

import pandas as pd
import streamlit as st

from pricing_engine import preprocessing

st.title("Feature Engineering")

if "portfolio" not in st.session_state:
    st.info("Load a dataset first — go to Data Import.")
    st.stop()

portfolio: pd.DataFrame = st.session_state["portfolio"]
spec = st.session_state["spec"]

if "predictor_select" not in st.session_state:
    st.session_state["predictor_select"] = list(spec.predictors)

if flash := st.session_state.pop("fe_flash", None):
    st.success(flash)

special = {spec.target, spec.offset, "IDpol"}
candidates = [c for c in portfolio.columns if c not in special]


def _apply_predictors() -> None:
    current = st.session_state["spec"]
    st.session_state["spec"] = replace(
        current, predictors=tuple(st.session_state["predictor_select"])
    )


def _cap_exposure() -> None:
    df = st.session_state["portfolio"]
    current = st.session_state["spec"]
    capped, n_capped = preprocessing.cap_column(df, current.offset, 1.0)
    st.session_state["portfolio"] = capped
    st.session_state["fe_flash"] = (
        f"Capped {n_capped:,} value(s) of {current.offset} at 1.0 policy-years."
    )


def _create_band() -> None:
    df = st.session_state["portfolio"]
    banded, new_column = preprocessing.bin_numeric(
        df,
        st.session_state["bin_column"],
        bins=st.session_state["bin_bands"],
        strategy=st.session_state["bin_strategy"],
    )
    st.session_state["portfolio"] = banded
    predictors = list(st.session_state["predictor_select"])
    if new_column not in predictors:
        predictors.append(new_column)
    st.session_state["predictor_select"] = predictors
    st.session_state["spec"] = replace(st.session_state["spec"], predictors=tuple(predictors))
    n_bands = banded[new_column].nunique()
    st.session_state["fe_flash"] = (
        f"Added banded variable '{new_column}' ({n_bands} bands) to the model predictors."
    )


def _add_log() -> None:
    df = st.session_state["portfolio"]
    column = st.session_state["log_column"]
    st.session_state["portfolio"] = preprocessing.log_transform(df, [column])
    new_column = f"{column}_log"
    predictors = list(st.session_state["predictor_select"])
    if new_column not in predictors:
        predictors.append(new_column)
    st.session_state["predictor_select"] = predictors
    st.session_state["spec"] = replace(st.session_state["spec"], predictors=tuple(predictors))
    st.session_state["fe_flash"] = f"Added log variable '{new_column}' to the model predictors."


st.subheader("Variables")
st.multiselect(
    "Model predictors",
    candidates,
    key="predictor_select",
    on_change=_apply_predictors,
    help="Deselect a variable to exclude it from the model formula.",
)

if spec.offset is not None:
    st.subheader("Exposure")
    n_over = int((portfolio[spec.offset] > 1.0).sum())
    st.caption(
        f"{n_over:,} rows have {spec.offset} above 1.0 policy-years. The literature "
        "caps exposure at 1 (a policy cannot be at risk for more than a year per record)."
    )
    st.button(f"Cap {spec.offset} at 1.0", on_click=_cap_exposure, disabled=n_over == 0)

st.subheader("Binning")
numeric_candidates = [c for c in candidates if pd.api.types.is_numeric_dtype(portfolio[c])]
if numeric_candidates:
    st.selectbox("Numeric variable", numeric_candidates, key="bin_column")
    st.slider("Bands", min_value=2, max_value=12, value=8, key="bin_bands")
    st.radio(
        "Strategy",
        preprocessing.BIN_STRATEGIES,
        key="bin_strategy",
        horizontal=True,
        format_func=lambda s: f"{s} (equal exposure)" if s == "quantile" else f"{s} (equal width)",
    )
    st.button("Create banded variable", on_click=_create_band)
else:
    st.caption("No numeric variables available for binning.")

st.subheader("Log transform")
positive_candidates = [c for c in numeric_candidates if bool((portfolio[c] > 0).all())]
if positive_candidates:
    st.selectbox("Strictly positive variable", positive_candidates, key="log_column")
    st.button("Add log variable", on_click=_add_log)
else:
    st.caption("No strictly positive numeric variables available.")

st.subheader("Encoding")
st.info(
    "Categorical predictors are encoded automatically (treatment coding) when the GLM "
    "is fitted — no manual one-hot encoding is needed."
)

st.subheader("Current model specification")
current_spec = st.session_state["spec"]
offset_text = current_spec.offset if current_spec.offset is not None else "(none)"
st.markdown(
    f"- **Target:** {current_spec.target}\n"
    f"- **Offset:** {offset_text}\n"
    f"- **Predictors ({len(current_spec.predictors)}):** " + ", ".join(current_spec.predictors)
)
