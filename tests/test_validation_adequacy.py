from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from physicsguard.core.model_dataset_validation import validate_model_dataset
from physicsguard.core.project_closure import _consume_validation_depth_receipt
from physicsguard.core.validation_adequacy import evaluate_validation_adequacy_artifacts
from physicsguard.core.validation_depth import _residual_series_receipt
from physicsguard.io.hierarchy_loader import load_hierarchical_audit_spec
from physicsguard.io.observation_loader import load_observed_series
from physicsguard.io.test_file_contract_loader import (
    load_data_file_manifest,
    load_model_validation_plan,
    load_parameter_role_matrix,
    load_project_evidence_registry,
)
from physicsguard.schema.data_file_manifest import DataFileManifestSpec
from physicsguard.schema.model_dataset_validation import ModelValidationPlanSpec, ValidationVariableRoleSpec
from physicsguard.schema.parameter_coverage import ParameterRoleMatrixSpec
from physicsguard.schema.validation_adequacy import ParameterTemporalPolicySpec, ValidationAdequacyPlanSpec
from physicsguard.schema.validation_depth import ObservedSeriesSpec


ROOT = Path(__file__).resolve().parents[1]
PUMP = ROOT / "examples" / "testfile_contracts" / "pump_loop"


def _inputs():
    plan = load_model_validation_plan(PUMP / "validation" / "clean_validation_plan.yaml")
    audit = load_hierarchical_audit_spec(PUMP / "model" / "pump_loop_hierarchy.yaml")
    manifest = load_data_file_manifest(PUMP / "data" / "clean_manifest.yaml")
    roles = load_parameter_role_matrix(PUMP / "coverage" / "pump_loop_role_matrix.yaml")
    series = load_observed_series(PUMP / "observed" / "clean_observed_series.yaml")
    registry = load_project_evidence_registry(PUMP / "evidence" / "project_evidence_registry.yaml")
    bundle = next(item for item in registry.evidence_bundles if item.bundle_id == "pump_loop_validation_bundle_001")
    bindings = [item for item in registry.evidence_bindings if item.binding_id in set(bundle.bindings)]
    return plan, audit, manifest, roles, series, bindings


def _residual(points, *, blocked_parameters: set[str] | None = None):
    blocked_parameters = blocked_parameters or set()
    parameter_ids = sorted(
        {
            target
            for point in points
            for target in point.variables
            if target not in {"pump_signal_map.x", "pump_signal_map.y"}
        }
    )
    contributions = []
    for parameter_id in parameter_ids:
        present = [point for point in points if parameter_id in point.variables]
        distinct_count = len(
            {point.variables[parameter_id].value for point in present}
        )
        blocked = parameter_id in blocked_parameters or distinct_count < 2
        contributions.append(
            {
                "parameter_id": parameter_id,
                "expectation": "sensitive",
                "model_parameter_exists": not blocked,
                "observed_point_ids": [point.point_id for point in present],
                "applied_point_ids": [point.point_id for point in present],
                "counterfactual_point_ids": [point.point_id for point in present],
                "distinct_observed_value_count": distinct_count,
                "maximum_normalized_residual_effect": None if blocked else 1.0,
                "affected_residual_ids": [] if blocked else ["fixture_residual"],
                "status": "blocked" if blocked else "pass",
                "non_sensitive_reason": None,
                "non_sensitive_claim_boundary": None,
            }
        )
    return {
        "points": [{"point_id": point.point_id, "status": "pass"} for point in points],
        "parameter_contributions": contributions,
    }


def _time_varying_policy(
    parameter_id: str,
    *,
    minimum_valid_points: int = 3,
    minimum_valid_ratio: float = 0.003,
    minimum_time_span: float = 1.0,
    maximum_time_gap: float = 600.0,
) -> dict[str, object]:
    return {
        "parameter_id": parameter_id,
        "temporal_behavior": "time_varying",
        "classification_source": "fixture target-owned temporal policy v1",
        "availability_source_id": "manifest:rows",
        "minimum_valid_points": minimum_valid_points,
        "minimum_valid_ratio": minimum_valid_ratio,
        "minimum_distinct_timestamps": 3,
        "minimum_time_span": minimum_time_span,
        "maximum_time_gap": maximum_time_gap,
        "contribution_expectation": "sensitive",
        "minimum_normalized_contribution_effect": 1.0e-9,
        "required_strata": [
            {
                "stratum_id": "startup",
                "start_fraction": 0.0,
                "end_fraction": 0.2,
                "minimum_valid_points": 1,
            },
            {
                "stratum_id": "steady",
                "start_fraction": 0.4,
                "end_fraction": 0.6,
                "minimum_valid_points": 1,
            },
            {
                "stratum_id": "shutdown",
                "start_fraction": 0.8,
                "end_fraction": 1.0,
                "minimum_valid_points": 1,
            },
        ],
    }


