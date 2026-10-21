"""Deterministic strict task-local hypothesis and model-revision evaluation."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any, Iterable

from physicsguard.schema.task_local_revision import (
    DiagnosticObservationSpec,
    HypothesisExpectationSpec,
    HypothesisPlanSpec,
    NativeDepthGapSpec,
    NativeDepthReceiptSpec,
    TaskModelIdentitySpec,
)


def _fingerprint(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _resolve_path(base_dir: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else base_dir / path


def _identity_receipt(identity: TaskModelIdentitySpec, base_dir: Path) -> dict[str, Any]:
    path = _resolve_path(base_dir, identity.path)
    actual = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else ""
    return {
        **identity.model_dump(mode="json"),
        "resolved_path": str(path.resolve()) if path.exists() else str(path),
        "actual_sha256": actual,
        "status": "current" if actual == identity.sha256 else "stale",
    }


def _native_gap_rows(receipt: NativeDepthReceiptSpec) -> list[dict[str, Any]]:
    return [gap.model_dump(mode="json") for gap in receipt.gaps]


def _native_gap_map(receipt: NativeDepthReceiptSpec) -> dict[str, NativeDepthGapSpec]:
    return {gap.gap_id: gap for gap in receipt.gaps}


def _gap_next_actions(gaps: Iterable[NativeDepthGapSpec]) -> list[str]:
    return sorted({gap.next_action for gap in gaps})


def _external_input_ids(gaps: Iterable[NativeDepthGapSpec]) -> list[str]:
    return sorted(
        {
            gap.external_input_id
            for gap in gaps
            if gap.resolution_class == "external_input_required"
            and gap.external_input_id is not None
        }
    )


def rank_observation_candidates(plan: HypothesisPlanSpec) -> list[dict[str, Any]]:
    """Rank declared probes by residual relevance and hypothesis discrimination."""

    hypothesis_count = len(plan.hypotheses)
    rows: list[dict[str, Any]] = []
    for candidate in plan.observation_candidates:
        distinct = len(set(candidate.predicted_outcomes.values()))
        discrimination = (
            0.0
            if hypothesis_count <= 1
            else float(distinct - 1) / float(hypothesis_count - 1)
        )
        combined = (
            plan.selection_weights.residual_relevance * candidate.residual_relevance
            + plan.selection_weights.hypothesis_discrimination * discrimination
        )
        rows.append(
            {
                **candidate.model_dump(mode="json"),
                "hypothesis_discrimination": discrimination,
                "combined_score": combined,
            }
        )
    return sorted(rows, key=lambda item: (-item["combined_score"], item["candidate_id"]))


def freeze_hypothesis_plan(
    plan: HypothesisPlanSpec,
    *,
    base_dir: Path,
) -> dict[str, Any]:
    """Freeze the strict plan and its six-family native-depth authority."""

    model = _identity_receipt(plan.model, base_dir)
    plan_content = plan.model_dump(mode="json")
    plan_fingerprint = _fingerprint(plan_content)
    native_gaps = _native_gap_rows(plan.native_depth_receipt)
    status = "pass" if model["status"] == "current" else "blocked"
    next_actions = _gap_next_actions(plan.native_depth_receipt.gaps)
    if not native_gaps:
        next_actions.append("evaluate_regression_holdout_and_predictive_receipts")
    payload = {
        "artifact_kind": "physicsguard_task_hypothesis_plan_receipt",
        "receipt_version": "2.0",
        "status": status,
        "plan_id": plan.plan_id,
        "task_id": plan.task_id,
        "purpose": plan.purpose,
        "coverage": plan.coverage.model_dump(mode="json"),
        "blueprint": plan.blueprint.model_dump(mode="json"),
        "assumptions": list(plan.assumptions),
        "unknowns": list(plan.unknowns),
        "iteration": plan.iteration,
        "max_iterations": plan.max_iterations,
        "predecessor": (
            None if plan.predecessor is None else plan.predecessor.model_dump(mode="json")
        ),
        "model": model,
        "native_depth_receipt_fingerprint": plan.native_depth_receipt.receipt_fingerprint,
        "native_source_receipt_ids": dict(plan.native_depth_receipt.source_receipt_ids),
        "native_gaps": native_gaps,
        "open_gap_ids": [gap["gap_id"] for gap in native_gaps],
        "required_next_actions": sorted(set(next_actions)),
        "ranked_observation_candidates": rank_observation_candidates(plan),
        "plan_fingerprint": plan_fingerprint,
        "next_iteration_required": bool(native_gaps),
        "terminal_reason": "continue_iteration",
        "claim_boundary": (
            "This receipt freezes only the exact task purpose, independently owned coverage "
            "universe, base model, hypotheses, and current six-family native-depth receipt. "
            "It does not identify a true physical cause or close the task model."
        ),
    }
    payload["receipt_fingerprint"] = _fingerprint(payload)
    return payload


def evaluate_hypothesis_observation(
    plan: HypothesisPlanSpec,
    observation: DiagnosticObservationSpec,
    *,
    base_dir: Path,
) -> dict[str, Any]:
    """Compare one immutable post-prediction observation with the frozen plan."""

    if observation.task_id != plan.task_id or observation.plan_id != plan.plan_id:
        raise ValueError("observation task/plan identity does not match the frozen plan")
    if observation.observation_sequence <= plan.prediction_sequence:
        raise ValueError("observation sequence must be strictly later than prediction sequence")
    frozen = freeze_hypothesis_plan(plan, base_dir=base_dir)
    if frozen["status"] != "pass":
        raise ValueError("hypothesis plan model identity is not current")
    if observation.frozen_plan_fingerprint != frozen["plan_fingerprint"]:
        raise ValueError("observation frozen-plan fingerprint is stale or foreign")
    if observation.blueprint_fingerprint != plan.blueprint.blueprint_fingerprint:
        raise ValueError("observation blueprint fingerprint is stale or foreign")
    if observation.affected_slice_fingerprint != plan.blueprint.affected_slice_fingerprint:
        raise ValueError("observation affected blueprint slice is stale or foreign")
    candidate_ids = {item.candidate_id for item in plan.observation_candidates}
    if observation.selected_candidate_id not in candidate_ids:
        raise ValueError("observation does not identify a declared observation candidate")

    hypothesis_results: list[dict[str, Any]] = []
    mismatches: list[str] = []
    missing: list[str] = []
    for hypothesis in plan.hypotheses:
        contradicted: list[str] = []
        undetermined: list[str] = []
        for expectation in hypothesis.expectations:
            result = _evaluate_expectation(expectation, observation)
            if result == "contradicted":
                contradicted.append(expectation.expectation_id)
                mismatches.append(f"{hypothesis.hypothesis_id}:{expectation.expectation_id}")
            elif result == "undetermined":
                undetermined.append(expectation.expectation_id)
                missing.append(f"{hypothesis.hypothesis_id}:{expectation.expectation_id}")
        disposition = (
            "weakened"
            if contradicted
            else "undetermined"
            if undetermined
            else "supported"
        )
        hypothesis_results.append(
            {
                "hypothesis_id": hypothesis.hypothesis_id,
                "disposition": disposition,
                "contradicted_expectation_ids": contradicted,
                "undetermined_expectation_ids": undetermined,
            }
        )

    all_hypotheses_contradicted = bool(hypothesis_results) and all(
        row["disposition"] == "weakened" for row in hypothesis_results
    )
    native_gap_map = _native_gap_map(plan.native_depth_receipt)
    open_gap_ids = set(native_gap_map)
    for mismatch_id in missing:
        open_gap_ids.add(f"observation_missing:{mismatch_id}")
    if all_hypotheses_contradicted:
        open_gap_ids.add("model_miss:observation_outside_hypothesis_space")

    next_actions = _gap_next_actions(native_gap_map.values())
    next_actions.extend(f"acquire_observation:{gap_id}" for gap_id in sorted(missing))
    if all_hypotheses_contradicted:
        next_actions.append("revise_hypothesis_universe_from_unexpected_observation")
        next_actions.append("revise_blueprint_or_native_bindings_from_model_miss")
        next_actions.append("rebind_native_depth_to_new_blueprint_revision")
        terminal_reason = "model_miss"
    else:
        native_external = _external_input_ids(native_gap_map.values())
        exact_external = sorted(set(native_external) | set(observation.external_input_ids))
        if exact_external:
            terminal_reason = "external_input_required"
        else:
            terminal_reason = "continue_iteration"
        next_actions.append("build_or_revalidate_candidate_model_revision")

    exact_external = sorted(
        set(_external_input_ids(native_gap_map.values()))
        | set(observation.external_input_ids)
    )
    payload = {
        "artifact_kind": "physicsguard_hypothesis_observation_receipt",
        "receipt_version": "2.0",
        "status": "blocked" if terminal_reason != "continue_iteration" else "pass",
        "task_id": plan.task_id,
        "plan_id": plan.plan_id,
        "plan_fingerprint": frozen["plan_fingerprint"],
        "observation_id": observation.observation_id,
        "selected_candidate_id": observation.selected_candidate_id,
        "observation_evidence": observation.evidence.model_dump(mode="json"),
        "blueprint": plan.blueprint.model_dump(mode="json"),
        "observation_fingerprint": _fingerprint(observation.model_dump(mode="json")),
        "prediction_sequence": plan.prediction_sequence,
        "observation_sequence": observation.observation_sequence,
        "hypothesis_results": hypothesis_results,
        "mismatch_ids": sorted(mismatches),
        "missing_expectation_ids": sorted(missing),
        "all_hypotheses_contradicted": all_hypotheses_contradicted,
        "model_miss_gap_id": (
            "model_miss:observation_outside_hypothesis_space"
            if all_hypotheses_contradicted
            else None
        ),
        "blueprint_revision_required": all_hypotheses_contradicted,
        "invalidated_broad_claim_blueprint_fingerprints": (
            [plan.blueprint.blueprint_fingerprint]
            if all_hypotheses_contradicted
            else []
        ),
        "model_miss_evidence_kind": (
            observation.evidence.evidence_kind
            if all_hypotheses_contradicted
            else None
        ),
        "native_depth_receipt_fingerprint": plan.native_depth_receipt.receipt_fingerprint,
        "open_gap_ids": sorted(open_gap_ids),
        "required_next_actions": sorted(set(next_actions)),
        "external_input_ids": exact_external,
        "terminal_reason": terminal_reason,
        "next_iteration_required": terminal_reason == "continue_iteration",
        "physical_cause_licensed": False,
        "claim_boundary": (
            "Observation comparison is task-local to the frozen hypotheses, selected probe, "
            "exact evidence identity, and current native depth receipt. A zero-survivor result "
            "is a model miss, not proof of a physical cause."
        ),
    }
    payload["receipt_fingerprint"] = _fingerprint(payload)
    return payload


def _evaluate_expectation(
    expectation: HypothesisExpectationSpec,
    observation: DiagnosticObservationSpec,
) -> str:
    if expectation.kind == "signal":
        observed = observation.signals.get(expectation.target_id)
        if observed is None:
            return "undetermined"
        if expectation.operator in {"increase", "decrease", "stable"}:
            if observed.trend is None:
                return "undetermined"
            return "supported" if observed.trend == expectation.operator else "contradicted"
        if observed.value is None:
            return "undetermined"
        return _numeric_result(expectation, observed.value)
    if expectation.kind == "residual":
        value = observation.residuals.get(expectation.target_id)
        return "undetermined" if value is None else _numeric_result(expectation, value)
    left = observation.timings.get(expectation.target_id)
    right = observation.timings.get(expectation.compare_target_id or "")
    if left is None or right is None:
        return "undetermined"
    delta = left - right
    if expectation.operator == "before":
        return "supported" if delta < -expectation.tolerance else "contradicted"
    if expectation.operator == "after":
        return "supported" if delta > expectation.tolerance else "contradicted"
    return "supported" if abs(delta) <= expectation.tolerance else "contradicted"


def _numeric_result(expectation: HypothesisExpectationSpec, value: float) -> str:
    if expectation.operator == "between":
        assert expectation.lower is not None and expectation.upper is not None
        return (
            "supported"
            if expectation.lower - expectation.tolerance
            <= value
            <= expectation.upper + expectation.tolerance
            else "contradicted"
        )
    if expectation.operator == "positive":
        return "supported" if value > expectation.tolerance else "contradicted"
    if expectation.operator == "negative":
        return "supported" if value < -expectation.tolerance else "contradicted"
    return "undetermined"


__all__ = [
    "evaluate_hypothesis_observation",
    "freeze_hypothesis_plan",
    "rank_observation_candidates",
]
