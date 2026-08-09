from __future__ import annotations

from copy import deepcopy

import pytest

import physicsguard.core.physical_blueprint_trace as trace_module
from physicsguard.core.physical_blueprint_trace import (
    affected_physical_blueprint_projection,
    compile_physical_blueprint_graph,
    full_physical_blueprint_projection,
    reverse_trace_physical_blueprint_projection,
    summary_physical_blueprint_projection,
)
from physicsguard.core.physical_model_blueprint import review_physical_model_blueprint
from physicsguard.schema.physical_model_blueprint import (
    PhysicalModelBlueprint,
    PhysicalModelBlueprintReview,
    fingerprint_inventory,
    fingerprint_review,
)


def _reviewed(complete_physical_blueprint):
    blueprint, base_dir = complete_physical_blueprint()
    return blueprint, complete_physical_blueprint.review(blueprint, base_dir=base_dir)


def _affected(complete_physical_blueprint, blueprint, review, seed_ids):
    return affected_physical_blueprint_projection(
        blueprint,
        review,
        seed_ids,
        target_inventory_authority=(
            complete_physical_blueprint.target_inventory_authority
        ),
        blueprint_base_dir=complete_physical_blueprint.blueprint_base_dir,
        authority_base_dir=complete_physical_blueprint.authority_base_dir,
    )


def _reverse(complete_physical_blueprint, blueprint, review, seed_ids):
    return reverse_trace_physical_blueprint_projection(
        blueprint,
        review,
        seed_ids,
        target_inventory_authority=(
            complete_physical_blueprint.target_inventory_authority
        ),
        blueprint_base_dir=complete_physical_blueprint.blueprint_base_dir,
        authority_base_dir=complete_physical_blueprint.authority_base_dir,
    )


def test_child_interface_impact_includes_parent_sibling_and_shared_consumers(
    complete_physical_blueprint,
) -> None:
    blueprint, review = _reviewed(complete_physical_blueprint)

    projection = _affected(
        complete_physical_blueprint,
        blueprint,
        review,
        ["port.pump.discharge_pressure"],
    )

    included = set(projection.included_member_ids)
    assert "port:port.pump.discharge_pressure" in included
    assert "element:pump" in included
    assert "element:pump_loop" in included
    assert "element:pipe" in included
    assert "mapping:map.pump-pressure.pipe-pressure" in included
    assert "semantic:sem.pipe.pressure_flow" in included
    assert "provider:provider.pump-loop" in projection.outside_scope_ids
    assert projection.first_gap_id is None


def test_shared_resource_change_selects_each_exact_consumer(complete_physical_blueprint) -> None:
    blueprint, review = _reviewed(complete_physical_blueprint)

    projection = _affected(
        complete_physical_blueprint,
        blueprint,
        review,
        ["artifacts/resource.txt"],
    )

    included = set(projection.included_member_ids)
    assert "binding:binding.pump_loop.resource" in included
    assert "binding:binding.pump.resource" in included
    assert "binding:binding.pipe.resource" in included
    assert "artifact:" + next(
        item.artifact.sha256 for item in blueprint.bindings if item.binding_id == "binding.pump.resource"
    ) in included


def test_reverse_trace_from_parent_output_reaches_child_semantics_and_native_ground(
    complete_physical_blueprint,
) -> None:
    blueprint, review = _reviewed(complete_physical_blueprint)

    projection = _reverse(
        complete_physical_blueprint,
        blueprint,
        review,
        ["port.loop.flow"],
    )

    included = set(projection.included_member_ids)
    assert "port:port.loop.flow" in included
    assert "semantic:sem.loop.mass" in included
    assert "contribution:contribution.pipe-flow" in included
    assert "semantic:sem.pipe.pressure_flow" in included
    assert "binding:binding.pipe.implementation" in included
    assert "element:pipe" in included
    assert "element:pump_loop" in included
    assert projection.trace_status == "pass"
    assert projection.terminal_input_ids
    assert projection.terminal_binding_ids
    assert projection.terminal_resource_ids


