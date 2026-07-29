"""TC3 supplements from stepwise-selection.md: forward direction, refit
reproduces the log's final AIC, run-history row count unchanged.

Engine-only (no app). Run from the repo root:
    uv run python e2e/e2e_stepwise_tc3b.py
"""

import time
from dataclasses import replace

from pricing_engine import storage
from pricing_engine.data import load_dataset
from pricing_engine.glm import fit_frequency_glm, stepwise_selection

df, spec = load_dataset("fremtpl2_freq")
reduced = replace(spec, predictors=("BonusMalus", "DrivAge", "VehGas"))

with storage.connect() as conn:
    runs_before = len(storage.list_model_runs(conn))

# forward direction on the real data
messages: list[str] = []
t0 = time.perf_counter()
selected_f, log_f = stepwise_selection(df, reduced, direction="forward", on_fit=messages.append)
elapsed_f = time.perf_counter() - t0
assert elapsed_f < 360, elapsed_f
assert "BonusMalus" in selected_f, selected_f
assert set(selected_f) <= set(reduced.predictors)
assert log_f.iloc[0]["action"] == "start"
assert (log_f["value"].diff().dropna() <= 0).all()
assert (log_f["n_predictors"].diff().dropna() == 1).all()  # forward adds one per step
assert len([m for m in messages if m]) >= 3

# refit with the selected predictors reproduces the log's final criterion value
terms = " + ".join(selected_f)
refit = fit_frequency_glm(df, f"{reduced.target} ~ {terms}", offset_column=reduced.offset)
final_logged = float(log_f.iloc[-1]["value"])
assert abs(float(refit.aic) - final_logged) < 0.5, (refit.aic, final_logged)

# ValueErrors are fast (no fitting before validation)
t0 = time.perf_counter()
for kwargs in ({"direction": "sideways"}, {"criterion": "r2"}):
    try:
        stepwise_selection(df, reduced, **kwargs)  # type: ignore[arg-type]
        raise SystemExit(f"FAIL: no ValueError for {kwargs}")
    except ValueError:
        pass
assert time.perf_counter() - t0 < 1.0

# run history untouched by selection
with storage.connect() as conn:
    runs_after = len(storage.list_model_runs(conn))
assert runs_after == runs_before, (runs_before, runs_after)

print(
    f"TC3 SUPPLEMENT PASS (forward {elapsed_f:.0f}s, selected={selected_f}, "
    f"actions={list(log_f['action'])}, refit AIC matches log: {final_logged:,.0f}, "
    f"run history {runs_before} -> {runs_after})"
)
