from __future__ import annotations

import json
from pathlib import Path

import yaml

from physicsguard.core.physical_model_blueprint import review_physical_model_blueprint
from physicsguard.core.target_inventory_authority import observe_target_inventory_authority
from physicsguard.io.physical_model_blueprint_loader import (
    load_physical_model_blueprint,
    load_target_inventory_authority,
)
from physicsguard.schema.fmi_observation import FmiObservationRequest


EXAMPLE_ROOT = (
    Path(__file__).resolve().parents[1]
    / "examples"
    / "external_targets"
    / "reference_fmus_v0_0_40_bouncing_ball"
)


def test_canonical_reference_fmus_model_is_portable_and_explicitly_not_run() -> None:
    blueprint = load_physical_model_blueprint(EXAMPLE_ROOT / "physical_blueprint.yaml")
    authority = load_target_inventory_authority(
        EXAMPLE_ROOT / "target_inventory_authority.yaml"
    )
    request = FmiObservationRequest.model_validate_json(
        json.dumps(
            yaml.safe_load(
                (EXAMPLE_ROOT / "fmi_observation_request.yaml").read_text(
                    encoding="utf-8"
                )
            )
        )
    )

    serialized = json.dumps(
        {
            "blueprint": blueprint.model_dump(mode="json", exclude_none=False),
            "authority": authority.model_dump(mode="json", exclude_none=False),
            "request": request.model_dump(mode="json", exclude_none=False),
        },
        sort_keys=True,
    )
    assert "C:\\" not in serialized
    assert "physicsguard-fmi-target-" not in serialized
    assert blueprint.artifact_root == "explicit_material_root"
    assert blueprint.understanding_target == "object_dna"
    assert len(blueprint.source_mappings) == 41
    assert request.source.source_uri == "https://github.com/modelica/Reference-FMUs"
    assert request.source.release_version == "v0.0.40"
    assert request.source.license_id == "BSD-2-Clause"
    assert all(item.relative_path for item in request.artifacts)
    assert len(request.semantic_selectors) == 17
    assert observe_target_inventory_authority(authority, base_dir=EXAMPLE_ROOT).status == "pass"

    review = review_physical_model_blueprint(
        blueprint,
        target_inventory_authority=authority,
    )

    assert review.status == "blocked"
    assert review.gaps[0].code == "external_resource_not_run"
    assert "no target bytes or native owner were executed" in review.gaps[0].message


def test_canonical_reference_fmus_model_binds_hierarchy_cases_code_tests_and_oracles() -> None:
    blueprint = load_physical_model_blueprint(EXAMPLE_ROOT / "physical_blueprint.yaml")
    elements = {item.element_id: item for item in blueprint.elements}
    cases = {item.case_id: item for item in blueprint.behavior_cases}

    assert set(elements) == {"bouncing_ball", "free_flight", "impact_event"}
    assert elements["bouncing_ball"].parent_id is None
    assert elements["free_flight"].parent_id == "bouncing_ball"
    assert elements["impact_event"].parent_id == "bouncing_ball"
    assert len(blueprint.ports) == 29
    assert len(blueprint.semantics) == 17
    assert len(blueprint.inventory.members) == 61
    assert len(cases) == 5
    assert sum(len(item.semantic_contracts) for item in blueprint.source_mappings) == 17
    assert sum(len(item.port_contracts) for item in blueprint.source_mappings) == 22

    restitution = cases["case.impact.restitution"]
    stopped = cases["case.impact.stop"]
    protected = cases["case.impact.v-min-constant"]
    assert restitution.input_values["port.impact.h"] == 0.0
    assert restitution.input_values["port.impact.v"] == -1.0
    assert restitution.input_values["port.impact.e"] == 0.7
    assert restitution.expected_output_values == {
        "port.impact.v_post": 0.7,
        "port.impact.g_post": -9.81,
    }
    assert stopped.input_values["port.impact.v"] == -0.1
    assert stopped.expected_output_values == {
        "port.impact.v_post": 0.0,
        "port.impact.g_post": 0.0,
    }
    assert "port.impact.stopped" in stopped.expected_effect_port_ids
    assert protected.expected_effect_port_ids == ["port.impact.rejected"]
    assert all(item.status == "pass" for item in cases.values())
    assert all(item.native_result_binding_id for item in cases.values())
    assert all(
        item.native_value_bindings or not item.expected_output_values
        for item in cases.values()
    )

    semantics_by_owner = {
        owner: {item.semantic_id for item in blueprint.semantics if item.owner_element_id == owner}
        for owner in elements
    }
    for owner, semantic_ids in semantics_by_owner.items():
        bindings = {
            item.binding_kind: item
            for item in blueprint.bindings
            if item.owner_element_id == owner
        }
        assert set(bindings["source"].semantic_ids) == semantic_ids
        assert set(bindings["test"].semantic_ids) == semantic_ids
        assert set(bindings["oracle"].semantic_ids) == semantic_ids

    for case in cases.values():
        assert len(case.test_binding_ids) == 1
        assert len(case.evidence_binding_ids) == 1
        assert len(case.oracle_binding_ids) == 1
        assert case.case_fingerprint
        bound_ids = (
            case.test_binding_ids
            + case.evidence_binding_ids
            + case.oracle_binding_ids
        )
        binding_by_id = {item.binding_id: item for item in blueprint.bindings}
        assert all(binding_by_id[item].native_execution_id for item in bound_ids)