def _representative_parameter_case(sample_count: int = 32):
    plan, audit, manifest, roles, series, bindings = _inputs()
    row_indices = [round(index * 999 / (sample_count - 1)) for index in range(sample_count)]
    points = []
    for index, row_index in enumerate(row_indices):
        base = series.points[index % len(series.points)]
        variables = dict(base.variables)
        variables["pump_signal_map.a"] = next(iter(base.variables.values())).model_copy(
            update={
                "value": 1.8 + index / 100.0,
                "unit": "1",
                "source": "fact:pump_signal_map.a",
            }
        )
        points.append(
            base.model_copy(
                update={
                    "point_id": f"representative_{index}",
                    "timestamp": float(row_index),
                    "source_row_index": row_index,
                    "event_tags": [],
                    "peak_tags": [],
                    "boundary_tags": [],
                    "variables": variables,
                }
            )
        )
    sampled = series.model_copy(update={"points": points})
    long_manifest = manifest.model_copy(
        update={
            "shape": manifest.shape.model_copy(
                update={"row_count": 1000, "sample_count": 1000}
            )
        }
    )
    scenarios = []
    for scenario in plan.depth.scenarios:
        if scenario.scenario_id != "speed_ramp":
            scenarios.append(scenario)
            continue
        perturbation = scenario.perturbations[0].model_copy(
            update={
                "target": "pump_signal_map.a",
                "unit": "1",
                "value": {"start": 1.8, "end": 2.11},
                "reason": "native contribution regression perturbation",
            }
        )
        scenarios.append(scenario.model_copy(update={"perturbations": [perturbation]}))
    envelope = plan.physical_envelopes[0].model_copy(
        update={"target": "pump_signal_map.a", "lower": 1.0, "upper": 3.0, "unit": "1"}
    )
    representative_plan = plan.model_copy(
        update={
            "physical_envelopes": [*plan.physical_envelopes, envelope],
            "depth": plan.depth.model_copy(update={"scenarios": scenarios}),
        }
    )
    policy = plan.depth.adequacy.model_dump(mode="python")
    policy.update(
        {
            "sampling_mode": "stratified",
            "minimum_selected_ratio": 0.003,
            "minimum_per_parameter_valid_ratio": 0.003,
            "minimum_time_span": 999.0,
            "maximum_time_gap": 40.0,
            "required_event_tags": [],
            "required_peak_tags": [],
            "required_boundary_tags": [],
            "parameter_temporal_policies": [
                _time_varying_policy(
                    "pump_signal_map.a",
                    minimum_valid_ratio=0.003,
                    minimum_time_span=999.0,
                    maximum_time_gap=40.0,
                )
            ],
        }
    )
    return (
        representative_plan,
        audit,
        long_manifest,
        roles,
        sampled,
        bindings,
        policy,
    )


def test_current_fixture_has_target_owned_deep_adequacy_receipt() -> None:
    report = validate_model_dataset(PUMP / "validation" / "clean_validation_plan.yaml")
    receipt = report.depth_receipt["adequacy"]
    assert report.ok
    assert receipt["status"] == "pass"
    assert receipt["universe"]["available_point_count"] == 3
    assert receipt["universe"]["selected_point_count"] == 3
    assert receipt["universe"]["validated_point_count"] == 3
    assert receipt["temporal"]["covered_strata"] == ["end", "middle", "start"]
    assert receipt["missing_critical_parameters"] == []
    assert receipt["universe"]["available_parameter_ids"] == ["pump_signal_map.a"]
    assert receipt["universe"]["validated_parameter_ids"] == ["pump_signal_map.a"]
    parameter = receipt["per_parameter"][0]
    assert parameter["parameter_id"] == "pump_signal_map.a"
    assert parameter["temporal_behavior"] == "static"
    assert parameter["availability_source_id"] is None
    assert parameter["available_point_count"] == 1
    assert parameter["selected_point_count"] == 1
    assert parameter["validated_point_count"] == 1
    assert parameter["required_strata_results"] == []
    assert parameter["status"] == "pass"


def test_full_time_varying_fixture_applies_parameter_values_to_native_model() -> None:
    report = validate_model_dataset(
        PUMP / "validation" / "deep_time_varying_validation_plan.yaml"
    )
    assert report.ok
    contribution = report.depth_receipt["residual_series"]["parameter_contributions"][0]
    assert contribution["parameter_id"] == "pump_signal_map.a"
    assert contribution["distinct_observed_value_count"] == 3
    assert contribution["maximum_normalized_residual_effect"] > 1.0
    assert contribution["affected_residual_ids"] == ["pump_signal_map.linear_relation"]
    assert contribution["status"] == "pass"
    applied = [
        point["applied_parameter_values"]["pump_signal_map.a"]
        for point in report.depth_receipt["residual_series"]["points"]
    ]
    assert applied == [2.0, 2.1, 1.9]


def test_sensitive_time_varying_parameter_with_effectless_native_replay_is_blocked() -> None:
    plan = load_model_validation_plan(
        PUMP / "validation" / "deep_time_varying_validation_plan.yaml"
    )
    audit = load_hierarchical_audit_spec(PUMP / "model" / "pump_loop_hierarchy.yaml")
    manifest = load_data_file_manifest(PUMP / "data" / "clean_manifest.yaml")
    roles = load_parameter_role_matrix(PUMP / "coverage" / "pump_loop_role_matrix.yaml")
    series = load_observed_series(
        PUMP / "observed" / "deep_time_varying_parameter_series.yaml"
    )
    _, _, _, _, _, bindings = _inputs()
    zero_relation = series.model_copy(
        update={
            "points": [
                point.model_copy(
                    update={
                        "variables": {
                            **point.variables,
                            "pump_signal_map.x": point.variables[
                                "pump_signal_map.x"
                            ].model_copy(update={"value": 0.0}),
                            "pump_signal_map.y": point.variables[
                                "pump_signal_map.y"
                            ].model_copy(update={"value": 0.0}),
                        }
                    }
                )
                for point in series.points
            ]
        }
    )
    findings: list[dict[str, object]] = []
    residual, _ = _residual_series_receipt(
        audit,
        zero_relation,
        findings,
        parameter_policies=plan.depth.adequacy.parameter_temporal_policies,
    )
    contribution = residual["parameter_contributions"][0]
    assert contribution["distinct_observed_value_count"] == 3
    assert contribution["maximum_normalized_residual_effect"] == 0.0
    assert contribution["status"] == "blocked"

    result = evaluate_validation_adequacy_artifacts(
        adequacy=plan.depth.adequacy,
        claim_scope="scenario_set",
        dataset_identity_ids={"clean_csv"},
        manifest=manifest,
        role_matrix=roles,
        plan=plan,
        audit_spec=audit,
        series=zero_relation,
        residual_receipt=residual,
        bindings=bindings,
    )
    assert result.receipt["per_parameter"][0]["contribution_status"] == "blocked"
    assert result.receipt["status"] == "blocked"
    assert "time_varying_parameter_model_contribution_missing" in {
        item["type"] for item in result.findings
    }


