"""Task-local competing hypotheses: rank the next observation and compare it with frozen predictions."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from physicsguard.schema.task_local_revision import (
    DiagnosticObservationSpec,
    HypothesisExpectationSpec,
    HypothesisPlanSpec,
    TaskModelIdentitySpec,
)


def _resolve_path(base_dir: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else base_dir / path


def _model_status(identity: TaskModelIdentitySpec, base_dir: Path) -> dict[str, Any]:
    path = _resolve_path(base_dir, identity.path)
    return {
        **identity.model_dump(mode="json"),
        "resolved_path": str(path),
        "status": "found" if path.is_file() else "missing",
    }


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
    """Freeze the competing hypotheses and rank the next observation."""

    model = _model_status(plan.model, base_dir)
    status = "pass" if model["status"] == "found" else "blocked"
    next_actions = ["acquire_top_ranked_observation"]
    if status != "pass":
        next_actions = ["point model.path at the hierarchy YAML the hypotheses are about"]
    return {
        "artifact_kind": "physicsguard_task_hypothesis_plan",
        "status": status,
        "plan_id": plan.plan_id,
        "task_id": plan.task_id,
        "purpose": plan.purpose,
        "model": model,
        "assumptions": list(plan.assumptions),
        "unknowns": list(plan.unknowns),
        "iteration": plan.iteration,
        "max_iterations": plan.max_iterations,
        "hypothesis_ids": [item.hypothesis_id for item in plan.hypotheses],
        "ranked_observation_candidates": rank_observation_candidates(plan),
        "required_next_actions": next_actions,
        "claim_boundary": (
            "The plan freezes task-local hypotheses and predictions before the next "
            "observation. It does not identify the true physical cause."
        ),
    }


def evaluate_hypothesis_observation(
    plan: HypothesisPlanSpec,
    observation: DiagnosticObservationSpec,
    *,
    base_dir: Path,
) -> dict[str, Any]:
    """Compare one post-prediction observation with the frozen hypotheses."""

    if observation.task_id != plan.task_id or observation.plan_id != plan.plan_id:
        raise ValueError("observation task/plan identity does not match the plan")
    if observation.observation_sequence <= plan.prediction_sequence:
        raise ValueError("observation sequence must be strictly later than prediction sequence")
    frozen = freeze_hypothesis_plan(plan, base_dir=base_dir)
    if frozen["status"] != "pass":
        raise ValueError("hypothesis plan model file is missing")
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
    open_gap_ids = {f"observation_missing:{item}" for item in missing}
    next_actions = [f"acquire_observation:{item}" for item in sorted(missing)]
    if all_hypotheses_contradicted:
        open_gap_ids.add("model_miss:observation_outside_hypothesis_space")
        next_actions.append("revise_hypothesis_universe_from_unexpected_observation")
        terminal_reason = "model_miss"
    elif observation.external_input_ids:
        terminal_reason = "external_input_required"
    else:
        terminal_reason = "continue_iteration"
        next_actions.append("refine_the_supported_hypothesis_block")
    return {
        "artifact_kind": "physicsguard_hypothesis_observation",
        "status": "blocked" if terminal_reason != "continue_iteration" else "pass",
        "task_id": plan.task_id,
        "plan_id": plan.plan_id,
        "observation_id": observation.observation_id,
        "selected_candidate_id": observation.selected_candidate_id,
        "observation_evidence": observation.evidence.model_dump(mode="json"),
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
        "model_miss_evidence_kind": (
            observation.evidence.evidence_kind if all_hypotheses_contradicted else None
        ),
        "open_gap_ids": sorted(open_gap_ids),
        "required_next_actions": sorted(set(next_actions)),
        "external_input_ids": list(observation.external_input_ids),
        "terminal_reason": terminal_reason,
        "physical_cause_licensed": False,
        "claim_boundary": (
            "The comparison is task-local to the frozen hypotheses and the selected "
            "observation. A zero-survivor result is a model miss, not proof of a physical cause."
        ),
    }


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