def test_unknown_or_ambiguous_seed_is_a_bounded_gap_without_automatic_broadening(
    complete_physical_blueprint,
) -> None:
    blueprint, review = _reviewed(complete_physical_blueprint)
    unknown = _affected(
        complete_physical_blueprint,
        blueprint,
        review,
        ["missing.member"],
    )

    assert unknown.included_member_ids == []
    assert unknown.first_gap_id is not None
    assert [gap.code for gap in unknown.gaps] == ["trace_seed_unknown"]
    assert len(unknown.outside_scope_ids) > 1

    data = deepcopy(blueprint.model_dump(mode="json"))
    data["bindings"][0]["subject_id"] = "pump"
    ambiguous_blueprint = PhysicalModelBlueprint.model_validate(data)
    ambiguous_review = complete_physical_blueprint.review(
        ambiguous_blueprint,
        base_dir=complete_physical_blueprint()[1],
    )
    ambiguous = _affected(
        complete_physical_blueprint,
        ambiguous_blueprint,
        ambiguous_review,
        ["pump"],
    )

    assert ambiguous.included_member_ids == []
    assert [gap.code for gap in ambiguous.gaps] == ["trace_seed_ambiguous"]


def test_mixed_known_and_unknown_seeds_block_the_whole_projection(
    complete_physical_blueprint,
) -> None:
    blueprint, review = _reviewed(complete_physical_blueprint)

    projection = _affected(
        complete_physical_blueprint,
        blueprint,
        review,
        ["port.pump.discharge_pressure", "missing.member"],
    )

    assert projection.included_member_ids == []
    assert [gap.code for gap in projection.gaps] == ["trace_seed_unknown"]
    assert "port:port.pump.discharge_pressure" in projection.outside_scope_ids


def test_mixed_known_and_unknown_reverse_seeds_block_the_whole_projection(
    complete_physical_blueprint,
) -> None:
    blueprint, review = _reviewed(complete_physical_blueprint)

    projection = _reverse(
        complete_physical_blueprint,
        blueprint,
        review,
        ["port.loop.flow", "missing.member"],
    )

    assert projection.included_member_ids == []
    assert [gap.code for gap in projection.gaps] == ["trace_seed_unknown"]
    assert "port:port.loop.flow" in projection.outside_scope_ids


def test_reverse_trace_with_no_terminal_seed_fails_visibly_and_selects_nothing(
    complete_physical_blueprint,
) -> None:
    blueprint, review = _reviewed(complete_physical_blueprint)

    projection = _reverse(
        complete_physical_blueprint,
        blueprint,
        review,
        [],
    )

    assert projection.included_member_ids == []
    assert [gap.code for gap in projection.gaps] == ["trace_seed_missing"]


@pytest.mark.parametrize(
    "seed_id",
    [
        "blueprint.external-pump-loop.r1",
        "blueprint:blueprint.external-pump-loop.r1",
        "external-pump-loop",
        "inventory.external-pump-loop.r1",
    ],
)
def test_reverse_trace_non_terminal_dead_end_is_not_an_empty_chain_success(
    complete_physical_blueprint,
    seed_id: str,
) -> None:
    blueprint, review = _reviewed(complete_physical_blueprint)

    projection = _reverse(
        complete_physical_blueprint,
        blueprint,
        review,
        [seed_id],
    )

    assert projection.first_gap_id is not None
    assert [gap.code for gap in projection.gaps] == ["trace_non_terminal_dead_end"]
    assert projection.trace_status == "blocked"
    assert projection.terminal_input_ids == []
    assert projection.terminal_binding_ids == []
    assert projection.terminal_resource_ids == []


