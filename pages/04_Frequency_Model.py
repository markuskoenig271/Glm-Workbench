"""Frequency Model (screen 5 in docs/ui_screens.md)."""

import streamlit as st

from pricing_engine import diagnostics, glm, storage

st.title("Frequency Model")

if "portfolio" not in st.session_state:
    st.info("Load a dataset first — go to Data Import.")
    st.stop()

portfolio = st.session_state["portfolio"]
spec = st.session_state["spec"]

st.subheader("Model setup")
family = st.selectbox(
    "Distribution",
    glm.FREQUENCY_FAMILIES,
    format_func=lambda f: f.replace("_", " ").title(),
)
try:
    formula = glm.build_formula(spec)
except ValueError as exc:
    st.error(str(exc))
    st.stop()
st.code(formula, language="text")
if spec.offset is not None:
    st.caption(
        f"Log link with offset log({spec.offset}) — coefficients act multiplicatively "
        "on the expected claim frequency per policy-year."
    )
else:
    st.caption("Log link, no exposure offset (this dataset defines none).")

if st.button("Fit model", type="primary"):
    with st.spinner(f"Fitting {family} GLM on {len(portfolio):,} rows..."):
        model = glm.fit_frequency_glm(portfolio, formula, family=family, offset_column=spec.offset)
    info = diagnostics.information_criteria(model)
    st.session_state["freq_model"] = model
    st.session_state["freq_model_meta"] = {"formula": formula, "family": family, **info}
    with storage.connect() as conn:
        storage.record_model_run(
            conn,
            dataset=spec.name,
            target=spec.target,
            offset=spec.offset,
            formula=formula,
            family=family,
            n_obs=info["n_obs"],
            aic=info["aic"],
            bic=info["bic"],
            deviance=info["deviance"],
            log_likelihood=info["log_likelihood"],
            coefficients=model.params.to_dict(),
        )
    st.success(f"Model fitted and recorded (AIC {info['aic']:,.0f}).")

if "freq_model" in st.session_state:
    model = st.session_state["freq_model"]
    meta = st.session_state["freq_model_meta"]

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("AIC", f"{meta['aic']:,.0f}")
    col2.metric("BIC", f"{meta['bic']:,.0f}")
    col3.metric("Deviance", f"{meta['deviance']:,.0f}")
    col4.metric("Parameters", f"{meta['n_params']:,}")

    st.subheader("Coefficients")
    table = diagnostics.coefficient_table(model)
    st.caption(
        "exp(coef) is the risk relativity: how one unit (or one level vs the baseline) "
        "multiplies the expected claim frequency."
    )
    st.dataframe(table.round(4))

    non_intercept = table[table["term"] != "Intercept"]
    significant = non_intercept[non_intercept["significant"]]
    top = significant.reindex(significant["coef"].abs().sort_values(ascending=False).index).head(5)
    if not top.empty:
        st.markdown("**What the strongest effects mean:**")
        for _, row in top.iterrows():
            pct = (row["exp_coef"] - 1) * 100
            direction = "higher" if pct > 0 else "lower"
            if "[T." in row["term"]:
                variable, level = row["term"].split("[T.")
                level = level.rstrip("]")
                st.markdown(
                    f"- **{row['term']}**: policies with {variable} = {level} show "
                    f"{abs(pct):.0f}% {direction} expected claim frequency than the "
                    f"baseline level (relativity {row['exp_coef']:.3f})."
                )
            else:
                st.markdown(
                    f"- **{row['term']}**: each additional unit multiplies expected "
                    f"claim frequency by {row['exp_coef']:.3f} ({pct:+.1f}%)."
                )

    insignificant = non_intercept[~non_intercept["significant"]]
    if not insignificant.empty:
        st.warning(
            "Statistically insignificant terms (p ≥ 0.05) — candidates for removal: "
            + ", ".join(insignificant["term"])
        )
    else:
        st.caption("All model terms are statistically significant (p < 0.05).")

st.subheader("Run history")
with storage.connect() as conn:
    runs = storage.list_model_runs(conn)
if runs.empty:
    st.caption("No model runs recorded yet — fit a model above.")
else:
    st.caption("Recorded in SQLite — survives browser refreshes and app restarts.")
    st.dataframe(
        runs[
            ["id", "created_at", "dataset", "family", "formula", "n_obs", "aic", "bic", "deviance"]
        ].round(1)
    )
