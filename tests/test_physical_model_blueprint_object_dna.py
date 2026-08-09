from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import physicsguard.core.physical_model_blueprint as review_module
from physicsguard.core.physical_blueprint_bundle import (
    build_physical_blueprint_export_bundle,
    query_physical_blueprint_export_bundle,
)
from physicsguard.core.physical_blueprint_trace import (
    affected_physical_blueprint_projection,
    compile_physical_blueprint_graph,
    reverse_trace_physical_blueprint_projection,
)
from physicsguard.core.physical_model_blueprint_adapters import (
    NativeAuthorityObservation,
)
from physicsguard.core.fmi_observation import load_fmi_observation_request
from physicsguard.core.target_inventory_authority import (
    TargetInventoryAuthorityObservation,
    current_target_inventory_provider_registry,
)
from physicsguard.io.physical_model_blueprint_loader import (
    load_physical_model_blueprint,
    load_target_inventory_authority,
)
from physicsguard.schema.physical_model_blueprint import (
    PhysicalModelBlueprint,
    canonical_blueprint_fingerprint,
    fingerprint_native_behavior_case_universe_member,
    fingerprint_observed_semantic_selector,
    fingerprint_physical_behavior_case,
)


EXAMPLE_ROOT = (
    Path(__file__).resolve().parents[1]
    / "examples"
    / "external_targets"
    / "reference_fmus_v0_0_40_bouncing_ball"
)


def _canonical_target():
    return (
        load_physical_model_blueprint(EXAMPLE_ROOT / "physical_blueprint.yaml"),
        load_target_inventory_authority(EXAMPLE_ROOT / "target_inventory_authority.yaml"),
    )


def _source_census(blueprint: PhysicalModelBlueprint) -> tuple[dict[str, object], ...]:
    semantic_expressions = {
        "fmi.semantic:oracle.free-flight-kinematics:dh": "v",
        "fmi.semantic:oracle.free-flight-kinematics:dv": "g",
        "fmi.semantic:oracle.impact-momentum-reflection:candidate": "-e * v",
    }
    request = load_fmi_observation_request(EXAMPLE_ROOT / "fmi_observation_request.yaml")
    selector_member_path = {
        item.member_id: item.member_path for item in request.expected_members
    }
    selectors_by_source: dict[str, list[dict[str, object]]] = {}
    for selector in request.semantic_selectors:
        fragment = " ".join(selector.source_fragment.split())
        payload: dict[str, object] = {
            "selector_id": selector.selector_id,
            "function_name": selector.function_name,
            "normalized_source_fragment": fragment,
            "source_fragment_fingerprint": canonical_blueprint_fingerprint(fragment),
            "semantic_kind": selector.semantic_kind,
            "semantic_statement": selector.semantic_statement,
            "semantic_expression": selector.semantic_expression,
            "status": "verified",
            "claim_boundary": selector.claim_boundary,
            "first_gap_code": None,
        }
        payload["selector_fingerprint"] = fingerprint_observed_semantic_selector(payload)
        source_id = f"fmi.member:{selector_member_path[selector.source_member_id]}"
        selectors_by_source.setdefault(source_id, []).append(payload)
    variable_contract_by_source = {
        mapping.source_member_id: mapping.fmi_variable_contract.model_dump(
            mode="json", exclude_none=False
        )
        for mapping in blueprint.source_mappings
        if mapping.fmi_variable_contract is not None
    }
    source_ids = sorted({item.source_member_id for item in blueprint.source_mappings})
    return tuple(
        {
            "source_member_id": source_id,
            "source_kind": (
                "semantic_fact"
                if source_id.startswith("fmi.semantic:")
                else "native_case"
                if source_id.startswith("fmi.case:")
                else "variable"
                if source_id.startswith("fmi.variable:")
                else "archive_member"
            ),
            "locator": f"fixture:{source_id}",
            "role": "independent_fixture_projection",
            "member_fingerprint": canonical_blueprint_fingerprint(source_id),
            **(
                {"semantic_expression": semantic_expressions[source_id]}
                if source_id in semantic_expressions
                else {}
            ),
            **(
                {"fmi_variable_contract": variable_contract_by_source[source_id]}
                if source_id in variable_contract_by_source
                else {}
            ),
            **(
                {"semantic_selectors": selectors_by_source[source_id]}
                if source_id in selectors_by_source
                else {}
            ),
        }
        for source_id in source_ids
    )


