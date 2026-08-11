from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil

import pytest

from physicsguard.guard_model_contract import (
    GuardModelContractError,
    validate_baseline_bundle,
    validate_baseline_contract_bundle,
)
from physicsguard.skill_execution_depth import ROUTE_POLICIES


ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = ROOT / "skill"
CANONICAL_REVIEW_OPERATION = (
    "command:python -m physicsguard.cli blueprint review BLUEPRINT "
    "--target-authority AUTHORITY --pretty"
)
BLUEPRINT_RUNTIME_INPUTS = {
    "src/physicsguard/schema/physical_model_blueprint.py",
    "src/physicsguard/core/physical_model_blueprint.py",
    "src/physicsguard/core/physical_blueprint_trace.py",
    "src/physicsguard/core/target_inventory_authority.py",
    "src/physicsguard/io/physical_model_blueprint_loader.py",
}
BLUEPRINT_TEST_INPUTS = {
    "tests/fixtures/physicsguard_skill_execution_cases.json",
    "tests/test_physicsguard_skill_blueprint_contracts.py",
    "tests/test_skill_execution_depth.py",
}
BLUEPRINT_BLOCK_CODES = {
    "blueprint_projection_missing_stale_foreign_or_ambiguous",
    "blueprint_authority_boundary_violated",
    "blueprint_required_obligation_unproved",
    "blueprint_gap_or_claim_boundary_unreconciled",
}
ROUTE_SPECIFIC_BLUEPRINT_BLOCK_CODES = {
    "physicsguard-candidate-model-blueprint": {
        "blueprint_material_root_boundary_violated",
        "blueprint_fmi_oracle_independence_violated",
        "blueprint_projection_execution_promoted",
    },
    "physicsguard-audit-closure": {
        "blueprint_projection_promoted_to_closure",
        "blueprint_identity_only_terminal_promoted",
    },
}
ROUTE_SPECIFIC_BLUEPRINT_INPUTS = {
    "physicsguard-candidate-model-blueprint": {
        "src/physicsguard/core/physical_model_blueprint_adapters.py",
        "src/physicsguard/schema/fmi_observation.py",
        "src/physicsguard/core/fmi_observation.py",
        "templates/physical_model_blueprint.yaml",
        "tests/fixtures/physical_model_blueprint/canonical_minimal.json",
        "tests/fixtures/physical_model_blueprint/canonical_minimal.yaml",
        "examples/testfile_contracts/pump_loop/pump_loop_physical_blueprint.yaml",
        "examples/testfile_contracts/pump_loop/pump_loop_target_material.json",
        "tests/test_physical_blueprint_impact_trace.py",
        "tests/test_physical_model_blueprint_bad_cases.py",
        "tests/test_physical_model_blueprint_cli.py",
        "tests/test_physical_model_blueprint_external_target.py",
        "tests/test_physical_model_blueprint_native_authorities.py",
        "tests/test_physical_model_blueprint_provider_neutral.py",
        "tests/test_physical_model_blueprint_review.py",
        "tests/test_physical_model_blueprint_schema.py",
        "tests/test_physical_model_blueprint_target_authority.py",
        "tests/test_fmi_observation.py",
        "tests/test_reference_fmus_bouncing_ball_example.py",
    },
    "physicsguard-signal-mapping-review": {
        "src/physicsguard/schema/signal_mapping.py",
        "src/physicsguard/core/signal_mapping.py",
        "templates/parameter_mapping_edges.yaml",
        "examples/testfile_contracts/pump_loop/coverage/pump_loop_mapping_edges.yaml",
        "tests/test_signal_mapping_ledger.py",
    },
    "physicsguard-project-evidence-registry": {
        "src/physicsguard/schema/project_evidence.py",
        "src/physicsguard/core/project_evidence.py",
        "templates/project_evidence_registry.yaml",
        "examples/testfile_contracts/pump_loop/evidence/project_evidence_registry.yaml",
        "tests/test_project_evidence_registry.py",
    },
    "physicsguard-model-dataset-validation": {
        "src/physicsguard/schema/model_dataset_validation.py",
        "src/physicsguard/core/model_dataset_validation.py",
        "src/physicsguard/schema/validation_adequacy.py",
        "src/physicsguard/core/validation_adequacy.py",
        "src/physicsguard/schema/validation_depth.py",
        "src/physicsguard/core/validation_depth.py",
        "src/physicsguard/schema/evidence_mesh.py",
        "src/physicsguard/core/evidence_mesh.py",
        "tests/test_model_dataset_validation.py",
        "tests/test_validation_adequacy.py",
        "tests/test_validation_depth_receipts.py",
        "tests/test_evidence_mesh.py",
        "tests/test_predictive_rollout_validation.py",
    },
    "physicsguard-audit-closure": {
        "tests/test_reference_fmus_bouncing_ball_example.py",
        "tests/test_validation_blueprint_coverage.py",
    },
}


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _fingerprint(value: object) -> str:
    payload = (json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n").encode(
        "utf-8"
    )
    return hashlib.sha256(payload).hexdigest().upper()


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
def test_each_skill_guard_model_binds_its_native_blueprint_contract(
    skill_id: str,
) -> None:
    skill_root = SKILL_ROOT / skill_id
    policy = ROUTE_POLICIES[skill_id]
    contract = _load(skill_root / "guard-model" / "contract.json")
    candidate = _load(skill_root / "guard-model" / "candidate.json")
    oracles = _load(skill_root / "guard-model" / "oracles.json")
    known_good = _load(skill_root / "guard-model" / "known-good.json")
    known_bad = _load(skill_root / "guard-model" / "known-bad.json")

    blueprint = contract["blueprint_route_contract"]
    fingerprint = _fingerprint(blueprint)
    assert contract["blueprint_route_contract_fingerprint"] == fingerprint
    assert blueprint["authority_mode"] == policy.blueprint_authority_mode
    assert blueprint["projection_kinds"] == list(policy.blueprint_projection_kinds)
    assert blueprint["required_operation_ids"] == list(
        policy.blueprint_required_operation_ids
    )
    assert blueprint["required_obligation_ids"] == list(
        policy.blueprint_required_obligation_ids
    )
    assert blueprint["self_reported_status_allowed"] is False
    assert blueprint["missing_projection_behavior"] == "block_visible_no_fallback"
    expected_block_codes = BLUEPRINT_BLOCK_CODES | ROUTE_SPECIFIC_BLUEPRINT_BLOCK_CODES.get(
        skill_id, set()
    )
    assert {row["finding_code"] for row in blueprint["block_on"]} == expected_block_codes

    expected_projection = {
        "authority_mode": policy.blueprint_authority_mode,
        "projection_kinds": list(policy.blueprint_projection_kinds),
        "required_operation_ids": list(policy.blueprint_required_operation_ids),
        "required_obligation_ids": list(policy.blueprint_required_obligation_ids),
        "claim_boundary": blueprint["claim_boundary"],
    }
    assert candidate["blueprint_route_contract_fingerprint"] == fingerprint
    assert candidate["blueprint_projection_contract"] == expected_projection
    assert candidate["candidate_definition"][
        "blueprint_route_contract_fingerprint"
    ] == fingerprint

    assert oracles["blueprint_route_contract_fingerprint"] == fingerprint
    assert {
        row["obligation_id"] for row in oracles["blueprint_oracles"]
    } == set(policy.blueprint_required_obligation_ids)
    assert {
        row["predicate_kind"] for row in oracles["blueprint_oracles"]
    } == {"native_blueprint_obligation_must_pass"}

    assert known_good["blueprint_route_contract_fingerprint"] == fingerprint
    assert known_good["covered_blueprint_obligation_ids"] == list(
        policy.blueprint_required_obligation_ids
    )
    assert known_good["covered_blueprint_projection_kinds"] == list(
        policy.blueprint_projection_kinds
    )
    assert known_good["executed_blueprint_operation_ids"] == list(
        policy.blueprint_required_operation_ids
    )
    assert known_good["self_reported_outcome_allowed"] is False

    assert known_bad["blueprint_route_contract_fingerprint"] == fingerprint
    assert {
        row["expected_finding_code"] for row in known_bad["blueprint_cases"]
    } == expected_block_codes
    assert all(
        row["expected_native_status"] == "blocked"
        and row["self_reported_outcome_allowed"] is False
        for row in known_bad["blueprint_cases"]
    )

    if skill_id == "physicsguard-candidate-model-blueprint":
        assert policy.blueprint_authority_mode == "sole_author_full_reviewer"
        assert CANONICAL_REVIEW_OPERATION in policy.blueprint_required_operation_ids
        assert set(policy.blueprint_projection_kinds) == {
            "summary",
            "affected",
            "reverse_trace",
            "full",
        }
        assert {
            "schema:physicsguard.fmi-observation-request.v1",
        } <= set(policy.blueprint_required_operation_ids)
        assert {
            "blueprint_material_root_resolution",
            "blueprint_external_resource_not_run_boundary",
            "blueprint_generic_fmi_observation_and_independent_oracle",
            "blueprint_native_directory_dna_identity",
            "blueprint_in_memory_compact_or_single_selector",
            "blueprint_in_memory_execution_claim_boundary",
        } <= set(policy.blueprint_required_obligation_ids)
    elif skill_id == "physicsguard-audit-closure":
        assert {
            "blueprint_in_memory_projection_identity_consumption",
            "blueprint_identity_only_terminal_accounting",
            "blueprint_in_memory_execution_claim_boundary",
        } <= set(policy.blueprint_required_obligation_ids)
    else:
        assert policy.blueprint_authority_mode == "consumer_only"
        assert CANONICAL_REVIEW_OPERATION not in policy.blueprint_required_operation_ids

    validated = validate_baseline_bundle(skill_root)
    assert validated["blueprint_route_contract_fingerprint"] == fingerprint


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
def test_each_skillguard_component_map_has_exact_blueprint_owners(
    skill_id: str,
) -> None:
    source = _load(SKILL_ROOT / skill_id / ".skillguard" / "contract-source.json")
    checks = {row["check_id"]: row for row in source["checks"]}
    contract_check = checks[f"check:{skill_id}:family-baseline-contract"]
    task_check = checks[f"check:{skill_id}:task-local-model-deepening"]

    contract_paths = {
        row["path"]
        for row in contract_check["input_selectors"]
        if row.get("kind") == "path"
    }
    task_paths = {
        row["path"]
        for row in task_check["input_selectors"]
        if row.get("kind") == "path"
    }
    assert BLUEPRINT_RUNTIME_INPUTS <= contract_paths
    assert BLUEPRINT_RUNTIME_INPUTS <= task_paths
    assert BLUEPRINT_TEST_INPUTS <= task_paths
    route_paths = ROUTE_SPECIFIC_BLUEPRINT_INPUTS.get(skill_id, set())
    assert route_paths <= task_paths
    assert {
        f"skill/{skill_id}/SKILL.md",
        f"skill/{skill_id}/agents/openai.yaml",
        f"skill/{skill_id}/references/route-capsule.json",
        f"skill/{skill_id}/references/native-route-protocol.md",
        f"skill/{skill_id}/references/native-depth-and-purpose.md",
        f"skill/{skill_id}/.skillguard/contract-source.json",
    } <= task_paths
    assert task_check["execution_owner_id"] == (
        f"owner:{skill_id}:task-local-model-deepening"
    )
    assert BLUEPRINT_RUNTIME_INPUTS | BLUEPRINT_TEST_INPUTS | route_paths <= set(
        source["implementation_paths"]
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
def test_blueprint_guard_contract_mutation_blocks_without_self_report_fallback(
    skill_id: str,
    tmp_path: Path,
) -> None:
    copied = tmp_path / skill_id
    shutil.copytree(SKILL_ROOT / skill_id, copied)
    known_bad_path = copied / "guard-model" / "known-bad.json"
    known_bad = _load(known_bad_path)
    known_bad["blueprint_cases"][0]["self_reported_outcome_allowed"] = True
    known_bad_path.write_text(json.dumps(known_bad), encoding="utf-8")

    with pytest.raises(GuardModelContractError, match="blueprint_known_bad_case_invalid"):
        validate_baseline_contract_bundle(copied)
