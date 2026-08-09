from __future__ import annotations

import json
import hashlib
from pathlib import Path

import pytest
import yaml

from physicsguard.cli import main
from physicsguard.core.physical_blueprint_trace import (
    affected_physical_blueprint_projection,
    reverse_trace_physical_blueprint_projection,
)
from physicsguard.core.physical_model_blueprint import review_physical_model_blueprint
from physicsguard.io.physical_model_blueprint_loader import load_physical_model_blueprint
from physicsguard.schema.physical_model_blueprint import (
    TargetInventoryAuthority,
    canonical_blueprint_fingerprint,
    fingerprint_target_inventory_authority,
    fingerprint_target_inventory_execution,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
TARGET_ROOT = REPOSITORY_ROOT / "examples" / "testfile_contracts" / "pump_loop"
BLUEPRINT = TARGET_ROOT / "pump_loop_physical_blueprint.yaml"
TARGET_MATERIAL = TARGET_ROOT / "pump_loop_target_material.json"


def _authority_bundle(tmp_path: Path, blueprint):
    material_path = tmp_path / TARGET_MATERIAL.name
    material_bytes = TARGET_MATERIAL.read_bytes()
    material_path.write_bytes(material_bytes)
    material_sha256 = hashlib.sha256(material_bytes).hexdigest()
    material_request_id = json.loads(material_bytes)["request_id"]
    input_fingerprints = {"target_material": material_sha256}
    execution = {
        "execution_id": "execution.pump-loop-contract-fixture.target-inventory.r1",
        "owner_id": "physicsguard.target-material-inventory",
        "request_id": material_request_id,
        "input_reference_ids": ["target_material"],
        "target_system_id": blueprint.target.target_system_id,
        "subject_revision": blueprint.target.subject_revision,
        "adapter_tool_id": "physicsguard.target-material-inventory",
        "adapter_tool_version": "1",
        "result_status": "pass",
        "terminal_status": "success",
        "result_fingerprint": blueprint.inventory.inventory_fingerprint,
        "terminal_receipt_fingerprint": canonical_blueprint_fingerprint(
            {
                "execution_id": "execution.pump-loop-contract-fixture.target-inventory.r1",
                "owner_id": "physicsguard.target-material-inventory",
                "request_id": material_request_id,
                "input_fingerprints": input_fingerprints,
                "target_system_id": blueprint.target.target_system_id,
                "subject_revision": blueprint.target.subject_revision,
                "adapter_tool_id": "physicsguard.target-material-inventory",
                "adapter_tool_version": "1",
                "result_status": "pass",
                "terminal_status": "success",
                "result_fingerprint": blueprint.inventory.inventory_fingerprint,
            }
        ),
    }
    execution["execution_fingerprint"] = fingerprint_target_inventory_execution(
        execution
    )
    authority_data = {
        "schema_version": "physicsguard.target-inventory-authority.v1",
        "authority_id": "authority.pump-loop-contract-fixture.target-inventory.r1",
        "status": "current",
        "owner_id": "physicsguard.target-material-inventory",
        "request_id": material_request_id,
        "provider_id": blueprint.inventory.provider_id,
        "target_system_id": blueprint.target.target_system_id,
        "subject_revision": blueprint.target.subject_revision,
        "boundary_fingerprint": blueprint.target.boundary_fingerprint,
        "input_references": [
            {
                "reference_id": "target_material",
                "artifact": {
                    "repo_path": material_path.name,
                    "sha256": material_sha256,
                },
            }
        ],
        "inventory": blueprint.inventory.model_dump(mode="json", exclude_none=True),
        "execution": execution,
    }
    authority_data["authority_fingerprint"] = fingerprint_target_inventory_authority(
        authority_data
    )
    authority = TargetInventoryAuthority.model_validate(authority_data)
    authority_path = tmp_path / "pump_loop_target_inventory_authority.yaml"
    authority_path.write_text(
        yaml.safe_dump(authority.model_dump(mode="json", exclude_none=True), sort_keys=False),
        encoding="utf-8",
    )
    return authority, authority_path


def _reviewed_external_target(tmp_path: Path):
    blueprint = load_physical_model_blueprint(BLUEPRINT)
    authority, _ = _authority_bundle(tmp_path, blueprint)
    review = review_physical_model_blueprint(
        blueprint,
        target_inventory_authority=authority,
        base_dir=BLUEPRINT.parent,
        authority_base_dir=tmp_path,
    )
    return blueprint, review, authority


def test_representative_external_target_is_three_layers_and_passes_public_cli(
    capsys,
    tmp_path: Path,
) -> None:
    before = sorted(path.relative_to(TARGET_ROOT) for path in TARGET_ROOT.rglob("*"))
    blueprint = load_physical_model_blueprint(BLUEPRINT)
    _, authority_path = _authority_bundle(tmp_path, blueprint)

    assert blueprint.artifact_root == "blueprint_directory"
    assert {element.depth for element in blueprint.elements} == {0, 1, 2}
    assert max(element.depth for element in blueprint.elements) == 2
    assert blueprint.target.target_kind == "mixed_physical_workflow"

    assert main(
        [
            "blueprint",
            "review",
            str(BLUEPRINT),
            "--target-authority",
            str(authority_path),
        ]
    ) == 0
    report = json.loads(capsys.readouterr().out)

    assert report["status"] == "pass"
    assert report["deepest_licensed_layer"] == "static_blueprint"
    assert report["coverage"]["uncovered_member_ids"] == []
    assert report["external_identity_only_binding_ids"] == []
    assert sorted(path.relative_to(TARGET_ROOT) for path in TARGET_ROOT.rglob("*")) == before


def test_representative_target_affected_and_reverse_paths_use_public_blueprint(
    tmp_path: Path,
) -> None:
    blueprint, review, authority = _reviewed_external_target(tmp_path)

    affected = affected_physical_blueprint_projection(
        blueprint,
        review,
        ["port.signal.speed"],
        target_inventory_authority=authority,
        blueprint_base_dir=BLUEPRINT.parent,
        authority_base_dir=tmp_path,
    )
    reverse = reverse_trace_physical_blueprint_projection(
        blueprint,
        review,
        ["port.root.flow"],
        target_inventory_authority=authority,
        blueprint_base_dir=BLUEPRINT.parent,
        authority_base_dir=tmp_path,
    )

    assert "element:pump_signal_relation" in affected.included_member_ids
    assert "element:fixture_validation_path" in affected.included_member_ids
    assert "element:pump_loop_fixture" in affected.included_member_ids
    assert "semantic:sem.signal.relation" in reverse.included_member_ids
    assert "binding:binding.signal.implementation" in reverse.included_member_ids
    assert affected.first_gap_id is None
    assert reverse.first_gap_id is None


@pytest.mark.parametrize(
    ("seed_id", "expected_owner"),
    [
        ("port.signal.speed", "element:pump_signal_relation"),
        ("sem.mode.constraint", "element:valve_mode_context"),
        ("port.mode.valve_state", "element:valve_mode_context"),
        ("validity.signal", "element:pump_signal_relation"),
        ("data/clean.csv", "element:pump_loop_fixture"),
        ("data/clean_manifest.yaml", "element:pump_loop_fixture"),
    ],
)
def test_representative_target_forward_impact_covers_each_required_seed_class(
    seed_id: str,
    expected_owner: str,
    tmp_path: Path,
) -> None:
    blueprint, review, authority = _reviewed_external_target(tmp_path)

    projection = affected_physical_blueprint_projection(
        blueprint,
        review,
        [seed_id],
        target_inventory_authority=authority,
        blueprint_base_dir=BLUEPRINT.parent,
        authority_base_dir=tmp_path,
    )

    assert projection.first_gap_id is None
    assert expected_owner in projection.included_member_ids


@pytest.mark.parametrize(
    "seed_id",
    [
        "port.root.flow",
        "port.root.diagnostic",
        "binding.root.test",
        "binding.root.evidence",
    ],
)
def test_representative_target_reverse_trace_covers_output_diagnostic_test_and_evidence(
    seed_id: str,
    tmp_path: Path,
) -> None:
    blueprint, review, authority = _reviewed_external_target(tmp_path)

    projection = reverse_trace_physical_blueprint_projection(
        blueprint,
        review,
        [seed_id],
        target_inventory_authority=authority,
        blueprint_base_dir=BLUEPRINT.parent,
        authority_base_dir=tmp_path,
    )

    assert projection.first_gap_id is None
    assert any(
        member_id.startswith("element:")
        for member_id in projection.included_member_ids
    )


def test_local_binding_paths_are_forward_relative_to_the_blueprint_directory() -> None:
    blueprint = load_physical_model_blueprint(BLUEPRINT)

    assert all(binding.artifact.repo_path is not None for binding in blueprint.bindings)
    assert all(".." not in Path(binding.artifact.repo_path).parts for binding in blueprint.bindings)
    assert all((BLUEPRINT.parent / binding.artifact.repo_path).is_file() for binding in blueprint.bindings)


def test_representative_target_does_not_relabel_physicsguard_software_as_physical_elements() -> None:
    blueprint = load_physical_model_blueprint(BLUEPRINT)
    forbidden_software_names = {
        "physicsguard.cli",
        "physical_model_blueprint.py",
        "SKILL.md",
        "agents/openai.yaml",
    }

    assert not (
        forbidden_software_names
        & {element.element_id for element in blueprint.elements}
    )
    assert all("src/physicsguard" not in (binding.artifact.repo_path or "") for binding in blueprint.bindings)