def test_verified_non_sensitive_parameter_requires_native_ceiling_and_bounded_disposition() -> None:
    plan = load_model_validation_plan(
        PUMP / "validation" / "deep_time_varying_validation_plan.yaml"
    )
    audit = load_hierarchical_audit_spec(PUMP / "model" / "pump_loop_hierarchy.yaml")
    manifest = load_data_file_manifest(PUMP / "data" / "clean_manifest.yaml")
    roles = load_parameter_role_matrix(PUMP / "coverage" / "pump_loop_role_matrix.yaml")
    series = load_observed_series(
        PUMP / "observed" / "deep_time_varying_parameter_series.yaml"
    )
    _, _, _, _, _, bindings = _inputs()
    zero_relation = series.model_copy(
        update={
            "points": [
                point.model_copy(
                    update={
                        "variables": {
                            **point.variables,
                            "pump_signal_map.x": point.variables[
                                "pump_signal_map.x"
                            ].model_copy(update={"value": 0.0}),
                            "pump_signal_map.y": point.variables[
                                "pump_signal_map.y"
                            ].model_copy(update={"value": 0.0}),
                        }
                    }
                )
                for point in series.points
            ]
        }
    )
    policy_payload = plan.depth.adequacy.parameter_temporal_policies[0].model_dump(
        mode="python"
    )
    policy_payload.update(
        {
            "contribution_expectation": "verified_non_sensitive",
            "minimum_normalized_contribution_effect": None,
            "maximum_non_sensitive_contribution_effect": 0.0,
            "non_sensitive_reason": (
                "The bounded zero-input fixture makes this gain observationally "
                "non-contributing while still executing the native model path."
            ),
            "non_sensitive_claim_boundary": (
                "Only the exact three zero-input fixture rows are covered; no other "
                "operating point may reuse this disposition."
            ),
        }
    )
    policy = ParameterTemporalPolicySpec.model_validate(policy_payload)
    adequacy_payload = plan.depth.adequacy.model_dump(mode="python")
    adequacy_payload["parameter_temporal_policies"] = [policy.model_dump(mode="python")]
    adequacy = ValidationAdequacyPlanSpec.model_validate(adequacy_payload)
    bounded_plan = plan.model_copy(
        update={
            "depth": plan.depth.model_copy(update={"adequacy": adequacy})
        }
    )
    findings: list[dict[str, object]] = []
    residual, _ = _residual_series_receipt(
        audit,
        zero_relation,
        findings,
        parameter_policies=(policy,),
    )
    contribution = residual["parameter_contributions"][0]
    assert contribution["maximum_normalized_residual_effect"] == 0.0
    assert contribution["status"] == "verified_non_sensitive"

    result = evaluate_validation_adequacy_artifacts(
        adequacy=adequacy,
        claim_scope="scenario_set",
        dataset_identity_ids={"clean_csv"},
        manifest=manifest,
        role_matrix=roles,
        plan=bounded_plan,
        audit_spec=audit,
        series=zero_relation,
        residual_receipt=residual,
        bindings=bindings,
    )
    parameter = result.receipt["per_parameter"][0]
    assert parameter["contribution_status"] == "verified_non_sensitive"
    assert parameter["non_sensitive_reason"] == policy.non_sensitive_reason
    assert parameter["non_sensitive_claim_boundary"] == policy.non_sensitive_claim_boundary
    assert result.receipt["status"] == "pass"


def test_three_distributed_points_from_1000_still_fail_dynamic_floor() -> None:
    plan, audit, manifest, roles, series, bindings = _inputs()
    points = []
    for index, row_index in enumerate((0, 500, 999)):
        base = series.points[index]
        variables = dict(base.variables)
        variables["pump_signal_map.a"] = next(iter(base.variables.values())).model_copy(
            update={"value": 1.9 + index / 10.0, "unit": "1", "source": "fact:pump_signal_map.a"}
        )
        points.append(
            base.model_copy(
                update={"timestamp": float(row_index), "source_row_index": row_index, "variables": variables}
            )
        )
    sampled = series.model_copy(update={"points": points})
    long_manifest = manifest.model_copy(
        update={"shape": manifest.shape.model_copy(update={"row_count": 1000, "sample_count": 1000})}
    )
    payload = plan.depth.adequacy.model_dump(mode="python")
    payload.update(
        {
            "sampling_mode": "stratified",
            "minimum_selected_ratio": 0.003,
            "minimum_per_parameter_valid_ratio": 0.003,
            "minimum_time_span": 999.0,
            "maximum_time_gap": 1000.0,
            "required_event_tags": [],
            "required_peak_tags": [],
            "required_boundary_tags": [],
            "parameter_temporal_policies": [
                _time_varying_policy(
                    "pump_signal_map.a",
                    minimum_valid_ratio=0.003,
                    minimum_time_span=999.0,
                    maximum_time_gap=1000.0,
                )
            ],
        }
    )
    result = evaluate_validation_adequacy_artifacts(
        adequacy=ValidationAdequacyPlanSpec.model_validate(payload),
        claim_scope="time_window",
        dataset_identity_ids={"clean_csv"},
        manifest=long_manifest,
        role_matrix=roles,
        plan=plan,
        audit_spec=audit,
        series=sampled,
        residual_receipt=_residual(sampled.points),
        bindings=bindings,
    )
    floor = result.receipt["universe"]["selection_floor"]
    parameter = result.receipt["per_parameter"][0]
    assert floor["universal_minimum_count"] == 32
    assert floor["effective_minimum_count"] == 32
    assert parameter["coverage_floor"]["effective_minimum_count"] == 32
    assert result.receipt["status"] == "blocked"
    assert "selected_point_floor_not_met" in {item["type"] for item in result.findings}


def test_dynamic_representative_parameter_can_pass_without_full_1000_rows() -> None:
    plan, audit, manifest, roles, series, bindings, payload = _representative_parameter_case()
    result = evaluate_validation_adequacy_artifacts(
        adequacy=ValidationAdequacyPlanSpec.model_validate(payload),
        claim_scope="time_window",
        dataset_identity_ids={"clean_csv"},
        manifest=manifest,
        role_matrix=roles,
        plan=plan,
        audit_spec=audit,
        series=series,
        residual_receipt=_residual(series.points),
        bindings=bindings,
    )
    parameter = result.receipt["per_parameter"][0]
    assert result.receipt["status"] == "pass"
    assert result.receipt["universe"]["selected_point_count"] == 32
    assert parameter["available_point_count"] == 1000
    assert parameter["validated_point_count"] == 32
    assert parameter["coverage_floor"]["effective_minimum_count"] == 32
    assert parameter["status"] == "pass"


