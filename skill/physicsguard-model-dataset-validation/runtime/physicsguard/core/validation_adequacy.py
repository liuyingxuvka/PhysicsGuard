"""Target-owned quantitative coverage and sampling adequacy evaluation."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Iterable

from physicsguard.io.test_file_contract_loader import (
    load_data_file_manifest,
    load_parameter_role_matrix,
    load_project_evidence_registry,
)
from physicsguard.schema.data_file_manifest import DataFileManifestSpec
from physicsguard.schema.hierarchy_spec import HierarchicalAuditSpec
from physicsguard.schema.model_dataset_validation import ModelValidationPlanSpec
from physicsguard.schema.parameter_coverage import ParameterRoleMatrixSpec
from physicsguard.schema.project_evidence import EvidenceBindingRecordSpec
from physicsguard.schema.validation_adequacy import (
    ANTI_DEGENERACY_FLOOR_ALGORITHM,
    FamilyQuotaPlanSpec,
    ValidationAdequacyPlanSpec,
    ValidationAdequacyReceiptSpec,
)
from physicsguard.schema.validation_depth import ObservedSeriesSpec, ValidationDepthPlanSpec


@dataclass(frozen=True)
class ValidationAdequacyEvaluation:
    receipt: dict[str, Any]
    findings: list[dict[str, Any]]


def evaluate_validation_adequacy(
    plan: ModelValidationPlanSpec,
    depth: ValidationDepthPlanSpec,
    *,
    base_dir: Path,
    audit_spec: HierarchicalAuditSpec,
    series: ObservedSeriesSpec | None,
    residual_receipt: dict[str, Any],
) -> ValidationAdequacyEvaluation:
    """Load exact target artifacts and evaluate quantitative adequacy."""

    if depth.time_scope.claim_scope == "snapshot" and depth.adequacy is None:
        return ValidationAdequacyEvaluation(
            receipt=_not_applicable_receipt(series, residual_receipt),
            findings=[],
        )
    if depth.adequacy is None:
        finding = _finding(
            "error",
            "validation_adequacy_plan_missing",
            "every non-snapshot claim requires a target-owned adequacy plan",
        )
        receipt = _blocked_empty_receipt(series, residual_receipt, [finding["type"]])
        return ValidationAdequacyEvaluation(receipt=receipt, findings=[finding])

    load_findings: list[dict[str, Any]] = []
    manifest = _load_or_find(
        load_data_file_manifest,
        _resolve_path(base_dir, depth.dataset.field_schema.path),
        "validation_manifest_unreadable",
        load_findings,
    )
    role_matrix = _load_or_find(
        load_parameter_role_matrix,
        _resolve_path(base_dir, depth.dataset.parameter_roles.path),
        "validation_role_matrix_unreadable",
        load_findings,
    )
    registry = _load_or_find(
        load_project_evidence_registry,
        _resolve_path(base_dir, depth.mapping_review.registry.path),
        "validation_evidence_registry_unreadable",
        load_findings,
    )
    if manifest is None or role_matrix is None or registry is None:
        receipt = _blocked_empty_receipt(
            series,
            residual_receipt,
            [item["type"] for item in load_findings],
            depth.adequacy,
        )
        return ValidationAdequacyEvaluation(receipt=receipt, findings=load_findings)

    bundle = next(
        (item for item in registry.evidence_bundles if item.bundle_id == depth.mapping_review.bundle_id),
        None,
    )
    if bundle is None:
        finding = _finding(
            "error",
            "validation_adequacy_bundle_missing",
            "the mapping-review bundle required for target coverage does not exist",
            depth.mapping_review.bundle_id,
        )
        receipt = _blocked_empty_receipt(
            series,
            residual_receipt,
            [finding["type"]],
            depth.adequacy,
        )
        return ValidationAdequacyEvaluation(receipt=receipt, findings=[finding])
    binding_ids = set(bundle.bindings)
    bindings = [
        item
        for item in registry.evidence_bindings
        if item.binding_id in binding_ids and item.status == "active"
    ]
    result = evaluate_validation_adequacy_artifacts(
        adequacy=depth.adequacy,
        claim_scope=depth.time_scope.claim_scope,
        dataset_identity_ids={item.identity_id for item in depth.dataset.files},
        manifest=manifest,
        role_matrix=role_matrix,
        plan=plan,
        audit_spec=audit_spec,
        series=series,
        residual_receipt=residual_receipt,
        bindings=bindings,
    )
    return ValidationAdequacyEvaluation(
        receipt=result.receipt,
        findings=[*load_findings, *result.findings],
    )


def evaluate_validation_adequacy_artifacts(
    *,
    adequacy: ValidationAdequacyPlanSpec,
    claim_scope: str,
    dataset_identity_ids: set[str],
    manifest: DataFileManifestSpec,
    role_matrix: ParameterRoleMatrixSpec,
    plan: ModelValidationPlanSpec,
    audit_spec: HierarchicalAuditSpec,
    series: ObservedSeriesSpec | None,
    residual_receipt: dict[str, Any],
    bindings: Iterable[EvidenceBindingRecordSpec] = (),
) -> ValidationAdequacyEvaluation:
    """Pure evaluator used by the runtime integration and shallow-negative tests."""

    findings: list[dict[str, Any]] = []
    points = list(series.points) if series is not None else []
    valid_points = [item for item in points if item.valid]
    available_points = _authoritative_manifest_point_count(manifest, findings)
    eligible_points = available_points
    selection_floor = _coverage_floor(
        available_count=eligible_points,
        plan_minimum_count=adequacy.minimum_selected_points,
        plan_minimum_ratio=adequacy.minimum_selected_ratio,
        convergence_minimum_count=adequacy.adaptive_minimum_selected_points,
        convergence_minimum_ratio=adequacy.adaptive_minimum_selected_ratio,
        full_sequence_required=adequacy.sampling_mode == "full",
    )
    residual_status_by_point = {
        str(item.get("point_id")): str(item.get("status"))
        for item in residual_receipt.get("points", [])
        if item.get("point_id") is not None
    }
    role_by_source = {item.source_id: item for item in role_matrix.roles}
    raw_source_ids = [f"field:{item.name}" for item in manifest.fields]
    time_source_ids = {
        source_id
        for source_id, role in role_by_source.items()
        if role.testbench_role.lower() in {"time", "time_basis", "timestamp"}
        or role.physical_role.lower() in {"time", "metadata"}
        and "time" in source_id.lower()
    }
    available_signal_ids = sorted(set(raw_source_ids) - time_source_ids)
    excluded_signal_ids = sorted(
        source_id
        for source_id in available_signal_ids
        if role_by_source.get(source_id) is not None
        and role_by_source[source_id].coverage_status == "excluded"
    )
    eligible_signal_ids = sorted(
        source_id
        for source_id in available_signal_ids
        if role_by_source.get(source_id) is not None
        and role_by_source[source_id].coverage_status == "covered"
    )

    binding_list = list(bindings)
    selected_signal_ids = {
        item.source_id for item in plan.variable_roles if item.source_id in available_signal_ids
    }
    selected_signal_ids.update(
        item.source_field
        for item in binding_list
        if item.source_field in available_signal_ids and item.model_target
    )
    target_to_sources: dict[str, set[str]] = {}
    covered_model_targets: set[str] = set()
    for item in binding_list:
        if item.model_target:
            covered_model_targets.add(item.model_target)
        if item.source_field and item.model_target:
            target_to_sources.setdefault(item.model_target, set()).add(item.source_field)
        if item.source_fact and item.model_target:
            target_to_sources.setdefault(item.model_target, set()).add(f"fact:{item.source_fact}")
    for item in plan.variable_roles:
        if item.source_id:
            target_to_sources.setdefault(item.target, set()).add(item.source_id)
        covered_model_targets.add(item.target)

    required_signals = {
        variable
        for block in audit_spec.hierarchy.blocks
        for variable in block.required_variables
    } | set(adequacy.critical_signals)
    required_parameters = {
        parameter
        for block in audit_spec.hierarchy.blocks
        for parameter in block.required_parameters
    } | set(adequacy.critical_parameters)
    parameter_role_targets = {
        item.target
        for item in plan.variable_roles
        if item.validation_role == "calibration_candidate"
    }
    bound_parameter_targets = {
        item.model_target
        for item in binding_list
        if item.binding_kind == "fact_to_model_parameter" and item.model_target
    }
    parameter_policies = {
        item.parameter_id: item
        for item in adequacy.parameter_temporal_policies
    }
    available_parameter_ids = sorted(
        required_parameters
        | parameter_role_targets
        | bound_parameter_targets
        | set(parameter_policies)
    )
    required_parameters |= parameter_role_targets
    covered_parameters = sorted(set(available_parameter_ids) & covered_model_targets)
    model_parameter_ids = {
        f"{component.id}.{parameter_name}"
        for component in audit_spec.system.components
        for parameter_name in component.parameters
    }
    contribution_by_parameter = {
        str(item.get("parameter_id")): item
        for item in residual_receipt.get("parameter_contributions", [])
        if item.get("parameter_id") is not None
    }

    per_signal: list[dict[str, Any]] = []
    signal_time_matrix: list[dict[str, Any]] = []
    per_signal_pass: dict[str, bool] = {}
    for point in valid_points:
        signal_time_matrix.append(
            {
                "point_id": point.point_id,
                "timestamp": point.timestamp,
                "source_identity_id": point.source_identity_id,
                "source_row_index": point.source_row_index,
                "present_targets": sorted(point.variables),
            }
        )
    signal_targets = sorted(
        required_signals
        | {
            item.target
            for item in plan.variable_roles
            if item.validation_role != "calibration_candidate"
        }
    )
    for target in signal_targets:
        present = [point for point in valid_points if target in point.variables]
        timestamps = sorted(
            point.timestamp for point in present if point.timestamp is not None
        )
        distinct = sorted(set(timestamps))
        span = distinct[-1] - distinct[0] if len(distinct) >= 2 else None
        max_gap = _max_gap(distinct)
        ratio = _ratio(len(present), len(valid_points))
        evaluated = sum(
            1
            for point in present
            if residual_status_by_point.get(point.point_id) in {"pass", "fail"}
        )
        validated = sum(
            1
            for point in present
            if residual_status_by_point.get(point.point_id) == "pass"
        )
        validated_ratio = _ratio(validated, len(valid_points))
        passed = (
            validated >= adequacy.minimum_per_signal_valid_points
            and validated_ratio >= adequacy.minimum_per_signal_valid_ratio
            and len(distinct) >= adequacy.minimum_distinct_timestamps
            and span is not None
            and span >= adequacy.minimum_time_span
            and max_gap is not None
            and max_gap <= adequacy.maximum_time_gap
        )
        per_signal_pass[target] = passed
        if target in required_signals and not passed:
            findings.append(
                _finding(
                    "error",
                    "critical_signal_time_coverage_insufficient",
                    "critical signal lacks sufficient pointwise time coverage",
                    target,
                    {
                        "valid_point_count": len(present),
                        "evaluated_point_count": evaluated,
                        "validated_point_count": validated,
                        "valid_ratio": ratio,
                        "validated_ratio": validated_ratio,
                        "distinct_timestamp_count": len(distinct),
                        "time_span": span,
                        "maximum_observed_gap": max_gap,
                    },
                )
            )
        per_signal.append(
            {
                "signal_id": target,
                "source_ids": sorted(target_to_sources.get(target, set())),
                "valid_point_count": len(present),
                "evaluated_point_count": evaluated,
                "validated_point_count": validated,
                "missing_point_count": len(valid_points) - len(present),
                "valid_ratio": ratio,
                "validated_ratio": validated_ratio,
                "required_minimum_valid_points": adequacy.minimum_per_signal_valid_points,
                "required_minimum_valid_ratio": adequacy.minimum_per_signal_valid_ratio,
                "distinct_timestamp_count": len(distinct),
                "time_span": span,
                "maximum_observed_gap": max_gap,
                "status": "pass" if passed else "blocked",
            }
        )

    missing_parameter_classifications = sorted(
        set(available_parameter_ids) - set(parameter_policies)
    )
    for target in missing_parameter_classifications:
        findings.append(
            _finding(
                "error",
                "parameter_temporal_classification_missing",
                "parameter must be classified as static or time-varying from a named project source",
                target,
            )
        )

    per_parameter: list[dict[str, Any]] = []
    per_parameter_pass: dict[str, bool] = {}
    for target in available_parameter_ids:
        policy = parameter_policies.get(target)
        if policy is None:
            per_parameter_pass[target] = False
            continue
        present = [point for point in valid_points if target in point.variables]
        selected_rows = {
            int(point.source_row_index)
            for point in present
            if point.source_row_index is not None
        }
        evaluated_rows = {
            int(point.source_row_index)
            for point in present
            if point.source_row_index is not None
            and residual_status_by_point.get(point.point_id) in {"pass", "fail"}
        }
        validated_rows = {
            int(point.source_row_index)
            for point in present
            if point.source_row_index is not None
            and residual_status_by_point.get(point.point_id) == "pass"
        }
        timestamps = sorted(
            point.timestamp for point in present if point.timestamp is not None
        )
        distinct = sorted(set(timestamps))
        span = distinct[-1] - distinct[0] if len(distinct) >= 2 else None
        max_gap = _max_gap(distinct)
        evaluated = len(evaluated_rows)
        validated = len(validated_rows)
        residual_evidence_point_ids = sorted(
            point.point_id
            for point in present
            if residual_status_by_point.get(point.point_id) == "pass"
        )
        direction_evidence_scenario_ids = sorted(
            {
                scenario.scenario_id
                for scenario in (plan.depth.scenarios if plan.depth is not None else [])
                if any(perturbation.target == target for perturbation in scenario.perturbations)
                and any(point.scenario_id == scenario.scenario_id for point in present)
            }
        )
        direction_distinct_value_count = len(
            {point.variables[target].value for point in present}
        )
        physical_envelope_declared = any(
            envelope.target == target for envelope in plan.physical_envelopes
        )
        contribution = contribution_by_parameter.get(target, {})
        model_parameter_exists = target in model_parameter_ids and bool(
            contribution.get("model_parameter_exists", False)
        )
        contribution_status = str(contribution.get("status", "blocked"))
        contribution_evidence_point_ids = sorted(
            str(item) for item in contribution.get("counterfactual_point_ids", [])
        )
        contribution_distinct_value_count = int(
            contribution.get("distinct_observed_value_count", 0)
        )
        contribution_max_effect = contribution.get(
            "maximum_normalized_residual_effect"
        )
        contribution_affected_residual_ids = sorted(
            str(item) for item in contribution.get("affected_residual_ids", [])
        )
        if policy.contribution_expectation == "sensitive":
            contribution_passed = (
                contribution_status == "pass"
                and contribution_distinct_value_count >= 2
                and contribution_max_effect is not None
                and float(contribution_max_effect)
                >= float(policy.minimum_normalized_contribution_effect or math.inf)
                and bool(contribution_affected_residual_ids)
            )
        else:
            contribution_passed = (
                contribution_status == "verified_non_sensitive"
                and contribution_distinct_value_count >= 2
                and contribution_max_effect is not None
                and float(contribution_max_effect)
                <= float(policy.maximum_non_sensitive_contribution_effect or 0.0)
                and contribution.get("non_sensitive_reason")
                == policy.non_sensitive_reason
                and contribution.get("non_sensitive_claim_boundary")
                == policy.non_sensitive_claim_boundary
            )
        required_strata_results: list[dict[str, Any]] = []
        covered_universal_strata: list[str] = []
        missing_universal_strata: list[str] = []
        availability_source_id = policy.availability_source_id
        if policy.temporal_behavior == "time_varying":
            parameter_available_points = _parameter_available_point_count(
                policy.availability_source_id,
                target,
                manifest,
                available_points,
                target_to_sources,
                findings,
            )
            selected_count = len(selected_rows)
            ratio = _ratio(selected_count, parameter_available_points)
            validated_ratio = _ratio(validated, parameter_available_points)
            coverage_floor = _coverage_floor(
                available_count=parameter_available_points,
                plan_minimum_count=adequacy.minimum_per_parameter_valid_points,
                plan_minimum_ratio=adequacy.minimum_per_parameter_valid_ratio,
                project_minimum_count=policy.minimum_valid_points,
                project_minimum_ratio=policy.minimum_valid_ratio,
                convergence_minimum_count=policy.convergence_minimum_valid_points,
                convergence_minimum_ratio=policy.convergence_minimum_valid_ratio,
                full_sequence_required=adequacy.sampling_mode == "full",
            )
            maximum_observed_row_gap = _max_int_gap(sorted(validated_rows))
            universal_maximum_row_gap = _universal_maximum_row_gap(
                parameter_available_points,
                int(coverage_floor["effective_minimum_count"]),
            )
            universal_strata = _row_strata_counts(
                parameter_available_points,
                selected_rows,
                evaluated_rows,
                validated_rows,
                (
                    ("early", 0.0, 1 / 3, 1),
                    ("middle", 1 / 3, 2 / 3, 1),
                    ("late", 2 / 3, 1.0, 1),
                ),
            )
            covered_universal_strata = [
                row["stratum_id"]
                for row in universal_strata
                if row["validated_count"] >= row["minimum_valid_points"]
            ]
            missing_universal_strata = sorted(
                {"early", "middle", "late"} - set(covered_universal_strata)
            )
            required_strata_results = _row_strata_counts(
                parameter_available_points,
                selected_rows,
                evaluated_rows,
                validated_rows,
                tuple(
                    (
                        item.stratum_id,
                        item.start_fraction,
                        item.end_fraction,
                        item.minimum_valid_points,
                    )
                    for item in policy.required_strata
                ),
            )
            missing_required_strata = [
                row["stratum_id"]
                for row in required_strata_results
                if row["validated_count"] < row["minimum_valid_points"]
            ]
            representative_evidence_required = adequacy.sampling_mode != "full"
            representative_evidence_passed = (
                bool(residual_evidence_point_ids)
                and bool(direction_evidence_scenario_ids)
                and direction_distinct_value_count >= 2
                and physical_envelope_declared
            )
            if representative_evidence_required and not residual_evidence_point_ids:
                findings.append(
                    _finding(
                        "error",
                        "time_varying_parameter_residual_evidence_missing",
                        "representative parameter sampling requires current pointwise residual evidence",
                        target,
                    )
                )
            if representative_evidence_required and (
                not direction_evidence_scenario_ids or direction_distinct_value_count < 2
            ):
                findings.append(
                    _finding(
                        "error",
                        "time_varying_parameter_direction_evidence_missing",
                        "representative parameter sampling requires a declared perturbation and observed value direction",
                        target,
                    )
                )
            if representative_evidence_required and not physical_envelope_declared:
                findings.append(
                    _finding(
                        "error",
                        "time_varying_parameter_physical_envelope_missing",
                        "representative parameter sampling requires a declared physical envelope",
                        target,
                    )
                )
            if not model_parameter_exists:
                findings.append(
                    _finding(
                        "error",
                        "time_varying_parameter_model_target_missing",
                        "time-varying parameter is not an executable component parameter in the current model",
                        target,
                    )
                )
            if not contribution_passed:
                findings.append(
                    _finding(
                        "error",
                        "time_varying_parameter_model_contribution_missing",
                        "native counterfactual replay did not prove the declared parameter contribution or non-sensitive disposition",
                        target,
                        {
                            "expectation": policy.contribution_expectation,
                            "contribution_status": contribution_status,
                            "distinct_observed_value_count": contribution_distinct_value_count,
                            "maximum_normalized_residual_effect": contribution_max_effect,
                        },
                    )
                )
            passed = (
                target in covered_model_targets
                and model_parameter_exists
                and parameter_available_points > 0
                and validated >= int(coverage_floor["effective_minimum_count"])
                and validated_ratio >= float(coverage_floor["effective_minimum_ratio"])
                and len(distinct) >= int(policy.minimum_distinct_timestamps or 0)
                and span is not None
                and span >= float(policy.minimum_time_span or math.inf)
                and max_gap is not None
                and max_gap <= float(policy.maximum_time_gap or 0.0)
                and not missing_universal_strata
                and not missing_required_strata
                and maximum_observed_row_gap is not None
                and universal_maximum_row_gap is not None
                and maximum_observed_row_gap <= universal_maximum_row_gap
                and contribution_passed
                and (
                    not representative_evidence_required
                    or representative_evidence_passed
                )
                and (
                    adequacy.sampling_mode != "full"
                    or validated == parameter_available_points
                )
            )
            if not passed:
                findings.append(
                    _finding(
                        "error",
                        "time_varying_parameter_time_coverage_insufficient",
                        "time-varying parameter lacks its own sufficient temporal coverage",
                        target,
                        {
                            "availability_source_id": availability_source_id,
                            "available_point_count": parameter_available_points,
                            "valid_point_count": len(present),
                            "unique_selected_row_count": selected_count,
                            "evaluated_point_count": evaluated,
                            "validated_point_count": validated,
                            "valid_ratio": ratio,
                            "validated_ratio": validated_ratio,
                            "distinct_timestamp_count": len(distinct),
                            "time_span": span,
                            "maximum_observed_gap": max_gap,
                            "missing_universal_strata": missing_universal_strata,
                            "missing_required_strata": missing_required_strata,
                            "effective_minimum_valid_points": coverage_floor["effective_minimum_count"],
                            "effective_minimum_valid_ratio": coverage_floor["effective_minimum_ratio"],
                            "maximum_observed_row_gap": maximum_observed_row_gap,
                            "universal_maximum_row_gap": universal_maximum_row_gap,
                        },
                    )
                )
        else:
            parameter_available_points = 1
            selected_count = 1 if target in covered_model_targets else 0
            evaluated = selected_count
            validated = selected_count
            ratio = float(selected_count)
            validated_ratio = float(validated)
            representative_evidence_required = False
            representative_evidence_passed = True
            coverage_floor = None
            maximum_observed_row_gap = None
            universal_maximum_row_gap = None
            contribution_status = "not_applicable"
            contribution_passed = True
            model_parameter_exists = target in model_parameter_ids
            passed = target in covered_model_targets and model_parameter_exists
            if not passed:
                findings.append(
                    _finding(
                        "error",
                        "static_parameter_evidence_missing",
                        "static parameter lacks active binding evidence or an executable model parameter target",
                        target,
                    )
                )
        per_parameter_pass[target] = passed
        per_parameter.append(
            {
                "parameter_id": target,
                "temporal_behavior": policy.temporal_behavior,
                "classification_source": policy.classification_source,
                "availability_source_id": availability_source_id,
                "source_ids": sorted(target_to_sources.get(target, set())),
                "available_point_count": parameter_available_points,
                "selected_point_count": selected_count,
                "unique_selected_row_count": len(selected_rows) if policy.temporal_behavior == "time_varying" else selected_count,
                "valid_point_count": len(present),
                "evaluated_point_count": evaluated,
                "validated_point_count": validated,
                "missing_point_count": max(parameter_available_points - selected_count, 0),
                "valid_ratio": ratio,
                "validated_ratio": validated_ratio,
                "required_minimum_valid_points": (
                    coverage_floor["effective_minimum_count"] if coverage_floor else None
                ),
                "required_minimum_valid_ratio": (
                    coverage_floor["effective_minimum_ratio"] if coverage_floor else None
                ),
                "required_minimum_distinct_timestamps": policy.minimum_distinct_timestamps,
                "required_minimum_time_span": policy.minimum_time_span,
                "required_maximum_time_gap": policy.maximum_time_gap,
                "coverage_floor": coverage_floor,
                "distinct_timestamp_count": len(distinct),
                "time_span": span,
                "maximum_observed_gap": max_gap,
                "maximum_observed_row_gap": maximum_observed_row_gap,
                "universal_maximum_row_gap": universal_maximum_row_gap,
                "covered_universal_strata": covered_universal_strata,
                "missing_universal_strata": missing_universal_strata,
                "required_strata_results": required_strata_results,
                "residual_evidence_point_ids": residual_evidence_point_ids,
                "direction_evidence_scenario_ids": direction_evidence_scenario_ids,
                "direction_distinct_value_count": direction_distinct_value_count,
                "physical_envelope_declared": physical_envelope_declared,
                "representative_evidence_status": (
                    "pass"
                    if representative_evidence_required and representative_evidence_passed
                    else "blocked"
                    if representative_evidence_required
                    else "not_applicable"
                ),
                "model_parameter_exists": model_parameter_exists,
                "contribution_expectation": policy.contribution_expectation,
                "contribution_evidence_point_ids": contribution_evidence_point_ids,
                "contribution_distinct_value_count": contribution_distinct_value_count,
                "contribution_max_normalized_residual_effect": contribution_max_effect,
                "contribution_affected_residual_ids": contribution_affected_residual_ids,
                "contribution_status": contribution_status,
                "non_sensitive_reason": policy.non_sensitive_reason,
                "non_sensitive_claim_boundary": policy.non_sensitive_claim_boundary,
                "status": "pass" if passed else "blocked",
            }
        )

    missing_critical_signals = sorted(target for target in required_signals if not per_signal_pass.get(target, False))
    validated_parameter_ids = sorted(
        target for target, passed in per_parameter_pass.items() if passed
    )
    missing_critical_parameters = sorted(
        required_parameters - set(validated_parameter_ids)
    )
    for target in missing_critical_parameters:
        findings.append(
            _finding(
                "error",
                "critical_parameter_uncovered",
                "hierarchy-required or declared critical parameter lacks adequate classified evidence",
                target,
            )
        )

    temporal = _temporal_receipt(
        adequacy,
        claim_scope,
        dataset_identity_ids,
        available_points,
        valid_points,
        residual_status_by_point,
        findings,
    )
    selected_rows = {
        (point.source_identity_id, point.source_row_index)
        for point in valid_points
        if point.source_identity_id is not None and point.source_row_index is not None
    }
    residual_points = residual_receipt.get("points", [])
    evaluated_points = sum(1 for item in residual_points if item.get("status") in {"pass", "fail"})
    validated_points = sum(1 for item in residual_points if item.get("status") == "pass")
    point_ratio = _ratio(len(selected_rows), eligible_points)
    signal_ratio = _ratio(len(selected_signal_ids), len(eligible_signal_ids))
    parameter_ratio = _ratio(len(covered_parameters), len(available_parameter_ids))
    exclusion_ratio = _ratio(len(excluded_signal_ids), len(available_signal_ids))

    if len(selected_rows) < int(selection_floor["effective_minimum_count"]):
        findings.append(
            _finding(
                "error",
                "selected_point_floor_not_met",
                "selected point count is below the resolved universal/project/convergence floor",
                details={"selection_floor": selection_floor},
            )
        )
    if point_ratio < float(selection_floor["effective_minimum_ratio"]):
        findings.append(
            _finding(
                "error",
                "selected_point_ratio_not_met",
                "selected/raw point ratio is below the resolved universal/project/convergence floor",
                details={"selection_floor": selection_floor},
            )
        )
    if adequacy.sampling_mode == "full" and len(selected_rows) != eligible_points:
        findings.append(_finding("error", "full_sampling_incomplete", "full mode requires every eligible source row"))
    if signal_ratio < adequacy.minimum_signal_coverage_ratio:
        findings.append(_finding("error", "signal_coverage_ratio_not_met", "selected/eligible signal ratio is below the declared floor"))
    if parameter_ratio < adequacy.minimum_parameter_coverage_ratio:
        findings.append(
            _finding(
                "error",
                "parameter_coverage_ratio_not_met",
                "selected/available parameter ratio is below the declared floor",
                details={
                    "available_parameter_count": len(available_parameter_ids),
                    "selected_parameter_count": len(covered_parameters),
                    "selected_parameter_ratio": parameter_ratio,
                    "minimum_parameter_coverage_ratio": adequacy.minimum_parameter_coverage_ratio,
                },
            )
        )
    if exclusion_ratio > adequacy.maximum_exclusion_ratio:
        findings.append(_finding("error", "exclusion_ratio_exceeded", "raw signal exclusion ratio exceeds the declared maximum"))

    reasons = Counter(
        (role.reason or "").strip().lower()
        for role in role_matrix.roles
        if role.coverage_status == "excluded"
    )
    repeated_reasons = {
        reason: count
        for reason, count in reasons.items()
        if reason and count > adequacy.maximum_repeated_exclusion_reason_count
    }
    generic = {"n/a", "na", "none", "other", "unused", "excluded", "irrelevant", "not used"}
    templated_reasons = sorted(reason for reason in reasons if reason in generic or (reason and len(reason) < 8))
    if adequacy.reject_repeated_exclusion_reasons and repeated_reasons:
        findings.append(_finding("error", "repeated_exclusion_reason", "multiple exclusions reuse one reason", details=repeated_reasons))
    if templated_reasons:
        findings.append(_finding("error", "templated_exclusion_reason", "generic exclusion reasons cannot support broad coverage", details={"reasons": templated_reasons}))

    validated_signal_ids = set()
    for target, sources in target_to_sources.items():
        if target in covered_model_targets and (per_signal_pass.get(target, False) or target not in signal_targets):
            validated_signal_ids.update(sources)
    validated_signal_ids &= set(selected_signal_ids)

    families = [
        _family_receipt(quota, per_signal_pass, set(validated_parameter_ids), covered_model_targets, findings)
        for quota in adequacy.family_quotas
    ]
    subsystem_families = []
    for block in audit_spec.hierarchy.blocks:
        members = [*block.required_variables, *block.required_parameters]
        covered = [
            member
            for member in members
            if per_signal_pass.get(member, False) or member in validated_parameter_ids
        ]
        ratio = _ratio(len(covered), len(members)) if members else 1.0
        status = "pass" if len(covered) == len(members) else "blocked"
        if status == "blocked":
            findings.append(
                _finding(
                    "error",
                    "subsystem_critical_coverage_missing",
                    "subsystem does not cover every required variable and parameter",
                    block.id,
                    {"members": members, "covered": covered},
                )
            )
        subsystem_families.append(
            {
                "family_id": f"subsystem:{block.id}",
                "member_ids": members,
                "covered_member_ids": sorted(covered),
                "covered_count": len(covered),
                "covered_ratio": ratio,
                "minimum_covered_count": len(members),
                "minimum_covered_ratio": 1.0,
                "status": status,
            }
        )

    if adequacy.sampling_mode == "adaptive" and adequacy.adaptive_converged is not True:
        findings.append(_finding("error", "adaptive_sampling_not_converged", "adaptive sampling lacks convergence evidence"))

    status = _status(findings)
    universe_payload = {
        "available_point_count": available_points,
        "eligible_point_count": eligible_points,
        "selected_point_count": len(valid_points),
        "unique_selected_row_count": len(selected_rows),
        "evaluated_point_count": evaluated_points,
        "validated_point_count": validated_points,
        "available_signal_ids": available_signal_ids,
        "eligible_signal_ids": eligible_signal_ids,
        "selected_signal_ids": sorted(selected_signal_ids),
        "validated_signal_ids": sorted(validated_signal_ids),
        "excluded_signal_ids": excluded_signal_ids,
        "available_parameter_ids": available_parameter_ids,
        "eligible_parameter_ids": available_parameter_ids,
        "selected_parameter_ids": covered_parameters,
        "validated_parameter_ids": validated_parameter_ids,
        "required_parameter_ids": sorted(required_parameters),
        "covered_parameter_ids": covered_parameters,
        "point_selection_ratio": point_ratio,
        "signal_selection_ratio": signal_ratio,
        "parameter_selection_ratio": parameter_ratio,
        "exclusion_ratio": exclusion_ratio,
        "selection_floor": selection_floor,
    }
    universe_payload["universe_fingerprint"] = _fingerprint(universe_payload)
    receipt = {
        "artifact_kind": "physicsguard_validation_adequacy_receipt",
        "receipt_version": "1.0",
        "status": status,
        "sampling_mode": adequacy.sampling_mode,
        "threshold_source": adequacy.threshold_source,
        "selection_policy_id": adequacy.selection_policy_id,
        "selection_rationale": adequacy.selection_rationale,
        "sampling_policy_fingerprint": _fingerprint(adequacy.model_dump(mode="json")),
        "universe": universe_payload,
        "temporal": temporal,
        "per_signal": per_signal,
        "per_parameter": per_parameter,
        "signal_time_matrix": signal_time_matrix,
        "families": families,
        "subsystem_families": subsystem_families,
        "missing_critical_signals": missing_critical_signals,
        "missing_critical_parameters": missing_critical_parameters,
        "missing_parameter_temporal_classifications": missing_parameter_classifications,
        "critical_point_ids": _critical_point_ids(adequacy, valid_points),
        "critical_signal_ids": sorted(required_signals),
        "critical_parameter_ids": sorted(required_parameters),
        "repeated_exclusion_reasons": repeated_reasons,
        "templated_exclusion_reasons": templated_reasons,
        "finding_codes": sorted({item["type"] for item in findings}),
        "claim_boundary": (
            "adequacy covers only the exact hashed manifest, hierarchy, role matrix, evidence bundle, "
            "selected source rows, timestamps, signals, classified static/time-varying parameters, "
            "resolved anti-degeneracy floors, native parameter-contribution counterfactuals, families, and declared thresholds"
        ),
    }
    validated = ValidationAdequacyReceiptSpec.model_validate(receipt).model_dump(mode="json")
    return ValidationAdequacyEvaluation(receipt=validated, findings=findings)


def _temporal_receipt(
    adequacy: ValidationAdequacyPlanSpec,
    claim_scope: str,
    dataset_identity_ids: set[str],
    available_points: int,
    points,
    residual_status_by_point: dict[str, str],
    findings: list[dict[str, Any]],
) -> dict[str, Any]:
    timestamps = [point.timestamp for point in points if point.timestamp is not None]
    counts = Counter(timestamps)
    duplicates = sorted(value for value, count in counts.items() if count > 1)
    distinct = sorted(counts)
    span = distinct[-1] - distinct[0] if len(distinct) >= 2 else None
    max_gap = _max_gap(distinct)
    missing_lineage = []
    out_of_range = []
    row_tokens = []
    for point in points:
        if point.source_identity_id is None or point.source_row_index is None:
            missing_lineage.append(point.point_id)
            continue
        token = f"{point.source_identity_id}:{point.source_row_index}"
        row_tokens.append(token)
        if (
            point.source_identity_id not in dataset_identity_ids
            or point.source_row_index < 0
            or point.source_row_index >= available_points
        ):
            out_of_range.append(token)
    duplicate_rows = sorted(token for token, count in Counter(row_tokens).items() if count > 1)

    stratum_point_ids: dict[str, set[str]] = {
        "start": set(),
        "middle": set(),
        "end": set(),
    }
    if available_points > 1:
        for point in points:
            if point.source_row_index is None:
                continue
            for stratum_id in _universal_row_strata(
                int(point.source_row_index), available_points
            ):
                stratum_point_ids[stratum_id].add(point.point_id)
    covered_strata = {
        stratum_id for stratum_id, point_ids in stratum_point_ids.items() if point_ids
    }
    missing_strata = sorted({"start", "middle", "end"} - covered_strata) if adequacy.require_start_middle_end else []
    events = {tag for point in points for tag in point.event_tags}
    peaks = {tag for point in points for tag in point.peak_tags}
    boundaries = {tag for point in points for tag in point.boundary_tags}
    modes = {point.mode_id for point in points if point.mode_id}
    missing_events = sorted(set(adequacy.required_event_tags) - events)
    missing_peaks = sorted(set(adequacy.required_peak_tags) - peaks)
    missing_boundaries = sorted(set(adequacy.required_boundary_tags) - boundaries)
    missing_modes = sorted(set(adequacy.required_mode_ids) - modes)

    checks = {
        "temporal_distinct_timestamp_floor_not_met": len(distinct) < adequacy.minimum_distinct_timestamps,
        "temporal_duplicate_timestamps": bool(duplicates),
        "temporal_positive_span_missing": span is None or span < adequacy.minimum_time_span,
        "temporal_maximum_gap_exceeded": max_gap is None or max_gap > adequacy.maximum_time_gap,
        "temporal_strata_missing": bool(missing_strata),
        "temporal_event_tags_missing": bool(missing_events),
        "temporal_peak_tags_missing": bool(missing_peaks),
        "temporal_boundary_tags_missing": bool(missing_boundaries),
        "temporal_modes_missing": bool(missing_modes),
        "source_row_lineage_missing": bool(missing_lineage),
        "source_row_lineage_duplicate": bool(duplicate_rows),
        "source_row_lineage_out_of_range": bool(out_of_range),
    }
    if claim_scope != "snapshot":
        for code, failed in checks.items():
            if failed:
                findings.append(_finding("error", code, "temporal/source-row adequacy gate failed"))
    strata_results = [
        {
            "stratum_id": stratum_id,
            "selected_count": len(point_ids),
            "evaluated_count": sum(
                1
                for point_id in point_ids
                if residual_status_by_point.get(point_id) in {"pass", "fail"}
            ),
            "validated_count": sum(
                1
                for point_id in point_ids
                if residual_status_by_point.get(point_id) == "pass"
            ),
        }
        for stratum_id, point_ids in sorted(stratum_point_ids.items())
    ]
    return {
        "status": "blocked" if claim_scope != "snapshot" and any(checks.values()) else "pass",
        "distinct_timestamp_count": len(distinct),
        "duplicate_timestamps": duplicates,
        "time_span": span,
        "maximum_observed_gap": max_gap,
        "covered_strata": sorted(covered_strata),
        "missing_strata": missing_strata,
        "missing_event_tags": missing_events,
        "missing_peak_tags": missing_peaks,
        "missing_boundary_tags": missing_boundaries,
        "missing_mode_ids": missing_modes,
        "duplicate_source_rows": duplicate_rows,
        "out_of_range_source_rows": out_of_range,
        "missing_source_lineage": missing_lineage,
        "strata_results": strata_results,
    }


def _family_receipt(
    quota: FamilyQuotaPlanSpec,
    per_signal_pass: dict[str, bool],
    covered_parameters: set[str],
    covered_targets: set[str],
    findings: list[dict[str, Any]],
) -> dict[str, Any]:
    covered = sorted(
        member
        for member in quota.member_ids
        if per_signal_pass.get(member, False) or member in covered_parameters or member in covered_targets
    )
    ratio = _ratio(len(covered), len(quota.member_ids))
    passed = len(covered) >= quota.minimum_covered_count and ratio >= quota.minimum_covered_ratio
    if not passed:
        findings.append(_finding("error", "family_quota_not_met", "declared signal/parameter family quota is not met", quota.family_id))
    return {
        "family_id": quota.family_id,
        "member_ids": list(quota.member_ids),
        "covered_member_ids": covered,
        "covered_count": len(covered),
        "covered_ratio": ratio,
        "minimum_covered_count": quota.minimum_covered_count,
        "minimum_covered_ratio": quota.minimum_covered_ratio,
        "status": "pass" if passed else "blocked",
    }


def _not_applicable_receipt(series, residual_receipt) -> dict[str, Any]:
    selected = len(series.points) if series is not None else 0
    evaluated = sum(1 for item in residual_receipt.get("points", []) if item.get("status") in {"pass", "fail"})
    payload = _empty_universe(selected, evaluated)
    payload["universe_fingerprint"] = _fingerprint(payload)
    return ValidationAdequacyReceiptSpec.model_validate(
        {
            "artifact_kind": "physicsguard_validation_adequacy_receipt",
            "status": "not_applicable",
            "universe": payload,
            "temporal": _empty_temporal("not_applicable"),
            "claim_boundary": "snapshot-only evidence; no broad temporal, signal-family, or predictive adequacy claim",
        }
    ).model_dump(mode="json")


def _blocked_empty_receipt(series, residual_receipt, codes, adequacy=None) -> dict[str, Any]:
    selected = len(series.points) if series is not None else 0
    evaluated = sum(1 for item in residual_receipt.get("points", []) if item.get("status") in {"pass", "fail"})
    payload = _empty_universe(selected, evaluated)
    payload["universe_fingerprint"] = _fingerprint(payload)
    return ValidationAdequacyReceiptSpec.model_validate(
        {
            "artifact_kind": "physicsguard_validation_adequacy_receipt",
            "status": "blocked",
            "sampling_mode": adequacy.sampling_mode if adequacy else None,
            "threshold_source": adequacy.threshold_source if adequacy else None,
            "universe": payload,
            "temporal": _empty_temporal("blocked"),
            "finding_codes": sorted(set(codes)),
            "claim_boundary": "adequacy could not be established from current target-owned artifacts",
        }
    ).model_dump(mode="json")


def _empty_universe(selected: int, evaluated: int) -> dict[str, Any]:
    return {
        "universe_fingerprint": "",
        "available_point_count": 0,
        "eligible_point_count": 0,
        "selected_point_count": selected,
        "unique_selected_row_count": 0,
        "evaluated_point_count": evaluated,
        "validated_point_count": 0,
        "available_signal_ids": [],
        "eligible_signal_ids": [],
        "selected_signal_ids": [],
        "validated_signal_ids": [],
        "excluded_signal_ids": [],
        "available_parameter_ids": [],
        "eligible_parameter_ids": [],
        "selected_parameter_ids": [],
        "validated_parameter_ids": [],
        "required_parameter_ids": [],
        "covered_parameter_ids": [],
        "point_selection_ratio": 0.0,
        "signal_selection_ratio": 0.0,
        "parameter_selection_ratio": 0.0,
        "exclusion_ratio": 0.0,
        "selection_floor": _coverage_floor(
            available_count=0,
            plan_minimum_count=0,
            plan_minimum_ratio=0.0,
        ),
    }


def _empty_temporal(status: str) -> dict[str, Any]:
    return {
        "status": status,
        "distinct_timestamp_count": 0,
        "duplicate_timestamps": [],
        "time_span": None,
        "maximum_observed_gap": None,
        "covered_strata": [],
        "missing_strata": [],
        "missing_event_tags": [],
        "missing_peak_tags": [],
        "missing_boundary_tags": [],
        "missing_mode_ids": [],
        "duplicate_source_rows": [],
        "out_of_range_source_rows": [],
        "missing_source_lineage": [],
        "strata_results": [],
    }


def _load_or_find(loader, path: Path, code: str, findings: list[dict[str, Any]]):
    try:
        return loader(path)
    except Exception as exc:
        findings.append(_finding("error", code, "target-owned adequacy artifact could not be loaded", str(path), {"error": str(exc)}))
        return None


def _authoritative_manifest_point_count(
    manifest: DataFileManifestSpec,
    findings: list[dict[str, Any]],
) -> int:
    """Resolve one conservative point denominator from the current manifest."""

    row_count = manifest.shape.row_count
    sample_count = manifest.shape.sample_count
    if (
        row_count is not None
        and sample_count is not None
        and row_count != sample_count
    ):
        findings.append(
            _finding(
                "error",
                "manifest_point_count_mismatch",
                "row_count and sample_count disagree; broad adequacy cannot choose "
                "the smaller denominator",
                details={
                    "row_count": row_count,
                    "sample_count": sample_count,
                    "conservative_point_count": max(row_count, sample_count),
                },
            )
        )
    declared = [
        int(value)
        for value in (row_count, sample_count)
        if value is not None
    ]
    return max(declared, default=0)


def _parameter_available_point_count(
    availability_source_id: str | None,
    parameter_id: str,
    manifest: DataFileManifestSpec,
    manifest_point_count: int,
    target_to_sources: dict[str, set[str]],
    findings: list[dict[str, Any]],
) -> int:
    """Resolve a time-varying parameter denominator from target-owned artifacts."""

    if availability_source_id == "manifest:rows":
        count = manifest_point_count
        if count <= 0:
            findings.append(
                _finding(
                    "error",
                    "parameter_availability_count_missing",
                    "manifest row/sample count is unavailable for the time-varying parameter",
                    parameter_id,
                )
            )
        return count
    if availability_source_id and availability_source_id.startswith("field:"):
        if availability_source_id not in target_to_sources.get(parameter_id, set()):
            findings.append(
                _finding(
                    "error",
                    "parameter_availability_source_unbound",
                    "time-varying parameter availability source is not an active target binding",
                    parameter_id,
                    {"availability_source_id": availability_source_id},
                )
            )
            return 0
        field_name = availability_source_id.removeprefix("field:")
        field = next((item for item in manifest.fields if item.name == field_name), None)
        if field is None or field.non_null_count is None or field.non_null_count <= 0:
            findings.append(
                _finding(
                    "error",
                    "parameter_availability_count_missing",
                    "bound manifest field does not provide a positive non-null count",
                    parameter_id,
                    {"availability_source_id": availability_source_id},
                )
            )
            return 0
        return int(field.non_null_count)
    findings.append(
        _finding(
            "error",
            "parameter_availability_source_invalid",
            "time-varying parameter availability must use manifest:rows or a bound field source",
            parameter_id,
            {"availability_source_id": availability_source_id},
        )
    )
    return 0


def _universal_row_strata(row_index: int, available_count: int) -> tuple[str, ...]:
    if available_count <= 1 or row_index < 0 or row_index >= available_count:
        return ()
    position = row_index / (available_count - 1)
    result: list[str] = []
    if position <= 1 / 3:
        result.append("start")
    if 1 / 3 <= position <= 2 / 3:
        result.append("middle")
    if position >= 2 / 3:
        result.append("end")
    return tuple(result)


def _row_strata_counts(
    available_count: int,
    selected_rows: set[int],
    evaluated_rows: set[int],
    validated_rows: set[int],
    strata: tuple[tuple[str, float, float, int], ...],
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    denominator = max(available_count - 1, 1)
    for stratum_id, start_fraction, end_fraction, minimum_valid_points in strata:
        eligible_count = 0
        if available_count > 0:
            lower = math.ceil(start_fraction * denominator - 1.0e-12)
            upper = math.floor(end_fraction * denominator + 1.0e-12)
            lower = max(lower, 0)
            upper = min(upper, available_count - 1)
            eligible_count = max(upper - lower + 1, 0)

        def inside(row_index: int) -> bool:
            if row_index < 0 or row_index >= available_count:
                return False
            position = row_index / denominator if available_count > 1 else 0.0
            return start_fraction <= position <= end_fraction

        selected_count = sum(1 for row in selected_rows if inside(row))
        evaluated_count = sum(1 for row in evaluated_rows if inside(row))
        validated_count = sum(1 for row in validated_rows if inside(row))
        result.append(
            {
                "stratum_id": stratum_id,
                "start_fraction": start_fraction,
                "end_fraction": end_fraction,
                "eligible_count": eligible_count,
                "selected_count": selected_count,
                "evaluated_count": evaluated_count,
                "validated_count": validated_count,
                "minimum_valid_points": minimum_valid_points,
                "status": "pass" if validated_count >= minimum_valid_points else "blocked",
            }
        )
    return result


def _max_gap(values: list[float]) -> float | None:
    if len(values) < 2:
        return None
    return max(right - left for left, right in zip(values, values[1:]))


def _max_int_gap(values: list[int]) -> int | None:
    if len(values) < 2:
        return None
    return max(right - left for left, right in zip(values, values[1:]))


def _coverage_floor(
    *,
    available_count: int,
    plan_minimum_count: int,
    plan_minimum_ratio: float,
    project_minimum_count: int | None = None,
    project_minimum_ratio: float | None = None,
    convergence_minimum_count: int | None = None,
    convergence_minimum_ratio: float | None = None,
    full_sequence_required: bool = False,
) -> dict[str, Any]:
    """Resolve an N-aware floor that project policy may strengthen but never weaken."""

    count = max(int(available_count), 0)
    if count == 0:
        universal_count = 0
    else:
        universal_count = min(
            count,
            max(12, math.ceil(math.sqrt(count)), 9),
        )
    universal_ratio = _ratio(universal_count, count)
    candidates = [
        universal_count,
        max(int(plan_minimum_count), 0),
        math.ceil(max(float(plan_minimum_ratio), 0.0) * count),
    ]
    for value in (project_minimum_count, convergence_minimum_count):
        if value is not None:
            candidates.append(max(int(value), 0))
    for value in (project_minimum_ratio, convergence_minimum_ratio):
        if value is not None:
            candidates.append(math.ceil(max(float(value), 0.0) * count))
    if full_sequence_required:
        candidates.append(count)
    effective_count = min(count, max(candidates, default=0)) if count else 0
    return {
        "algorithm_id": ANTI_DEGENERACY_FLOOR_ALGORITHM,
        "available_count": count,
        "universal_minimum_count": universal_count,
        "universal_minimum_ratio": universal_ratio,
        "plan_minimum_count": max(int(plan_minimum_count), 0),
        "plan_minimum_ratio": max(float(plan_minimum_ratio), 0.0),
        "project_minimum_count": project_minimum_count,
        "project_minimum_ratio": project_minimum_ratio,
        "convergence_minimum_count": convergence_minimum_count,
        "convergence_minimum_ratio": convergence_minimum_ratio,
        "full_sequence_required": full_sequence_required,
        "effective_minimum_count": effective_count,
        "effective_minimum_ratio": _ratio(effective_count, count),
    }


def _universal_maximum_row_gap(
    available_count: int,
    effective_minimum_count: int,
) -> int | None:
    if available_count <= 1 or effective_minimum_count <= 1:
        return None
    # Two ideal intervals of slack allow event-aware placement while preventing
    # all representative points from collapsing into a few phases.
    return max(
        1,
        math.ceil(2 * (available_count - 1) / (effective_minimum_count - 1)),
    )


def _critical_point_ids(
    adequacy: ValidationAdequacyPlanSpec,
    points: Iterable[Any],
) -> list[str]:
    required_events = set(adequacy.required_event_tags)
    required_peaks = set(adequacy.required_peak_tags)
    required_boundaries = set(adequacy.required_boundary_tags)
    required_modes = set(adequacy.required_mode_ids)
    return sorted(
        point.point_id
        for point in points
        if (
            required_events.intersection(point.event_tags)
            or required_peaks.intersection(point.peak_tags)
            or required_boundaries.intersection(point.boundary_tags)
            or (point.mode_id is not None and point.mode_id in required_modes)
        )
    )


def _ratio(numerator: int, denominator: int) -> float:
    return float(numerator / denominator) if denominator else 0.0


def _fingerprint(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _status(findings: list[dict[str, Any]]) -> str:
    if any(item["severity"] == "error" for item in findings):
        return "blocked"
    if any(item["severity"] == "warning" for item in findings):
        return "partial"
    return "pass"


def _finding(severity: str, code: str, message: str, target: str | None = None, details: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"severity": severity, "type": code, "message": message, "target": target, "details": details or {}}


def _resolve_path(base_dir: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else base_dir / path


__all__ = [
    "ValidationAdequacyEvaluation",
    "evaluate_validation_adequacy",
    "evaluate_validation_adequacy_artifacts",
]
