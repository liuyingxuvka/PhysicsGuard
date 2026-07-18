"""Deterministic task-local hypothesis and candidate-revision evaluation."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any

from physicsguard.schema.task_local_revision import (
    CandidateModelRevisionSpec,
    DiagnosticObservationSpec,
    HypothesisExpectationSpec,
    HypothesisPlanSpec,
    TaskModelIdentitySpec,
)
from physicsguard.schema.predictive_rollout import PredictiveRolloutReceiptSpec


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
    model = _identity_receipt(plan.model, base_dir)
    status = "pass" if model["status"] == "current" else "blocked"
    content = plan.model_dump(mode="json")
    return {
        "artifact_kind": "physicsguard_task_hypothesis_plan_receipt",
        "receipt_version": "1.0",
        "status": status,
        "plan_id": plan.plan_id,
        "prediction_sequence": plan.prediction_sequence,
        "model_identity": model,
        "plan_fingerprint": _fingerprint(content),
        "ranked_observation_candidates": rank_observation_candidates(plan),
        "claim_boundary": (
            "This receipt freezes only the declared task model, hypotheses, expectations, "
            "probe candidates, weights, and sequence; it does not prove external clock order "
            "or that the hypotheses exhaust physical reality."
        ),
    }


def evaluate_hypothesis_observation(
    plan: HypothesisPlanSpec,
    observation: DiagnosticObservationSpec,
    *,
    base_dir: Path,
) -> dict[str, Any]:
    if observation.plan_id != plan.plan_id:
        raise ValueError("observation plan_id does not match the frozen hypothesis plan")
    if observation.observation_sequence <= plan.prediction_sequence:
        raise ValueError("observation_sequence must be strictly later than prediction_sequence")
    frozen = freeze_hypothesis_plan(plan, base_dir=base_dir)
    if frozen["status"] != "pass":
        raise ValueError("hypothesis plan model identity is not current")

    hypothesis_results: list[dict[str, Any]] = []
    mismatch_ids: list[str] = []
    for hypothesis in plan.hypotheses:
        matched: list[str] = []
        contradicted: list[str] = []
        missing: list[str] = []
        for expectation in hypothesis.expectations:
            result = _evaluate_expectation(expectation, observation)
            {"matched": matched, "contradicted": contradicted, "missing": missing}[result].append(
                expectation.expectation_id
            )
            if result == "contradicted":
                mismatch_ids.append(
                    f"{hypothesis.hypothesis_id}:{expectation.expectation_id}"
                )
        if contradicted:
            disposition = "weakened"
        elif missing:
            disposition = "undetermined"
        else:
            disposition = "supported"
        hypothesis_results.append(
            {
                "hypothesis_id": hypothesis.hypothesis_id,
                "disposition": disposition,
                "matched_expectation_ids": matched,
                "contradicted_expectation_ids": contradicted,
                "missing_expectation_ids": missing,
            }
        )

    observation_content = observation.model_dump(mode="json")
    return {
        "artifact_kind": "physicsguard_hypothesis_observation_receipt",
        "receipt_version": "1.0",
        "status": "pass",
        "plan_id": plan.plan_id,
        "observation_id": observation.observation_id,
        "prediction_sequence": plan.prediction_sequence,
        "observation_sequence": observation.observation_sequence,
        "plan_fingerprint": frozen["plan_fingerprint"],
        "observation_fingerprint": _fingerprint(observation_content),
        "hypothesis_results": hypothesis_results,
        "mismatch_ids": mismatch_ids,
        "next_observation_candidates": frozen["ranked_observation_candidates"],
        "claim_boundary": (
            "The comparison covers only the typed declared expectations and supplied observation; "
            "missing targets remain undetermined and no Guard source or threshold is modified."
        ),
    }


def _evaluate_expectation(
    expectation: HypothesisExpectationSpec,
    observation: DiagnosticObservationSpec,
) -> str:
    if expectation.kind == "signal":
        signal = observation.signals.get(expectation.target_id)
        if signal is None:
            return "missing"
        if expectation.operator in {"increase", "decrease", "stable"}:
            if signal.trend is None:
                return "missing"
            return "matched" if signal.trend == expectation.operator else "contradicted"
        if signal.value is None:
            return "missing"
        return _numeric_result(expectation, signal.value)
    if expectation.kind == "residual":
        value = observation.residuals.get(expectation.target_id)
        return "missing" if value is None else _numeric_result(expectation, value)

    left = observation.timings.get(expectation.target_id)
    right = observation.timings.get(expectation.compare_target_id or "")
    if left is None or right is None:
        return "missing"
    delta = left - right
    if expectation.operator == "before":
        matched = delta < -expectation.tolerance
    elif expectation.operator == "after":
        matched = delta > expectation.tolerance
    else:
        matched = abs(delta) <= expectation.tolerance
    return "matched" if matched else "contradicted"


def _numeric_result(expectation: HypothesisExpectationSpec, value: float) -> str:
    if expectation.operator == "between":
        matched = bool(expectation.lower <= value <= expectation.upper)  # type: ignore[operator]
    elif expectation.operator == "positive":
        matched = value > expectation.tolerance
    elif expectation.operator == "negative":
        matched = value < -expectation.tolerance
    else:
        raise ValueError(
            f"operator {expectation.operator!r} is not a numeric expectation operator"
        )
    return "matched" if matched else "contradicted"


def evaluate_candidate_model_revision(
    revision: CandidateModelRevisionSpec,
    *,
    base_dir: Path,
) -> dict[str, Any]:
    base = _identity_receipt(revision.base_model, base_dir)
    candidate = _identity_receipt(revision.candidate_model, base_dir)
    identity_findings: list[str] = []
    if base["status"] != "current":
        identity_findings.append("base_model_identity_stale")
    if candidate["status"] != "current":
        identity_findings.append("candidate_model_identity_stale")
    if (
        Path(base["resolved_path"]) == Path(candidate["resolved_path"])
        or base["actual_sha256"] == candidate["actual_sha256"]
    ):
        identity_findings.append("candidate_not_distinct_from_base")

    checks: list[dict[str, Any]] = []
    for check in revision.checks:
        effective_status = check.status
        native_receipt_fingerprint = None
        native_model_identity_status = None
        if check.kind == "predictive_rollout":
            native = PredictiveRolloutReceiptSpec.model_validate(
                check.native_receipt or {}
            ).model_dump(mode="json")
            native_model = native.get("model_identity")
            native_model_identity_status = (
                "current_candidate"
                if isinstance(native_model, dict)
                and native_model.get("identity_id") == revision.candidate_model.model_id
                and native_model.get("status") == "current"
                and native_model.get("expected_sha256")
                == revision.candidate_model.sha256
                and native_model.get("actual_sha256")
                == revision.candidate_model.sha256
                else "mismatch"
            )
            effective_status = (
                "pass"
                if native["status"] == "pass"
                and native_model_identity_status == "current_candidate"
                else "blocked"
            )
            native_receipt_fingerprint = _fingerprint(native)
        checks.append(
            {
                "check_id": check.check_id,
                "kind": check.kind,
                "declared_status": check.status,
                "effective_status": effective_status,
                "evidence_ref": check.evidence_ref,
                "native_receipt_fingerprint": native_receipt_fingerprint,
                "native_model_identity_status": native_model_identity_status,
            }
        )

    failed = [item["check_id"] for item in checks if item["effective_status"] != "pass"]
    rollback = None
    if identity_findings:
        disposition = "blocked"
    elif not failed:
        disposition = "accepted"
    elif not revision.candidate_applied:
        disposition = "rejected"
    else:
        assert revision.rollback_model is not None
        rollback = _identity_receipt(revision.rollback_model, base_dir)
        if (
            rollback["status"] == "current"
            and rollback["actual_sha256"] == base["actual_sha256"]
            and rollback["model_id"] == base["model_id"]
            and rollback["model_version"] == base["model_version"]
        ):
            disposition = "rolled_back"
        else:
            disposition = "blocked"
            identity_findings.append("rollback_identity_does_not_match_current_base")

    return {
        "artifact_kind": "physicsguard_task_model_revision_receipt",
        "receipt_version": "1.0",
        "status": "pass" if disposition in {"accepted", "rejected", "rolled_back"} else "blocked",
        "revision_id": revision.revision_id,
        "plan_id": revision.plan_id,
        "revision_kind": revision.revision_kind,
        "disposition": disposition,
        "base_model": base,
        "candidate_model": candidate,
        "rollback_model": rollback,
        "triggering_mismatch_ids": revision.triggering_mismatch_ids,
        "required_check_ids": revision.required_check_ids,
        "check_results": checks,
        "failed_check_ids": failed,
        "identity_findings": identity_findings,
        "base_model_preserved": base["status"] == "current",
        "revision_fingerprint": _fingerprint(revision.model_dump(mode="json")),
        "claim_boundary": (
            "This read-only decision applies only to the exact task-local base, candidate, "
            "mismatches, and declared checks. It never edits PhysicsGuard, its thresholds, "
            "the reusable model library, or an installed skill."
        ),
    }


__all__ = [
    "evaluate_candidate_model_revision",
    "evaluate_hypothesis_observation",
    "freeze_hypothesis_plan",
    "rank_observation_candidates",
]
