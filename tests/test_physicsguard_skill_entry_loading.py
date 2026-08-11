from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest
import yaml

from scripts import upgrade_purpose_contracts as purpose_contract_generator


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
EXPECTED_OPENAI_DEFAULT_PROMPTS = {
    "physicsguard-candidate-model-blueprint": "Use $physicsguard-candidate-model-blueprint as the sole PhysicalModelBlueprint author/full reviewer; resolve blueprint_directory versus explicit_material_root and --material-root, run the canonical review, and compose only an in-memory selector when explicitly requested while keeping identity gaps and native execution separate.",
    "physicsguard-model-understanding-preflight": "Use $physicsguard-model-understanding-preflight directly to freeze target identity, boundary, inventory providers, capabilities, and the first useful blueprint layer; consume only the current summary or affected slice and do not claim full blueprint qualification.",
    "physicsguard-project-evidence-registry": "Use $physicsguard-project-evidence-registry directly; bind current evidence/resource identities and freshness to exact blueprint elements in the summary or affected slice, and return missing or stale gaps without a project-wide pass.",
    "physicsguard-test-file-contract-review": "Use $physicsguard-test-file-contract-review directly; bind deterministic files, fields, datasets, and testbench I/O to the exact affected blueprint interfaces, state, obligations, and evidence, with no full-blueprint fallback.",
    "physicsguard-signal-mapping-review": "Use $physicsguard-signal-mapping-review directly on the exact affected interface slice; validate source/target identity, units, frames, conversion, time semantics, revision, evidence, and downstream blueprint consumers.",
    "physicsguard-model-dataset-validation": "Use $physicsguard-model-dataset-validation directly; consume the current affected or whole blueprint projection and report per-element obligations, validation modes, validity, residual/oracle, evidence fingerprints, and unsupported claims.",
    "physicsguard-model-library": "Use $physicsguard-model-library directly; index or select assets by current blueprint fingerprint, obligation, profile, validity boundary, testbench, receipt, and verified reuse limits, never by loose similarity.",
    "physicsguard-project-adoption": "Use $physicsguard-project-adoption directly; record the current blueprint identity, target scope, artifact-root meaning, native authorities, and projection kind while keeping adoption separate from completeness or physical truth.",
    "physicsguard-audit-closure": "Use $physicsguard-audit-closure directly; consume the exact whole or affected review and any in-memory projection status, preserve identity-only gaps, and keep interpretation separate from current native execution and closure.",
    "physicsguard-ai-debugging": "Use $physicsguard-ai-debugging only for genuinely mixed routing; consume current blueprint summary/affected/reverse trace, delegate to the minimum direct owners, and never become a second blueprint author or reviewer.",
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


def _current_toolchain_identity() -> dict[str, str]:
    return purpose_contract_generator.current_toolchain_identity(
        repository_root=ROOT,
        flowguard_project_path=ROOT / ".flowguard" / "project.toml",
    )


@pytest.mark.parametrize(
    "skill_id",
    [
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
    ],
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
    [
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
    ],
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
    [
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
    ],
)
def test_openai_metadata_invokes_only_the_selected_direct_skill(skill_id: str) -> None:
    metadata = yaml.safe_load(
        (SKILL_ROOT / skill_id / "agents" / "openai.yaml").read_text(encoding="utf-8")
    )
    interface = metadata["interface"]
    assert 25 <= len(interface["short_description"]) <= 64
    assert interface["default_prompt"] == EXPECTED_OPENAI_DEFAULT_PROMPTS[skill_id]
    if skill_id != "physicsguard-ai-debugging":
        assert "$physicsguard-ai-debugging" not in interface["default_prompt"]


def test_prompt_load_graph_and_all_known_bads() -> None:
    checker = _load_checker()
    graph = _load_json(GRAPH_PATH)
    expected_toolchain_identity = _current_toolchain_identity()
    report = checker.check_prompt_load_graph(graph)
    assert report["structure_status"] == "pass", report["findings"]
    assert report["route_count"] == 10
    assert graph["suite_version"] == expected_toolchain_identity["physicsguard_version"]
    assert graph["toolchain_identity"] == expected_toolchain_identity
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