def test_parameter_floor_uses_strictest_universal_project_and_convergence_term() -> None:
    plan, audit, manifest, roles, series, bindings, payload = _representative_parameter_case()
    policy = payload["parameter_temporal_policies"][0]
    policy.update(
        {
            "minimum_valid_points": 35,
            "minimum_valid_ratio": 0.035,
            "convergence_evidence_id": "parameter_convergence_receipt_v1",
            "convergence_minimum_valid_points": 40,
            "convergence_minimum_valid_ratio": 0.04,
        }
    )
    result = evaluate_validation_adequacy_artifacts(
        adequacy=ValidationAdequacyPlanSpec.model_validate(payload),
        claim_scope="time_window",
        dataset_identity_ids={"clean_csv"},
        manifest=manifest,
        role_matrix=roles,
        plan=plan,
        audit_spec=audit,
        series=series,
        residual_receipt=_residual(series.points),
        bindings=bindings,
    )
    floor = result.receipt["per_parameter"][0]["coverage_floor"]
    assert floor["universal_minimum_count"] == 32
    assert floor["project_minimum_count"] == 35
    assert floor["convergence_minimum_count"] == 40
    assert floor["effective_minimum_count"] == 40
    assert result.receipt["per_parameter"][0]["status"] == "blocked"


def test_disconnected_parameter_evidence_cannot_pass_deep_coverage() -> None:
    plan, audit, manifest, roles, series, bindings, payload = _representative_parameter_case()
    result = evaluate_validation_adequacy_artifacts(
        adequacy=ValidationAdequacyPlanSpec.model_validate(payload),
        claim_scope="time_window",
        dataset_identity_ids={"clean_csv"},
        manifest=manifest,
        role_matrix=roles,
        plan=plan,
        audit_spec=audit,
        series=series,
        residual_receipt=_residual(
            series.points,
            blocked_parameters={"pump_signal_map.a"},
        ),
        bindings=bindings,
    )
    parameter = result.receipt["per_parameter"][0]
    assert parameter["validated_point_count"] == 32
    assert parameter["contribution_status"] == "blocked"
    assert parameter["status"] == "blocked"
    assert "time_varying_parameter_model_contribution_missing" in {
        item["type"] for item in result.findings
    }


def test_1000_point_endpoints_are_blocked() -> None:
    plan, audit, manifest, roles, series, bindings = _inputs()
    first = series.points[0].model_copy(update={"timestamp": 0.0, "source_row_index": 0})
    last = series.points[-1].model_copy(update={"timestamp": 999.0, "source_row_index": 999})
    shallow = series.model_copy(update={"points": [first, last]})
    large_manifest = manifest.model_copy(
        update={"shape": manifest.shape.model_copy(update={"row_count": 1000, "sample_count": 1000})}
    )
    adequacy = plan.depth.adequacy.model_copy(
        update={
            "sampling_mode": "stratified",
            "minimum_selected_ratio": 0.001,
            "maximum_time_gap": 1000.0,
            "required_event_tags": [],
            "required_peak_tags": [],
            "required_boundary_tags": [],
        }
    )
    result = evaluate_validation_adequacy_artifacts(
        adequacy=adequacy,
        claim_scope="time_window",
        dataset_identity_ids={"clean_csv"},
        manifest=large_manifest,
        role_matrix=roles,
        plan=plan,
        audit_spec=audit,
        series=shallow,
        residual_receipt=_residual(shallow.points),
        bindings=bindings,
    )
    codes = {item["type"] for item in result.findings}
    assert result.receipt["status"] == "blocked"
    assert "selected_point_floor_not_met" in codes
    assert "temporal_strata_missing" in codes


def test_duplicate_timestamp_and_missing_transient_are_blocked() -> None:
    plan, audit, manifest, roles, series, bindings = _inputs()
    points = [
        item.model_copy(update={"timestamp": 0.0, "event_tags": []})
        for item in series.points
    ]
    shallow = series.model_copy(update={"points": points})
    result = evaluate_validation_adequacy_artifacts(
        adequacy=plan.depth.adequacy,
        claim_scope="time_window",
        dataset_identity_ids={"clean_csv"},
        manifest=manifest,
        role_matrix=roles,
        plan=plan,
        audit_spec=audit,
        series=shallow,
        residual_receipt=_residual(shallow.points),
        bindings=bindings,
    )
    codes = {item["type"] for item in result.findings}
    assert "temporal_duplicate_timestamps" in codes
    assert "temporal_positive_span_missing" in codes
    assert "temporal_event_tags_missing" in codes


def test_long_signal_history_requires_gap_tags_modes_and_source_lineage() -> None:
    plan, audit, manifest, roles, series, bindings = _inputs()
    points = [
        series.points[0].model_copy(
            update={"timestamp": 0.0, "peak_tags": [], "mode_id": None}
        ),
        series.points[1].model_copy(
            update={
                "timestamp": 0.05,
                "source_identity_id": None,
                "source_row_index": None,
                "peak_tags": [],
                "mode_id": None,
            }
        ),
        series.points[2].model_copy(
            update={
                "timestamp": 0.2,
                "source_row_index": 9,
                "peak_tags": [],
                "mode_id": None,
            }
        ),
    ]
    shallow = series.model_copy(update={"points": points})
    result = evaluate_validation_adequacy_artifacts(
        adequacy=plan.depth.adequacy,
        claim_scope="time_window",
        dataset_identity_ids={"clean_csv"},
        manifest=manifest,
        role_matrix=roles,
        plan=plan,
        audit_spec=audit,
        series=shallow,
        residual_receipt=_residual(shallow.points),
        bindings=bindings,
    )
    codes = {item["type"] for item in result.findings}
    assert {
        "temporal_maximum_gap_exceeded",
        "temporal_peak_tags_missing",
        "temporal_modes_missing",
        "source_row_lineage_missing",
        "source_row_lineage_out_of_range",
        "critical_signal_time_coverage_insufficient",
    } <= codes


