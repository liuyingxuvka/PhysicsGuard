from __future__ import annotations

from copy import deepcopy

import pytest
from pydantic import ValidationError

from physicsguard.core.physical_model_blueprint import review_physical_model_blueprint
from physicsguard.io.physical_model_blueprint_loader import (
    BlueprintLoadError,
    physical_model_blueprint_from_mapping,
)
from physicsguard.schema.physical_model_blueprint import (
    PhysicalModelBlueprint,
    ProviderRegistry,
    TargetInventoryAuthority,
    canonical_blueprint_fingerprint,
    fingerprint_inventory,
    fingerprint_provider_registry,
    fingerprint_provider_registry_entry,
    fingerprint_target_inventory_authority,
    fingerprint_target_inventory_execution,
)


def _review_mutation(complete_physical_blueprint, mutate):
    blueprint, base_dir = complete_physical_blueprint()
    data = deepcopy(blueprint.model_dump(mode="json"))
    mutate(data)
    changed = PhysicalModelBlueprint.model_validate(data)
    review = complete_physical_blueprint.review(changed, base_dir=base_dir)
    assert review.status != "pass"
    assert review.deepest_licensed_layer != "static_blueprint"
    assert review.first_gap_id is not None
    assert "passed static physical-blueprint closure" not in review.safe_claim
    return review


def _remove_mapping(data, mapping_id: str) -> None:
    data["refinements"][0]["port_mappings"] = [
        item
        for item in data["refinements"][0]["port_mappings"]
        if item["mapping_id"] != mapping_id
    ]


def _shrink_blueprint_to_root(data) -> None:
    retained_element_ids = {"pump_loop"}
    retained_binding_ids = {
        item["binding_id"]
        for item in data["bindings"]
        if item["owner_element_id"] in retained_element_ids
    }
    data["elements"] = [
        item for item in data["elements"] if item["element_id"] in retained_element_ids
    ]
    data["ports"] = [
        item for item in data["ports"] if item["owner_element_id"] in retained_element_ids
    ]
    data["semantics"] = [
        item for item in data["semantics"] if item["owner_element_id"] in retained_element_ids
    ]
    data["validity_boundaries"] = [
        item
        for item in data["validity_boundaries"]
        if item["owner_element_id"] in retained_element_ids
    ]
    data["refinements"] = []
    data["bindings"] = [
        item for item in data["bindings"] if item["binding_id"] in retained_binding_ids
    ]
    used_execution_ids = {
        item["native_execution_id"]
        for item in data["bindings"]
        if item.get("native_execution_id")
    }
    data["native_executions"] = [
        item
        for item in data["native_executions"]
        if item["execution_id"] in used_execution_ids
    ]
    data["inventory"]["members"] = [
        item
        for item in data["inventory"]["members"]
        if (
            item.get("blueprint_element_id") in retained_element_ids
            or bool(set(item.get("binding_ids", [])) & retained_binding_ids)
        )
    ]
    data["inventory"]["inventory_fingerprint"] = fingerprint_inventory(data["inventory"])
    data["providers"][0]["payload_fingerprint"] = data["inventory"]["inventory_fingerprint"]


@pytest.mark.parametrize(
    ("mapping_id", "expected_code"),
    [
        ("map.pump-pressure.pipe-pressure", "child_output_unconsumed"),
        ("map.pipe-mass.loop-mass", "child_state_not_accounted"),
        ("map.pipe-heat.loop-heat", "child_effect_not_propagated"),
    ],
)
def test_unaccounted_child_interface_is_an_exact_gap(
    complete_physical_blueprint,
    mapping_id: str,
    expected_code: str,
) -> None:
    review = _review_mutation(
        complete_physical_blueprint,
        lambda data: _remove_mapping(data, mapping_id),
    )

    assert any(gap.code == expected_code for gap in review.gaps)


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("unit", "kPa"),
        ("reference_frame", "opposite-flow-frame"),
        ("time_basis", "continuous"),
    ],
)
def test_interface_unit_frame_and_time_mismatch_requires_conversion(
    complete_physical_blueprint,
    field_name: str,
    value: str,
) -> None:
    def mutate(data) -> None:
        port = next(item for item in data["ports"] if item["port_id"] == "port.pipe.inlet_pressure")
        port[field_name] = value

    review = _review_mutation(complete_physical_blueprint, mutate)

    mismatch = next(gap for gap in review.gaps if gap.code == "interface_contract_mismatch")
    assert field_name in mismatch.message