def test_reverse_trace_from_incomplete_review_is_explicitly_non_success(
    complete_physical_blueprint,
) -> None:
    blueprint, base_dir = complete_physical_blueprint()
    data = deepcopy(blueprint.model_dump(mode="json"))
    data["refinements"][0]["port_mappings"] = data["refinements"][0][
        "port_mappings"
    ][1:]
    incomplete = PhysicalModelBlueprint.model_validate(data)
    review = complete_physical_blueprint.review(incomplete, base_dir=base_dir)

    projection = _reverse(
        complete_physical_blueprint,
        incomplete,
        review,
        ["port.loop.flow"],
    )

    assert review.status == "incomplete"
    assert projection.included_member_ids == []
    assert projection.trace_status == "incomplete"
    assert [gap.code for gap in projection.gaps] == [
        "trace_source_review_not_qualified"
    ]


def test_affected_and_reverse_reject_a_passed_review_after_raw_material_changes(
    complete_physical_blueprint,
) -> None:
    blueprint, base_dir = complete_physical_blueprint()
    review = complete_physical_blueprint.review(blueprint, base_dir=base_dir)
    material_path = complete_physical_blueprint.target_material_path
    material_path.write_bytes(material_path.read_bytes() + b"\n")
    changed_material = material_path.read_bytes()

    affected = _affected(
        complete_physical_blueprint,
        blueprint,
        review,
        ["port.pump.discharge_pressure"],
    )
    reverse = _reverse(
        complete_physical_blueprint,
        blueprint,
        review,
        ["port.loop.flow"],
    )

    assert review.status == "pass"
    assert material_path.read_bytes() == changed_material
    for projection in (affected, reverse):
        assert projection.included_member_ids == []
        assert projection.trace_status == "stale"
        assert [gap.code for gap in projection.gaps] == [
            "trace_source_review_not_qualified"
        ]


def test_affected_query_without_source_authority_fails_stale(
    complete_physical_blueprint,
) -> None:
    blueprint, review = _reviewed(complete_physical_blueprint)

    projection = affected_physical_blueprint_projection(
        blueprint,
        review,
        ["port.pump.discharge_pressure"],
    )

    assert projection.included_member_ids == []
    assert projection.trace_status == "stale"
    assert [gap.code for gap in projection.gaps] == [
        "trace_source_review_context_missing"
    ]


@pytest.mark.parametrize(
    ("projection_name", "seed_id"),
    [
        ("affected_physical_blueprint_projection", "port.pump.discharge_pressure"),
        ("reverse_trace_physical_blueprint_projection", "port.loop.flow"),
    ],
)
def test_qualified_source_gate_runs_once_before_graph_compilation(
    complete_physical_blueprint,
    monkeypatch,
    projection_name: str,
    seed_id: str,
) -> None:
    blueprint, base_dir = complete_physical_blueprint()
    review = complete_physical_blueprint.review(blueprint, base_dir=base_dir)
    real_review = trace_module.review_physical_model_blueprint
    real_compile = trace_module.compile_physical_blueprint_graph
    events: list[str] = []

    def tracked_review(*args, **kwargs):
        events.append("review")
        return real_review(*args, **kwargs)

    def tracked_compile(*args, **kwargs):
        events.append("compile")
        return real_compile(*args, **kwargs)

    monkeypatch.setattr(
        trace_module,
        "review_physical_model_blueprint",
        tracked_review,
    )
    monkeypatch.setattr(
        trace_module,
        "compile_physical_blueprint_graph",
        tracked_compile,
    )
    projection = getattr(trace_module, projection_name)(
        blueprint,
        review,
        [seed_id],
        target_inventory_authority=(
            complete_physical_blueprint.target_inventory_authority
        ),
        blueprint_base_dir=base_dir,
        authority_base_dir=complete_physical_blueprint.authority_base_dir,
    )

    assert projection.trace_status == "pass"
    assert events == ["review", "compile"]