def _native_case_results(blueprint: PhysicalModelBlueprint) -> tuple[dict[str, object], ...]:
    results: list[dict[str, object]] = []
    for case in blueprint.behavior_cases:
        expected_values = {
            **case.expected_output_values,
            **case.expected_post_state_values,
        }
        value_by_port = {item.port_id: item for item in case.native_value_bindings}
        observed_values = {
            value_by_port[port_id].native_variable_name: value
            for port_id, value in expected_values.items()
        }
        results.append(
            {
                "case_id": case.native_case_id,
                "terminal_status": case.expected_terminal_status,
                "observed_values": observed_values,
                "status": "pass",
            }
        )
    return tuple(results)


def _native_case_universe(blueprint: PhysicalModelBlueprint) -> tuple[dict[str, object], ...]:
    universe: list[dict[str, object]] = []
    for case in blueprint.behavior_cases:
        payload: dict[str, object] = {
            "native_case_id": case.native_case_id,
            "disposition": "required",
            "native_input_fingerprint": canonical_blueprint_fingerprint(case.native_case_id),
        }
        payload["member_fingerprint"] = fingerprint_native_behavior_case_universe_member(payload)
        universe.append(payload)
    return tuple(sorted(universe, key=lambda item: str(item["native_case_id"])))


def _install_current_native_observations(
    monkeypatch,
    canonical_blueprint: PhysicalModelBlueprint,
    authority,
) -> None:
    census = _source_census(canonical_blueprint)
    census_fingerprint = canonical_blueprint_fingerprint(census)
    native_results = _native_case_results(canonical_blueprint)
    native_case_universe = _native_case_universe(canonical_blueprint)
    native_case_universe_fingerprint = canonical_blueprint_fingerprint(native_case_universe)

    def observe_bindings(bindings, **_kwargs):
        output = {}
        for binding in bindings:
            replayable = binding.native_schema == "fmi_observation_request"
            output[binding.binding_id] = NativeAuthorityObservation(
                binding_id=binding.binding_id,
                adapter_id=f"fixture.{binding.native_schema}",
                status="current",
                expected_sha256=binding.artifact.sha256,
                actual_sha256=binding.artifact.sha256,
                native_identity=binding.subject_id,
                findings=(),
                content_verified=True,
                subject_identity_verified=True,
                semantic_binding_verified=True,
                replayable=replayable,
                native_owner_executed=replayable,
                execution_identity_verified=replayable,
                terminal_receipt_verified=replayable,
                terminal_receipt_fingerprint=(
                    canonical_blueprint_fingerprint(binding.binding_id)
                    if replayable
                    else None
                ),
                source_census=census if replayable else (),
                source_census_fingerprint=(census_fingerprint if replayable else None),
                native_case_results=native_results if replayable else (),
                native_case_universe=native_case_universe if replayable else (),
                native_case_universe_fingerprint=(
                    native_case_universe_fingerprint if replayable else None
                ),
                object_dna_contract_kind=("fmi.v1" if replayable else None),
                object_dna_contract_verified=replayable,
            )
        return output

    registry = current_target_inventory_provider_registry()
    authority_observation = TargetInventoryAuthorityObservation(
        status="pass",
        inventory=authority.inventory,
        provider_registry_fingerprint=registry.registry_fingerprint,
        expected_inventory_fingerprint=authority.inventory.inventory_fingerprint,
        findings=(),
    )
    monkeypatch.setattr(review_module, "observe_native_bindings", observe_bindings)
    monkeypatch.setattr(
        review_module,
        "observe_target_inventory_authority",
        lambda *_args, **_kwargs: authority_observation,
    )


def _review(monkeypatch, blueprint: PhysicalModelBlueprint):
    canonical, authority = _canonical_target()
    _install_current_native_observations(monkeypatch, canonical, authority)
    return review_module.review_physical_model_blueprint(
        blueprint,
        target_inventory_authority=authority,
        base_dir=EXAMPLE_ROOT,
    )


def test_object_dna_reference_model_closes_source_mapping_and_native_results(monkeypatch) -> None:
    blueprint, authority = _canonical_target()
    _install_current_native_observations(monkeypatch, blueprint, authority)

    review = review_module.review_physical_model_blueprint(
        blueprint,
        target_inventory_authority=authority,
        base_dir=EXAMPLE_ROOT,
    )

    assert review.status == "pass"
    assert review.declared_consistency_status == "pass"
    assert review.object_dna_readiness == "pass"
    assert review.source_census_fingerprint
    assert len(review.source_census_member_ids) == 41
    assert review.mapped_source_member_ids == review.source_census_member_ids
    assert review.unmapped_source_member_ids == []