def test_weaker_child_validity_is_not_hidden_at_parent(complete_physical_blueprint) -> None:
    def mutate(data) -> None:
        data["refinements"][0]["propagated_validity_boundary_ids"].remove("validity.pipe")

    review = _review_mutation(complete_physical_blueprint, mutate)

    assert any(gap.code == "child_validity_not_propagated" for gap in review.gaps)


def test_declarations_without_equation_residual_constraint_or_update_do_not_count_as_physical_relation(
    complete_physical_blueprint,
) -> None:
    def mutate(data) -> None:
        semantic = next(item for item in data["semantics"] if item["semantic_id"] == "sem.pump.pressure_rise")
        semantic["semantic_kind"] = "assumption"

    review = _review_mutation(complete_physical_blueprint, mutate)

    assert any(gap.code == "element_has_no_independent_physical_relation" for gap in review.gaps)


@pytest.mark.parametrize(
    "binding_id",
    [
        "binding.pump.implementation",
        "binding.pump.test",
        "binding.pump.resource",
    ],
)
def test_stale_source_test_or_resource_binding_remains_stale(
    complete_physical_blueprint,
    binding_id: str,
) -> None:
    def mutate(data) -> None:
        binding = next(item for item in data["bindings"] if item["binding_id"] == binding_id)
        binding["status"] = "stale"

    review = _review_mutation(complete_physical_blueprint, mutate)

    assert review.status == "stale"
    assert any(
        gap.code == "native_binding_not_current" and binding_id in gap.target_ids
        for gap in review.gaps
    )


def test_caller_cannot_rewrite_authoritative_inventory_disposition(
    complete_physical_blueprint,
) -> None:
    def mutate(data) -> None:
        member = next(item for item in data["inventory"]["members"] if item["member_id"] == "pump")
        member["disposition"] = "unresolved"
        member["reason"] = "Independent inventory cannot yet identify the pump implementation owner."
        member["disposition_evidence"] = [data["bindings"][0]["artifact"]]
        data["inventory"]["inventory_fingerprint"] = fingerprint_inventory(data["inventory"])
        data["providers"][0]["payload_fingerprint"] = data["inventory"]["inventory_fingerprint"]

    review = _review_mutation(complete_physical_blueprint, mutate)

    assert "pump" in review.coverage.governed_member_ids
    assert "pump" in review.coverage.uncovered_member_ids
    assert any(
        gap.code == "blueprint_inventory_member_disposition_mismatch"
        for gap in review.gaps
    )


def test_caller_cannot_shrink_blueprint_inventory_and_provider_result_together(
    complete_physical_blueprint,
) -> None:
    """A self-consistent caller projection is not an independent denominator."""

    blueprint, base_dir = complete_physical_blueprint()
    original_governed_count = len(blueprint.inventory.members)
    data = deepcopy(blueprint.model_dump(mode="json"))
    _shrink_blueprint_to_root(data)

    shrunk = PhysicalModelBlueprint.model_validate(data)
    review = complete_physical_blueprint.review(shrunk, base_dir=base_dir)

    assert len(review.coverage.governed_member_ids) == original_governed_count
    assert review.status != "pass"
    assert any(gap.code == "target_inventory_authority_member_missing" for gap in review.gaps)
    assert "pump" in review.coverage.uncovered_member_ids
    assert "pipe" in review.coverage.uncovered_member_ids


