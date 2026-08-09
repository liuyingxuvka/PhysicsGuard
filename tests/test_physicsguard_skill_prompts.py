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
            "portable_bundle_status_and_identity",
            "portable_query_identity_and_gaps",
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
            "portable_bundle_identity",
            "portable_query_status",
            "frozen_case_status",
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
        "query_physical_blueprint_export_bundle",
    },
    "physicsguard-candidate-model-blueprint": {
        "summary_physical_blueprint_projection",
        "affected_physical_blueprint_projection",
        "reverse_trace_physical_blueprint_projection",
        "full_physical_blueprint_projection",
        "build_physical_blueprint_export_bundle",
        "materialize_physical_blueprint_export_bundle",
        "query_physical_blueprint_export_bundle",
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
    args = task_check["args"]
    assert args[:7] == [
        "-m",
        "pytest",
        "tests/test_task_local_revision.py",
        "tests/test_physicsguard_skill_prompts.py",
        "tests/test_physicsguard_skill_entry_loading.py",
        "tests/test_skill_execution_depth.py",
        "tests/test_physicsguard_skill_blueprint_contracts.py",
    ]
    route_tests = args[7:-3]
    assert all(path.startswith("tests/") and path.endswith(".py") for path in route_tests)
    assert args[-3:] == [
        "-q",
        "-k",
        " or ".join(
            (
                "test_task_local_revision",
                skill_id.replace("-", "_"),
                *(path.removeprefix("tests/").removesuffix(".py") for path in route_tests),
            )
        ),
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
    assert "tests/test_skill_execution_depth.py" in selected_paths
    assert "tests/test_physicsguard_skill_blueprint_contracts.py" in selected_paths
    assert "src/physicsguard/core/physical_blueprint_trace.py" in selected_paths
    assert "src/physicsguard/schema/physical_model_blueprint.py" in selected_paths
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


def test_candidate_protocol_exposes_material_fmi_and_portable_boundaries() -> None:
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
        "blueprint bundle-export",
        "blueprint bundle-query",
        "exactly one deep selector",
        "observed_at_export_unlicensed",
        "portable_query_identity_only_terminal",
        "execution_claim_licensed=false",
    ):
        assert token in protocol


def test_audit_protocol_keeps_frozen_bundle_separate_from_current_execution() -> None:
    protocol = (
        SKILL_ROOT
        / "physicsguard-audit-closure"
        / "references"
        / "native-route-protocol.md"
    ).read_text(encoding="utf-8")

    for token in (
        "query_physical_blueprint_export_bundle",
        "observed_at_export_unlicensed",
        "portable_query_identity_only_terminal",
        "frozen_case_status=pass",
        "current_execution_status=not_run",
        "execution_claim_licensed=false",
    ):
        assert token in protocol
