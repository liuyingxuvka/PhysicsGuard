from __future__ import annotations

from pathlib import Path

from physicsguard.core.diagnosability import evaluate_diagnosability, evaluate_interval_residual
from physicsguard.io.test_file_contract_loader import load_yaml_mapping
from physicsguard.schema.diagnosability import DiagnosabilityRequestSpec, IntervalResidualSpec
from physicsguard.workflow import review_external_model_intake, review_model_understanding_preflight


ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = ROOT / "skill"


def test_skill_preflight_and_intake_templates_pass_their_reviews() -> None:
    for skill in ("physicsguard-ai-debugging", "physicsguard-model-understanding-preflight"):
        review = review_model_understanding_preflight(SKILL_ROOT / skill / "references/templates/model_understanding_preflight.yaml")
        assert review.status == "pass"
    for skill in ("physicsguard-ai-debugging", "physicsguard-signal-mapping-review"):
        review = review_external_model_intake(SKILL_ROOT / skill / "references/templates/external_model_intake.yaml")
        assert review.status == "pass"


def test_skill_task_model_templates_are_valid_inputs() -> None:
    templates = SKILL_ROOT / "physicsguard-ai-debugging" / "references" / "templates"
    residual = IntervalResidualSpec.model_validate(load_yaml_mapping(templates / "interval_residual.yaml"))
    assert evaluate_interval_residual(residual)["status"] == "robust_pass"
    request = DiagnosabilityRequestSpec.model_validate(load_yaml_mapping(templates / "diagnosability_request.yaml"))
    assert evaluate_diagnosability(request)["status"] == "isolable"
