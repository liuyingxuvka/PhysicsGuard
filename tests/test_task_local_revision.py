from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

import physicsguard.core.task_local_revision as task_local_revision_runtime
from physicsguard.cli import main as physicsguard_main
from physicsguard.core.predictive_rollout import evaluate_predictive_rollout
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
)
from tests.test_predictive_rollout_validation import PUMP, _plan as predictive_plan

ROOT = Path(__file__).resolve().parents[1]
def _write_model(path: Path, content: str) -> dict[str, str]:
    path.write_text(content, encoding="utf-8")
    return {
        "model_id": "pump-loop",
        "model_version": "v1" if "base" in content else "v2",
        "path": str(path),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


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


def _plan_data(model: dict[str, str]) -> dict:
    return {
        "plan_id": "diagnosis-1",
        "non_trivial": True,
        "model": model,
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
    }


def _observation(sequence: int = 5) -> DiagnosticObservationSpec:
    return DiagnosticObservationSpec.model_validate(
        {
            "observation_id": "obs-1",
            "plan_id": "diagnosis-1",
            "observation_sequence": sequence,
            "source_ref": "testbench:run-1",
            "signals": {"speed": {"value": 10.0, "trend": "increase"}},
            "residuals": {"balance": 0.0},
            "timings": {"temperature_change": 1.0, "speed_change": 2.0},
        }
    )


def _revision(
    base: dict[str, str],
    candidate: dict[str, str],
    *,
    check_status: str = "pass",
    candidate_applied: bool = False,
    rollback: dict[str, str] | None = None,
    predictive_receipt: dict | None = None,
) -> CandidateModelRevisionSpec:
    checks = [
        {
            "check_id": "regression",
            "kind": "regression",
            "status": check_status,
            "evidence_ref": "pytest:regression",
        },
        {
            "check_id": "holdout",
            "kind": "holdout",
            "status": "pass",
            "evidence_ref": "pytest:holdout",
        },
    ]
    if predictive_receipt is not None:
        checks.append(
            {
                "check_id": "predictive",
                "kind": "predictive_rollout",
                "status": "pass",
                "evidence_ref": "physicsguard:predictive-rollout",
                "native_receipt": predictive_receipt,
            }
        )
    return CandidateModelRevisionSpec.model_validate(
        {
            "revision_id": "revision-1",
            "plan_id": "diagnosis-1",
            "base_model": base,
            "candidate_model": candidate,
            "revision_kind": "mapping_update",
            "triggering_mismatch_ids": ["H2:h2-signal"],
            "required_check_ids": [item["check_id"] for item in checks],
            "checks": checks,
            "candidate_applied": candidate_applied,
            "rollback_model": rollback,
        }
    )


def test_nontrivial_plan_requires_competing_hypotheses(tmp_path: Path) -> None:
    model = _write_model(tmp_path / "base.json", "base model")
    data = _plan_data(model)
    data["hypotheses"] = data["hypotheses"][:1]
    data["observation_candidates"][0]["predicted_outcomes"] = {"H1": "up"}
    data["observation_candidates"][1]["predicted_outcomes"] = {"H1": "up"}

    with pytest.raises(ValidationError, match="at least 2 hypothesis"):
        HypothesisPlanSpec.model_validate(data)


def test_discriminating_observation_breaks_residual_relevance_tie(tmp_path: Path) -> None:
    model = _write_model(tmp_path / "base.json", "base model")
    plan = HypothesisPlanSpec.model_validate(_plan_data(model))

    ranked = rank_observation_candidates(plan)

    assert ranked[0]["candidate_id"] == "discriminating"
    assert ranked[0]["hypothesis_discrimination"] == 1.0
    assert ranked[1]["hypothesis_discrimination"] == 0.0


def test_prediction_must_precede_observation(tmp_path: Path) -> None:
    model = _write_model(tmp_path / "base.json", "base model")
    plan = HypothesisPlanSpec.model_validate(_plan_data(model))

    with pytest.raises(ValueError, match="strictly later"):
        evaluate_hypothesis_observation(plan, _observation(4), base_dir=tmp_path)


def test_observation_weakens_one_hypothesis_and_preserves_another(tmp_path: Path) -> None:
    model = _write_model(tmp_path / "base.json", "base model")
    plan = HypothesisPlanSpec.model_validate(_plan_data(model))

    receipt = evaluate_hypothesis_observation(plan, _observation(), base_dir=tmp_path)
    results = {item["hypothesis_id"]: item for item in receipt["hypothesis_results"]}

    assert results["H1"]["disposition"] == "supported"
    assert results["H2"]["disposition"] == "weakened"
    assert results["H2"]["contradicted_expectation_ids"] == ["h2-signal"]
    assert receipt["mismatch_ids"] == ["H2:h2-signal"]


def test_missing_target_remains_undetermined(tmp_path: Path) -> None:
    model = _write_model(tmp_path / "base.json", "base model")
    plan = HypothesisPlanSpec.model_validate(_plan_data(model))
    observation = _observation().model_copy(
        update={"signals": {}, "residuals": {}, "timings": {}}
    )

    receipt = evaluate_hypothesis_observation(plan, observation, base_dir=tmp_path)

    assert all(
        item["disposition"] == "undetermined"
        for item in receipt["hypothesis_results"]
    )


def test_candidate_accept_reject_and_rollback_preserve_base(tmp_path: Path) -> None:
    base = _write_model(tmp_path / "base.json", "base model")
    candidate = _write_model(tmp_path / "candidate.json", "candidate model")

    accepted = evaluate_candidate_model_revision(
        _revision(base, candidate),
        base_dir=tmp_path,
    )
    rejected = evaluate_candidate_model_revision(
        _revision(base, candidate, check_status="fail"),
        base_dir=tmp_path,
    )
    rolled_back = evaluate_candidate_model_revision(
        _revision(
            base,
            candidate,
            check_status="fail",
            candidate_applied=True,
            rollback=base,
        ),
        base_dir=tmp_path,
    )

    assert accepted["disposition"] == "accepted"
    assert rejected["disposition"] == "rejected"
    assert rolled_back["disposition"] == "rolled_back"
    assert accepted["base_model_preserved"]
    assert rejected["base_model_preserved"]
    assert rolled_back["base_model_preserved"]
    assert (tmp_path / "base.json").read_text(encoding="utf-8") == "base model"


def test_candidate_must_be_distinct_from_base(tmp_path: Path) -> None:
    base = _write_model(tmp_path / "base.json", "base model")

    receipt = evaluate_candidate_model_revision(
        _revision(base, base),
        base_dir=tmp_path,
    )

    assert receipt["status"] == "blocked"
    assert "candidate_not_distinct_from_base" in receipt["identity_findings"]


def test_candidate_consumes_existing_predictive_rollout_receipt(tmp_path: Path) -> None:
    base = _write_model(tmp_path / "base.json", "base model")
    candidate_path = PUMP / "model" / "pump_loop_hierarchy.yaml"
    candidate = {
        "model_id": "pump_model",
        "model_version": "v2",
        "path": str(candidate_path),
        "sha256": hashlib.sha256(candidate_path.read_bytes()).hexdigest(),
    }
    native = evaluate_predictive_rollout(
        "stateful_dynamic",
        predictive_plan(),
        base_dir=PUMP,
    ).receipt

    receipt = evaluate_candidate_model_revision(
        _revision(base, candidate, predictive_receipt=native),
        base_dir=tmp_path,
    )
    predictive = next(
        item for item in receipt["check_results"] if item["kind"] == "predictive_rollout"
    )

    assert receipt["disposition"] == "accepted"
    assert predictive["effective_status"] == "pass"
    assert predictive["native_model_identity_status"] == "current_candidate"
    assert predictive["native_receipt_fingerprint"]
    assert native["metrics"]["aligned_step_count"] == 3


def test_predictive_rollout_for_another_model_blocks_candidate(
    tmp_path: Path,
) -> None:
    base = _write_model(tmp_path / "base.json", "base model")
    candidate = _write_model(tmp_path / "candidate.json", "candidate model")
    native = evaluate_predictive_rollout(
        "stateful_dynamic",
        predictive_plan(),
        base_dir=PUMP,
    ).receipt

    receipt = evaluate_candidate_model_revision(
        _revision(base, candidate, predictive_receipt=native),
        base_dir=tmp_path,
    )
    predictive = next(
        item for item in receipt["check_results"] if item["kind"] == "predictive_rollout"
    )

    assert receipt["disposition"] == "rejected"
    assert predictive["effective_status"] == "blocked"
    assert predictive["native_model_identity_status"] == "mismatch"


def test_task_model_plan_cli_emits_ranked_receipt(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    model = _write_model(tmp_path / "base.json", "base model")
    plan_path = tmp_path / "plan.json"
    plan_path.write_text(json.dumps(_plan_data(model)), encoding="utf-8")

    exit_code = physicsguard_main(["task-model", "plan", str(plan_path)])
    output = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert output["status"] == "pass"
    assert output["ranked_observation_candidates"][0]["candidate_id"] == "discriminating"


def test_task_local_revision_uses_the_canonical_package_runtime() -> None:
    assert Path(task_local_revision_runtime.__file__).resolve() == (
        ROOT / "src" / "physicsguard" / "core" / "task_local_revision.py"
    ).resolve()
    assert not (
        ROOT / "skill" / "physicsguard-model-dataset-validation" / "runtime"
    ).exists()