def test_all_declared_sampling_modes_execute_the_native_adequacy_gate() -> None:
    plan, audit, manifest, roles, series, bindings = _inputs()
    base = plan.depth.adequacy.model_dump(mode="python")
    for mode in ("full", "stratified", "event_aware", "project_declared", "adaptive"):
        payload = {**base, "sampling_mode": mode}
        if mode == "adaptive":
            payload.update(
                {
                    "adaptive_converged": True,
                    "adaptive_evidence_id": "fixture_convergence_receipt_v1",
                    "adaptive_minimum_selected_points": 3,
                    "adaptive_minimum_selected_ratio": 1.0,
                }
            )
        adequacy = ValidationAdequacyPlanSpec.model_validate(payload)
        result = evaluate_validation_adequacy_artifacts(
            adequacy=adequacy,
            claim_scope="scenario_set",
            dataset_identity_ids={"clean_csv"},
            manifest=manifest,
            role_matrix=roles,
            plan=plan,
            audit_spec=audit,
            series=series,
            residual_receipt=_residual(series.points),
            bindings=bindings,
        )
        assert result.receipt["status"] == "pass", mode
        assert result.receipt["sampling_mode"] == mode


def test_omitted_sampling_mode_defaults_to_full_sequence_validation() -> None:
    plan, *_ = _inputs()
    payload = plan.depth.adequacy.model_dump(mode="python")
    payload.pop("sampling_mode")
    adequacy = ValidationAdequacyPlanSpec.model_validate(payload)
    assert adequacy.sampling_mode == "full"


def test_time_varying_parameter_cannot_use_one_point_from_long_series() -> None:
    plan, audit, manifest, roles, series, bindings = _inputs()
    timestamps = (0.0, 500.0, 999.0)
    points = []
    for index, (point, timestamp) in enumerate(zip(series.points, timestamps)):
        variables = dict(point.variables)
        if index == 0:
            variables["pump_signal_map.a"] = next(iter(point.variables.values())).model_copy(
                update={"value": 2.0, "unit": "1", "source": "fact:pump_signal_map.a"}
            )
        points.append(
            point.model_copy(
                update={
                    "timestamp": timestamp,
                    "source_row_index": int(timestamp),
                    "variables": variables,
                }
            )
        )
    sparse_parameter_series = series.model_copy(update={"points": points})
    long_manifest = manifest.model_copy(
        update={
            "shape": manifest.shape.model_copy(
                update={"row_count": 1000, "sample_count": 1000}
            )
        }
    )
    policy = plan.depth.adequacy.model_dump(mode="python")
    policy.update(
        {
            "sampling_mode": "stratified",
            "minimum_selected_ratio": 0.003,
            "minimum_per_parameter_valid_ratio": 0.003,
            "minimum_time_span": 999.0,
            "maximum_time_gap": 1000.0,
            "parameter_temporal_policies": [
                _time_varying_policy(
                    "pump_signal_map.a",
                    minimum_time_span=999.0,
                    maximum_time_gap=600.0,
                )
            ],
        }
    )
    adequacy = ValidationAdequacyPlanSpec.model_validate(policy)
    result = evaluate_validation_adequacy_artifacts(
        adequacy=adequacy,
        claim_scope="time_window",
        dataset_identity_ids={"clean_csv"},
        manifest=long_manifest,
        role_matrix=roles,
        plan=plan,
        audit_spec=audit,
        series=sparse_parameter_series,
        residual_receipt=_residual(sparse_parameter_series.points),
        bindings=bindings,
    )
    parameter = next(
        item
        for item in result.receipt["per_parameter"]
        if item["parameter_id"] == "pump_signal_map.a"
    )
    assert result.receipt["universe"]["available_point_count"] == 1000
    assert parameter["valid_point_count"] == 1
    assert parameter["status"] == "blocked"
    codes = {item["type"] for item in result.findings}
    assert "selected_point_floor_not_met" in codes
    assert "time_varying_parameter_time_coverage_insufficient" in codes


def test_1000_point_parameter_endpoints_do_not_count_as_deep_history() -> None:
    plan, audit, manifest, roles, series, bindings = _inputs()
    points = []
    for index, (point, timestamp) in enumerate(zip(series.points, (0.0, 500.0, 999.0))):
        variables = dict(point.variables)
        if index in {0, 2}:
            variables["pump_signal_map.a"] = next(iter(point.variables.values())).model_copy(
                update={"value": 2.0 + index, "unit": "1", "source": "fact:pump_signal_map.a"}
            )
        points.append(
            point.model_copy(
                update={"timestamp": timestamp, "source_row_index": int(timestamp), "variables": variables}
            )
        )
    sparse = series.model_copy(update={"points": points})
    long_manifest = manifest.model_copy(
        update={"shape": manifest.shape.model_copy(update={"row_count": 1000, "sample_count": 1000})}
    )
    adequacy = plan.depth.adequacy.model_copy(
        update={
            "sampling_mode": "stratified",
            "minimum_selected_ratio": 0.003,
            "minimum_time_span": 999.0,
            "maximum_time_gap": 1000.0,
            "required_event_tags": [],
            "required_peak_tags": [],
            "required_boundary_tags": [],
            "parameter_temporal_policies": [
                ValidationAdequacyPlanSpec.model_validate(
                    {
                        **plan.depth.adequacy.model_dump(mode="python"),
                        "minimum_per_parameter_valid_ratio": 0.002,
                        "maximum_time_gap": 1000.0,
                        "parameter_temporal_policies": [
                            _time_varying_policy(
                                "pump_signal_map.a",
                                minimum_valid_ratio=0.002,
                                minimum_time_span=999.0,
                                maximum_time_gap=1000.0,
                            )
                        ],
                    }
                ).parameter_temporal_policies[0]
            ],
        }
    )
    result = evaluate_validation_adequacy_artifacts(
        adequacy=adequacy,
        claim_scope="time_window",
        dataset_identity_ids={"clean_csv"},
        manifest=long_manifest,
        role_matrix=roles,
        plan=plan,
        audit_spec=audit,
        series=sparse,
        residual_receipt=_residual(sparse.points),
        bindings=bindings,
    )
    parameter = result.receipt["per_parameter"][0]
    assert parameter["available_point_count"] == 1000
    assert parameter["unique_selected_row_count"] == 2
    assert parameter["missing_universal_strata"] == ["middle"]
    assert parameter["status"] == "blocked"


