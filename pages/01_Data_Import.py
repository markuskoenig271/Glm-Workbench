"""Data Import (screen 2 in docs/ui_screens.md)."""

import streamlit as st

from pricing_engine import data

st.title("Data Import")

source = st.radio("Source", ["Built-in dataset", "CSV upload"], horizontal=True)

if source == "Built-in dataset":
    specs = data.list_datasets()
    labels = {spec.label: spec.name for spec in specs}
    chosen = st.selectbox("Dataset", list(labels))
    if st.button("Load dataset", type="primary"):
        try:
            df, spec = data.load_dataset(labels[chosen])
        except FileNotFoundError as exc:
            st.error(str(exc))
        else:
            st.session_state["portfolio"] = df
            st.session_state["spec"] = spec
            st.success(f"Loaded {spec.label}: {len(df):,} rows")
else:
    upload = st.file_uploader("Portfolio CSV", type="csv")
    if upload is not None:
        uploaded_df = data.load_portfolio(upload)
        columns = list(uploaded_df.columns)
        st.caption(f"Uploaded '{upload.name}': {len(uploaded_df):,} rows, {len(columns)} columns")

        st.markdown("**Column mapping** — describe the dataset for modelling:")
        target = st.selectbox("Target (claim count)", columns)
        offset_choice = st.selectbox("Offset (exposure, optional)", ["<none>", *columns])
        offset = None if offset_choice == "<none>" else offset_choice
        predictor_candidates = [c for c in columns if c not in {target, offset}]
        predictors = st.multiselect(
            "Predictors", predictor_candidates, default=predictor_candidates
        )

        if st.button("Use this dataset", type="primary"):
            spec = data.DatasetSpec(
                name="upload",
                label=f"Upload: {upload.name}",
                target=target,
                offset=offset,
                predictors=tuple(predictors),
            )
            st.session_state["portfolio"] = uploaded_df
            st.session_state["spec"] = spec
            st.success(f"Loaded {spec.label}: {len(uploaded_df):,} rows")

if "portfolio" in st.session_state:
    portfolio = st.session_state["portfolio"]
    active_spec = st.session_state["spec"]

    st.subheader("Preview")
    st.caption(
        f"Active dataset: {active_spec.label} — "
        f"{len(portfolio):,} rows × {portfolio.shape[1]} columns"
    )
    st.dataframe(portfolio.head(20))

    st.subheader("Validation report")
    findings = data.validate_portfolio(portfolio, active_spec)
    if findings:
        for finding in findings:
            st.warning(finding)
    else:
        st.success("No issues found — portfolio is ready for modelling.")