def test_synchronized_case_and_mapping_shrink_cannot_shrink_native_denominator(monkeypatch) -> None:
    blueprint, _ = _canonical_target()
    data = deepcopy(blueprint.model_dump(mode="json"))
    retained_case_id = "case.impact.restitution"
    data["behavior_cases"] = [
        item for item in data["behavior_cases"] if item["case_id"] == retained_case_id
    ]
    data["source_mappings"] = [
        item
        for item in data["source_mappings"]
        if not item["source_member_id"].startswith("fmi.case:")
        or retained_case_id in item["target_ids"]
    ]
    shrunk = PhysicalModelBlueprint.model_validate(data)

    review = _review(monkeypatch, shrunk)

    assert review.status != "pass"
    gap = next(item for item in review.gaps if item.code == "object_dna_source_member_unmapped")
    assert set(gap.target_ids) == {
        "fmi.case:free-flight-e-max",
        "fmi.case:free-flight-e-min",
        "fmi.case:impact-below-stop-threshold",
        "fmi.case:v-min-is-constant",
    }


def test_caller_dispositions_cannot_shrink_five_native_cases_to_one(monkeypatch) -> None:
    blueprint, _ = _canonical_target()
    data = deepcopy(blueprint.model_dump(mode="json"))
    retained_case_id = "case.impact.restitution"
    retained_native_case_id = "impact-restitution-e-0.7"
    data["behavior_cases"] = [
        item for item in data["behavior_cases"] if item["case_id"] == retained_case_id
    ]
    for mapping in data["source_mappings"]:
        if (
            mapping["source_member_id"].startswith("fmi.case:")
            and mapping["source_member_id"] != f"fmi.case:{retained_native_case_id}"
        ):
            mapping["relation"] = "dispositioned"
            mapping["target_ids"] = []
            mapping["reason"] = "Caller claims this native case is unnecessary."
    shrunk = PhysicalModelBlueprint.model_validate(data)

    review = _review(monkeypatch, shrunk)

    assert review.status == "blocked"
    missing_native_ids = {
        target_id
        for gap in review.gaps
        if gap.code == "object_dna_native_case_universe_mapping_invalid"
        for target_id in gap.target_ids
    }
    assert missing_native_ids == {
        "free-flight-e-max",
        "free-flight-e-min",
        "impact-below-stop-threshold",
        "v-min-is-constant",
    }


def test_coherent_velocity_gravity_target_swap_fails_typed_native_contract(monkeypatch) -> None:
    blueprint, _ = _canonical_target()
    data = deepcopy(blueprint.model_dump(mode="json"))
    velocity = next(
        item for item in data["source_mappings"] if item["source_member_id"] == "fmi.variable:v"
    )
    gravity = next(
        item for item in data["source_mappings"] if item["source_member_id"] == "fmi.variable:g"
    )
    velocity["target_ids"], gravity["target_ids"] = gravity["target_ids"], velocity["target_ids"]
    velocity["port_contracts"], gravity["port_contracts"] = (
        gravity["port_contracts"],
        velocity["port_contracts"],
    )

    review = _review(monkeypatch, PhysicalModelBlueprint.model_validate(data))

    assert review.status == "blocked"
    assert any(
        gap.code in {
            "object_dna_source_target_unit_mismatch",
            "object_dna_source_target_quantity_mismatch",
        }
        and "fmi.variable:v" in gap.target_ids
        for gap in review.gaps
    )


def test_wrong_non_defines_trigger_fails_exact_source_selector(monkeypatch) -> None:
    blueprint, _ = _canonical_target()
    data = deepcopy(blueprint.model_dump(mode="json"))
    trigger = next(
        item for item in data["semantics"] if item["semantic_id"] == "sem.impact.trigger"
    )
    trigger["expression"] = "event = (h < 0) and (v < 0)"

    review = _review(monkeypatch, PhysicalModelBlueprint.model_validate(data))

    assert review.status == "blocked"
    assert any(
        gap.code == "object_dna_semantic_selector_meaning_mismatch"
        and "sem.impact.trigger" in gap.target_ids
        for gap in review.gaps
    )