def test_same_early_stage_points_cannot_impersonate_early_middle_late() -> None:
    plan, audit, manifest, roles, series, bindings = _inputs()
    row_indices = (0, 50, 100, 500, 750, 999)
    points = []
    for index, row_index in enumerate(row_indices):
        base = series.points[index % len(series.points)]
        variables = dict(base.variables)
        if index < 3:
            variables["pump_signal_map.a"] = next(iter(base.variables.values())).model_copy(
                update={"value": 2.0 + index, "unit": "1", "source": "fact:pump_signal_map.a"}
            )
        points.append(
            base.model_copy(
                update={
                    "point_id": f"same_stage_{index}",
                    "timestamp": float(row_index),
                    "source_row_index": row_index,
                    "event_tags": [],
                    "peak_tags": [],
                    "boundary_tags": [],
                    "variables": variables,
                }
            )
        )
    sampled = series.model_copy(update={"points": points})
    long_manifest = manifest.model_copy(
        update={"shape": manifest.shape.model_copy(update={"row_count": 1000, "sample_count": 1000})}
    )
    policy_data = plan.depth.adequacy.model_dump(mode="python")
    policy_data.update(
        {
            "sampling_mode": "stratified",
            "minimum_selected_points": 6,
            "minimum_selected_ratio": 0.006,
            "minimum_time_span": 100.0,
            "maximum_time_gap": 500.0,
            "minimum_per_parameter_valid_ratio": 0.003,
            "required_event_tags": [],
            "required_peak_tags": [],
            "required_boundary_tags": [],
            "parameter_temporal_policies": [
                _time_varying_policy(
                    "pump_signal_map.a",
                    minimum_valid_ratio=0.003,
                    minimum_time_span=100.0,
                    maximum_time_gap=60.0,
                )
            ],
        }
    )
    result = evaluate_validation_adequacy_artifacts(
        adequacy=ValidationAdequacyPlanSpec.model_validate(policy_data),
        claim_scope="time_window",
        dataset_identity_ids={"clean_csv"},
        manifest=long_manifest,
        role_matrix=roles,
        plan=plan,
        audit_spec=audit,
        series=sampled,
        residual_receipt=_residual(sampled.points),
        bindings=bindings,
    )
    parameter = result.receipt["per_parameter"][0]
    assert parameter["validated_point_count"] == 3
    assert parameter["missing_universal_strata"] == ["late", "middle"]
    assert {row["stratum_id"] for row in parameter["required_strata_results"] if row["status"] == "blocked"} == {
        "shutdown",
        "steady",
    }
    assert parameter["status"] == "blocked"


def test_one_shallow_parameter_is_not_hidden_by_other_deep_parameters() -> None:
    plan, audit, manifest, roles, series, bindings = _inputs()
    parameter_ids = [
        "pump_signal_map.a",
        "pump_signal_map.b",
        "pump_signal_map.residual_scale",
        "pump_signal_map.x_scale",
    ]
    rows = [round(index * 999 / 31) for index in range(32)]
    points = []
    for index, row_index in enumerate(rows):
        base = series.points[index % len(series.points)]
        variables = dict(base.variables)
        for parameter_id in parameter_ids:
            if parameter_id != parameter_ids[-1] or index == 0:
                variables[parameter_id] = next(iter(base.variables.values())).model_copy(
                    update={
                        "value": 1.0 + index / 100.0,
                        "unit": "1",
                        "source": f"fact:{parameter_id}",
                    }
                )
        points.append(
            base.model_copy(
                update={
                    "point_id": f"rich_sibling_{index}",
                    "timestamp": float(row_index),
                    "source_row_index": row_index,
                    "event_tags": [],
                    "peak_tags": [],
                    "boundary_tags": [],
                    "variables": variables,
                }
            )
        )
    sampled = series.model_copy(update={"points": points})
    long_manifest = manifest.model_copy(
        update={"shape": manifest.shape.model_copy(update={"row_count": 1000, "sample_count": 1000})}
    )
    parameter_block = audit.hierarchy.blocks[0].model_copy(update={"required_parameters": parameter_ids})
    parameter_audit = audit.model_copy(
        update={"hierarchy": audit.hierarchy.model_copy(update={"blocks": [parameter_block]})}
    )
    signal_bindings = [item for item in bindings if item.binding_kind != "fact_to_model_parameter"]
    binding_template = next(item for item in bindings if item.binding_kind == "fact_to_model_parameter")
    parameter_bindings = [
        binding_template.model_copy(
            update={
                "binding_id": f"binding_{parameter_id}",
                "source_fact": parameter_id,
                "model_target": parameter_id,
            }
        )
        for parameter_id in parameter_ids
    ]
    envelope_template = plan.physical_envelopes[0]
    parameter_envelopes = [
        envelope_template.model_copy(
            update={"target": parameter_id, "lower": 0.0, "upper": 10.0, "unit": "1"}
        )
        for parameter_id in parameter_ids
    ]
    scenarios = []
    for scenario in plan.depth.scenarios:
        if scenario.scenario_id != "speed_ramp":
            scenarios.append(scenario)
            continue
        perturbation_template = scenario.perturbations[0]
        scenarios.append(
            scenario.model_copy(
                update={
                    "perturbations": [
                        perturbation_template.model_copy(
                            update={"target": parameter_id, "unit": "1"}
                        )
                        for parameter_id in parameter_ids
                    ]
                }
            )
        )
    parameter_plan = plan.model_copy(
        update={
            "physical_envelopes": [*plan.physical_envelopes, *parameter_envelopes],
            "depth": plan.depth.model_copy(update={"scenarios": scenarios}),
        }
    )
    policy_data = plan.depth.adequacy.model_dump(mode="python")
    policy_data.update(
        {
            "sampling_mode": "stratified",
            "minimum_selected_ratio": 0.003,
            "minimum_per_parameter_valid_ratio": 0.003,
            "minimum_time_span": 999.0,
            "maximum_time_gap": 600.0,
            "critical_parameters": parameter_ids,
            "parameter_temporal_policies": [
                _time_varying_policy(
                    parameter_id,
                    minimum_valid_ratio=0.003,
                    minimum_time_span=999.0,
                    maximum_time_gap=600.0,
                )
                for parameter_id in parameter_ids
            ],
            "family_quotas": [],
            "required_event_tags": [],
            "required_peak_tags": [],
            "required_boundary_tags": [],
        }
    )
    result = evaluate_validation_adequacy_artifacts(
        adequacy=ValidationAdequacyPlanSpec.model_validate(policy_data),
        claim_scope="time_window",
        dataset_identity_ids={"clean_csv"},
        manifest=long_manifest,
        role_matrix=roles,
        plan=parameter_plan,
        audit_spec=parameter_audit,
        series=sampled,
        residual_receipt=_residual(sampled.points),
        bindings=[*signal_bindings, *parameter_bindings],
    )
    by_id = {row["parameter_id"]: row for row in result.receipt["per_parameter"]}
    assert result.receipt["universe"]["parameter_selection_ratio"] == 1.0
    assert all(by_id[parameter_id]["status"] == "pass" for parameter_id in parameter_ids[:-1])
    assert by_id[parameter_ids[-1]]["status"] == "blocked"
    assert parameter_ids[-1] in result.receipt["missing_critical_parameters"]


