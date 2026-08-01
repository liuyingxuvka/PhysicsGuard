from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = ROOT / "skill"
GRAPH_PATH = ROOT / ".flowguard" / "physicsguard_skill_prompt_load_graph.json"
CHECKER_PATH = ROOT / ".flowguard" / "check_physicsguard_skill_suite_mesh.py"
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
EXPECTED_TOOLCHAIN_IDENTITY = {
    "physicsguard_version": "0.15.1",
    "flowguard_version": "0.68.2",
    "flowguard_schema_version": "1.0",
    "skillguard_version": "0.7.2",
}
DEEP_TOKENS = (
    "exactly six families",
    "execution depth, mapping, residual, uncertainty, diagnosability, and predictive rollout",
    "Freeze the prediction before observation",
    "model_miss",
    "one independent holdout receipt",
    "one predictive-rollout receipt",
    "model_closed_for_task",
    "external_input_required",
    "progress_stalled",
    "iteration_limit",
    "scope_excluded",
)


def _load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_checker():
    spec = importlib.util.spec_from_file_location("physicsguard_skill_mesh_checker", CHECKER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    "skill_id",
    sorted(EXPECTED_SKILLS),
    ids=lambda value: value.replace("-", "_"),
)
def test_route_capsule_is_direct_current_and_prompt_is_compact(skill_id: str) -> None:
    skill_root = SKILL_ROOT / skill_id
    prompt_path = skill_root / "SKILL.md"
    capsule = _load_json(skill_root / "references" / "route-capsule.json")
    contract = _load_json(skill_root / "guard-model" / "contract.json")

    assert capsule["schema_version"] == "physicsguard.skill_route_capsule.v1"
    assert capsule["target_skill_id"] == skill_id
    assert capsule["native_owner_id"] == contract["native_owner_id"]
    assert capsule["native_route_id"] == contract["native_route_id"]
    assert capsule["route_role"] == (
        "composite" if skill_id == "physicsguard-ai-debugging" else "direct"
    )
    assert capsule["broad_route_prerequisite"] is False
    assert capsule["maximum_reference_depth"] == 1
    assert capsule["entry_prompt_sha256"] == _sha256(prompt_path)
    assert prompt_path.stat().st_size <= 6_000
    prompt = prompt_path.read_text(encoding="utf-8")
    assert "BEGIN MANAGED VALIDATED TEMPLATE PACK" not in prompt
    assert "BEGIN MANAGED PURPOSE AND BLOCKABILITY" not in prompt
    assert "references/route-capsule.json" in prompt
    assert "references/native-route-protocol.md" in prompt
    assert "references/native-depth-and-purpose.md" in prompt
    assert "references/template-pack-routing.md" in prompt


@pytest.mark.parametrize(
    "skill_id",
    sorted(EXPECTED_SKILLS),
    ids=lambda value: value.replace("-", "_"),
)
def test_conditional_references_are_current_and_preserve_deep_capability(skill_id: str) -> None:
    skill_root = SKILL_ROOT / skill_id
    capsule = _load_json(skill_root / "references" / "route-capsule.json")
    references = {
        str(row["path"]): row for row in capsule["conditional_references"]
    }
    assert set(references) == {
        "references/native-route-protocol.md",
        "references/native-depth-and-purpose.md",
        "references/template-pack-routing.md",
    }
    for relative, row in references.items():
        path = skill_root / relative
        assert path.is_file()
        assert row["sha256"] == _sha256(path)
        assert row["load_when"]

    depth = (skill_root / "references" / "native-depth-and-purpose.md").read_text(
        encoding="utf-8"
    )
    assert all(token in depth for token in DEEP_TOKENS)
    assert f"check:{skill_id}:task-local-model-deepening" in depth
    template = (skill_root / "references" / "template-pack-routing.md").read_text(
        encoding="utf-8"
    )
    assert "complete candidate and rejection accounting" in template
    assert "A preview is planning evidence, never domain proof" in template
    assert "harvest disposition" in template


@pytest.mark.parametrize(
    "skill_id",
    sorted(EXPECTED_SKILLS),
    ids=lambda value: value.replace("-", "_"),
)
def test_openai_metadata_invokes_only_the_selected_direct_skill(skill_id: str) -> None:
    metadata = yaml.safe_load(
        (SKILL_ROOT / skill_id / "agents" / "openai.yaml").read_text(encoding="utf-8")
    )
    interface = metadata["interface"]
    assert 25 <= len(interface["short_description"]) <= 64
    assert f"${skill_id}" in interface["default_prompt"]
    if skill_id != "physicsguard-ai-debugging":
        assert "$physicsguard-ai-debugging" not in interface["default_prompt"]


def test_prompt_load_graph_and_all_known_bads() -> None:
    checker = _load_checker()
    graph = _load_json(GRAPH_PATH)
    report = checker.check_prompt_load_graph(graph)
    assert report["structure_status"] == "pass", report["findings"]
    assert report["route_count"] == 10
    assert graph["suite_version"] == "0.15.1"
    assert graph["toolchain_identity"] == EXPECTED_TOOLCHAIN_IDENTITY
    known_bads = checker.prompt_load_known_bad_results(graph)
    assert set(known_bads) == set(graph["known_bad_cases"])
    assert set(known_bads.values()) == {"blocked"}


def test_clear_satellite_routes_do_not_require_composite_debugging() -> None:
    graph = _load_json(GRAPH_PATH)
    routes = {row["target_skill_id"]: row for row in graph["routes"]}
    assert routes["physicsguard-ai-debugging"]["route_role"] == "composite"
    for skill_id in sorted(EXPECTED_SKILLS - {"physicsguard-ai-debugging"}):
        route = routes[skill_id]
        assert route["route_role"] == "direct"
        assert route["broad_route_prerequisite"] is False
        assert route["selection_fixture"]["expected_skill_id"] == skill_id
        assert route["initial_paths"] == [
            f"skill/{skill_id}/agents/openai.yaml",
            f"skill/{skill_id}/SKILL.md",
            f"skill/{skill_id}/references/route-capsule.json",
        ]