def test_caller_cannot_self_sign_shrunk_blueprint_authority_and_registry_while_raw_target_is_unchanged(
    complete_physical_blueprint,
) -> None:
    blueprint, base_dir = complete_physical_blueprint()
    data = deepcopy(blueprint.model_dump(mode="json"))
    _shrink_blueprint_to_root(data)
    shrunk = PhysicalModelBlueprint.model_validate(data)

    authority_data = deepcopy(
        complete_physical_blueprint.target_inventory_authority.model_dump(mode="json")
    )
    input_fingerprints = {
        item["reference_id"]: item["artifact"]["sha256"]
        for item in authority_data["input_references"]
    }
    authority_data["inventory"] = shrunk.inventory.model_dump(
        mode="json", exclude_none=True
    )
    execution = authority_data["execution"]
    execution["result_fingerprint"] = shrunk.inventory.inventory_fingerprint
    execution["terminal_receipt_fingerprint"] = canonical_blueprint_fingerprint(
        {
            "execution_id": execution["execution_id"],
            "owner_id": execution["owner_id"],
            "request_id": execution["request_id"],
            "input_fingerprints": input_fingerprints,
            "target_system_id": execution["target_system_id"],
            "subject_revision": execution["subject_revision"],
            "adapter_tool_id": execution["adapter_tool_id"],
            "adapter_tool_version": execution["adapter_tool_version"],
            "result_status": "pass",
            "terminal_status": "success",
            "result_fingerprint": shrunk.inventory.inventory_fingerprint,
        }
    )
    execution["execution_fingerprint"] = fingerprint_target_inventory_execution(
        execution
    )
    authority_data["authority_fingerprint"] = fingerprint_target_inventory_authority(
        authority_data
    )
    self_signed_authority = TargetInventoryAuthority.model_validate(authority_data)

    entry = {
        "registration_id": "caller.self-signed-adapter",
        "status": "current",
        "capability_ids": ["artifact_inventory"],
        "owner_id": self_signed_authority.owner_id,
        "adapter_tool_id": self_signed_authority.execution.adapter_tool_id,
        "adapter_tool_version": self_signed_authority.execution.adapter_tool_version,
        "execution_mode": "local",
        "input_reference_ids": ["target_material"],
        "input_schema_version": "physicsguard.target-material.v1",
    }
    entry["entry_fingerprint"] = fingerprint_provider_registry_entry(entry)
    registry_data = {
        "schema_version": "physicsguard.provider-registry.v1",
        "registry_id": "caller.self-signed",
        "registry_revision": "1",
        "status": "current",
        "entries": [entry],
    }
    registry_data["registry_fingerprint"] = fingerprint_provider_registry(
        registry_data
    )
    self_signed_registry = ProviderRegistry.model_validate(registry_data)

    with pytest.raises(TypeError, match="provider_registry"):
        review_physical_model_blueprint(
            shrunk,
            target_inventory_authority=self_signed_authority,
            provider_registry=self_signed_registry,
            base_dir=base_dir,
            authority_base_dir=complete_physical_blueprint.authority_base_dir,
        )

    review = review_physical_model_blueprint(
        shrunk,
        target_inventory_authority=self_signed_authority,
        base_dir=base_dir,
        authority_base_dir=complete_physical_blueprint.authority_base_dir,
    )

    assert review.status != "pass"
    assert len(review.coverage.governed_member_ids) == len(blueprint.inventory.members)
    assert "pump" in review.coverage.uncovered_member_ids
    assert "pipe" in review.coverage.uncovered_member_ids
    assert any(
        gap.code == "target_inventory_authority_not_verified"
        and "runtime-derived target inventory" in gap.message
        for gap in review.gaps
    )


def test_inventory_provider_must_advertise_inventory_capability(complete_physical_blueprint) -> None:
    def mutate(data) -> None:
        data["required_capability_ids"].remove("artifact_inventory")
        del data["capability_owners"]["artifact_inventory"]
        data["providers"][0]["capability_ids"].remove("artifact_inventory")

    review = _review_mutation(complete_physical_blueprint, mutate)

    assert any(gap.code == "inventory_provider_missing_capability" for gap in review.gaps)


def test_state_lifecycle_requires_explicit_termination_or_handoff(complete_physical_blueprint) -> None:
    def mutate(data) -> None:
        state = next(item for item in data["ports"] if item["port_id"] == "port.pipe.mass")
        state["termination_semantic_id"] = None

    review = _review_mutation(complete_physical_blueprint, mutate)

    assert any(gap.code == "state_port_has_no_termination_semantic" for gap in review.gaps)


def test_pointwise_only_test_evidence_cannot_license_stateful_obligation(
    complete_physical_blueprint,
) -> None:
    def mutate(data) -> None:
        test = next(item for item in data["bindings"] if item["binding_id"] == "binding.pipe.test")
        test["validation_modes"] = ["pointwise", "interface_unit", "boundary_invalid_region"]

    review = _review_mutation(complete_physical_blueprint, mutate)

    assert any(gap.code == "validation_mode_missing_temporal_stateful" for gap in review.gaps)


def test_orphan_child_and_missing_initial_state_are_schema_failures(complete_physical_blueprint) -> None:
    blueprint, _ = complete_physical_blueprint()
    orphan = deepcopy(blueprint.model_dump(mode="json"))
    next(item for item in orphan["elements"] if item["element_id"] == "pipe")["parent_id"] = "missing"
    with pytest.raises(ValidationError, match="unknown parent"):
        PhysicalModelBlueprint.model_validate(orphan)

    missing_initial = deepcopy(blueprint.model_dump(mode="json"))
    next(
        item for item in missing_initial["ports"] if item["port_id"] == "port.pipe.mass"
    )["initial_state_semantic_id"] = None
    with pytest.raises(ValidationError, match="initial_state_semantic_id"):
        PhysicalModelBlueprint.model_validate(missing_initial)

    skipped_depth = deepcopy(blueprint.model_dump(mode="json"))
    next(
        item for item in skipped_depth["elements"] if item["element_id"] == "pipe"
    )["depth"] = 99
    with pytest.raises(ValidationError, match="parent depth plus one"):
        PhysicalModelBlueprint.model_validate(skipped_depth)