@pytest.mark.parametrize(
    ("projection_name", "seed_id"),
    [
        ("affected_physical_blueprint_projection", "port.pump.discharge_pressure"),
        ("reverse_trace_physical_blueprint_projection", "port.loop.flow"),
    ],
)
def test_failed_qualified_source_gate_never_compiles_graph(
    complete_physical_blueprint,
    monkeypatch,
    projection_name: str,
    seed_id: str,
) -> None:
    blueprint, base_dir = complete_physical_blueprint()
    review = complete_physical_blueprint.review(blueprint, base_dir=base_dir)
    material_path = complete_physical_blueprint.target_material_path
    material_path.write_bytes(material_path.read_bytes() + b"\n")
    real_review = trace_module.review_physical_model_blueprint
    events: list[str] = []

    def tracked_review(*args, **kwargs):
        events.append("review")
        return real_review(*args, **kwargs)

    def forbidden_compile(*args, **kwargs):
        events.append("compile")
        raise AssertionError("graph compilation must not run after source rejection")

    monkeypatch.setattr(
        trace_module,
        "review_physical_model_blueprint",
        tracked_review,
    )
    monkeypatch.setattr(
        trace_module,
        "compile_physical_blueprint_graph",
        forbidden_compile,
    )
    projection = getattr(trace_module, projection_name)(
        blueprint,
        review,
        [seed_id],
        target_inventory_authority=(
            complete_physical_blueprint.target_inventory_authority
        ),
        blueprint_base_dir=base_dir,
        authority_base_dir=complete_physical_blueprint.authority_base_dir,
    )

    assert projection.included_member_ids == []
    assert projection.trace_status == "stale"
    assert events == ["review"]


def test_caller_cannot_rehash_an_incomplete_review_as_pass(
    complete_physical_blueprint,
) -> None:
    blueprint, base_dir = complete_physical_blueprint()
    data = deepcopy(blueprint.model_dump(mode="json"))
    data["refinements"][0]["port_mappings"] = data["refinements"][0][
        "port_mappings"
    ][1:]
    incomplete = PhysicalModelBlueprint.model_validate(data)
    actual_review = complete_physical_blueprint.review(incomplete, base_dir=base_dir)
    assert actual_review.status == "incomplete"
    forged_payload = actual_review.model_dump(mode="json")
    forged_payload["status"] = "pass"
    forged_payload["declared_consistency_status"] = "pass"
    forged_payload["gaps"] = []
    forged_payload["first_gap_id"] = None
    forged_payload["logical_report_fingerprint"] = fingerprint_review(forged_payload)
    forged_review = PhysicalModelBlueprintReview.model_validate(forged_payload)

    projection = _affected(
        complete_physical_blueprint,
        incomplete,
        forged_review,
        ["port.loop.flow"],
    )

    assert forged_review.status == "pass"
    assert projection.included_member_ids == []
    assert projection.trace_status == "incomplete"
    assert [gap.code for gap in projection.gaps] == [
        "trace_source_review_not_qualified"
    ]


def test_exact_blocked_review_cannot_enter_query_graph(
    complete_physical_blueprint,
) -> None:
    blueprint, base_dir = complete_physical_blueprint()
    data = deepcopy(blueprint.model_dump(mode="json"))
    data["unresolved_relations"] = [
        {
            "relation_id": "relation.unsupported.current-source",
            "relation_kind": "provider_to_artifact",
            "source_ids": ["binding.pump.implementation"],
            "target_ids": ["sem.pump.pressure_rise"],
            "status": "unsupported",
            "reason": "The current source relation has no supported native owner.",
            "evidence": [data["bindings"][0]["artifact"]],
        }
    ]
    blocked_blueprint = PhysicalModelBlueprint.model_validate(data)
    blocked_review = complete_physical_blueprint.review(
        blocked_blueprint,
        base_dir=base_dir,
    )

    projection = _affected(
        complete_physical_blueprint,
        blocked_blueprint,
        blocked_review,
        ["binding.pump.implementation"],
    )

    assert blocked_review.status == "blocked"
    assert projection.included_member_ids == []
    assert projection.trace_status == "blocked"
    assert [gap.code for gap in projection.gaps] == [
        "trace_source_review_not_qualified"
    ]


