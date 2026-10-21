from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from physicsguard.cli import main as physicsguard_main
from physicsguard.core.task_local_revision import (
    evaluate_hypothesis_observation,
    freeze_hypothesis_plan,
    rank_observation_candidates,
)
from physicsguard.schema.task_local_revision import DiagnosticObservationSpec, HypothesisPlanSpec


def _write_model(tmp_path: Path) -> dict[str, str]:
    path = tmp_path / "pump_loop.yaml"
    path.write_text("system_name: pump_loop\n", encoding="utf-8")
    return {"model_id": "pump-loop", "model_version": "v1", "path": str(path)}


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
    ]


def _plan_data(model: dict[str, str]) -> dict:
    return {
        "plan_id": "diagnosis-1",
        "task_id": "task-1",
        "purpose": "localize the bounded pump-loop mismatch",
        "non_trivial": True,
        "model": model,
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
        "iteration": 0,
        "max_iterations": 4,
    }


def _plan(tmp_path: Path) -> HypothesisPlanSpec:
    return HypothesisPlanSpec.model_validate(_plan_data(_write_model(tmp_path)))


def _observation(**overrides) -> DiagnosticObservationSpec:
    data = {
        "observation_id": "obs-1",
        "task_id": "task-1",
        "plan_id": "diagnosis-1",
        "selected_candidate_id": "discriminating",
        "observation_sequence": 5,
        "evidence": {
            "evidence_id": "evidence:speed-export",
            "producer_id": "test-bench export",
            "source_ref": "run-17.csv",
            "independence_group": "run-17",
            "evidence_kind": "test",
        },
        "signals": {"speed": {"trend": "increase"}},
        "residuals": {"balance": 0.0},
        "timings": {},
        "external_input_ids": [],
    }
    data.update(overrides)
    return DiagnosticObservationSpec.model_validate(data)


def test_removed_receipt_fields_are_rejected(tmp_path: Path) -> None:
    for key in ("native_depth_receipt", "blueprint", "coverage", "predecessor"):
        data = _plan_data(_write_model(tmp_path))
        data[key] = None
        with pytest.raises(ValidationError):
            HypothesisPlanSpec.model_validate(data)


def test_nontrivial_plan_requires_competing_hypotheses(tmp_path: Path) -> None:
    data = _plan_data(_write_model(tmp_path))
    data["hypotheses"] = data["hypotheses"][:1]
    for candidate in data["observation_candidates"]:
        candidate["predicted_outcomes"] = {"H1": "up"}
    with pytest.raises(ValidationError, match="at least 2 hypothesis"):
        HypothesisPlanSpec.model_validate(data)


def test_one_expectation_is_enough_but_none_is_rejected(tmp_path: Path) -> None:
    data = _plan_data(_write_model(tmp_path))
    data["hypotheses"][0]["expectations"] = data["hypotheses"][0]["expectations"][:1]
    assert HypothesisPlanSpec.model_validate(data).hypotheses[0].expectations
    data["hypotheses"][0]["expectations"] = []
    with pytest.raises(ValidationError, match="at least one expectation"):
        HypothesisPlanSpec.model_validate(data)


def test_discriminating_observation_breaks_residual_relevance_tie(tmp_path: Path) -> None:
    ranked = rank_observation_candidates(_plan(tmp_path))
    assert ranked[0]["candidate_id"] == "discriminating"
    assert ranked[0]["hypothesis_discrimination"] == 1.0


def test_plan_is_blocked_until_the_model_file_exists(tmp_path: Path) -> None:
    data = _plan_data(_write_model(tmp_path))
    data["model"]["path"] = str(tmp_path / "missing.yaml")
    frozen = freeze_hypothesis_plan(HypothesisPlanSpec.model_validate(data), base_dir=tmp_path)
    assert frozen["status"] == "blocked"
    assert frozen["model"]["status"] == "missing"
    passing = freeze_hypothesis_plan(_plan(tmp_path), base_dir=tmp_path)
    assert passing["status"] == "pass"
    assert "fingerprint" not in json.dumps(passing)


def test_prediction_must_precede_observation(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="strictly later"):
        evaluate_hypothesis_observation(_plan(tmp_path), _observation(observation_sequence=4), base_dir=tmp_path)


def test_observation_must_name_a_declared_candidate(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="declared observation candidate"):
        evaluate_hypothesis_observation(
            _plan(tmp_path), _observation(selected_candidate_id="unknown"), base_dir=tmp_path
        )


def test_observation_weakens_one_hypothesis_and_preserves_another(tmp_path: Path) -> None:
    result = evaluate_hypothesis_observation(_plan(tmp_path), _observation(), base_dir=tmp_path)
    dispositions = {row["hypothesis_id"]: row["disposition"] for row in result["hypothesis_results"]}
    assert dispositions == {"H1": "supported", "H2": "weakened"}
    assert result["terminal_reason"] == "continue_iteration"
    assert not result["physical_cause_licensed"]


def test_missing_target_remains_undetermined_and_open(tmp_path: Path) -> None:
    result = evaluate_hypothesis_observation(
        _plan(tmp_path), _observation(signals={}, residuals={}), base_dir=tmp_path
    )
    assert all(row["disposition"] == "undetermined" for row in result["hypothesis_results"])
    assert any(gap.startswith("observation_missing:") for gap in result["open_gap_ids"])


@pytest.mark.parametrize("evidence_kind", ["runtime", "test", "dataset"])
def test_all_hypotheses_contradicted_creates_model_miss(tmp_path: Path, evidence_kind: str) -> None:
    observation = _observation(
        signals={"speed": {"trend": "stable"}},
        residuals={"balance": 2.0},
        evidence={
            "evidence_id": "evidence:unexpected",
            "producer_id": "test-bench export",
            "source_ref": "run-18.csv",
            "independence_group": "run-18",
            "evidence_kind": evidence_kind,
        },
    )
    result = evaluate_hypothesis_observation(_plan(tmp_path), observation, base_dir=tmp_path)
    assert result["all_hypotheses_contradicted"]
    assert result["terminal_reason"] == "model_miss"
    assert result["model_miss_gap_id"] in result["open_gap_ids"]
    assert result["model_miss_evidence_kind"] == evidence_kind
    assert "revise_hypothesis_universe_from_unexpected_observation" in result["required_next_actions"]


def test_external_input_is_reported_as_its_own_terminal_reason(tmp_path: Path) -> None:
    result = evaluate_hypothesis_observation(
        _plan(tmp_path), _observation(external_input_ids=["signal:pressure"]), base_dir=tmp_path
    )
    assert result["terminal_reason"] == "external_input_required"
    assert result["external_input_ids"] == ["signal:pressure"]


def test_task_model_plan_and_observe_cli(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    import yaml

    plan_path = tmp_path / "plan.yaml"
    plan_path.write_text(yaml.safe_dump(_plan_data(_write_model(tmp_path))), encoding="utf-8")
    observation_path = tmp_path / "observation.yaml"
    observation_path.write_text(yaml.safe_dump(_observation().model_dump(mode="json")), encoding="utf-8")

    assert physicsguard_main(["task-model", "plan", str(plan_path)]) == 0
    plan_output = json.loads(capsys.readouterr().out)
    assert plan_output["ranked_observation_candidates"][0]["candidate_id"] == "discriminating"
    assert physicsguard_main(["task-model", "observe", str(plan_path), str(observation_path)]) == 0
    observe_output = json.loads(capsys.readouterr().out)
    assert observe_output["terminal_reason"] == "continue_iteration"