def test_foreign_owner_inventory_binding_is_visible_and_blocked_in_whole_and_affected_reviews(
    complete_physical_blueprint,
) -> None:
    blueprint, base_dir = complete_physical_blueprint()
    data = deepcopy(blueprint.model_dump(mode="json"))
    member = next(
        item for item in data["inventory"]["members"] if item["member_id"] == "pump"
    )
    member["binding_ids"] = ["binding.pipe.resource"]
    data["inventory"]["inventory_fingerprint"] = fingerprint_inventory(data["inventory"])
    data["providers"][0]["payload_fingerprint"] = data["inventory"]["inventory_fingerprint"]
    changed = PhysicalModelBlueprint.model_validate(data)

    whole = complete_physical_blueprint.review(changed, base_dir=base_dir)
    affected = complete_physical_blueprint.review(
        changed,
        base_dir=base_dir,
        affected_element_ids=["pump"],
    )

    for review in (whole, affected):
        assert review.status == "blocked"
        assert "pump" in review.coverage.governed_member_ids
        assert any(
            gap.code == "inventory_binding_owner_mismatch"
            and "binding.pipe.resource" in gap.target_ids
            for gap in review.gaps
        )


def test_caller_cannot_enlarge_affected_authority_denominator_with_unregistered_members(
    complete_physical_blueprint,
) -> None:
    blueprint, base_dir = complete_physical_blueprint()
    data = deepcopy(blueprint.model_dump(mode="json"))
    data["inventory"]["members"].extend(
        [
            {
                "member_id": "member.element-only.selected",
                "member_kind": "physical_element",
                "disposition": "modeled",
                "blueprint_element_id": "pump",
                "binding_ids": [],
                "disposition_evidence": [],
            },
            {
                "member_id": "member.binding-only.selected",
                "member_kind": "resource",
                "disposition": "supporting",
                "blueprint_element_id": None,
                "binding_ids": ["binding.pump.resource"],
                "disposition_evidence": [],
            },
            {
                "member_id": "member.binding-mixed.selected-unselected",
                "member_kind": "resource",
                "disposition": "supporting",
                "blueprint_element_id": None,
                "binding_ids": ["binding.pump.resource", "binding.pipe.resource"],
                "disposition_evidence": [],
            },
            {
                "member_id": "member.element-only.unselected",
                "member_kind": "physical_element",
                "disposition": "modeled",
                "blueprint_element_id": "pipe",
                "binding_ids": [],
                "disposition_evidence": [],
            },
        ]
    )
    data["inventory"]["inventory_fingerprint"] = fingerprint_inventory(data["inventory"])
    data["providers"][0]["payload_fingerprint"] = data["inventory"]["inventory_fingerprint"]
    changed = PhysicalModelBlueprint.model_validate(data)

    affected = complete_physical_blueprint.review(
        changed,
        base_dir=base_dir,
        affected_element_ids=["pump"],
    )

    governed = set(affected.coverage.governed_member_ids)
    assert "pump" in governed
    assert "member.element-only.selected" not in governed
    assert "member.binding-only.selected" not in governed
    assert "member.binding-mixed.selected-unselected" not in governed
    assert "member.element-only.unselected" not in governed
    unauthorized = next(
        gap
        for gap in affected.gaps
        if gap.code == "blueprint_inventory_member_not_authorized"
    )
    assert {
        "member.element-only.selected",
        "member.binding-only.selected",
        "member.binding-mixed.selected-unselected",
        "member.element-only.unselected",
    } <= set(unauthorized.target_ids)


def test_unknown_blueprint_schema_has_no_legacy_loader_fallback(complete_physical_blueprint) -> None:
    blueprint, _ = complete_physical_blueprint()
    data = deepcopy(blueprint.model_dump(mode="json"))
    data["schema_version"] = "physicsguard.physical-model-blueprint.v0"

    with pytest.raises(BlueprintLoadError) as exc_info:
        physical_model_blueprint_from_mapping(data)

    assert exc_info.value.category == "unsupported_schema"
