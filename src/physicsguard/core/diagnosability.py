"""Interval residual status and task-local fault diagnosability."""

from __future__ import annotations

import hashlib
import json
from itertools import combinations
from typing import Any

from physicsguard.schema.diagnosability import (
    DiagnosabilityRequestSpec,
    IntervalResidualSpec,
    IntervalValueSpec,
)


def _fingerprint(value: Any) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _overlaps(left: IntervalValueSpec, right: IntervalValueSpec) -> bool:
    return left.lower <= right.upper and right.lower <= left.upper


def evaluate_interval_residual(
    residual: IntervalResidualSpec,
) -> dict[str, Any]:
    """Classify robust pass/fail without collapsing uncertainty to a point."""

    if residual.observed is None:
        status = "not_run"
        reason = "observed_interval_missing"
    elif (
        residual.acceptable.lower <= residual.observed.lower
        and residual.observed.upper <= residual.acceptable.upper
    ):
        status = "robust_pass"
        reason = "entire_observed_interval_is_acceptable"
    elif not _overlaps(residual.observed, residual.acceptable):
        status = "robust_fail"
        reason = "entire_observed_interval_is_outside_acceptance"
    else:
        status = "indeterminate"
        reason = "observed_interval_crosses_acceptance_boundary"
    content = residual.model_dump(mode="json")
    return {
        "artifact_kind": "physicsguard_interval_residual_receipt",
        "receipt_version": "1.0",
        "residual_id": residual.residual_id,
        "status": status,
        "reason_code": reason,
        "observed_interval": (
            residual.observed.model_dump(mode="json")
            if residual.observed is not None
            else None
        ),
        "acceptable_interval": residual.acceptable.model_dump(mode="json"),
        "source_ref": residual.source_ref,
        "input_fingerprint": _fingerprint(content),
        "claim_boundary": (
            "This robust status covers only the supplied interval and "
            "acceptance interval. It does not replace the ordinary PhysicsGuard "
            "audit status or prove unmodeled uncertainty."
        ),
    }


def evaluate_diagnosability(
    request: DiagnosabilityRequestSpec,
) -> dict[str, Any]:
    """Derive pairwise distinguishability and the best declared next signal."""

    by_hypothesis = {
        item.hypothesis_id: item for item in request.fault_signatures
    }
    viable: list[str] = []
    rejected: list[str] = []
    for hypothesis_id, signature in sorted(by_hypothesis.items()):
        compatible = all(
            signal_id not in signature.predicted_intervals
            or _overlaps(
                observed,
                signature.predicted_intervals[signal_id],
            )
            for signal_id, observed in request.observed_signals.items()
        )
        (viable if compatible else rejected).append(hypothesis_id)

    pairs = tuple(combinations(viable, 2))
    signal_pair_coverage: dict[str, list[list[str]]] = {
        signal_id: [] for signal_id in sorted(request.available_signal_ids)
    }
    unresolved: list[list[str]] = []
    pair_rows: list[dict[str, Any]] = []
    for left_id, right_id in pairs:
        left = by_hypothesis[left_id].predicted_intervals
        right = by_hypothesis[right_id].predicted_intervals
        distinguishing = tuple(
            signal_id
            for signal_id in sorted(request.available_signal_ids)
            if signal_id in left
            and signal_id in right
            and not _overlaps(left[signal_id], right[signal_id])
        )
        if not distinguishing:
            unresolved.append([left_id, right_id])
        for signal_id in distinguishing:
            signal_pair_coverage[signal_id].append([left_id, right_id])
        pair_rows.append(
            {
                "hypothesis_pair": [left_id, right_id],
                "distinguishing_signal_ids": list(distinguishing),
                "status": (
                    "distinguishable"
                    if distinguishing
                    else "indistinguishable"
                ),
            }
        )

    ranked = sorted(
        (
            {
                "signal_id": signal_id,
                "newly_distinguished_pair_count": len(pair_ids),
                "hypothesis_pairs": pair_ids,
            }
            for signal_id, pair_ids in signal_pair_coverage.items()
        ),
        key=lambda item: (
            -item["newly_distinguished_pair_count"],
            item["signal_id"],
        ),
    )
    next_signal = (
        ranked[0]["signal_id"]
        if ranked and ranked[0]["newly_distinguished_pair_count"] > 0
        else ""
    )
    if len(viable) <= 1:
        status = "isolated_within_declared_signatures"
    elif not unresolved:
        status = "isolable"
    elif next_signal:
        status = "partially_isolable"
    else:
        status = "indistinguishable"
    content = request.model_dump(mode="json")
    return {
        "artifact_kind": "physicsguard_diagnosability_receipt",
        "receipt_version": "1.0",
        "diagnosis_id": request.diagnosis_id,
        "status": status,
        "viable_hypothesis_ids": viable,
        "rejected_hypothesis_ids": rejected,
        "pairwise_diagnosability": pair_rows,
        "unresolved_hypothesis_pairs": unresolved,
        "ranked_next_signal_candidates": ranked,
        "recommended_next_signal_id": next_signal,
        "request_fingerprint": _fingerprint(content),
        "claim_boundary": (
            "This result is task-local to the declared fault signatures, "
            "intervals, observations, and available signals. It does not prove "
            "that the hypotheses exhaust physical reality or identify a true "
            "fault without external evidence."
        ),
    }


__all__ = ["evaluate_diagnosability", "evaluate_interval_residual"]
