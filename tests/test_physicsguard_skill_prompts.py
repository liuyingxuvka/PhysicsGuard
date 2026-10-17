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

BLUEPRINT_ROUTE_EXPECTATIONS = {
    "physicsguard-candidate-model-blueprint": (
        "This route alone authors",
        {
            "physical_blueprint_review",
            "blueprint_fingerprint",
            "material_root_disposition",
            "native_execution_status",
            "deepest_licensed_layer",
            "first_gap",
            "safe_claim",
            "native_directory_dna_status",
            "in_memory_query_identity_and_gaps",
            "execution_claim_licensed",
        },
    ),
    "physicsguard-model-understanding-preflight": (
        "first useful understanding layer",
        {"blueprint_summary_inputs", "first_useful_layer"},
    ),
    "physicsguard-project-evidence-registry": (
        "exact blueprint element",
        {"affected_slice_fingerprint", "blueprint_binding_gaps"},
    ),
    "physicsguard-test-file-contract-review": (
        "exact blueprint input/output/state/effect ports",
        {"blueprint_interface_bindings", "affected_slice_fingerprint"},
    ),
    "physicsguard-signal-mapping-review": (
        "exact affected interface projection",
        {"affected_slice_fingerprint", "downstream_blueprint_consumers"},
    ),
    "physicsguard-model-dataset-validation": (
        "per blueprint element and obligation",
        {"per_blueprint_element_coverage", "affected_slice_fingerprint", "unsupported_claims"},
    ),
    "physicsguard-model-library": (
        "exact current blueprint fingerprint",
        {"selected_blueprint_fingerprints", "verified_reuse_limits"},
    ),
    "physicsguard-project-adoption": (
        "Blueprint adoption identity",
        {"blueprint_identity", "adoption_boundary"},
    ),
    "physicsguard-audit-closure": (
        "one current whole or affected",
        {
            "blueprint_scope_fingerprint",
            "blueprint_depth_and_first_gap",
            "in_memory_projection_identity",
            "in_memory_query_status",
            "current_execution_status",
            "execution_claim_licensed",
        },
    ),
    "physicsguard-ai-debugging": (
        "never authors or fully reviews",
        {"blueprint_trace_projection", "delegated_blueprint_owner"},
    ),
}

BLUEPRINT_PROJECTION_API_EXPECTATIONS = {
    "physicsguard-ai-debugging": {
        "affected_physical_blueprint_projection",
        "reverse_trace_physical_blueprint_projection",
    },
    "physicsguard-audit-closure": {
        "affected_physical_blueprint_projection",
        "full_physical_blueprint_projection",
    },
    "physicsguard-candidate-model-blueprint": {
        "summary_physical_blueprint_projection",
        "affected_physical_blueprint_projection",
        "reverse_trace_physical_blueprint_projection",
        "full_physical_blueprint_projection",
    },
    "physicsguard-model-dataset-validation": {
        "affected_physical_blueprint_projection",
        "full_physical_blueprint_projection",
    },
    "physicsguard-model-library": {
        "summary_physical_blueprint_projection",
        "affected_physical_blueprint_projection",
        "full_physical_blueprint_projection",
    },
    "physicsguard-model-understanding-preflight": {
        "summary_physical_blueprint_projection",
        "affected_physical_blueprint_projection",
    },
    "physicsguard-project-adoption": {
        "summary_physical_blueprint_projection",
    },
    "physicsguard-project-evidence-registry": {
        "summary_physical_blueprint_projection",
        "affected_physical_blueprint_projection",
        "full_physical_blueprint_projection",
    },
    "physicsguard-signal-mapping-review": {
        "affected_physical_blueprint_projection",
    },
    "physicsguard-test-file-contract-review": {
        "affected_physical_blueprint_projection",
    },
}


