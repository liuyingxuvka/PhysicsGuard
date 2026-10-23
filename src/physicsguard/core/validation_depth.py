"""Native dataset/time/scenario depth evaluation for model validation.

This module extends the existing model-dataset validator.  It applies the
existing low-fidelity hierarchy relations pointwise and emits evidence for
downstream gates; it is not a second physical simulator.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path
import statistics
from typing import Any, Iterable

from physicsguard.core.hierarchy import HierarchicalAuditRunner
from physicsguard.core.predictive_rollout import evaluate_predictive_rollout
from physicsguard.core.parameter_coverage import _metadata_is_stale
from physicsguard.core.validation_adequacy import evaluate_validation_adequacy, load_contract_field_mappings
from physicsguard.io.observation_loader import load_observed_series
from physicsguard.io.test_file_contract_loader import load_test_file_contract
from physicsguard.schema.hierarchy_spec import HierarchicalAuditSpec
from physicsguard.schema.model_dataset_validation import ModelValidationPlanSpec
from physicsguard.schema.observation_spec import ObservedValuesSpec
from physicsguard.schema.validation_adequacy import ParameterTemporalPolicySpec
from physicsguard.schema.validation_depth import (
    CalibrationSplitPlanSpec,
    ObservedSeriesPointSpec,
    ObservedSeriesSpec,
    ValidationIdentityReferenceSpec,
)


DEPTH_KIND = "physicsguard_validation_depth"
UNSAFE_BOUNDARY = (
    "validation depth covers only the checked low-fidelity relations, files, mappings, "
    "time points, and scenarios; it does not prove high-fidelity behavior, recover a "
    "commercial model, establish commercial-tool equivalence, or support extrapolation "
    "outside that boundary"
)


@dataclass(frozen=True)
class ValidationDepthEvaluation:
    """Depth computations, findings promoted to the report, and series validation."""

    payload: dict[str, Any]
    promoted_findings: list[dict[str, Any]]
    envelope_findings: list[dict[str, Any]]
    series_direct_validation: dict[str, Any] | None


def evaluate_validation_depth(
    plan: ModelValidationPlanSpec,
    *,
    base_dir: Path,
    audit_spec: HierarchicalAuditSpec,
    scalar_observed: ObservedValuesSpec,
    scalar_direct: dict[str, Any],
) -> ValidationDepthEvaluation:
    """Evaluate the optional depth plan and always return the depth payload."""

    if plan.depth is None:
        return _legacy_snapshot_depth(plan, base_dir, scalar_observed, scalar_direct)

    depth = plan.depth
    findings: list[dict[str, Any]] = []

    dataset_receipt = _dataset_identity_receipt(depth.dataset, base_dir, findings)
    series_identity = _identity_receipt(depth.observed_series, base_dir)
    dataset_receipt["files"].append(series_identity)
    if series_identity["status"] != "current":
        dataset_receipt["status"] = "missing" if series_identity["status"] == "missing" else "stale"
        _add_finding(
            findings,
            "error",
            "observed_series_missing",
            "observed series file is missing",
            depth.observed_series.path,
            {"identity": series_identity},
        )

    series = _load_series(depth.observed_series, base_dir, findings)
    mapping_receipt = _mapping_review_receipt(plan, base_dir, findings)
    time_receipt = _time_receipt(depth.time_scope, series, findings)
    scenario_receipt = _scenario_receipt(depth, series, findings)
    split_receipt = _split_receipt(plan, base_dir, depth.split, findings)
    residual_receipt, series_direct = _residual_series_receipt(
        audit_spec,
        series,
        findings,
        parameter_policies=(
            depth.adequacy.parameter_temporal_policies
            if depth.adequacy is not None
            else ()
        ),
    )
    envelope_receipt, envelope_findings = _envelope_receipt(plan, series, findings)
    adequacy_evaluation = evaluate_validation_adequacy(
        plan,
        depth,
        base_dir=base_dir,
        audit_spec=audit_spec,
        series=series,
        residual_receipt=residual_receipt,
    )
    findings.extend(adequacy_evaluation.findings)
    predictive_evaluation = evaluate_predictive_rollout(
        depth.model_semantics,
        depth.predictive_rollout,
        base_dir=base_dir,
    )
    findings.extend(predictive_evaluation.findings)

    # A hard envelope violation is part of the physical audit result even when
    # the residual average is small.
    if envelope_receipt["status"] == "blocked":
        residual_receipt["audit_pass"] = False
        if residual_receipt["status"] == "pass":
            residual_receipt["status"] = "blocked"
        if series_direct is not None:
            series_direct["audit_pass"] = False
            series_direct.setdefault("warnings", []).append(
                "hard physical-envelope violation prevents a series audit pass"
            )

    status = _depth_status(findings)
    payload = {
        "artifact_kind": DEPTH_KIND,
        "validation_id": plan.validation_id,
        "status": status,
        "ok": status == "pass",
        "claim_scope": depth.time_scope.claim_scope,
        "covered_scope": time_receipt["observed_scope"],
        "model_semantics": depth.model_semantics,
        "dataset": dataset_receipt,
        "mapping": mapping_receipt,
        "time": time_receipt,
        "scenarios": scenario_receipt,
        "split": split_receipt,
        "residual_series": residual_receipt,
        "envelopes": envelope_receipt,
        "adequacy": adequacy_evaluation.receipt,
        "predictive": predictive_evaluation.receipt,
        "assumptions": list(depth.assumptions),
        "findings": findings,
        "safe_claim": _safe_depth_claim(status, depth.time_scope.claim_scope),
        "unsafe_claim_boundary": UNSAFE_BOUNDARY,
    }
    return ValidationDepthEvaluation(
        payload=payload,
        promoted_findings=findings,
        envelope_findings=envelope_findings,
        series_direct_validation=series_direct,
    )


def summarize_validation_depth(payload: dict[str, Any]) -> dict[str, Any]:
    """Compact view of the depth computations for the default validation report."""

    adequacy = payload.get("adequacy", {})
    universe = adequacy.get("universe", {})
    temporal = adequacy.get("temporal", {})
    residual = payload.get("residual_series", {})
    aggregate = residual.get("aggregate", {})
    return {
        "status": payload.get("status"),
        "claim_scope": payload.get("claim_scope"),
        "covered_scope": payload.get("covered_scope"),
        "model_semantics": payload.get("model_semantics"),
        "dataset_status": payload.get("dataset", {}).get("status"),
        "mapping_status": payload.get("mapping", {}).get("status"),
        "unresolved_mapping_targets": payload.get("mapping", {}).get("unresolved_targets", []),
        "point_count": payload.get("time", {}).get("point_count"),
        "valid_point_count": payload.get("time", {}).get("valid_point_count"),
        "series_audit_pass": residual.get("audit_pass"),
        "series_max_abs_normalized_residual": aggregate.get("max_abs_normalized_residual"),
        "invalid_point_count": aggregate.get("invalid_point_count", 0),
        "envelope_violation_count": payload.get("envelopes", {}).get("aggregate", {}).get("violation_count", 0),
        "split_status": payload.get("split", {}).get("status"),
        "adequacy": {
            "status": adequacy.get("status"),
            "selected_point_count": universe.get("selected_point_count"),
            "available_point_count": universe.get("available_point_count"),
            "distinct_timestamp_count": temporal.get("distinct_timestamp_count"),
            "time_span": temporal.get("time_span"),
            "maximum_observed_gap": temporal.get("maximum_observed_gap"),
            "missing_strata": temporal.get("missing_strata", []),
            "signals_below_floor": [
                row.get("signal_id") for row in adequacy.get("per_signal", []) if row.get("status") != "pass"
            ],
            "parameters_below_floor": [
                row.get("parameter_id") for row in adequacy.get("per_parameter", []) if row.get("status") != "pass"
            ],
        },
        "predictive_status": payload.get("predictive", {}).get("status"),
        "finding_codes": sorted({item["type"] for item in payload.get("findings", [])}),
        "safe_claim": payload.get("safe_claim"),
    }


def _legacy_snapshot_depth(
    plan: ModelValidationPlanSpec,
    base_dir: Path,
    observed: ObservedValuesSpec,
    direct: dict[str, Any],
) -> ValidationDepthEvaluation:
    """Preserve scalar commands while explicitly preventing broad depth claims."""

    point = {
        "point_id": observed.observation_name or "legacy_snapshot",
        "timestamp": None,
        "scenario_id": "legacy_snapshot",
        "case_id": None,
        "status": "pass" if direct.get("audit_pass") else "fail",
        "audit_pass": bool(direct.get("audit_pass")),
        "max_abs_normalized_residual": direct.get("max_abs_normalized_residual"),
        "residual_norm": direct.get("residual_norm"),
        "missing_variables": [],
        "warnings": list(direct.get("warnings", [])),
        "top_residuals": list(direct.get("top_residuals", [])),
    }
    split_findings: list[dict[str, Any]] = []
    split = _split_receipt(plan, base_dir, None, split_findings, legacy=True)
    findings = [
        {
            "severity": "warning",
            "type": "validation_depth_not_declared",
            "message": (
                "legacy scalar validation is usable only as a snapshot; exact dataset, "
                "current mapping, time/scenario, and series depth were not declared"
            ),
            "target": plan.validation_id,
            "details": {},
        },
        *split_findings,
    ]
    status = "blocked" if any(item["severity"] == "error" for item in findings) else "partial"
    payload = {
        "artifact_kind": DEPTH_KIND,
        "validation_id": plan.validation_id,
        "status": status,
        "ok": False,
        "claim_scope": "snapshot",
        "covered_scope": "snapshot",
        "model_semantics": "pointwise",
        "dataset": {
            "dataset_id": "not_declared",
            "status": "not_declared",
            "files": [],
            "field_schema": None,
            "parameter_roles": None,
            "testbench": None,
            "expected_testbench_version": None,
            "observed_testbench_version": None,
        },
        "mapping": {
            "status": "partial",
            "mapping_edge_files": [],
            "minimum_confidence": None,
            "signals": [],
            "unresolved_targets": [role.target for role in _required_mapping_roles(plan)],
        },
        "time": {
            "status": "partial",
            "declared_scope": "snapshot",
            "observed_scope": "snapshot",
            "time_unit": "unknown",
            "point_count": 1,
            "valid_point_count": 1,
            "start_time": None,
            "end_time": None,
            "snapshot_only": True,
        },
        "scenarios": {
            "status": "partial",
            "declared_scenarios": [],
            "observed_scenarios": ["legacy_snapshot"],
            "missing_scenarios": [],
            "undeclared_scenarios": ["legacy_snapshot"],
            "perturbation_count": 0,
            "perturbations": [],
        },
        "split": split,
        "residual_series": {
            "status": "partial",
            "audit_pass": bool(direct.get("audit_pass")),
            "points": [point],
            "invalid_intervals": [],
            "missing_intervals": [],
            "aggregate": {
                "point_count": 1,
                "evaluated_point_count": 1,
                "source_observed_file": plan.observed_file,
                "scope_boundary": "single scalar snapshot only",
            },
        },
        "envelopes": {
            "status": "partial",
            "checked_point_count": 1,
            "violations": [],
            "violation_intervals": [],
            "aggregate": {
                "envelope_count": len(plan.physical_envelopes),
                "series_envelope_evidence": False,
            },
        },
        "adequacy": {
            "artifact_kind": "physicsguard_validation_adequacy_receipt",
            "receipt_version": "1.0",
            "status": "not_applicable",
            "sampling_mode": None,
            "threshold_source": None,
            "universe": {
                "available_point_count": 0,
                "eligible_point_count": 0,
                "selected_point_count": 1,
                "unique_selected_row_count": 0,
                "evaluated_point_count": 1,
                "validated_point_count": 1 if direct.get("audit_pass") else 0,
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
                "selection_floor": {
                    "algorithm_id": "sqrt_n_stage_v1",
                    "available_count": 0,
                    "universal_minimum_count": 0,
                    "universal_minimum_ratio": 0.0,
                    "plan_minimum_count": 0,
                    "plan_minimum_ratio": 0.0,
                    "project_minimum_count": None,
                    "project_minimum_ratio": None,
                    "convergence_minimum_count": None,
                    "convergence_minimum_ratio": None,
                    "full_sequence_required": False,
                    "effective_minimum_count": 0,
                    "effective_minimum_ratio": 0.0,
                },
            },
            "temporal": {
                "status": "not_applicable",
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
            },
            "per_signal": [],
            "signal_time_matrix": [],
            "families": [],
            "subsystem_families": [],
            "missing_critical_signals": [],
            "missing_critical_parameters": [],
            "repeated_exclusion_reasons": {},
            "templated_exclusion_reasons": [],
            "finding_codes": ["validation_depth_not_declared"],
            "claim_boundary": "scalar snapshot only; quantitative adequacy not applicable",
        },
        "predictive": evaluate_predictive_rollout("pointwise", None, base_dir=base_dir).receipt,
        "assumptions": ["scalar snapshot input; no validation-depth plan was declared"],
        "findings": findings,
        "safe_claim": "one low-fidelity scalar snapshot was evaluated; no time-series or scenario claim is supported",
        "unsafe_claim_boundary": UNSAFE_BOUNDARY,
    }
    # Split overlap is a real calibration defect even for a scalar snapshot and
    # is therefore promoted. The generic depth-not-declared warning remains
    # receipt-local for the explicit scalar-snapshot route.
    promoted = [item for item in split_findings if item["severity"] == "error"]
    return ValidationDepthEvaluation(payload, promoted, [], None)


def _dataset_identity_receipt(dataset, base_dir: Path, findings: list[dict[str, Any]]) -> dict[str, Any]:
    files = [_identity_receipt(item, base_dir) for item in dataset.files]
    field_schema = _identity_receipt(dataset.field_schema, base_dir)
    parameter_roles = _identity_receipt(dataset.parameter_roles, base_dir)
    testbench = _identity_receipt(dataset.testbench, base_dir)
    identities = [*files, field_schema, parameter_roles, testbench]
    for identity in identities:
        if identity["status"] != "current":
            _add_finding(
                findings,
                "error",
                "dataset_file_missing",
                "validation input file is missing",
                identity["identity_id"],
                {"identity": identity},
            )

    observed_version = None
    if testbench["status"] != "missing":
        try:
            contract = load_test_file_contract(_resolve_path(base_dir, dataset.testbench.path))
            observed_version = contract.metadata.get("testbench_version")
        except Exception as exc:
            _add_finding(
                findings,
                "error",
                "testbench_identity_unreadable",
                "testbench profile could not be read for version identity",
                dataset.testbench.path,
                {"error": str(exc)},
            )
    if observed_version != dataset.testbench_version:
        _add_finding(
            findings,
            "error",
            "testbench_version_mismatch",
            "testbench version differs from the validation-depth declaration",
            dataset.testbench.identity_id,
            {"expected": dataset.testbench_version, "observed": observed_version},
        )

    if any(item["status"] == "missing" for item in identities):
        status = "missing"
    elif any(item["status"] == "stale" for item in identities) or observed_version != dataset.testbench_version:
        status = "stale"
    else:
        status = "current"
    return {
        "dataset_id": dataset.dataset_id,
        "status": status,
        "files": files,
        "field_schema": field_schema,
        "parameter_roles": parameter_roles,
        "testbench": testbench,
        "expected_testbench_version": dataset.testbench_version,
        "observed_testbench_version": observed_version,
    }


def _mapping_review_receipt(
    plan: ModelValidationPlanSpec,
    base_dir: Path,
    findings: list[dict[str, Any]],
) -> dict[str, Any]:
    assert plan.depth is not None
    mapping = plan.depth.mapping_review
    load_findings: list[dict[str, Any]] = []
    edges, edge_files = load_contract_field_mappings(plan, base_dir, load_findings)
    findings.extend(load_findings)

    signal_receipts: list[dict[str, Any]] = []
    unresolved: list[str] = []
    for role in _required_mapping_roles(plan):
        candidates = [item for item in edges if item.target == role.target]
        if role.source_id:
            candidates = [item for item in candidates if item.source_id == role.source_id]
        candidate = max(candidates, key=lambda item: item.confidence or -1.0, default=None)
        if candidate is None:
            signal_receipts.append(
                {
                    "target": role.target,
                    "source_id": role.source_id,
                    "unit": None,
                    "confidence": None,
                    "mapping_status": "missing",
                    "issue_codes": ["mapping_missing"],
                }
            )
            unresolved.append(role.target)
            _add_finding(
                findings,
                "error",
                "mapping_required_signal_missing",
                "required validation signal has no mapping edge in the referenced contracts",
                role.target,
                {"source_id": role.source_id},
            )
            continue
        issues: list[str] = []
        if _metadata_is_stale(candidate.metadata):
            issues.append("mapping_stale")
        if not candidate.unit_evidence:
            issues.append("unit_evidence_missing")
        if candidate.confidence is None or candidate.confidence < mapping.minimum_confidence:
            issues.append("confidence_below_threshold")
        if candidate.review_required:
            issues.append("human_review_required")
        signal_receipts.append(
            {
                "target": role.target,
                "source_id": candidate.source_id,
                "unit": candidate.unit_evidence,
                "confidence": candidate.confidence,
                "mapping_status": "resolved" if not issues else "uncertain",
                "issue_codes": issues,
            }
        )
        if issues:
            unresolved.append(role.target)
            _add_finding(
                findings,
                "error",
                "mapping_required_signal_uncertain",
                "required signal mapping edge lacks unit evidence, enough confidence, or review",
                role.target,
                {
                    "edge_id": candidate.id,
                    "issue_codes": issues,
                    "minimum_confidence": mapping.minimum_confidence,
                },
            )

    status = "blocked" if unresolved or load_findings else "pass"
    return {
        "status": status,
        "mapping_edge_files": edge_files,
        "minimum_confidence": mapping.minimum_confidence,
        "signals": signal_receipts,
        "unresolved_targets": sorted(set(unresolved)),
    }


def _time_receipt(scope, series: ObservedSeriesSpec | None, findings: list[dict[str, Any]]) -> dict[str, Any]:
    points = list(series.points) if series is not None else []
    valid = [point for point in points if point.valid]
    timestamps = [point.timestamp for point in valid if point.timestamp is not None]
    scenarios = {point.scenario_id for point in valid}
    if len(valid) <= 1:
        observed_scope = "snapshot"
    elif len(scenarios) > 1:
        observed_scope = "scenario_set"
    else:
        observed_scope = "time_window"
    start = min(timestamps) if timestamps else None
    end = max(timestamps) if timestamps else None

    local_errors = 0
    if not valid:
        local_errors += 1
        _add_finding(findings, "error", "validation_series_empty", "no valid series points were available", None)
    if len(valid) == 1 and scope.claim_scope != "snapshot":
        local_errors += 1
        _add_finding(
            findings,
            "error",
            "snapshot_scope_overclaim",
            "one evaluated timestamp cannot support a time-window, scenario-set, or bounded-dataset claim",
            scope.claim_scope,
        )
    if scope.claim_scope == "scenario_set" and len(scenarios) < 2:
        local_errors += 1
        _add_finding(
            findings,
            "error",
            "scenario_set_scope_overclaim",
            "declared scenario-set scope requires at least two observed scenarios",
            scope.claim_scope,
        )
    if len(valid) > 1 and len(timestamps) != len(valid):
        local_errors += 1
        _add_finding(
            findings,
            "error",
            "time_series_timestamp_missing",
            "multi-point validation requires a timestamp for every valid point",
            None,
            {"valid_point_count": len(valid), "timestamp_count": len(timestamps)},
        )
    if scope.expected_point_count is not None and len(points) != scope.expected_point_count:
        local_errors += 1
        _add_finding(
            findings,
            "error",
            "time_scope_point_count_mismatch",
            "observed series point count differs from the declared scope",
            None,
            {"expected": scope.expected_point_count, "observed": len(points)},
        )
    if scope.start_time is not None and start != scope.start_time:
        local_errors += 1
        _add_finding(
            findings,
            "error",
            "time_scope_start_mismatch",
            "observed start time differs from the declared time boundary",
            None,
            {"expected": scope.start_time, "observed": start},
        )
    if scope.end_time is not None and end != scope.end_time:
        local_errors += 1
        _add_finding(
            findings,
            "error",
            "time_scope_end_mismatch",
            "observed end time differs from the declared time boundary",
            None,
            {"expected": scope.end_time, "observed": end},
        )
    if series is not None and series.time_unit != scope.time_unit:
        local_errors += 1
        _add_finding(
            findings,
            "error",
            "time_scope_unit_mismatch",
            "observed-series time unit differs from the declared time unit",
            None,
            {"expected": scope.time_unit, "observed": series.time_unit},
        )
    return {
        "status": "blocked" if local_errors else "pass",
        "declared_scope": scope.claim_scope,
        "observed_scope": observed_scope,
        "time_unit": scope.time_unit,
        "point_count": len(points),
        "valid_point_count": len(valid),
        "start_time": start,
        "end_time": end,
        "snapshot_only": len(valid) <= 1,
    }


def _scenario_receipt(depth, series: ObservedSeriesSpec | None, findings: list[dict[str, Any]]) -> dict[str, Any]:
    declared = [item.scenario_id for item in depth.scenarios]
    observed = sorted({item.scenario_id for item in (series.points if series is not None else []) if item.valid})
    missing = sorted(set(declared) - set(observed))
    undeclared = sorted(set(observed) - set(declared))
    errors = 0
    if missing:
        errors += 1
        _add_finding(
            findings,
            "error",
            "declared_scenarios_missing",
            "one or more declared scenarios have no valid observed points",
            None,
            {"missing_scenarios": missing},
        )
    if undeclared:
        errors += 1
        _add_finding(
            findings,
            "error",
            "observed_scenarios_undeclared",
            "observed series contains scenarios outside the declared validation boundary",
            None,
            {"undeclared_scenarios": undeclared},
        )
    perturbations: list[dict[str, Any]] = []
    for scenario in depth.scenarios:
        for perturbation in scenario.perturbations:
            perturbations.append(
                {"scenario_id": scenario.scenario_id, **perturbation.model_dump(mode="json")}
            )
        if scenario.baseline_scenario_id and not scenario.perturbations:
            errors += 1
            _add_finding(
                findings,
                "error",
                "scenario_perturbation_missing",
                "non-baseline scenario lacks a declared perturbation",
                scenario.scenario_id,
                {"baseline_scenario_id": scenario.baseline_scenario_id},
            )
        if scenario.case_ids:
            actual_cases = {
                point.case_id
                for point in (series.points if series is not None else [])
                if point.valid and point.scenario_id == scenario.scenario_id and point.case_id
            }
            missing_cases = sorted(set(scenario.case_ids) - actual_cases)
            if missing_cases:
                errors += 1
                _add_finding(
                    findings,
                    "error",
                    "scenario_cases_missing",
                    "declared scenario case identities are missing from the observed series",
                    scenario.scenario_id,
                    {"missing_case_ids": missing_cases},
                )
    return {
        "status": "blocked" if errors else "pass",
        "declared_scenarios": declared,
        "observed_scenarios": observed,
        "missing_scenarios": missing,
        "undeclared_scenarios": undeclared,
        "perturbation_count": len(perturbations),
        "perturbations": perturbations,
    }


def _split_receipt(
    plan: ModelValidationPlanSpec,
    base_dir: Path,
    split: CalibrationSplitPlanSpec | None,
    findings: list[dict[str, Any]],
    *,
    legacy: bool = False,
) -> dict[str, Any]:
    if not plan.calibration.enabled:
        return {
            "status": "not_applicable",
            "training": [],
            "holdout": [],
            "overlapping_paths": [],
            "overlapping_contents": [],
            "overlapping_case_ids": [],
        }

    if split is None and not legacy:
        _add_finding(
            findings,
            "error",
            "calibration_split_not_declared",
            "depth validation with calibration requires explicit training and holdout identities",
            plan.validation_id,
        )
        return {
            "status": "not_declared",
            "training": [],
            "holdout": [],
            "overlapping_paths": [],
            "overlapping_contents": [],
            "overlapping_case_ids": [],
        }

    if split is None:
        train_refs = _inferred_split_refs(plan.calibration.train_observed, "legacy_training", base_dir)
        holdout_refs = _inferred_split_refs(plan.calibration.holdout_observed, "legacy_holdout", base_dir)
    else:
        train_refs = split.training
        holdout_refs = split.holdout

    training = [_identity_receipt(item, base_dir) for item in train_refs]
    holdout = [_identity_receipt(item, base_dir) for item in holdout_refs]
    stale = [item for item in [*training, *holdout] if item["status"] != "current"]
    for item in stale:
        _add_finding(
            findings,
            "error",
            "calibration_split_file_missing",
            "training or holdout file is missing",
            item["identity_id"],
            {"identity": item},
        )

    train_paths = {_normalized_resolved_path(base_dir, item["path"]) for item in training}
    holdout_paths = {_normalized_resolved_path(base_dir, item["path"]) for item in holdout}
    train_cases = {case_id for item in training for case_id in item["case_ids"]}
    holdout_cases = {case_id for item in holdout for case_id in item["case_ids"]}
    overlap_paths = sorted(train_paths & holdout_paths)
    overlap_contents = sorted(
        f"{train['identity_id']}={held['identity_id']}"
        for train in training
        for held in holdout
        if _same_content(
            _resolve_path(base_dir, train["path"]),
            _resolve_path(base_dir, held["path"]),
        )
    )
    overlap_cases = sorted(train_cases & holdout_cases)

    if split is not None:
        active_train = _normalized_optional_path(base_dir, plan.calibration.train_observed)
        active_holdout = _normalized_optional_path(base_dir, plan.calibration.holdout_observed)
        missing_active = []
        if active_train and active_train not in train_paths:
            missing_active.append(active_train)
        if active_holdout and active_holdout not in holdout_paths:
            missing_active.append(active_holdout)
        if missing_active:
            _add_finding(
                findings,
                "error",
                "calibration_split_missing_active_evidence",
                "declared split does not include the files actually used for calibration/holdout",
                plan.validation_id,
                {"missing_active_paths": missing_active},
            )

    if overlap_paths or overlap_contents or overlap_cases:
        _add_finding(
            findings,
            "error",
            "calibration_holdout_identity_overlap",
            "training and holdout evidence overlap by path, file content, or case id",
            plan.validation_id,
            {
                "overlapping_paths": overlap_paths,
                "overlapping_contents": overlap_contents,
                "overlapping_case_ids": overlap_cases,
            },
        )
    blocked = bool(stale or overlap_paths or overlap_contents or overlap_cases)
    return {
        "status": "blocked" if blocked else "pass",
        "training": training,
        "holdout": holdout,
        "overlapping_paths": overlap_paths,
        "overlapping_contents": overlap_contents,
        "overlapping_case_ids": overlap_cases,
    }


def _residual_series_receipt(
    audit_spec: HierarchicalAuditSpec,
    series: ObservedSeriesSpec | None,
    findings: list[dict[str, Any]],
    *,
    parameter_policies: Iterable[ParameterTemporalPolicySpec] = (),
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    points = list(series.points) if series is not None else []
    time_varying_policies = {
        policy.parameter_id: policy
        for policy in parameter_policies
        if policy.temporal_behavior == "time_varying"
    }
    model_parameters = _model_parameter_values(audit_spec)
    contribution_effects: dict[str, list[dict[str, Any]]] = {
        parameter_id: [] for parameter_id in time_varying_policies
    }
    required_variables = {
        variable
        for block in audit_spec.hierarchy.blocks
        for variable in block.required_variables
    }
    receipts: list[dict[str, Any]] = []
    invalid_points: list[tuple[ObservedSeriesPointSpec, str]] = []
    missing_points: list[tuple[ObservedSeriesPointSpec, str]] = []
    max_values: list[float] = []
    norms: list[float] = []
    warnings: list[str] = []

    for point in points:
        if not point.valid:
            invalid_points.append((point, point.invalid_reason or "invalid point"))
            receipts.append(_unevaluated_point_receipt(point, "invalid", point.invalid_reason or "invalid point"))
            _add_finding(
                findings,
                "error",
                "residual_series_invalid_point",
                "declared series contains an invalid interval",
                point.point_id,
                {"reason": point.invalid_reason, "timestamp": point.timestamp},
            )
            continue
        observed = ObservedValuesSpec(
            observation_name=point.point_id,
            variables={
                name: value
                for name, value in point.variables.items()
                if name not in time_varying_policies
            },
            metadata={"scenario_id": point.scenario_id, "case_id": point.case_id},
        )
        applied_parameter_values = {
            parameter_id: float(point.variables[parameter_id].value)
            for parameter_id in time_varying_policies
            if parameter_id in point.variables and parameter_id in model_parameters
        }
        try:
            active_spec = _audit_with_parameter_overrides(
                audit_spec,
                applied_parameter_values,
            )
            report = HierarchicalAuditRunner(active_spec).evaluate_observed(
                observed,
                top_n_residuals=1_000_000,
                skip_unobserved=True,
            )
            missing = sorted(required_variables - (set(observed.variables) | set(report.derived_variables)))
            if not missing and report.metadata["unobserved_variables"]:
                raise ValueError("observed values missing required registered variables: "
                                 + ", ".join(report.metadata["unobserved_variables"]))
        except Exception as exc:
            invalid_points.append((point, str(exc)))
            receipts.append(_unevaluated_point_receipt(point, "invalid", str(exc)))
            _add_finding(
                findings,
                "error",
                "residual_series_point_evaluation_failed",
                "series point could not be evaluated by the existing hierarchy relations",
                point.point_id,
                {"error": str(exc), "timestamp": point.timestamp},
            )
            continue
        if missing:
            missing_points.append((point, "missing required variables"))
            receipt = _unevaluated_point_receipt(point, "missing", "missing required variables")
            receipt["missing_variables"] = missing
            receipts.append(receipt)
            _add_finding(
                findings,
                "error",
                "residual_series_required_values_missing",
                "series point omits variables required by the hierarchy boundary",
                point.point_id,
                {"missing_variables": missing, "timestamp": point.timestamp},
            )
            continue
        status = "pass" if report.audit_pass else "fail"
        max_value = float(report.max_abs_normalized_residual)
        norm = float(report.residual_norm)
        max_values.append(max_value)
        norms.append(norm)
        point_warnings = list(report.warnings)
        warnings.extend(point_warnings)
        point_parameter_effects: list[dict[str, Any]] = []
        for parameter_id, observed_value in sorted(applied_parameter_values.items()):
            counterfactual_overrides = dict(applied_parameter_values)
            counterfactual_overrides[parameter_id] = model_parameters[parameter_id]
            try:
                counterfactual = HierarchicalAuditRunner(
                    _audit_with_parameter_overrides(
                        audit_spec,
                        counterfactual_overrides,
                    )
                ).evaluate_observed(observed, top_n_residuals=1_000_000)
                effect, affected = _residual_effect(report, counterfactual)
                effect_row = {
                    "parameter_id": parameter_id,
                    "point_id": point.point_id,
                    "observed_parameter_value": observed_value,
                    "counterfactual_parameter_value": model_parameters[parameter_id],
                    "maximum_normalized_residual_effect": effect,
                    "affected_residual_ids": affected,
                    "status": "evaluated",
                }
            except Exception as exc:
                effect_row = {
                    "parameter_id": parameter_id,
                    "point_id": point.point_id,
                    "observed_parameter_value": observed_value,
                    "counterfactual_parameter_value": model_parameters[parameter_id],
                    "maximum_normalized_residual_effect": None,
                    "affected_residual_ids": [],
                    "status": "blocked",
                    "error": str(exc),
                }
            point_parameter_effects.append(effect_row)
            contribution_effects[parameter_id].append(effect_row)
        receipts.append(
            {
                "point_id": point.point_id,
                "derived_variables": report.derived_variables,
                "checked_residuals": report.checked_residuals,
                "unchecked_residuals": report.unchecked_residuals,
                "timestamp": point.timestamp,
                "scenario_id": point.scenario_id,
                "case_id": point.case_id,
                "status": status,
                "audit_pass": bool(report.audit_pass),
                "max_abs_normalized_residual": max_value,
                "residual_norm": norm,
                "missing_variables": list(report.missing_required_variables),
                "warnings": point_warnings,
                "top_residuals": [item.to_dict() if hasattr(item, "to_dict") else item.__dict__ for item in report.top_residuals],
                "applied_parameter_values": applied_parameter_values,
                "parameter_contribution_effects": point_parameter_effects,
            }
        )
        if not report.audit_pass:
            _add_finding(
                findings,
                "warning",
                "residual_series_point_failed",
                "one bounded point failed the low-fidelity residual audit",
                point.point_id,
                {"timestamp": point.timestamp, "max_abs_normalized_residual": max_value},
            )

    evaluated = [item for item in receipts if item["status"] in {"pass", "fail"}]
    passing = [item for item in evaluated if item["audit_pass"]]
    failing = [item for item in evaluated if not item["audit_pass"]]
    has_blocker = bool(invalid_points or missing_points or not evaluated)
    status = "blocked" if has_blocker else "partial" if failing else "pass"
    audit_pass = bool(evaluated) and not has_blocker and not failing
    aggregate = {
        "point_count": len(points),
        "evaluated_point_count": len(evaluated),
        "passing_point_count": len(passing),
        "failing_point_count": len(failing),
        "invalid_point_count": len(invalid_points),
        "missing_point_count": len(missing_points),
        "max_abs_normalized_residual": max(max_values) if max_values else None,
        "mean_abs_normalized_residual": statistics.fmean(max_values) if max_values else None,
        "p95_abs_normalized_residual": _percentile(max_values, 0.95),
        "mean_residual_norm": statistics.fmean(norms) if norms else None,
    }
    parameter_contributions = _parameter_contribution_receipts(
        time_varying_policies,
        model_parameters,
        points,
        contribution_effects,
    )
    receipt = {
        "status": status,
        "audit_pass": audit_pass,
        "points": receipts,
        "invalid_intervals": _intervals(invalid_points),
        "missing_intervals": _intervals(missing_points),
        "aggregate": aggregate,
        "parameter_contributions": parameter_contributions,
    }
    series_direct = {
        "audit_pass": audit_pass,
        "max_abs_normalized_residual": aggregate["max_abs_normalized_residual"],
        "residual_norm": math.sqrt(sum(value * value for value in norms)) if norms else None,
        "top_residuals": _worst_top_residuals(receipts),
        "top_blocks": [],
        "warnings": sorted(set(warnings)),
        "scope": "pointwise_observed_series",
        "point_count": len(points),
        "invalid_intervals": receipt["invalid_intervals"],
        "missing_intervals": receipt["missing_intervals"],
    }
    return receipt, series_direct


def _envelope_receipt(
    plan: ModelValidationPlanSpec,
    series: ObservedSeriesSpec | None,
    findings: list[dict[str, Any]],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    points = [item for item in (series.points if series is not None else []) if item.valid]
    violations: list[dict[str, Any]] = []
    outer_findings: list[dict[str, Any]] = []
    for point in points:
        for envelope in plan.physical_envelopes:
            if envelope.target not in point.variables:
                continue
            value = point.variables[envelope.target].value
            outside = (envelope.lower is not None and value < envelope.lower) or (
                envelope.upper is not None and value > envelope.upper
            )
            if not outside:
                continue
            violation = {
                "point_id": point.point_id,
                "timestamp": point.timestamp,
                "scenario_id": point.scenario_id,
                "target": envelope.target,
                "value": value,
                "lower": envelope.lower,
                "upper": envelope.upper,
                "unit": envelope.unit,
                "severity": envelope.severity,
            }
            violations.append(violation)
            finding_type = "physical_envelope_interval_violation"
            _add_finding(
                findings,
                envelope.severity,
                finding_type,
                "pointwise observed value is outside the declared physical envelope",
                envelope.target,
                violation,
            )
            outer_findings.append(
                {
                    "severity": envelope.severity,
                    "type": finding_type,
                    "message": "pointwise observed value is outside the declared physical envelope",
                    "target": envelope.target,
                    "details": violation,
                }
            )
    if any(item["severity"] == "error" for item in violations):
        status = "blocked"
    elif violations:
        status = "partial"
    else:
        status = "pass"
    return (
        {
            "status": status,
            "checked_point_count": len(points),
            "violations": violations,
            "violation_intervals": _violation_intervals(violations),
            "aggregate": {
                "envelope_count": len(plan.physical_envelopes),
                "violation_count": len(violations),
                "hard_violation_count": sum(item["severity"] == "error" for item in violations),
                "warning_violation_count": sum(item["severity"] == "warning" for item in violations),
            },
        },
        outer_findings,
    )


def _load_series(
    reference: ValidationIdentityReferenceSpec,
    base_dir: Path,
    findings: list[dict[str, Any]],
) -> ObservedSeriesSpec | None:
    try:
        return load_observed_series(_resolve_path(base_dir, reference.path))
    except Exception as exc:
        _add_finding(
            findings,
            "error",
            "observed_series_unreadable",
            "bounded observed series could not be loaded",
            reference.path,
            {"error": str(exc)},
        )
        return None


def _model_parameter_values(audit_spec: HierarchicalAuditSpec) -> dict[str, float]:
    values: dict[str, float] = {}
    for component in audit_spec.system.components:
        for name, value in component.parameters.items():
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                continue
            numeric = float(value)
            if math.isfinite(numeric):
                values[f"{component.id}.{name}"] = numeric
    return values


def _audit_with_parameter_overrides(
    audit_spec: HierarchicalAuditSpec,
    overrides: dict[str, float],
) -> HierarchicalAuditSpec:
    by_component: dict[str, dict[str, float]] = {}
    for target, value in overrides.items():
        component_id, separator, parameter_name = target.partition(".")
        if not separator or not component_id or not parameter_name:
            raise ValueError(f"parameter target must use component.parameter: {target}")
        by_component.setdefault(component_id, {})[parameter_name] = float(value)
    components = []
    for component in audit_spec.system.components:
        updates = by_component.get(component.id, {})
        if not updates:
            components.append(component)
            continue
        unknown = sorted(set(updates) - set(component.parameters))
        if unknown:
            raise ValueError(
                f"component {component.id!r} has no parameters: {', '.join(unknown)}"
            )
        components.append(
            component.model_copy(
                update={"parameters": {**component.parameters, **updates}}
            )
        )
    missing_components = sorted(set(by_component) - {item.id for item in components})
    if missing_components:
        raise ValueError(
            "parameter override references unknown components: "
            + ", ".join(missing_components)
        )
    return audit_spec.model_copy(
        update={
            "system": audit_spec.system.model_copy(update={"components": components})
        }
    )


def _residual_effect(left, right) -> tuple[float, list[str]]:
    left_values = {item.name: float(item.normalized_value) for item in left.top_residuals}
    right_values = {item.name: float(item.normalized_value) for item in right.top_residuals}
    deltas = {
        name: abs(left_values.get(name, 0.0) - right_values.get(name, 0.0))
        for name in set(left_values) | set(right_values)
    }
    affected = sorted(name for name, value in deltas.items() if value > 1.0e-12)
    return max(deltas.values(), default=0.0), affected


def _parameter_contribution_receipts(
    policies: dict[str, ParameterTemporalPolicySpec],
    model_parameters: dict[str, float],
    points: list[ObservedSeriesPointSpec],
    effects: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    receipts: list[dict[str, Any]] = []
    for parameter_id, policy in sorted(policies.items()):
        observed_points = [
            point for point in points if point.valid and parameter_id in point.variables
        ]
        rows = list(effects.get(parameter_id, []))
        evaluated_rows = [row for row in rows if row.get("status") == "evaluated"]
        effect_values = [
            float(row["maximum_normalized_residual_effect"])
            for row in evaluated_rows
            if row.get("maximum_normalized_residual_effect") is not None
        ]
        maximum_effect = max(effect_values) if effect_values else None
        distinct_values = {
            float(point.variables[parameter_id].value) for point in observed_points
        }
        affected = sorted(
            {
                str(residual_id)
                for row in evaluated_rows
                for residual_id in row.get("affected_residual_ids", [])
            }
        )
        common_ready = (
            parameter_id in model_parameters
            and len(evaluated_rows) == len(observed_points)
            and bool(evaluated_rows)
            and len(distinct_values) >= 2
            and maximum_effect is not None
        )
        if policy.contribution_expectation == "sensitive":
            passed = (
                common_ready
                and maximum_effect
                >= float(policy.minimum_normalized_contribution_effect or math.inf)
                and bool(affected)
            )
            status = "pass" if passed else "blocked"
        else:
            passed = (
                common_ready
                and maximum_effect
                <= float(policy.maximum_non_sensitive_contribution_effect or 0.0)
            )
            status = "verified_non_sensitive" if passed else "blocked"
        receipts.append(
            {
                "parameter_id": parameter_id,
                "expectation": policy.contribution_expectation,
                "model_parameter_exists": parameter_id in model_parameters,
                "observed_point_ids": sorted(point.point_id for point in observed_points),
                "applied_point_ids": sorted(str(row["point_id"]) for row in rows),
                "counterfactual_point_ids": sorted(
                    str(row["point_id"]) for row in evaluated_rows
                ),
                "distinct_observed_value_count": len(distinct_values),
                "maximum_normalized_residual_effect": maximum_effect,
                "affected_residual_ids": affected,
                "status": status,
                "non_sensitive_reason": policy.non_sensitive_reason,
                "non_sensitive_claim_boundary": policy.non_sensitive_claim_boundary,
            }
        )
    return receipts


def _identity_receipt(reference: ValidationIdentityReferenceSpec, base_dir: Path) -> dict[str, Any]:
    path = _resolve_path(base_dir, reference.path)
    return {
        "identity_id": reference.identity_id,
        "path": reference.path,
        "status": "current" if path.is_file() else "missing",
        "case_ids": list(reference.case_ids),
    }


def _inferred_split_refs(
    path_value: str | None,
    identity_id: str,
    base_dir: Path,
) -> list[ValidationIdentityReferenceSpec]:
    if not path_value:
        return []
    return [
        ValidationIdentityReferenceSpec(
            identity_id=identity_id,
            path=path_value,
            case_ids=[],
        )
    ]


def _required_mapping_roles(plan: ModelValidationPlanSpec):
    required_roles = {
        "model_input",
        "validation_output",
        "diagnostic_check",
        "redundant_measurement",
        "fallback_measurement",
        "check_only",
    }
    return [role for role in plan.variable_roles if role.validation_role in required_roles]


def _depth_status(findings: list[dict[str, Any]]) -> str:
    if any(item["severity"] == "error" for item in findings):
        return "blocked"
    if any(item["severity"] == "warning" for item in findings):
        return "partial"
    return "pass"


def _safe_depth_claim(status: str, scope: str) -> str:
    scope_text = {
        "snapshot": "one declared scalar snapshot",
        "time_window": "the exact declared time window",
        "scenario_set": "the exact declared scenario set and perturbations",
        "bounded_dataset": "the exact bounded dataset, time points, and scenarios",
    }[scope]
    if status == "pass":
        return f"validation-depth evidence passed for {scope_text} inside the low-fidelity relation boundary"
    if status == "partial":
        return f"validation-depth evidence is partial for {scope_text}; review warnings before reuse"
    return f"validation-depth evidence is blocked for {scope_text}; no broad validation claim is supported"


def _add_finding(
    findings: list[dict[str, Any]],
    severity: str,
    finding_type: str,
    message: str,
    target: str | None,
    details: dict[str, Any] | None = None,
) -> None:
    findings.append(
        {
            "severity": severity,
            "type": finding_type,
            "message": message,
            "target": target,
            "details": details or {},
        }
    )


def _unevaluated_point_receipt(
    point: ObservedSeriesPointSpec,
    status: str,
    warning: str,
) -> dict[str, Any]:
    return {
        "point_id": point.point_id,
        "timestamp": point.timestamp,
        "scenario_id": point.scenario_id,
        "case_id": point.case_id,
        "status": status,
        "audit_pass": False,
        "max_abs_normalized_residual": None,
        "residual_norm": None,
        "missing_variables": [],
        "warnings": [warning],
        "top_residuals": [],
    }


def _intervals(values: Iterable[tuple[ObservedSeriesPointSpec, str]]) -> list[dict[str, Any]]:
    return [
        {
            "start_point_id": point.point_id,
            "end_point_id": point.point_id,
            "start_time": point.timestamp,
            "end_time": point.timestamp,
            "scenario_id": point.scenario_id,
            "reason": reason,
        }
        for point, reason in values
    ]


def _violation_intervals(violations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "target": item["target"],
            "scenario_id": item["scenario_id"],
            "start_point_id": item["point_id"],
            "end_point_id": item["point_id"],
            "start_time": item["timestamp"],
            "end_time": item["timestamp"],
            "severity": item["severity"],
        }
        for item in violations
    ]


def _worst_top_residuals(receipts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    evaluated = [
        item
        for item in receipts
        if item["max_abs_normalized_residual"] is not None and item["top_residuals"]
    ]
    if not evaluated:
        return []
    worst = max(evaluated, key=lambda item: item["max_abs_normalized_residual"])
    return [
        {"point_id": worst["point_id"], "scenario_id": worst["scenario_id"], **item}
        for item in worst["top_residuals"]
    ]


def _percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, math.ceil(fraction * len(ordered)) - 1))
    return ordered[index]


def _same_content(left: Path, right: Path) -> bool:
    return left.is_file() and right.is_file() and left.read_bytes() == right.read_bytes()


def _resolve_path(base: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else base / path


def _normalized_resolved_path(base: Path, value: str) -> str:
    return str(_resolve_path(base, value).resolve()).casefold()


def _normalized_optional_path(base: Path, value: str | None) -> str | None:
    return _normalized_resolved_path(base, value) if value else None


__all__ = [
    "ValidationDepthEvaluation",
    "evaluate_validation_depth",
    "summarize_validation_depth",
]