def test_exact_stale_review_cannot_enter_query_graph(
    complete_physical_blueprint,
) -> None:
    blueprint, base_dir = complete_physical_blueprint()
    implementation_path = base_dir / "artifacts" / "implementation.txt"
    implementation_path.write_bytes(
        implementation_path.read_bytes() + b"changed after blueprint binding\n"
    )
    stale_review = complete_physical_blueprint.review(blueprint, base_dir=base_dir)

    projection = _reverse(
        complete_physical_blueprint,
        blueprint,
        stale_review,
        ["port.loop.flow"],
    )

    assert stale_review.status == "stale"
    assert projection.included_member_ids == []
    assert projection.trace_status == "stale"
    assert [gap.code for gap in projection.gaps] == [
        "trace_source_review_not_qualified"
    ]


def test_every_public_graph_object_has_an_exact_seed_and_raw_inventory_alias(
    complete_physical_blueprint,
) -> None:
    blueprint, review = _reviewed(complete_physical_blueprint)
    graph = compile_physical_blueprint_graph(blueprint, review)

    # The namespaced node ids are the complete query denominator: every typed
    # public graph object must be selectable without heuristic matching.
    for node in graph.nodes:
        projection = _affected(
            complete_physical_blueprint,
            blueprint,
            review,
            [node.node_id],
        )
        assert projection.first_gap_id is None, node.node_id
        assert node.node_id in projection.included_member_ids, node.node_id

    # Natural inventory member ids are aliases too.  When the same id names
    # both an observation and the modeled object, the declared equivalence is
    # selected as one public identity rather than reported as ambiguous.
    for member in blueprint.inventory.members:
        assert member.member_id in graph.aliases
        projection = _affected(
            complete_physical_blueprint,
            blueprint,
            review,
            [member.member_id],
        )
        assert projection.first_gap_id is None, member.member_id
        assert f"inventory:{member.member_id}" in projection.included_member_ids

    expected_seed_classes = {
        "physical_blueprint",
        "target",
        "provider",
        "provider_capability",
        "independent_inventory",
        "physical_element",
        "physical_input",
        "physical_output",
        "physical_state",
        "physical_effect",
        "validity_boundary",
        "refinement_contract",
        "port_mapping",
        "semantic_contribution",
        "content_addressed_artifact",
        "bounded_review_claim",
    }
    assert expected_seed_classes <= {node.node_kind for node in graph.nodes}


def test_provider_and_inventory_identity_changes_reach_observations_and_bindings(
    complete_physical_blueprint,
) -> None:
    blueprint, review = _reviewed(complete_physical_blueprint)

    provider_projection = _affected(
        complete_physical_blueprint,
        blueprint,
        review,
        ["provider.pump-loop"],
    )
    provider_included = set(provider_projection.included_member_ids)
    assert f"inventory-set:{blueprint.inventory.inventory_id}" in provider_included
    assert {f"inventory:{item.member_id}" for item in blueprint.inventory.members} <= provider_included
    assert {f"binding:{item.binding_id}" for item in blueprint.bindings} <= provider_included

    inventory_projection = _affected(
        complete_physical_blueprint,
        blueprint,
        review,
        [blueprint.inventory.inventory_id],
    )
    inventory_included = set(inventory_projection.included_member_ids)
    assert {f"inventory:{item.member_id}" for item in blueprint.inventory.members} <= inventory_included
    assert {f"binding:{item.binding_id}" for item in blueprint.bindings} <= inventory_included


