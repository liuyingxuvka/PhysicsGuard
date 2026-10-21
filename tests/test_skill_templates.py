from __future__ import annotations

from pathlib import Path

import shutil

from physicsguard.core.diagnosability import evaluate_diagnosability, evaluate_interval_residual
from physicsguard.core.task_local_revision import evaluate_hypothesis_observation, freeze_hypothesis_plan
from physicsguard.io.test_file_contract_loader import load_yaml_mapping
from physicsguard.schema.diagnosability import DiagnosabilityRequestSpec, IntervalResidualSpec
from physicsguard.schema.task_local_revision import DiagnosticObservationSpec, HypothesisPlanSpec
from physicsguard.workflow import review_external_model_intake, review_model_understanding_preflight


ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = ROOT / "skill"


def test_skill_preflight_and_intake_templates_pass_their_reviews() -> None:
    templates = SKILL_ROOT / "physicsguard" / "references" / "templates"
    assert review_model_understanding_preflight(templates / "model_understanding_preflight.yaml").status == "pass"
    assert review_external_model_intake(templates / "external_model_intake.yaml").status == "pass"


def test_skill_task_model_templates_are_valid_inputs() -> None:
    templates = SKILL_ROOT / "physicsguard" / "references" / "templates"
    residual = IntervalResidualSpec.model_validate(load_yaml_mapping(templates / "interval_residual.yaml"))
    assert evaluate_interval_residual(residual)["status"] == "robust_pass"
    request = DiagnosabilityRequestSpec.model_validate(load_yaml_mapping(templates / "diagnosability_request.yaml"))
    assert evaluate_diagnosability(request)["status"] == "isolable"


def test_skill_hypothesis_templates_block_until_the_model_path_is_real(tmp_path: Path) -> None:
    templates = SKILL_ROOT / "physicsguard" / "references" / "templates"
    plan = HypothesisPlanSpec.model_validate(load_yaml_mapping(templates / "hypothesis_plan.yaml"))
    assert freeze_hypothesis_plan(plan, base_dir=templates)["status"] == "blocked"
    shutil.copy(templates / "hypothesis_plan.yaml", tmp_path / "hypothesis_plan.yaml")
    (tmp_path / "AUDIT.yaml").write_text("system_name: example\n", encoding="utf-8")
    frozen = freeze_hypothesis_plan(plan, base_dir=tmp_path)
    assert frozen["status"] == "pass"
    assert frozen["ranked_observation_candidates"][0]["candidate_id"] == "speed_trend"
    observation = DiagnosticObservationSpec.model_validate(load_yaml_mapping(templates / "diagnostic_observation.yaml"))
    result = evaluate_hypothesis_observation(plan, observation, base_dir=tmp_path)
    assert {row["hypothesis_id"]: row["disposition"] for row in result["hypothesis_results"]} == {
        "gain": "supported",
        "mapping": "weakened",
    }