def test_wrong_equation_fails_against_independent_semantic_fact(monkeypatch) -> None:
    blueprint, _ = _canonical_target()
    data = deepcopy(blueprint.model_dump(mode="json"))
    rebound = next(
        item for item in data["semantics"] if item["semantic_id"] == "sem.impact.rebound"
    )
    rebound["expression"] = "candidate = e * v"

    review = _review(monkeypatch, PhysicalModelBlueprint.model_validate(data))

    assert review.status == "blocked"
    assert any(
        item.code == "object_dna_semantic_expression_mismatch"
        and "sem.impact.rebound" in item.target_ids
        for item in review.gaps
    )


def test_omitted_observed_source_mapping_blocks_object_dna(monkeypatch) -> None:
    blueprint, _ = _canonical_target()
    data = deepcopy(blueprint.model_dump(mode="json"))
    data["source_mappings"] = [
        item
        for item in data["source_mappings"]
        if item["source_member_id"] != "fmi.variable:v"
    ]

    review = _review(monkeypatch, PhysicalModelBlueprint.model_validate(data))

    assert review.status != "pass"
    assert any(
        item.code == "object_dna_source_member_unmapped"
        and "fmi.variable:v" in item.target_ids
        for item in review.gaps
    )


def test_wrong_source_target_mapping_blocks_reverse_model_coverage(monkeypatch) -> None:
    blueprint, _ = _canonical_target()
    data = deepcopy(blueprint.model_dump(mode="json"))
    velocity_mapping = next(
        item
        for item in data["source_mappings"]
        if item["source_member_id"] == "fmi.variable:v"
    )
    velocity_mapping["target_ids"] = ["port.impact.g_post"]
    velocity_mapping["port_contracts"] = []

    review = _review(monkeypatch, PhysicalModelBlueprint.model_validate(data))

    assert review.status != "pass"
    assert any(
        item.code == "object_dna_model_target_without_source"
        and "port.impact.v_post" in item.target_ids
        for item in review.gaps
    )


def test_rehashed_false_observed_value_fails_against_native_case_result(monkeypatch) -> None:
    blueprint, _ = _canonical_target()
    data = deepcopy(blueprint.model_dump(mode="json"))
    case = next(
        item
        for item in data["behavior_cases"]
        if item["case_id"] == "case.impact.restitution"
    )
    case["observed_output_values"]["port.impact.v_post"] = 999.0
    case["case_fingerprint"] = fingerprint_physical_behavior_case(case)

    review = _review(monkeypatch, PhysicalModelBlueprint.model_validate(data))

    assert review.status == "blocked"
    assert any(
        item.code == "object_dna_native_case_value_mismatch"
        and "port.impact.v_post" in item.target_ids
        for item in review.gaps
    )


def test_whole_and_affected_object_dna_keep_distinct_ids_and_global_denominator(monkeypatch) -> None:
    blueprint, authority = _canonical_target()
    _install_current_native_observations(monkeypatch, blueprint, authority)
    kwargs = {
        "target_inventory_authority": authority,
        "base_dir": EXAMPLE_ROOT,
    }

    whole = review_module.review_physical_model_blueprint(blueprint, **kwargs)
    affected = review_module.review_physical_model_blueprint(
        blueprint,
        affected_element_ids=["impact_event"],
        **kwargs,
    )

    assert whole.review_id != affected.review_id
    assert whole.logical_report_fingerprint != affected.logical_report_fingerprint
    assert whole.global_governed_member_ids == affected.global_governed_member_ids
    assert affected.outside_scope_member_ids
    assert set(affected.coverage.governed_member_ids) | set(affected.outside_scope_member_ids) == set(
        affected.global_governed_member_ids
    )


def test_portable_bundle_carries_compact_object_dna_closure(monkeypatch) -> None:
    blueprint, authority = _canonical_target()
    _install_current_native_observations(monkeypatch, blueprint, authority)
    review = review_module.review_physical_model_blueprint(
        blueprint,
        target_inventory_authority=authority,
        base_dir=EXAMPLE_ROOT,
    )

    bundle = build_physical_blueprint_export_bundle(blueprint, review, authority)
    status = query_physical_blueprint_export_bundle(bundle)

    assert bundle.understanding_target == "object_dna"
    assert bundle.object_dna_readiness == "pass"
    assert len(bundle.source_census) == 41
    assert len(bundle.source_mappings) == 41
    assert status.payload["source_census_fingerprint"] == review.source_census_fingerprint
    assert status.payload["native_behavior_case_universe_fingerprint"] == (
        review.native_behavior_case_universe_fingerprint
    )
    assert status.payload["target_counts"]["source_census_members"] == 41
    assert status.payload["target_counts"]["source_mappings"] == 41
    assert status.payload["target_counts"]["native_behavior_cases"] == 5