def test_compiled_affected_graph_does_not_expand_through_parent_to_unconnected_sibling(
    complete_physical_blueprint,
) -> None:
    blueprint, _ = complete_physical_blueprint()
    data = deepcopy(blueprint.model_dump(mode="json"))
    data["elements"].append(
        {
            "element_id": "unconnected_sensor_island",
            "name": "Unconnected sensor island",
            "element_kind": "component",
            "parent_id": "pump_loop",
            "depth": 1,
            "description": "A declared supporting child with no relation to the pump-pressure path.",
            "port_ids": [],
            "semantic_ids": [],
            "validity_boundary_ids": [],
            "native_binding_ids": [],
            "owned_behavior_ids": [],
            "supporting_only": True,
        }
    )
    data["refinements"][0]["child_element_ids"].append("unconnected_sensor_island")
    data["inventory"]["members"].append(
        {
            "member_id": "unconnected_sensor_island",
            "member_kind": "physical_element",
            "disposition": "modeled",
            "blueprint_element_id": "unconnected_sensor_island",
            "binding_ids": [],
            "disposition_evidence": [],
        }
    )
    data["inventory"]["inventory_fingerprint"] = fingerprint_inventory(data["inventory"])
    data["providers"][0]["payload_fingerprint"] = data["inventory"]["inventory_fingerprint"]
    sibling_blueprint = PhysicalModelBlueprint.model_validate(data)
    graph = compile_physical_blueprint_graph(sibling_blueprint)
    included = trace_module._walk(
        {"port:port.pump.discharge_pressure"},
        trace_module._affected_adjacency(graph),
    )
    all_node_ids = {node.node_id for node in graph.nodes}

    assert "element:pipe" in included
    assert "element:unconnected_sensor_island" in all_node_ids - included
    assert "inventory:unconnected_sensor_island" in all_node_ids - included


def test_unresolved_typed_relation_remains_visible_in_selected_projection(
    complete_physical_blueprint,
) -> None:
    blueprint, base_dir = complete_physical_blueprint()
    data = deepcopy(blueprint.model_dump(mode="json"))
    data["unresolved_relations"] = [
        {
            "relation_id": "relation.pipe-flow.dataset",
            "relation_kind": "dataset_to_obligation",
            "source_ids": ["binding.pipe.resource"],
            "target_ids": ["sem.pipe.pressure_flow"],
            "status": "unresolved",
            "reason": "No current typed relation identifies which dataset field grounds flow.",
            "evidence": [data["bindings"][0]["artifact"]],
        }
    ]
    incomplete = PhysicalModelBlueprint.model_validate(data)
    review = complete_physical_blueprint.review(incomplete, base_dir=base_dir)

    projection = _affected(
        complete_physical_blueprint,
        incomplete,
        review,
        ["sem.pipe.pressure_flow"],
    )

    assert review.status == "incomplete"
    assert projection.included_member_ids == []
    assert [gap.code for gap in projection.gaps] == [
        "trace_source_review_not_qualified"
    ]


def test_summary_affected_and_full_projections_are_deterministic_and_bound_identity(
    complete_physical_blueprint,
) -> None:
    blueprint, review = _reviewed(complete_physical_blueprint)

    first = _affected(
        complete_physical_blueprint,
        blueprint,
        review,
        ["sem.pipe.mass_step"],
    )
    second = _affected(
        complete_physical_blueprint,
        blueprint,
        review,
        ["sem.pipe.mass_step"],
    )
    summary = summary_physical_blueprint_projection(blueprint, review)
    full = full_physical_blueprint_projection(blueprint, review)

    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    assert first.projection_fingerprint == second.projection_fingerprint
    assert first.relation_set_fingerprint == full.relation_set_fingerprint
    assert first.source_blueprint_fingerprint == review.blueprint_fingerprint
    assert first.source_review_fingerprint == review.logical_report_fingerprint
    assert first.source_safe_claim == review.safe_claim
    assert set(summary.included_member_ids) < set(full.included_member_ids)


def test_projection_rejects_a_review_from_another_blueprint_identity(
    complete_physical_blueprint,
) -> None:
    blueprint, review = _reviewed(complete_physical_blueprint)
    changed = deepcopy(blueprint.model_dump(mode="json"))
    changed["target"]["purpose"] = "A changed target purpose with a new blueprint identity."
    changed_blueprint = PhysicalModelBlueprint.model_validate(changed)

    projection = _affected(
        complete_physical_blueprint,
        changed_blueprint,
        review,
        ["pump"],
    )

    assert projection.included_member_ids == []
    assert [gap.code for gap in projection.gaps] == [
        "trace_source_review_identity_mismatch"
    ]
    assert projection.gaps[0].status == "stale"
