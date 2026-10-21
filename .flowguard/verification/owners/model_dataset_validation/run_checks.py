"""Run FlowGuard checks for PhysicsGuard model-dataset validation and replay them on the real code."""

from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "models/owners"))

import yaml
from flowguard.explorer import Explorer

from model_dataset_validation import physicsguard_model_dataset_validation_model as model

ROOT = Path(__file__).resolve().parents[4]
PUMP = ROOT / "examples" / "testfile_contracts" / "pump_loop"
IMPLEMENTED_BY = {
    "CheckContracts": "src/physicsguard/core/model_dataset_validation.py:_contract_findings",
    "GateValidationDepth": "src/physicsguard/core/validation_depth.py:evaluate_validation_depth",
    "GateValidationDepth.adequacy": "src/physicsguard/core/validation_adequacy.py:evaluate_validation_adequacy_artifacts",
    "RunDirectValidation": "src/physicsguard/core/model_dataset_validation.py:_evaluate",
    "OptionalCalibration": "src/physicsguard/core/model_dataset_validation.py:_calibration_summary",
    "GateValidationClaim": "src/physicsguard/core/model_dataset_validation.py:_status",
}
TESTED_BY = {
    "no_pass_without_contracts": [
        "tests/test_model_dataset_validation.py:test_enabled_calibration_requires_bounded_parameters",
    ],
    "no_pass_without_depth_inputs": [
        "tests/test_validation_depth_receipts.py:test_uncertain_required_mapping_blocks_broad_validation",
        "tests/test_validation_depth_receipts.py:test_adequacy_floors_are_warnings_not_failures",
    ],
    "no_pass_without_holdout_and_feedback": [
        "tests/test_validation_depth_receipts.py:test_identical_content_under_different_holdout_label_is_overlap",
    ],
}
EXPECTED_STATUS = {"ValidationPassed": "pass", "ValidationPartial": "partial", "ValidationBlocked": "fail"}