def _load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def test_exact_physicsguard_skill_inventory() -> None:
    actual = {path.parent.name for path in SKILL_ROOT.glob("*/SKILL.md")}
    assert actual == EXPECTED_SKILLS

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
def test_skill_prompt_requires_receipt_derived_task_model_closure(skill_id: str) -> None:
    skill_dir = SKILL_ROOT / skill_id
    prompt = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
    depth = (skill_dir / "references" / "native-depth-and-purpose.md").read_text(
        encoding="utf-8"
    )
    capsule = _load_json(skill_dir / "references" / "route-capsule.json")

    assert len(prompt.encode("utf-8")) <= 6_000
    assert "references/native-depth-and-purpose.md" in prompt
    assert "references/template-pack-routing.md" in prompt
    assert "BEGIN MANAGED VALIDATED TEMPLATE PACK" not in prompt
    assert "BEGIN MANAGED PURPOSE AND BLOCKABILITY" not in prompt
    assert "### Strict task-local model deepening" in depth
    assert str(capsule["native_owner_id"]) in prompt
    assert str(capsule["native_route_id"]) in prompt
    assert "exactly six families" in depth
    assert "AI prose" in depth
    assert "model_miss" in depth
    assert "one independent holdout receipt" in depth
    assert "Renaming or deleting a caller gap is not progress" in depth
    assert "model_closed_for_task" in depth
    assert capsule["target_skill_id"] == skill_id




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
def test_each_skill_has_one_route_owned_blueprint_projection_contract(
    skill_id: str,
) -> None:
    skill_dir = SKILL_ROOT / skill_id
    prompt = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
    protocol = (skill_dir / "references" / "native-route-protocol.md").read_text(
        encoding="utf-8"
    )
    capsule = _load_json(skill_dir / "references" / "route-capsule.json")
    expected_phrase, expected_outputs = BLUEPRINT_ROUTE_EXPECTATIONS[skill_id]

    assert expected_phrase in protocol
    assert expected_outputs <= set(capsule["required_outputs"])
    assert "fallback" in (prompt + protocol).lower()
    assert capsule["initial_load"] == [
        "agents/openai.yaml",
        "SKILL.md",
        "references/route-capsule.json",
    ]
    native_reference = next(
        row
        for row in capsule["conditional_references"]
        if row["path"] == "references/native-route-protocol.md"
    )
    assert any("blueprint" in trigger for trigger in native_reference["load_when"])
    assert any("blueprint" in role for role in native_reference["required_for"])
    for api_name in BLUEPRINT_PROJECTION_API_EXPECTATIONS[skill_id]:
        assert f"physicsguard.{api_name}" in protocol


def test_candidate_is_the_only_full_blueprint_author_or_reviewer() -> None:
    canonical_command = (
        "python -m physicsguard.cli blueprint review BLUEPRINT "
        "--target-authority AUTHORITY --pretty"
    )
    for skill_id in sorted(EXPECTED_SKILLS):
        prompt = (SKILL_ROOT / skill_id / "SKILL.md").read_text(encoding="utf-8")
        if skill_id == "physicsguard-candidate-model-blueprint":
            assert "sole PhysicsGuard route" in prompt
            protocol = (
                SKILL_ROOT
                / skill_id
                / "references"
                / "native-route-protocol.md"
            ).read_text(encoding="utf-8")
            assert canonical_command in prompt
            assert canonical_command in protocol
            assert (
                "python -m physicsguard.cli blueprint review BLUEPRINT --pretty"
                not in prompt + protocol
            )
        else:
            assert "sole PhysicsGuard route" not in prompt
            assert "does not author" in prompt.lower() or "never author" in prompt.lower()


def test_candidate_protocol_exposes_material_fmi_and_native_directory_boundaries() -> None:
    protocol = (
        SKILL_ROOT
        / "physicsguard-candidate-model-blueprint"
        / "references"
        / "native-route-protocol.md"
    ).read_text(encoding="utf-8")

    for token in (
        "blueprint_directory",
        "explicit_material_root",
        "--material-root ROOT",
        "external_resource_not_run",
        "native_execution_status=not_run",
        "physicsguard.fmi-observation-request.v1",
        "restricted source-independent oracle",
        "native directory stays authoritative",
        "no standalone bundle is written",
        "one selector",
        "identity-only gaps",
        "execution_claim_licensed=false",
    ):
        assert token in protocol


def test_audit_protocol_keeps_in_memory_projection_separate_from_current_execution() -> None:
    protocol = (
        SKILL_ROOT
        / "physicsguard-audit-closure"
        / "references"
        / "native-route-protocol.md"
    ).read_text(encoding="utf-8")

    for token in (
        "in-memory projection",
        "identity-only gap",
        "current_execution_status=not_run",
        "execution_claim_licensed=false",
    ):
        assert token in protocol