def test_10000_parameter_universe_with_only_two_bound_is_blocked() -> None:
    plan, audit, manifest, roles, series, bindings = _inputs()
    parameter_ids = [f"parameter_{index:05d}" for index in range(10_000)]
    parameter_block = audit.hierarchy.blocks[0].model_copy(update={"required_parameters": parameter_ids})
    parameter_audit = audit.model_copy(
        update={"hierarchy": audit.hierarchy.model_copy(update={"blocks": [parameter_block]})}
    )
    signal_bindings = [item for item in bindings if item.binding_kind != "fact_to_model_parameter"]
    binding_template = next(item for item in bindings if item.binding_kind == "fact_to_model_parameter")
    selected = parameter_ids[:2]
    parameter_bindings = [
        binding_template.model_copy(
            update={
                "binding_id": f"binding_{parameter_id}",
                "source_fact": parameter_id,
                "model_target": parameter_id,
            }
        )
        for parameter_id in selected
    ]
    policy_data = plan.depth.adequacy.model_dump(mode="python")
    policy_data.update(
        {
            "critical_parameters": [],
            "parameter_temporal_policies": [
                {
                    "parameter_id": parameter_id,
                    "temporal_behavior": "static",
                    "classification_source": "fixture static binding inventory",
                }
                for parameter_id in selected
            ],
            "family_quotas": [],
        }
    )
    result = evaluate_validation_adequacy_artifacts(
        adequacy=ValidationAdequacyPlanSpec.model_validate(policy_data),
        claim_scope="scenario_set",
        dataset_identity_ids={"clean_csv"},
        manifest=manifest,
        role_matrix=roles,
        plan=plan,
        audit_spec=parameter_audit,
        series=series,
        residual_receipt=_residual(series.points),
        bindings=[*signal_bindings, *parameter_bindings],
    )
    universe = result.receipt["universe"]
    assert len(universe["available_parameter_ids"]) == 10_000
    assert universe["selected_parameter_ids"] == selected
    assert universe["parameter_selection_ratio"] == pytest.approx(2 / 10_000)
    assert "parameter_coverage_ratio_not_met" in {item["type"] for item in result.findings}


def test_parameter_universe_requires_static_or_time_varying_classification() -> None:
    plan, audit, manifest, roles, series, bindings = _inputs()
    adequacy = plan.depth.adequacy.model_copy(
        update={"parameter_temporal_policies": []}
    )
    result = evaluate_validation_adequacy_artifacts(
        adequacy=adequacy,
        claim_scope="scenario_set",
        dataset_identity_ids={"clean_csv"},
        manifest=manifest,
        role_matrix=roles,
        plan=plan,
        audit_spec=audit,
        series=series,
        residual_receipt=_residual(series.points),
        bindings=bindings,
    )
    assert result.receipt["universe"]["available_parameter_ids"] == [
        "pump_signal_map.a"
    ]
    assert result.receipt["missing_parameter_temporal_classifications"] == [
        "pump_signal_map.a"
    ]
    assert "parameter_temporal_classification_missing" in {
        item["type"] for item in result.findings
    }


def test_static_parameter_rejects_fabricated_temporal_requirements() -> None:
    with pytest.raises(ValidationError, match="static parameters must not declare"):
        ParameterTemporalPolicySpec.model_validate(
            {
                "parameter_id": "static_gain",
                "temporal_behavior": "static",
                "classification_source": "fixture static declaration",
                "availability_source_id": "manifest:rows",
                "minimum_valid_points": 3,
                "minimum_valid_ratio": 1.0,
                "minimum_distinct_timestamps": 3,
                "minimum_time_span": 1.0,
                "maximum_time_gap": 1.0,
                "required_strata": [
                    {"stratum_id": "early", "start_fraction": 0.0, "end_fraction": 0.2},
                    {"stratum_id": "middle", "start_fraction": 0.4, "end_fraction": 0.6},
                    {"stratum_id": "late", "start_fraction": 0.8, "end_fraction": 1.0},
                ],
            }
        )


