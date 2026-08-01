from __future__ import annotations

import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = ROOT / "skill"

EXPECTED_SKILLS = {
    "physicsguard-ai-debugging",
    "physicsguard-audit-closure",
    "physicsguard-candidate-model-blueprint",
    "physicsguard-model-dataset-validation",
    "physicsguard-model-library",
    "physicsguard-model-understanding-preflight",
    "physicsguard-project-adoption",
    "physicsguard-project-evidence-registry",
    "physicsguard-signal-mapping-review",
    "physicsguard-test-file-contract-review",
}


def _load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def test_exact_physicsguard_skill_inventory() -> None:
    actual = {path.parent.name for path in SKILL_ROOT.glob("*/SKILL.md")}
    assert actual == EXPECTED_SKILLS

@pytest.mark.parametrize(
    "skill_id",
    sorted(EXPECTED_SKILLS),
    ids=lambda value: value.replace("-", "_"),
)
def test_skill_prompt_requires_receipt_derived_task_model_closure(skill_id: str) -> None:
    skill_dir = SKILL_ROOT / skill_id
    prompt = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
    depth = (skill_dir / "references" / "native-depth-and-purpose.md").read_text(
        encoding="utf-8"
    )
    capsule = _load_json(skill_dir / "references" / "route-capsule.json")
    guard_contract = _load_json(skill_dir / "guard-model" / "contract.json")

    assert len(prompt.encode("utf-8")) <= 6_000
    assert "references/native-depth-and-purpose.md" in prompt
    assert "references/template-pack-routing.md" in prompt
    assert "BEGIN MANAGED VALIDATED TEMPLATE PACK" not in prompt
    assert "BEGIN MANAGED PURPOSE AND BLOCKABILITY" not in prompt
    assert "### Strict task-local model deepening" in depth
    assert str(guard_contract["native_owner_id"]) in prompt
    assert str(guard_contract["native_route_id"]) in prompt
    assert f"check:{skill_id}:task-local-model-deepening" in depth
    assert "exactly six families" in depth
    assert "AI prose" in depth
    assert "model_miss" in depth
    assert "one independent holdout receipt" in depth
    assert "Renaming or deleting a caller gap is not progress" in depth
    assert "model_closed_for_task" in depth
    assert capsule["target_skill_id"] == skill_id
    assert capsule["native_owner_id"] == guard_contract["native_owner_id"]
    assert capsule["native_route_id"] == guard_contract["native_route_id"]


@pytest.mark.parametrize(
    "skill_id",
    sorted(EXPECTED_SKILLS),
    ids=lambda value: value.replace("-", "_"),
)
def test_skill_author_contract_supervises_the_strict_task_model_check(
    skill_id: str,
) -> None:
    contract = _load_json(
        SKILL_ROOT / skill_id / ".skillguard" / "contract-source.json"
    )
    task_check_id = f"check:{skill_id}:task-local-model-deepening"
    task_obligation_id = f"obligation:{skill_id}:task-local-model-deepening"

    checks = {str(row["check_id"]): row for row in contract["checks"]}
    assert task_check_id in checks
    task_check = checks[task_check_id]
    assert task_check["covers_obligation_ids"] == [task_obligation_id]
    assert task_check["evidence_class"] == "hard"
    assert task_check["execution_owner_id"] == (
        f"owner:{skill_id}:task-local-model-deepening"
    )
    assert task_check["args"] == [
        "-m",
        "pytest",
        "tests/test_task_local_revision.py",
        "tests/test_physicsguard_skill_prompts.py",
        "tests/test_physicsguard_skill_entry_loading.py",
        "-q",
        "-k",
        f"test_task_local_revision or {skill_id.replace('-', '_')}",
    ]
    selected_paths = {
        str(row["path"])
        for row in task_check["input_selectors"]
        if row.get("kind") == "path"
    }
    assert f"skill/{skill_id}/SKILL.md" in selected_paths
    assert f"skill/{skill_id}/agents/openai.yaml" in selected_paths
    assert f"skill/{skill_id}/references/route-capsule.json" in selected_paths
    assert f"skill/{skill_id}/references/native-route-protocol.md" in selected_paths
    assert f"skill/{skill_id}/references/native-depth-and-purpose.md" in selected_paths
    assert f"skill/{skill_id}/references/template-pack-routing.md" in selected_paths
    assert f"skill/{skill_id}/.skillguard/contract-source.json" in selected_paths
    assert ".flowguard/physicsguard_skill_prompt_load_graph.json" in selected_paths
    assert ".flowguard/check_physicsguard_skill_suite_mesh.py" in selected_paths
    assert "tests/test_physicsguard_skill_entry_loading.py" in selected_paths
    assert not any(
        path.startswith("skill/")
        and not path.startswith(f"skill/{skill_id}/")
        for path in selected_paths
    )
    enforced = next(
        row for row in contract["closure_profiles"] if row["profile_id"] == "enforced"
    )
    assert task_obligation_id in enforced["required_obligation_ids"]

    profile = contract["depth_profile"]
    assert profile["profile_id"] == f"profile:{skill_id}:current-closure"
    assert task_check_id in profile["native_check_ids"]
    assert profile["model_deepening_check_id"] == task_check_id

    steps = {str(row["step_id"]): row for row in contract["step_bindings"]}
    step_id = f"step:{skill_id}:task-local-model-deepening"
    assert steps[step_id]["check_ids"] == [task_check_id]
