"""Frequency Model (screen 5 in docs/ui_screens.md)."""

from dataclasses import replace

import streamlit as st

from pricing_engine import diagnostics, glm, storage

st.title("Frequency Model")

if "portfolio" not in st.session_state:
    st.info("Load a dataset first — go to Data Import.")
    st.stop()

portfolio = st.session_state["portfolio"]
spec = st.session_state["spec"]

if spec.kind != "frequency":
    st.info(
        "The active dataset is a severity dataset (claim amounts) — use the "
        "Severity Model screen to fit it."
    )
    st.stop()

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
    # per-kind model slot (docs/architecture.md V3 slice 1): a severity model may coexist
    st.session_state["model_frequency"] = model
    st.session_state["model_frequency_meta"] = {
        "formula": formula,
        "family": family,
        "kind": "frequency",
        "source": "fitted",
        **info,
    }
    with storage.connect() as conn:
        run_id = storage.record_model_run(
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
        try:
            storage.save_model(conn, run_id, model)
        except OSError as exc:  # the run row stays valid, just not loadable
            st.warning(f"Model recorded but the model file could not be saved: {exc}")
        else:
            st.success(f"Model fitted and recorded (AIC {info['aic']:,.0f}) — saved for reuse.")

if "model_frequency" in st.session_state:
    model = st.session_state["model_frequency"]
    meta = st.session_state["model_frequency_meta"]

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

st.subheader("Variable selection")
st.caption(
    "Automated stepwise selection by information criterion. On a portfolio this "
    "large nearly every term is 'significant', so selection goes by AIC/BIC — "
    "a full pass refits the model many times (expect several minutes)."
)
sel_col1, sel_col2 = st.columns(2)
direction = sel_col1.radio(
    "Direction", glm.SELECTION_DIRECTIONS, horizontal=True, format_func=str.title
)
criterion = sel_col2.radio(
    "Criterion", glm.SELECTION_CRITERIA, horizontal=True, format_func=str.upper
)

if flash := st.session_state.pop("adopt_flash", None):
    st.success(flash)

if st.button("Run selection"):
    with st.status(
        f"Running {direction} selection by {criterion.upper()}...", expanded=True
    ) as status:
        progress_line = st.empty()
        selected, step_log = glm.stepwise_selection(
            portfolio,
            spec,
            family=family,
            direction=direction,
            criterion=criterion,
            on_fit=lambda msg: progress_line.text(msg),
        )
        progress_line.empty()
        status.update(label="Selection complete", state="complete")
    st.session_state["selection_result"] = {
        "selected": selected,
        "log": step_log,
        "direction": direction,
        "criterion": criterion,
    }

if "selection_result" in st.session_state:
    result = st.session_state["selection_result"]
    chosen = ", ".join(result["selected"]) if result["selected"] else "(intercept only)"
    st.markdown(
        f"**Selected predictors ({len(result['selected'])}), "
        f"{result['direction']} by {result['criterion'].upper()}:** {chosen}"
    )
    st.dataframe(result["log"].round(1))

    def _adopt_selection() -> None:
        outcome = st.session_state["selection_result"]
        st.session_state["spec"] = replace(
            st.session_state["spec"], predictors=tuple(outcome["selected"])
        )
        if "predictor_select" in st.session_state:
            st.session_state["predictor_select"] = list(outcome["selected"])
        st.session_state["adopt_flash"] = (
            f"Adopted {len(outcome['selected'])} predictor(s) — the formula above is "
            "updated; fit the model to record the leaner run."
        )

    st.button("Adopt selected predictors", on_click=_adopt_selection)

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

    if flash := st.session_state.pop("load_flash_frequency", None):
        (st.success if flash[0] == "success" else st.error)(flash[1])

    loadable = runs[runs["family"].isin(glm.FREQUENCY_FAMILIES) & runs["model_path"].notna()]
    if loadable.empty:
        st.caption(
            "No saved frequency model files yet — runs recorded before model "
            "persistence have none; fit a model to save one."
        )
    else:
        by_id = loadable.set_index("id")

        def _load_saved_model() -> None:
            run_id = int(st.session_state["load_run_frequency"])
            try:
                with storage.connect() as conn:
                    loaded, loaded_meta = storage.load_model(conn, run_id)
            except (ValueError, FileNotFoundError) as exc:
                st.session_state["load_flash_frequency"] = ("error", str(exc))
                return
            except Exception as exc:  # noqa: BLE001 — unreadable pickle stays friendly
                st.session_state["load_flash_frequency"] = (
                    "error",
                    f"The saved model file could not be read — refit instead. ({exc})",
                )
                return
            st.session_state["model_frequency"] = loaded
            st.session_state["model_frequency_meta"] = loaded_meta
            st.session_state["load_flash_frequency"] = (
                "success",
                f"Loaded run {run_id} ({loaded_meta['family']}, "
                f"AIC {loaded_meta['aic']:,.0f}) — no refit needed.",
            )

        st.selectbox(
            "Load a saved frequency model",
            loadable["id"].tolist(),
            format_func=lambda rid: (
                f"Run {rid} · {by_id.loc[rid, 'created_at']} · {by_id.loc[rid, 'family']} "
                f"· AIC {by_id.loc[rid, 'aic']:,.0f}"
            ),
            key="load_run_frequency",
        )
        st.button("Load saved model", on_click=_load_saved_model)
        st.caption(
            "Loading restores the fitted model without the ~12s refit — it predicts "
            "and reports coefficients; residual diagnostics need a fresh fit."
        )
