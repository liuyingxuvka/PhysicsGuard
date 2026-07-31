from __future__ import annotations

import json

from physicsguard.cli import main
from physicsguard.core.diagnosability import (
    evaluate_diagnosability,
    evaluate_interval_residual,
)
from physicsguard.schema.diagnosability import (
    DiagnosabilityRequestSpec,
    IntervalResidualSpec,
)


def test_interval_residual_preserves_robust_statuses() -> None:
    robust_pass = evaluate_interval_residual(
        IntervalResidualSpec.model_validate(
            {
                "residual_id": "r1",
                "observed": {"lower": -0.2, "upper": 0.4},
                "acceptable": {"lower": -1.0, "upper": 1.0},
                "source_ref": "test:interval",
            }
        )
    )
    indeterminate = evaluate_interval_residual(
        IntervalResidualSpec.model_validate(
            {
                "residual_id": "r2",
                "observed": {"lower": 0.5, "upper": 1.5},
                "acceptable": {"lower": -1.0, "upper": 1.0},
                "source_ref": "test:interval",
            }
        )
    )
    robust_fail = evaluate_interval_residual(
        IntervalResidualSpec.model_validate(
            {
                "residual_id": "r3",
                "observed": {"lower": 1.2, "upper": 1.5},
                "acceptable": {"lower": -1.0, "upper": 1.0},
                "source_ref": "test:interval",
            }
        )
    )
    not_run = evaluate_interval_residual(
        IntervalResidualSpec.model_validate(
            {
                "residual_id": "r4",
                "observed": None,
                "acceptable": {"lower": -1.0, "upper": 1.0},
                "source_ref": "test:interval",
            }
        )
    )
    assert robust_pass["status"] == "robust_pass"
    assert indeterminate["status"] == "indeterminate"
    assert robust_fail["status"] == "robust_fail"
    assert not_run["status"] == "not_run"


def _request() -> DiagnosabilityRequestSpec:
    return DiagnosabilityRequestSpec.model_validate(
        {
            "diagnosis_id": "pump-diagnosis",
            "fault_signatures": [
                {
                    "hypothesis_id": "gain",
                    "predicted_intervals": {
                        "speed": {"lower": 9.0, "upper": 11.0},
                        "current": {"lower": 4.0, "upper": 5.0},
                    },
                },
                {
                    "hypothesis_id": "mapping",
                    "predicted_intervals": {
                        "speed": {"lower": -11.0, "upper": -9.0},
                        "current": {"lower": 4.5, "upper": 5.5},
                    },
                },
                {
                    "hypothesis_id": "sensor",
                    "predicted_intervals": {
                        "speed": {"lower": 9.5, "upper": 10.5},
                        "current": {"lower": 7.0, "upper": 8.0},
                    },
                },
            ],
            "available_signal_ids": ["current", "speed"],
        }
    )


def test_diagnosability_reports_pairwise_evidence_and_next_signal() -> None:
    result = evaluate_diagnosability(_request())
    assert result["status"] == "isolable"
    assert result["recommended_next_signal_id"] == "current"
    assert result["unresolved_hypothesis_pairs"] == []
    assert {
        row["status"] for row in result["pairwise_diagnosability"]
    } == {"distinguishable"}


def test_observation_rejects_incompatible_signature() -> None:
    payload = _request().model_dump(mode="json")
    payload["observed_signals"] = {
        "speed": {"lower": 9.8, "upper": 10.2},
    }
    request = DiagnosabilityRequestSpec.model_validate(payload)
    result = evaluate_diagnosability(request)
    assert result["rejected_hypothesis_ids"] == ["mapping"]
    assert result["viable_hypothesis_ids"] == ["gain", "sensor"]


def test_task_model_diagnose_cli(tmp_path, capsys) -> None:
    path = tmp_path / "diagnosis.yaml"
    path.write_text(
        json.dumps(_request().model_dump(mode="json")),
        encoding="utf-8",
    )
    assert main(["task-model", "diagnose", str(path)]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "isolable"