def test_object_dna_graph_keeps_observed_sources_and_mappings_as_distinct_nodes(
    monkeypatch,
) -> None:
    blueprint, authority = _canonical_target()
    _install_current_native_observations(monkeypatch, blueprint, authority)
    review = review_module.review_physical_model_blueprint(
        blueprint,
        target_inventory_authority=authority,
        base_dir=EXAMPLE_ROOT,
    )

    graph = compile_physical_blueprint_graph(blueprint, review)
    source_nodes = [item for item in graph.nodes if item.node_id.startswith("source:fmi.")]
    mapping_nodes = [
        item for item in graph.nodes if item.node_id.startswith("source-mapping:")
    ]
    relations = {item.relation for item in graph.edges}
    selector_nodes = [
        item for item in graph.nodes if item.node_id.startswith("source-selector:")
    ]

    assert len(source_nodes) == 41
    assert len(mapping_nodes) == 41
    assert len(selector_nodes) == 17
    assert all(item.fingerprint for item in source_nodes)
    assert {
        "source_mapping_source",
        "source_mapping_observation",
        "source_mapping_target",
        "source_semantic_selector",
        "source_selector_contract",
    } <= relations


def test_object_dna_trace_walks_both_source_to_model_and_model_to_source(
    monkeypatch,
) -> None:
    blueprint, authority = _canonical_target()
    _install_current_native_observations(monkeypatch, blueprint, authority)
    review = review_module.review_physical_model_blueprint(
        blueprint,
        target_inventory_authority=authority,
        base_dir=EXAMPLE_ROOT,
    )
    trace_kwargs = {
        "target_inventory_authority": authority,
        "blueprint_base_dir": EXAMPLE_ROOT,
        "authority_base_dir": EXAMPLE_ROOT,
    }

    affected = affected_physical_blueprint_projection(
        blueprint,
        review,
        ["fmi.semantic:oracle.impact-momentum-reflection:candidate"],
        **trace_kwargs,
    )
    reverse = reverse_trace_physical_blueprint_projection(
        blueprint,
        review,
        ["port.impact.v_post"],
        **trace_kwargs,
    )
    reverse_case = reverse_trace_physical_blueprint_projection(
        blueprint,
        review,
        ["case.impact.restitution"],
        **trace_kwargs,
    )

    assert affected.trace_status == "pass"
    assert {
        "semantic:sem.impact.rebound",
        "port:port.impact.rebound_candidate",
        "case:case.impact.restitution",
    } <= set(affected.included_member_ids)
    assert reverse.trace_status == "pass"
    assert "source:fmi.variable:v" in reverse.included_member_ids
    assert "source:fmi.variable:v" in reverse.terminal_resource_ids
    assert reverse_case.trace_status == "pass"
    assert (
        "source:fmi.case:impact-restitution-e-0.7"
        in reverse_case.included_member_ids
    )


def test_model_change_carries_exact_source_mapping_revalidation_context(
    monkeypatch,
) -> None:
    blueprint, authority = _canonical_target()
    _install_current_native_observations(monkeypatch, blueprint, authority)
    review = review_module.review_physical_model_blueprint(
        blueprint,
        target_inventory_authority=authority,
        base_dir=EXAMPLE_ROOT,
    )

    affected = affected_physical_blueprint_projection(
        blueprint,
        review,
        ["sem.impact.rebound"],
        target_inventory_authority=authority,
        blueprint_base_dir=EXAMPLE_ROOT,
        authority_base_dir=EXAMPLE_ROOT,
    )

    assert affected.trace_status == "pass"
    assert "source-mapping:source-map.028" in affected.included_member_ids
    assert (
        "source:fmi.semantic:oracle.impact-momentum-reflection:candidate"
        in affected.included_member_ids
    )
    assert "binding:binding.bouncing_ball.test" in affected.included_member_ids