def _load(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _write(path: Path, data: dict) -> None:
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def _edit_plan(pump: Path, name: str, change) -> Path:
    path = pump / "validation" / name
    data = _load(path)
    change(pump, data)
    _write(path, data)
    return path


def _rollout(semantics: str):
    def change(pump: Path, plan: dict) -> None:
        def ref(identity_id: str, relative: str, cases=()):
            return {"identity_id": identity_id, "path": f"../{relative}", "case_ids": list(cases)}

        plan["depth"]["model_semantics"] = semantics
        plan["depth"]["predictive_rollout"] = {
            "rollout_id": "conformance_rollout",
            "producer_receipt_id": "conformance-producer",
            "model_identity": ref("pump_model", "model/pump_loop_hierarchy.yaml"),
            "training": [ref("training_series", "observed/clean_observed_series.yaml", ["baseline_case", "speed_ramp_case_01", "speed_ramp_case_02"])],
            "prediction_series": ref("prediction", "observed/predicted_future_series.yaml"),
            "future_holdout_series": ref("future_holdout", "observed/future_holdout_series.yaml", ["future_case_1", "future_case_2", "future_case_3"]),
            "training_end_time": 0.2,
            "initial_state": {"pump_signal_map.x": 11.0, "pump_signal_map.y": 22.0},
            "step_size": 1.0,
            "step_unit": "s",
            "horizon_steps": 3,
            "target_signals": ["pump_signal_map.x", "pump_signal_map.y"],
            "signal_scales": {"pump_signal_map.x": 1.0, "pump_signal_map.y": 2.0},
            "threshold_source": "conformance thresholds",
            "thresholds": {
                "maximum_worst_step_normalized_error": 0.0,
                "maximum_accumulated_normalized_error": 0.0,
                "maximum_absolute_lag_steps": 0,
                "maximum_phase_error": 0.0,
                "maximum_drift": 0.0,
                "maximum_error_growth": 0.0,
            },
        }

    return change


def _uncertain_mapping(pump: Path, plan: dict) -> None:
    edges_path = pump / "coverage" / "pump_loop_mapping_edges.yaml"
    edges = _load(edges_path)
    edge = next(item for item in edges["edges"] if item["target"] == "pump_signal_map.y")
    edge["confidence"] = 0.4
    _write(edges_path, edges)


def _snapshot_overclaim(pump: Path, plan: dict) -> None:
    series_path = pump / "observed" / "clean_observed_series.yaml"
    series = _load(series_path)
    series["points"] = series["points"][:1]
    _write(series_path, series)
    plan["depth"]["time_scope"] = {"claim_scope": "time_window", "start_time": 0.0, "end_time": 0.0, "time_unit": "s", "expected_point_count": 1}
    plan["depth"]["scenarios"] = plan["depth"]["scenarios"][:1]


def _split_overlap(pump: Path, plan: dict) -> None:
    shutil.copyfile(pump / "observed" / "calibration_train.yaml", pump / "observed" / "renamed_holdout.yaml")
    plan["calibration"]["holdout_observed"] = "../observed/renamed_holdout.yaml"
    plan["depth"] = _load(pump / "validation" / "clean_validation_plan.yaml")["depth"]
    plan["depth"]["split"] = {
        "training": [{"identity_id": "train", "path": "../observed/calibration_train.yaml", "case_ids": ["training_case"]}],
        "holdout": [{"identity_id": "holdout", "path": "../observed/renamed_holdout.yaml", "case_ids": ["holdout_case"]}],
    }


def _invalid_series_point(pump: Path, plan: dict) -> None:
    series_path = pump / "observed" / "clean_observed_series.yaml"
    series = _load(series_path)
    series["points"][1].update({"valid": False, "invalid_reason": "sensor export gap", "variables": {}})
    _write(series_path, series)


def _failing_holdout(pump: Path, plan: dict) -> None:
    holdout_path = pump / "observed" / "calibration_holdout.yaml"
    holdout = _load(holdout_path)
    for name, item in holdout["variables"].items():
        if name.endswith(".y"):
            item["value"] = float(item["value"]) * 3.0
    _write(holdout_path, holdout)
    plan["observed_file"] = "../observed/clean_observed.yaml"


REAL_CASES = {
    "clean_no_calibration": ("clean_validation_plan.yaml", lambda pump, plan: None),
    "missing_contract": ("clean_validation_plan.yaml", lambda pump, plan: plan["contracts"][0].update(contract="../contracts/unclassified_contract.yaml")),
    "calibrated_pass": ("calibration_validation_plan.yaml", lambda pump, plan: plan.update(observed_file="../observed/clean_observed.yaml")),
    "optimizer_only": ("calibration_validation_plan.yaml", _failing_holdout),
    "unbounded_calibration": ("calibration_validation_plan.yaml", lambda pump, plan: plan["calibration"]["parameters"][0].pop("upper")),
    "missing_dataset_file": ("clean_validation_plan.yaml", lambda pump, plan: plan["depth"]["dataset"]["files"][0].update(path="../data/missing.csv")),
    "uncertain_mapping": ("clean_validation_plan.yaml", _uncertain_mapping),
    "snapshot_overclaim": ("clean_validation_plan.yaml", _snapshot_overclaim),
    "split_overlap": ("calibration_validation_plan.yaml", _split_overlap),
    "series_missing": ("clean_validation_plan.yaml", _invalid_series_point),
    "one_point_time_varying_parameter": ("shallow_time_varying_validation_plan.yaml", lambda pump, plan: None),
    "pointwise_prediction": ("clean_validation_plan.yaml", _rollout("pointwise")),
    "stateful_rollout_pass": ("clean_validation_plan.yaml", _rollout("stateful_dynamic")),
}


def conformance() -> list[str]:
    """Run each mapped model case through validate_model_dataset; return the mismatches."""

    if str(ROOT / "src") not in sys.path:
        sys.path.insert(0, str(ROOT / "src"))
    from physicsguard.core.model_dataset_validation import validate_model_dataset

    workflow = model.build_workflow()
    inputs = {item.case_id: item for item in (*model.EXTERNAL_INPUTS, *model.DEPTH_EXTERNAL_INPUTS)}
    mismatches = []
    with tempfile.TemporaryDirectory() as tmp:
        for index, (case_id, (plan_name, change)) in enumerate(REAL_CASES.items()):
            pump = Path(tmp) / f"case_{index}" / "pump_loop"
            shutil.copytree(PUMP, pump)
            plan = _edit_plan(pump, plan_name, change)
            try:
                real_status = validate_model_dataset(plan).status
            except ValueError:
                real_status = "fail"
            run = workflow.execute(model.initial_state(), inputs[case_id], terminal_predicate=model.terminal_predicate)
            expected = EXPECTED_STATUS[type(run.completed_paths[0].current_input).__name__]
            if real_status != expected:
                mismatches.append(f"{case_id}: real status {real_status!r}, model expects {expected!r}")
    return mismatches


def main() -> int:
    report = Explorer(
        workflow=model.build_workflow(),
        initial_states=(model.initial_state(),),
        external_inputs=model.EXTERNAL_INPUTS,
        invariants=model.INVARIANTS,
        max_sequence_length=model.MAX_SEQUENCE_LENGTH,
        terminal_predicate=model.terminal_predicate,
        required_labels=(
            "contracts_passed",
            "direct_validation_ran",
            "calibration_not_enabled",
            "calibration_bounded",
            "validation_passed",
            "holdout_partial",
            "contracts_block_validation",
            "observed_mutation_blocked",
            "calibration_unbounded_blocked",
        ),
    ).explore()
    depth_report = Explorer(
        workflow=model.build_workflow(),
        initial_states=(model.initial_state(),),
        external_inputs=model.DEPTH_EXTERNAL_INPUTS,
        invariants=model.INVARIANTS,
        max_sequence_length=1,
        terminal_predicate=model.terminal_predicate,
        required_labels=(
            "dataset_files_missing_blocked",
            "mapping_review_uncertain_blocked",
            "split_overlap_blocked",
            "parameter_temporal_adequacy_failed_warning",
            "static_parameter_binding_missing_warning",
            "pointwise_prediction_forbidden_blocked",
            "validation_passed",
        ),
    ).explore()
    print(report.format_text())
    print(depth_report.format_text())
    mismatches = conformance()
    print(f"conformance: {len(REAL_CASES) - len(mismatches)}/{len(REAL_CASES)} model cases match the real code")
    for line in mismatches:
        print(f"  mismatch: {line}")
    return 0 if report.ok and depth_report.ok and not mismatches else 1


if __name__ == "__main__":
    from flowguard.map.runner import run_owner
    raise SystemExit(run_owner(main))
