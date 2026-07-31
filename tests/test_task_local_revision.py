from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

import physicsguard.core.task_local_revision as task_local_revision_runtime
from physicsguard.cli import main as physicsguard_main
from physicsguard.core.task_local_revision import (
    evaluate_candidate_model_revision,
    evaluate_hypothesis_observation,
    freeze_hypothesis_plan,
    rank_observation_candidates,
)
from physicsguard.schema.task_local_revision import (
    CandidateModelRevisionSpec,
    DiagnosticObservationSpec,
    HypothesisPlanSpec,
    NativeDepthReceiptSpec,
    fingerprint_native_depth_receipt,
    fingerprint_revision_check_receipt,
)


ROOT = Path(__file__).resolve().parents[1]
FAMILIES = (
    "execution_depth",
    "mapping",
    "residual",
    "uncertainty",
    "diagnosability",
    "predictive_rollout",
)
COVERAGE_FINGERPRINT = hashlib.sha256(b"coverage-universe-v1").hexdigest()


def _write_model(path: Path, content: str, *, model_id: str = "pump-loop") -> dict[str, str]:
    path.write_text(content, encoding="utf-8")
    return {
        "model_id": model_id,
        "model_version": "v1" if "base" in content else "v2",
        "path": str(path),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


def _coverage() -> dict:
    return {
        "coverage_universe_id": "coverage:pump-loop:v1",
        "coverage_universe_fingerprint": COVERAGE_FINGERPRINT,
        "owner_id": "physicsguard.project-evidence-registry",
        "discovery_evidence_id": "evidence:coverage-discovery:v1",
        "member_ids": ["speed", "balance", "timing"],
    }


def _gap(
    gap_id: str,
    family: str,
    *,
    resolution_class: str = "model_edit",
    external_input_id: str | None = None,
) -> dict:
    return {
        "gap_id": gap_id,
        "family": family,
        "resolution_class": resolution_class,
        "next_action": f"resolve:{gap_id}",
        "external_input_id": external_input_id,
    }


def _native_depth(
    model: dict[str, str],
    *,
    iteration: int,
    gaps: list[dict] | None = None,
    task_id: str = "task-1",
    plan_id: str = "diagnosis-1",
) -> dict:
    gaps = list(gaps or [])
    payload = {
        "artifact_kind": "physicsguard_task_native_depth_receipt",
        "receipt_version": "1.0",
        "producer_id": "physicsguard.native-task-depth",
        "status": "blocked" if gaps else "pass",
        "task_id": task_id,
        "plan_id": plan_id,
        "iteration": iteration,
        "model_sha256": model["sha256"],
        "coverage_universe_fingerprint": COVERAGE_FINGERPRINT,
        "source_receipt_ids": {family: f"receipt:{family}:{iteration}" for family in FAMILIES},
        "source_receipt_fingerprints": {
            family: hashlib.sha256(f"{family}:{iteration}".encode()).hexdigest()
            for family in FAMILIES
        },
        "gaps": gaps,
    }
    payload["receipt_fingerprint"] = fingerprint_native_depth_receipt(payload)
    return payload


def _expectations(prefix: str, *, signal_operator: str) -> list[dict]:
    return [
        {
            "expectation_id": f"{prefix}-signal",
            "kind": "signal",
            "target_id": "speed",
            "operator": signal_operator,
            "weakening_condition": "speed trend differs",
        },
        {
            "expectation_id": f"{prefix}-residual",
            "kind": "residual",
            "target_id": "balance",
            "operator": "between",
            "lower": -0.1,
            "upper": 0.1,
            "weakening_condition": "balance residual leaves the range",
        },
        {
            "expectation_id": f"{prefix}-timing",
            "kind": "timing",
            "target_id": "speed_change",
            "compare_target_id": "temperature_change",
            "operator": "after",
            "tolerance": 0.0,
            "weakening_condition": "speed does not change after temperature",
        },
    ]


def _plan_data(
    model: dict[str, str],
    *,
    iteration: int = 0,
    gaps: list[dict] | None = None,
    predecessor: dict | None = None,
) -> dict:
    return {
        "plan_id": "diagnosis-1",
        "task_id": "task-1",
        "purpose": "localize the bounded pump-loop mismatch",
        "non_trivial": True,
        "model": model,
        "coverage": _coverage(),
        "assumptions": [],
        "unknowns": ["true physical cause is not yet known"],
        "prediction_sequence": 4,
        "hypotheses": [
            {
                "hypothesis_id": "H1",
                "explanation": "feedback gain is wrong",
                "expectations": _expectations("h1", signal_operator="increase"),
            },
            {
                "hypothesis_id": "H2",
                "explanation": "signal mapping is reversed",
                "expectations": _expectations("h2", signal_operator="decrease"),
            },
        ],
        "observation_candidates": [
            {
                "candidate_id": "same-outcome",
                "target_id": "temperature",
                "residual_relevance": 0.8,
                "predicted_outcomes": {"H1": "up", "H2": "up"},
            },
            {
                "candidate_id": "discriminating",
                "target_id": "speed",
                "residual_relevance": 0.8,
                "predicted_outcomes": {"H1": "up", "H2": "down"},
            },
        ],
        "selection_weights": {
            "residual_relevance": 0.5,
            "hypothesis_discrimination": 0.5,
        },
        "iteration": iteration,
        "max_iterations": 4,
        "predecessor": predecessor,
        "native_depth_receipt": _native_depth(
            model, iteration=iteration, gaps=gaps
        ),
    }


def _plan(model: dict[str, str], *, gaps: list[dict] | None = None) -> HypothesisPlanSpec:
    return HypothesisPlanSpec.model_validate(_plan_data(model, gaps=gaps))


def _evidence(evidence_id: str, group: str) -> dict:
    return {
        "evidence_id": evidence_id,
        "evidence_fingerprint": hashlib.sha256(evidence_id.encode()).hexdigest(),
        "producer_id": f"producer:{evidence_id}",
        "source_ref": f"test:{evidence_id}",
        "independence_group": group,
    }


def _observation(
    plan: HypothesisPlanSpec,
    tmp_path: Path,
    *,
    sequence: int = 5,
    signals: dict | None = None,
    residuals: dict | None = None,
    timings: dict | None = None,
    external_input_ids: list[str] | None = None,
) -> DiagnosticObservationSpec:
    frozen = freeze_hypothesis_plan(plan, base_dir=tmp_path)
    return DiagnosticObservationSpec.model_validate(
        {
            "observation_id": "obs-1",
            "task_id": plan.task_id,
            "plan_id": plan.plan_id,
            "frozen_plan_fingerprint": frozen["plan_fingerprint"],
            "selected_candidate_id": "discriminating",
            "observation_sequence": sequence,
            "evidence": _evidence("observation-1", "external-testbench-run-1"),
            "signals": (
                {"speed": {"value": 10.0, "trend": "increase"}}
                if signals is None
                else signals
            ),
            "residuals": {"balance": 0.0} if residuals is None else residuals,
            "timings": (
                {"temperature_change": 1.0, "speed_change": 2.0}
                if timings is None
                else timings
            ),
            "external_input_ids": list(external_input_ids or []),
        }
    )


def _predictive_receipt(candidate: dict[str, str], *, status: str = "pass") -> dict:
    return {
        "artifact_kind": "physicsguard_predictive_rollout_receipt",
        "receipt_version": "1.0",
        "status": status,
        "model_semantics": "stateful_dynamic",
        "model_identity": {
            "identity_id": candidate["model_id"],
            "path": candidate["path"],
            "expected_sha256": candidate["sha256"],
            "actual_sha256": candidate["sha256"],
            "status": "current",
            "case_ids": ["future-1"],
        },
        "metrics": {
            "aligned_step_count": 3,
            "worst_step_normalized_error": 0.01,
            "accumulated_normalized_error": 0.02,
            "lag_steps": 0,
            "phase_error": 0.0,
            "drift": 0.0,
            "error_growth": 0.0,
            "stability_pass": True,
            "threshold_results": {"stability": True},
        },
        "claim_boundary": "exact synthetic future holdout used by the focused test",
    }


def _check(
    kind: str,
    candidate: dict[str, str],
    *,
    revision_id: str = "revision-1",
    status: str = "pass",
    independent_of: list[str] | None = None,
    group: str | None = None,
    predictive: dict | None = None,
) -> dict:
    check_id = {
        "regression": "regression",
        "holdout": "holdout",
        "predictive_rollout": "predictive",
    }[kind]
    payload = {
        "artifact_kind": "physicsguard_task_revision_check_receipt",
        "receipt_version": "1.0",
        "check_id": check_id,
        "kind": kind,
        "status": status,
        "task_id": "task-1",
        "plan_id": "diagnosis-1",
        "revision_id": revision_id,
        "candidate_model_sha256": candidate["sha256"],
        "coverage_universe_fingerprint": COVERAGE_FINGERPRINT,
        "evidence": _evidence(
            f"evidence-{check_id}", group or f"independent-{check_id}"
        ),
        "independent_of_evidence_ids": list(independent_of or []),
        "predictive_receipt": (
            predictive
            if kind == "predictive_rollout"
            else None
        ),
    }
    payload["receipt_fingerprint"] = fingerprint_revision_check_receipt(payload)
    return payload


def _revision_data(
    base: dict[str, str],
    candidate: dict[str, str],
    *,
    base_gaps: list[dict] | None = None,
    candidate_gaps: list[dict] | None = None,
    iteration: int = 1,
    max_iterations: int = 4,
    check_status: str = "pass",
    predictive: dict | None = None,
    candidate_applied: bool = False,
    rollback: dict[str, str] | None = None,
) -> dict:
    predictive = predictive or _predictive_receipt(candidate)
    checks = [
        _check("regression", candidate, status=check_status),
        _check(
            "holdout",
            candidate,
            independent_of=["construction-1"],
            group="independent-future-holdout",
        ),
        _check("predictive_rollout", candidate, predictive=predictive),
    ]
    return {
        "revision_id": "revision-1",
        "task_id": "task-1",
        "plan_id": "diagnosis-1",
        "frozen_plan_fingerprint": hashlib.sha256(b"plan").hexdigest(),
        "predecessor_observation_fingerprint": hashlib.sha256(b"observation").hexdigest(),
        "iteration": iteration,
        "max_iterations": max_iterations,
        "base_model": base,
        "candidate_model": candidate,
        "coverage": _coverage(),
        "base_native_depth_receipt": _native_depth(
            base, iteration=iteration - 1, gaps=base_gaps
        ),
        "candidate_native_depth_receipt": _native_depth(
            candidate, iteration=iteration, gaps=candidate_gaps
        ),
        "revision_kind": "mapping_update",
        "triggering_mismatch_ids": ["H2:h2-signal"],
        "candidate_construction_evidence_id": "construction-1",
        "required_check_ids": [item["check_id"] for item in checks],
        "checks": checks,
        "candidate_applied": candidate_applied,
        "rollback_model": rollback,
    }


def _revision(base: dict[str, str], candidate: dict[str, str], **kwargs) -> CandidateModelRevisionSpec:
    return CandidateModelRevisionSpec.model_validate(
        _revision_data(base, candidate, **kwargs)
    )


def test_old_optional_plan_shape_is_rejected(tmp_path: Path) -> None:
    model = _write_model(tmp_path / "base.json", "base model")
    retired = {
        "plan_id": "legacy",
        "non_trivial": True,
        "model": model,
        "prediction_sequence": 1,
        "hypotheses": [],
        "observation_candidates": [],
    }
    with pytest.raises(ValidationError):
        HypothesisPlanSpec.model_validate(retired)


def test_nontrivial_plan_requires_purpose_and_explicit_declarations(tmp_path: Path) -> None:
    model = _write_model(tmp_path / "base.json", "base model")
    data = _plan_data(model)
    data.pop("purpose")
    with pytest.raises(ValidationError, match="purpose"):
        HypothesisPlanSpec.model_validate(data)


def test_native_depth_receipt_requires_all_six_families_and_current_fingerprint(tmp_path: Path) -> None:
    model = _write_model(tmp_path / "base.json", "base model")
    missing_family = _native_depth(model, iteration=0)
    missing_family["source_receipt_ids"].pop("mapping")
    missing_family["receipt_fingerprint"] = fingerprint_native_depth_receipt(missing_family)
    with pytest.raises(ValidationError, match="six native gap families"):
        NativeDepthReceiptSpec.model_validate(missing_family)

    stale = _native_depth(model, iteration=0)
    stale["source_receipt_ids"]["mapping"] = "receipt:mapping:changed"
    with pytest.raises(ValidationError, match="fingerprint"):
        NativeDepthReceiptSpec.model_validate(stale)


def test_later_iteration_requires_exact_predecessor(tmp_path: Path) -> None:
    model = _write_model(tmp_path / "candidate.json", "candidate model")
    data = _plan_data(model, iteration=1, predecessor=None)
    with pytest.raises(ValidationError, match="predecessor"):
        HypothesisPlanSpec.model_validate(data)


def test_nontrivial_plan_requires_competing_hypotheses(tmp_path: Path) -> None:
    model = _write_model(tmp_path / "base.json", "base model")
    data = _plan_data(model)
    data["hypotheses"] = data["hypotheses"][:1]
    for candidate in data["observation_candidates"]:
        candidate["predicted_outcomes"] = {"H1": "up"}
    with pytest.raises(ValidationError, match="at least 2 hypothesis"):
        HypothesisPlanSpec.model_validate(data)


def test_discriminating_observation_breaks_residual_relevance_tie(tmp_path: Path) -> None:
    model = _write_model(tmp_path / "base.json", "base model")
    plan = _plan(model)
    ranked = rank_observation_candidates(plan)
    assert ranked[0]["candidate_id"] == "discriminating"
    assert ranked[0]["hypothesis_discrimination"] == 1.0


def test_plan_receipt_exposes_native_gaps_and_never_closes_task(tmp_path: Path) -> None:
    model = _write_model(tmp_path / "base.json", "base model")
    gap = _gap("mapping:unknown-speed", "mapping")
    receipt = freeze_hypothesis_plan(_plan(model, gaps=[gap]), base_dir=tmp_path)
    assert receipt["open_gap_ids"] == ["mapping:unknown-speed"]
    assert receipt["next_iteration_required"]
    assert receipt["terminal_reason"] == "continue_iteration"


def test_prediction_must_precede_observation(tmp_path: Path) -> None:
    model = _write_model(tmp_path / "base.json", "base model")
    plan = _plan(model)
    with pytest.raises(ValueError, match="strictly later"):
        evaluate_hypothesis_observation(
            plan, _observation(plan, tmp_path, sequence=4), base_dir=tmp_path
        )


def test_observation_must_bind_current_frozen_plan(tmp_path: Path) -> None:
    model = _write_model(tmp_path / "base.json", "base model")
    plan = _plan(model)
    observation = _observation(plan, tmp_path).model_copy(
        update={"frozen_plan_fingerprint": "0" * 64}
    )
    with pytest.raises(ValueError, match="frozen-plan"):
        evaluate_hypothesis_observation(plan, observation, base_dir=tmp_path)


def test_observation_weakens_one_hypothesis_and_preserves_another(tmp_path: Path) -> None:
    model = _write_model(tmp_path / "base.json", "base model")
    plan = _plan(model)
    receipt = evaluate_hypothesis_observation(
        plan, _observation(plan, tmp_path), base_dir=tmp_path
    )
    results = {item["hypothesis_id"]: item for item in receipt["hypothesis_results"]}
    assert results["H1"]["disposition"] == "supported"
    assert results["H2"]["disposition"] == "weakened"
    assert not receipt["physical_cause_licensed"]


def test_missing_target_remains_undetermined_and_open(tmp_path: Path) -> None:
    model = _write_model(tmp_path / "base.json", "base model")
    plan = _plan(model)
    receipt = evaluate_hypothesis_observation(
        plan,
        _observation(plan, tmp_path, signals={}, residuals={}, timings={}),
        base_dir=tmp_path,
    )
    assert all(row["disposition"] == "undetermined" for row in receipt["hypothesis_results"])
    assert any(gap.startswith("observation_missing:") for gap in receipt["open_gap_ids"])


def test_all_hypotheses_contradicted_creates_model_miss(tmp_path: Path) -> None:
    model = _write_model(tmp_path / "base.json", "base model")
    plan = _plan(model)
    receipt = evaluate_hypothesis_observation(
        plan,
        _observation(
            plan,
            tmp_path,
            signals={"speed": {"value": 0.0, "trend": "stable"}},
            residuals={"balance": 2.0},
            timings={"temperature_change": 2.0, "speed_change": 1.0},
        ),
        base_dir=tmp_path,
    )
    assert receipt["all_hypotheses_contradicted"]
    assert receipt["terminal_reason"] == "model_miss"
    assert receipt["model_miss_gap_id"] in receipt["open_gap_ids"]
    assert not receipt["physical_cause_licensed"]


def test_candidate_closes_only_with_zero_native_gaps_and_three_typed_checks(tmp_path: Path) -> None:
    base = _write_model(tmp_path / "base.json", "base model")
    candidate = _write_model(tmp_path / "candidate.json", "candidate model")
    receipt = evaluate_candidate_model_revision(
        _revision(
            base,
            candidate,
            base_gaps=[_gap("mapping:unknown-speed", "mapping")],
            candidate_gaps=[],
        ),
        base_dir=tmp_path,
    )
    assert receipt["status"] == "pass"
    assert receipt["disposition"] == "accepted"
    assert receipt["model_closed_for_task"]
    assert receipt["resolved_gap_ids"] == ["mapping:unknown-speed"]
    assert "SI-unit and low-fidelity assumptions" in receipt["claim_boundary"]


def test_candidate_must_be_distinct_from_base(tmp_path: Path) -> None:
    base = _write_model(tmp_path / "base.json", "base model")
    receipt = evaluate_candidate_model_revision(
        _revision(base, base), base_dir=tmp_path
    )
    assert receipt["status"] == "blocked"
    assert "candidate_not_distinct_from_base" in receipt["identity_findings"]


def test_candidate_check_bound_to_another_candidate_is_rejected_by_schema(tmp_path: Path) -> None:
    base = _write_model(tmp_path / "base.json", "base model")
    candidate = _write_model(tmp_path / "candidate.json", "candidate model")
    data = _revision_data(base, candidate)
    data["checks"][0]["candidate_model_sha256"] = "0" * 64
    data["checks"][0]["receipt_fingerprint"] = fingerprint_revision_check_receipt(
        data["checks"][0]
    )
    with pytest.raises(ValidationError, match="identity mismatch"):
        CandidateModelRevisionSpec.model_validate(data)


def test_holdout_must_be_independent_from_candidate_construction(tmp_path: Path) -> None:
    base = _write_model(tmp_path / "base.json", "base model")
    candidate = _write_model(tmp_path / "candidate.json", "candidate model")
    data = _revision_data(base, candidate)
    holdout = next(item for item in data["checks"] if item["kind"] == "holdout")
    holdout["independent_of_evidence_ids"] = []
    holdout["receipt_fingerprint"] = fingerprint_revision_check_receipt(holdout)
    with pytest.raises(ValidationError, match="candidate construction"):
        CandidateModelRevisionSpec.model_validate(data)


def test_gap_transition_is_derived_from_native_receipts(tmp_path: Path) -> None:
    base = _write_model(tmp_path / "base.json", "base model")
    candidate = _write_model(tmp_path / "candidate.json", "candidate model")
    receipt = evaluate_candidate_model_revision(
        _revision(
            base,
            candidate,
            base_gaps=[
                _gap("mapping:unknown-speed", "mapping"),
                _gap("residual:balance", "residual"),
            ],
            candidate_gaps=[
                _gap("residual:balance", "residual"),
                _gap("uncertainty:new-range", "uncertainty"),
            ],
        ),
        base_dir=tmp_path,
    )
    assert receipt["resolved_gap_ids"] == ["mapping:unknown-speed"]
    assert receipt["persisted_gap_ids"] == ["residual:balance"]
    assert receipt["introduced_gap_ids"] == ["uncertainty:new-range"]
    assert receipt["progressed"]
    assert receipt["terminal_reason"] == "continue_iteration"


def test_same_native_gaps_are_progress_stalled(tmp_path: Path) -> None:
    base = _write_model(tmp_path / "base.json", "base model")
    candidate = _write_model(tmp_path / "candidate.json", "candidate model")
    gap = _gap("residual:balance", "residual")
    receipt = evaluate_candidate_model_revision(
        _revision(base, candidate, base_gaps=[gap], candidate_gaps=[gap]),
        base_dir=tmp_path,
    )
    assert not receipt["progressed"]
    assert receipt["terminal_reason"] == "progress_stalled"


def test_external_input_and_iteration_limit_are_distinct(tmp_path: Path) -> None:
    base = _write_model(tmp_path / "base.json", "base model")
    candidate = _write_model(tmp_path / "candidate.json", "candidate model")
    external_gap = _gap(
        "mapping:missing-pressure",
        "mapping",
        resolution_class="external_input_required",
        external_input_id="signal:pressure",
    )
    external = evaluate_candidate_model_revision(
        _revision(base, candidate, base_gaps=[], candidate_gaps=[external_gap]),
        base_dir=tmp_path,
    )
    assert external["terminal_reason"] == "external_input_required"
    assert external["external_input_ids"] == ["signal:pressure"]

    limit_gap = _gap("residual:balance", "residual")
    limit = evaluate_candidate_model_revision(
        _revision(
            base,
            candidate,
            base_gaps=[_gap("mapping:old", "mapping")],
            candidate_gaps=[limit_gap],
            iteration=4,
            max_iterations=4,
        ),
        base_dir=tmp_path,
    )
    assert limit["terminal_reason"] == "iteration_limit"
    assert not limit["model_closed_for_task"]


def test_predictive_receipt_for_another_model_blocks_candidate(tmp_path: Path) -> None:
    base = _write_model(tmp_path / "base.json", "base model")
    candidate = _write_model(tmp_path / "candidate.json", "candidate model")
    other = _write_model(tmp_path / "other.json", "other candidate", model_id="other")
    receipt = evaluate_candidate_model_revision(
        _revision(base, candidate, predictive=_predictive_receipt(other)),
        base_dir=tmp_path,
    )
    predictive = next(
        item for item in receipt["check_results"] if item["kind"] == "predictive_rollout"
    )
    assert predictive["effective_status"] == "blocked"
    assert predictive["native_model_identity_status"] == "mismatch"
    assert receipt["disposition"] == "rejected"


def test_failed_applied_candidate_rolls_back_only_to_current_base(tmp_path: Path) -> None:
    base = _write_model(tmp_path / "base.json", "base model")
    candidate = _write_model(tmp_path / "candidate.json", "candidate model")
    receipt = evaluate_candidate_model_revision(
        _revision(
            base,
            candidate,
            check_status="fail",
            candidate_applied=True,
            rollback=base,
        ),
        base_dir=tmp_path,
    )
    assert receipt["disposition"] == "rolled_back"
    assert receipt["base_model_preserved"]
    assert not receipt["model_closed_for_task"]


def test_task_model_plan_cli_emits_strict_receipt(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    model = _write_model(tmp_path / "base.json", "base model")
    plan_path = tmp_path / "plan.json"
    plan_path.write_text(json.dumps(_plan_data(model)), encoding="utf-8")
    exit_code = physicsguard_main(["task-model", "plan", str(plan_path)])
    output = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert output["status"] == "pass"
    assert output["coverage"]["coverage_universe_fingerprint"] == COVERAGE_FINGERPRINT
    assert output["ranked_observation_candidates"][0]["candidate_id"] == "discriminating"
    assert output["terminal_reason"] == "continue_iteration"


def test_task_local_revision_uses_the_canonical_package_runtime() -> None:
    assert Path(task_local_revision_runtime.__file__).resolve() == (
        ROOT / "src" / "physicsguard" / "core" / "task_local_revision.py"
    ).resolve()
    assert not (
        ROOT / "skill" / "physicsguard-model-dataset-validation" / "runtime"
    ).exists()
