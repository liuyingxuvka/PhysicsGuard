"""One bounded experiment using the existing native solver, not a new simulator."""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path

import yaml

from physicsguard.core.predictive_rollout import evaluate_predictive_rollout
from physicsguard.core.residual import ResidualBuilder
from physicsguard.core.solver import BoundedSolver
from physicsguard.schema.predictive_rollout import PredictiveRolloutPlanSpec
from physicsguard.schema.system_spec import SystemSpec


def _write(path, data):
    path.write_text(yaml.safe_dump(data), encoding="utf-8")


def _series(name, values, dt=1.):
    return {"series_id": name, "time_unit": "s", "points": [
        {"point_id": f"step_{i}", "timestamp": i * dt,
         "variables": {"filter.measured_current": {"value": value}}}
        for i, value in enumerate(values, start=1)]}


def _produce(model_path):
    model = yaml.safe_load(model_path.read_text(encoding="utf-8"))
    previous, values, runs = 0., [], []
    for _ in range(3):
        step = deepcopy(model)
        step["boundaries"] = [
            {"variable": "filter.true_value_current", "value": 2.},
            {"variable": "filter.measured_previous", "value": previous}]
        spec = SystemSpec.model_validate(step)
        result = BoundedSolver(ResidualBuilder(spec), spec.solver).solve()
        if not result.optimization_success or not result.audit_pass:
            raise AssertionError("native producer failed its own scalar solve")
        previous = result.variables["filter.measured_current"]
        values.append(previous)
        runs.append({"audit_pass": result.audit_pass, "nfev": result.nfev})
    return values, runs


def run_native_rollout_probe(base: Path):
    base.mkdir(parents=True, exist_ok=True)
    model = {"system_name": "native_filter_producer", "components": [{
        "id": "filter", "type": "SensorLowPassFilterStepModule",
        "parameters": {"tau_s": 2., "dt_s": 1.}}]}
    model_path = base / "native_model.yaml"
    _write(model_path, model)
    initial_digest = sha256(model_path.read_bytes()).hexdigest()
    produced, runs = _produce(model_path)
    _write(base / "prediction.yaml", _series("native_prediction", produced))
    # Frozen independent arithmetic oracle; not a claim of real sensor measurement.
    _write(base / "holdout.yaml", _series("analytic_holdout", [1., 1.5, 1.75]))
    _write(base / "training.yaml", {"series_id": "training", "points": [
        {"point_id": "initial", "timestamp": 0., "variables": {"filter.measured_current": {"value": 0.}}}]})
    ref = lambda name, file: {"identity_id": name, "path": file}
    plan = PredictiveRolloutPlanSpec.model_validate({
        "rollout_id": "native_filter_three_steps", "producer_id": "actual-native-bounded-solver",
        "model_identity": ref("filter_model", model_path.name),
        "training": [ref("training", "training.yaml")],
        "prediction_series": ref("prediction", "prediction.yaml"),
        "future_holdout_series": ref("holdout", "holdout.yaml"),
        "training_end_time": 0., "initial_state": {"filter.measured_previous": 0.},
        "step_size": 1., "step_unit": "s", "horizon_steps": 3,
        "target_signals": ["filter.measured_current"], "signal_scales": {"filter.measured_current": 1.},
        "threshold_source": "independent-three-step-arithmetic-control",
        "thresholds": {"maximum_worst_step_normalized_error": 1e-6,
            "maximum_accumulated_normalized_error": 3e-6, "maximum_absolute_lag_steps": 0,
            "maximum_phase_error": 0., "maximum_drift": 1e-6, "maximum_error_growth": 1e-6}})
    evaluate = lambda value: evaluate_predictive_rollout("stateful_dynamic", value, base_dir=base).result
    good = evaluate(plan)
    model["components"][0]["parameters"]["tau_s"] = 4.
    _write(model_path, model)
    changed_digest = sha256(model_path.read_bytes()).hexdigest()
    stale = evaluate(plan)  # No producer ran between model edit and this comparison.
    parameter_values, parameter_runs = _produce(model_path)
    _write(base / "parameter_prediction.yaml", _series("changed_parameter", parameter_values))
    parameter_plan = plan.model_copy(update={"prediction_series": plan.prediction_series.model_copy(update={"path": "parameter_prediction.yaml"})})
    changed_parameter = evaluate(parameter_plan)
    model["components"][0]["parameters"].update(tau_s=2., dt_s=.5)
    _write(model_path, model)
    step_values, step_runs = _produce(model_path)
    _write(base / "step_prediction.yaml", _series("changed_step", step_values, .5))
    step_plan = plan.model_copy(update={"prediction_series": plan.prediction_series.model_copy(update={"path": "step_prediction.yaml"})})
    changed_step = evaluate(step_plan)
    return {"reference_kind": "independent frozen arithmetic, not external physical measurement",
        "actual_native_solver_runs": 9, "normal_values": produced, "normal_runs": runs,
        "initial_model_sha256": initial_digest, "changed_model_sha256": changed_digest,
        "normal": good, "model_changed_old_prediction": stale,
        "changed_parameter_values": parameter_values, "parameter_runs": parameter_runs,
        "changed_parameter": changed_parameter, "changed_step_values": step_values,
        "step_runs": step_runs, "changed_step": changed_step}