def test_10000_signals_with_only_two_selected_are_blocked() -> None:
    plan, audit, _, _, series, _ = _inputs()
    count = 10_000
    manifest = DataFileManifestSpec.model_validate(
        {
            "source_file": {"path": "memory.csv"},
            "format": {"kind": "csv"},
            "shape": {"field_count": count, "row_count": 3, "sample_count": 3},
            "fields": [{"name": f"sig_{index}", "data_type": "float"} for index in range(count)],
            "extractor": {"script": "test"},
        }
    )
    roles = ParameterRoleMatrixSpec.model_validate(
        {
            "roles": [
                {
                    "source_id": f"field:sig_{index}",
                    "testbench_role": "measurement",
                    "physical_role": "signal",
                    "model_role": "model_variable",
                    "coverage_status": "covered",
                }
                for index in range(count)
            ]
        }
    )
    variable_roles = [
        ValidationVariableRoleSpec(source_id="field:sig_0", target="pump_signal_map.x", validation_role="model_input"),
        ValidationVariableRoleSpec(source_id="field:sig_1", target="pump_signal_map.y", validation_role="validation_output"),
    ]
    shallow_plan = plan.model_copy(update={"variable_roles": variable_roles})
    shallow_audit = audit.model_copy(
        update={
            "hierarchy": audit.hierarchy.model_copy(
                update={
                    "blocks": [
                        block.model_copy(update={"required_parameters": []})
                        for block in audit.hierarchy.blocks
                    ]
                }
            )
        }
    )
    adequacy = plan.depth.adequacy.model_copy(
        update={
            "sampling_mode": "full",
            "critical_parameters": [],
            "family_quotas": [],
            "required_event_tags": [],
            "required_peak_tags": [],
            "required_boundary_tags": [],
            "required_mode_ids": [],
        }
    )
    result = evaluate_validation_adequacy_artifacts(
        adequacy=adequacy,
        claim_scope="time_window",
        dataset_identity_ids={"clean_csv"},
        manifest=manifest,
        role_matrix=roles,
        plan=shallow_plan,
        audit_spec=shallow_audit,
        series=series,
        residual_receipt=_residual(series.points),
    )
    assert result.receipt["universe"]["available_signal_ids"][0].startswith("field:sig_")
    assert result.receipt["universe"]["signal_selection_ratio"] == pytest.approx(2 / count)
    assert "signal_coverage_ratio_not_met" in {item["type"] for item in result.findings}


def test_repeated_template_exclusions_are_blocked() -> None:
    plan, audit, manifest, _, series, bindings = _inputs()
    fields = [
        {"name": f"sig_{index}", "data_type": "float"}
        for index in range(4)
    ]
    small_manifest = manifest.model_copy(
        update={
            "fields": [type(manifest.fields[0]).model_validate(item) for item in fields],
            "shape": manifest.shape.model_copy(update={"field_count": 4}),
        }
    )
    role_matrix = ParameterRoleMatrixSpec.model_validate(
        {
            "roles": [
                {
                    "source_id": f"field:sig_{index}",
                    "testbench_role": "measurement",
                    "physical_role": "signal",
                    "model_role": "model_variable" if index == 0 else "out_of_scope",
                    "coverage_status": "covered" if index == 0 else "excluded",
                    "reason": None if index == 0 else "not used",
                }
                for index in range(4)
            ]
        }
    )
    result = evaluate_validation_adequacy_artifacts(
        adequacy=plan.depth.adequacy.model_copy(update={"sampling_mode": "stratified"}),
        claim_scope="time_window",
        dataset_identity_ids={"clean_csv"},
        manifest=small_manifest,
        role_matrix=role_matrix,
        plan=plan,
        audit_spec=audit,
        series=series,
        residual_receipt=_residual(series.points),
        bindings=bindings,
    )
    codes = {item["type"] for item in result.findings}
    assert "repeated_exclusion_reason" in codes
    assert "templated_exclusion_reason" in codes


def test_empty_roles_rejected_for_non_snapshot_plan() -> None:
    plan = load_model_validation_plan(PUMP / "validation" / "clean_validation_plan.yaml")
    data = plan.model_dump(mode="python")
    data["variable_roles"] = []
    with pytest.raises(ValidationError, match="non-empty variable_roles"):
        ModelValidationPlanSpec.model_validate(data)


def test_conflicting_manifest_point_counts_fail_closed_on_larger_denominator() -> None:
    plan, audit, manifest, roles, series, bindings = _inputs()
    conflicting_manifest = manifest.model_copy(
        update={
            "shape": manifest.shape.model_copy(
                update={"row_count": 10, "sample_count": 1000}
            )
        }
    )

    result = evaluate_validation_adequacy_artifacts(
        adequacy=plan.depth.adequacy,
        claim_scope="time_window",
        dataset_identity_ids={"clean_csv"},
        manifest=conflicting_manifest,
        role_matrix=roles,
        plan=plan,
        audit_spec=audit,
        series=series,
        residual_receipt=_residual(series.points),
        bindings=bindings,
    )

    assert "manifest_point_count_mismatch" in {
        item["type"] for item in result.findings
    }
    assert result.receipt["universe"]["available_point_count"] == 1000
    assert result.receipt["universe"]["eligible_point_count"] == 1000


def test_snapshot_receipt_cannot_satisfy_validation_ready_closure() -> None:
    report = validate_model_dataset(PUMP / "validation" / "clean_validation_plan.yaml").to_dict()
    receipt = dict(report["depth_receipt"])
    receipt["claim_scope"] = "snapshot"
    receipt["covered_scope"] = "snapshot"
    receipt["time"] = {**receipt["time"], "observed_scope": "snapshot", "snapshot_only": True}
    receipt["adequacy"] = {**receipt["adequacy"], "status": "not_applicable"}
    report["depth_receipt"] = receipt
    checked, findings = [], []
    _consume_validation_depth_receipt(
        Path("memory-plan.yaml"),
        report,
        checked,
        findings,
        requested_claim_scope="validation_ready",
    )
    assert findings
    assert "snapshot_scope_incompatible" in findings[0].details["issue_codes"]
