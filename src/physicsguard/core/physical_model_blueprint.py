"""Read-only qualification of canonical PhysicsGuard physical blueprints."""

from __future__ import annotations

import hashlib
import math
from collections import defaultdict
from pathlib import Path
from typing import Iterable

from physicsguard.core.physical_model_blueprint_adapters import (
    NativeAuthorityObservation,
    observe_native_bindings,
)
from physicsguard.core.target_inventory_authority import (
    TargetInventoryAuthorityObservation,
    observe_target_inventory_authority,
)
from physicsguard.schema.physical_model_blueprint import (
    ArtifactReference,
    BlueprintCoverage,
    BlueprintGap,
    BlueprintLayerName,
    BlueprintLayerResult,
    PhysicalElement,
    PhysicalModelBlueprint,
    PhysicalModelBlueprintReview,
    ObservedNativeBehaviorCase,
    ObservedSourceMember,
    PhysicalPort,
    ReviewStatus,
    TargetInventoryAuthority,
    canonical_blueprint_fingerprint,
    fingerprint_blueprint,
    fingerprint_review,
)


BLUEPRINT_LAYER_ORDER: tuple[BlueprintLayerName, ...] = (
    "target_inventory",
    "hierarchy_ownership",
    "typed_interfaces",
    "independent_physical_semantics",
    "parent_child_refinement",
    "native_model_code_test",
    "resource_oracle",
    "static_blueprint",
)


def review_physical_model_blueprint(
    blueprint: PhysicalModelBlueprint,
    *,
    target_inventory_authority: TargetInventoryAuthority,
    base_dir: str | Path | None = None,
    authority_base_dir: str | Path | None = None,
    affected_element_ids: Iterable[str] | None = None,
) -> PhysicalModelBlueprintReview:
    """Derive bounded depth, replaying only explicitly bound native owners."""

    root = None if base_dir is None else Path(base_dir)
    authority_root = None if authority_base_dir is None else Path(authority_base_dir)
    blueprint_fingerprint = fingerprint_blueprint(blueprint)
    element_by_id = {item.element_id: item for item in blueprint.elements}
    port_by_id = {item.port_id: item for item in blueprint.ports}
    semantic_by_id = {item.semantic_id: item for item in blueprint.semantics}
    binding_by_id = {item.binding_id: item for item in blueprint.bindings}
    provider_by_id = {item.provider_id: item for item in blueprint.providers}
    observations = observe_native_bindings(
        blueprint.bindings,
        base_dir=root,
        providers=provider_by_id,
        target_system_id=blueprint.target.target_system_id,
        subject_revision=blueprint.target.subject_revision,
        executions={item.execution_id: item for item in blueprint.native_executions},
    )
    inventory_authority_observation = observe_target_inventory_authority(
        target_inventory_authority,
        base_dir=authority_root,
    )

    scope, selected_elements, scope_gaps = _select_scope(
        blueprint,
        element_by_id,
        affected_element_ids,
    )
    layer_gaps: dict[BlueprintLayerName, list[BlueprintGap]] = {
        layer: [] for layer in BLUEPRINT_LAYER_ORDER
    }
    layer_gaps["target_inventory"].extend(scope_gaps)
    if blueprint.artifact_root == "explicit_material_root" and root is None:
        layer_gaps["target_inventory"].append(
            _gap(
                "target_inventory",
                "blocked",
                "external_resource_not_run",
                [blueprint.blueprint_id, blueprint.target.target_system_id],
                "this reusable blueprint requires an explicit external material root; no target bytes or native owner were executed",
                "supply the exact material root explicitly and rerun the same public review",
            )
        )

    governed_ids, covered_ids = _review_target_inventory(
        blueprint,
        selected_elements,
        provider_by_id,
        binding_by_id,
        target_inventory_authority,
        inventory_authority_observation,
        authority_root,
        layer_gaps["target_inventory"],
    )
    _review_hierarchy(blueprint, selected_elements, layer_gaps["hierarchy_ownership"])
    _review_interfaces(
        blueprint,
        selected_elements,
        port_by_id,
        semantic_by_id,
        observations,
        layer_gaps["typed_interfaces"],
    )
    for relation in blueprint.unresolved_relations:
        if set(relation.source_ids) | set(relation.target_ids):
            layer_gaps["typed_interfaces"].append(
                _gap(
                    "typed_interfaces",
                    "stale" if relation.status == "stale" else ("blocked" if relation.status == "unsupported" else "incomplete"),
                    "unresolved_physical_relation",
                    [relation.relation_id, *relation.source_ids, *relation.target_ids],
                    f"physical relation is {relation.status}: {relation.reason}",
                    "resolve one exact typed relation or keep the affected claim bounded at this gap",
                )
            )
    _review_physical_semantics(
        blueprint,
        selected_elements,
        port_by_id,
        semantic_by_id,
        layer_gaps["independent_physical_semantics"],
    )
    _review_refinement(
        blueprint,
        selected_elements,
        semantic_by_id,
        observations,
        layer_gaps["parent_child_refinement"],
    )
    _review_native_model_code_test(
        blueprint,
        selected_elements,
        semantic_by_id,
        observations,
        layer_gaps["native_model_code_test"],
    )
    _review_resource_oracle(
        blueprint,
        selected_elements,
        semantic_by_id,
        observations,
        layer_gaps["resource_oracle"],
    )

    declared_consistency_status = _overall_status(
        gap for items in layer_gaps.values() for gap in items
    )
    (
        source_census,
        source_census_fingerprint,
        source_census_conflicts,
    ) = _collect_source_census(observations)
    (
        native_case_universe,
        native_case_universe_fingerprint,
        native_case_universe_conflicts,
    ) = _collect_native_case_universe(observations)
    mapped_source_ids = {
        mapping.source_member_id
        for mapping in blueprint.source_mappings
        if mapping.source_member_id in source_census
    }
    if blueprint.understanding_target == "object_dna":
        _review_object_dna(
            blueprint,
            selected_elements,
            observations,
            source_census,
            source_census_conflicts,
            native_case_universe,
            native_case_universe_conflicts,
            layer_gaps,
        )

    layer_results = _derive_layer_results(layer_gaps, blueprint, selected_elements)
    gaps = sorted(
        (gap for items in layer_gaps.values() for gap in items),
        key=lambda item: (
            BLUEPRINT_LAYER_ORDER.index(item.layer),
            item.code,
            item.target_ids,
            item.gap_id,
        ),
    )
    layer_results[-1] = _static_closure_result(layer_results[:-1], gaps, blueprint, selected_elements)
    deepest = _deepest_contiguous_layer(layer_results)
    status = _overall_status(gaps)
    uncovered_ids = sorted(set(governed_ids) - set(covered_ids))
    global_governed_ids = sorted(
        item.member_id
        for item in (
            inventory_authority_observation.inventory.members
            if inventory_authority_observation.inventory is not None
            else []
        )
    )
    outside_scope_member_ids = sorted(set(global_governed_ids) - set(governed_ids))
    coverage = BlueprintCoverage(
        governed_member_ids=sorted(governed_ids),
        covered_member_ids=sorted(set(covered_ids)),
        uncovered_member_ids=uncovered_ids,
    )
    external_identity_only_binding_ids = sorted(
        binding_id
        for binding_id, observation in observations.items()
        if observation.subject_identity_verified and not observation.content_verified
    )
    byte_identity_only_binding_ids = sorted(
        binding_id
        for binding_id, observation in observations.items()
        if observation.current
        and observation.content_verified
        and not observation.subject_identity_verified
    )
    safe_claim, unsafe_claim = _claims(
        blueprint,
        status,
        deepest,
        scope,
        external_identity_only_binding_ids,
        byte_identity_only_binding_ids,
        blueprint.understanding_target,
        declared_consistency_status,
    )
    scope_identity = canonical_blueprint_fingerprint(
        {
            "blueprint_fingerprint": blueprint_fingerprint,
            "scope": scope,
            "selected_element_ids": sorted(selected_elements),
            "inventory_fingerprint": (
                inventory_authority_observation.expected_inventory_fingerprint
                or target_inventory_authority.inventory.inventory_fingerprint
            ),
            "source_census_fingerprint": source_census_fingerprint,
        }
    )
    payload = {
        "schema_version": "physicsguard.physical-model-blueprint-review.v1",
        "review_id": (
            f"blueprint-review:{blueprint.blueprint_id}:{scope}:{scope_identity[:16]}"
        ),
        "status": status,
        "scope": scope,
        "understanding_target": blueprint.understanding_target,
        "declared_consistency_status": declared_consistency_status,
        "object_dna_readiness": (
            status if blueprint.understanding_target == "object_dna" else "not_requested"
        ),
        "target_system_id": blueprint.target.target_system_id,
        "subject_revision": blueprint.target.subject_revision,
        "blueprint_fingerprint": blueprint_fingerprint,
        "inventory_fingerprint": (
            inventory_authority_observation.expected_inventory_fingerprint
            or target_inventory_authority.inventory.inventory_fingerprint
        ),
        "target_inventory_authority_fingerprint": target_inventory_authority.authority_fingerprint,
        "provider_registry_fingerprint": inventory_authority_observation.provider_registry_fingerprint,
        "layer_results": [item.model_dump(mode="json") for item in layer_results],
        "deepest_licensed_layer": deepest,
        "first_gap_id": gaps[0].gap_id if gaps else None,
        "gaps": [gap.model_dump(mode="json") for gap in gaps],
        "coverage": coverage.model_dump(mode="json"),
        "global_governed_member_ids": global_governed_ids,
        "outside_scope_member_ids": outside_scope_member_ids,
        "source_census_fingerprint": source_census_fingerprint,
        "source_census": [source_census[item] for item in sorted(source_census)],
        "source_census_member_ids": sorted(source_census),
        "mapped_source_member_ids": sorted(mapped_source_ids),
        "unmapped_source_member_ids": sorted(set(source_census) - mapped_source_ids),
        "native_behavior_case_universe_fingerprint": native_case_universe_fingerprint,
        "native_behavior_case_universe": [
            native_case_universe[item] for item in sorted(native_case_universe)
        ],
        "required_native_behavior_case_ids": sorted(
            case_id
            for case_id, item in native_case_universe.items()
            if item.get("disposition") == "required"
        ),
        "mapped_native_behavior_case_ids": sorted(
            case_id
            for case_id, item in native_case_universe.items()
            if item.get("disposition") == "required"
            and any(
                case.native_case_id == case_id
                and case.owner_element_id in selected_elements
                for case in blueprint.behavior_cases
            )
        ),
        "unmapped_native_behavior_case_ids": sorted(
            case_id
            for case_id, item in native_case_universe.items()
            if item.get("disposition") == "required"
            and not any(
                case.native_case_id == case_id
                and case.owner_element_id in selected_elements
                for case in blueprint.behavior_cases
            )
        ),
        "dispositioned_native_behavior_case_ids": sorted(
            case_id
            for case_id, item in native_case_universe.items()
            if item.get("disposition") == "dispositioned"
        ),
        "affected_element_ids": sorted(selected_elements) if scope == "affected" else [],
        "external_identity_only_binding_ids": external_identity_only_binding_ids,
        "byte_identity_only_binding_ids": byte_identity_only_binding_ids,
        "safe_claim": safe_claim,
        "unsafe_claim_boundary": unsafe_claim,
    }
    payload["logical_report_fingerprint"] = fingerprint_review(payload)
    return PhysicalModelBlueprintReview.model_validate(payload)


def physical_model_blueprint_review_to_dict(
    review: PhysicalModelBlueprintReview,
) -> dict[str, object]:
    return review.model_dump(mode="json", exclude_none=False)


def _select_scope(
    blueprint: PhysicalModelBlueprint,
    element_by_id: dict[str, PhysicalElement],
    affected_element_ids: Iterable[str] | None,
) -> tuple[str, set[str], list[BlueprintGap]]:
    if affected_element_ids is None:
        return "whole", set(element_by_id), []
    requested = sorted(set(affected_element_ids))
    selected: set[str] = set()
    gaps: list[BlueprintGap] = []
    for element_id in requested:
        if element_id not in element_by_id:
            gaps.append(
                _gap(
                    "target_inventory",
                    "blocked",
                    "unknown_affected_element",
                    [element_id],
                    f"affected element is absent from blueprint {blueprint.blueprint_id}",
                    "supply an exact current blueprint element identity",
                )
            )
            continue
        current = element_by_id[element_id]
        while True:
            selected.add(current.element_id)
            if current.parent_id is None:
                break
            current = element_by_id[current.parent_id]
    return "affected", selected, gaps


def _review_target_inventory(
    blueprint: PhysicalModelBlueprint,
    selected_elements: set[str],
    providers: dict[str, object],
    bindings: dict[str, object],
    authority: TargetInventoryAuthority,
    authority_observation: TargetInventoryAuthorityObservation,
    authority_base_dir: Path | None,
    gaps: list[BlueprintGap],
) -> tuple[list[str], list[str]]:
    if (
        authority.target_system_id != blueprint.target.target_system_id
        or authority.subject_revision != blueprint.target.subject_revision
        or authority.boundary_fingerprint != blueprint.target.boundary_fingerprint
    ):
        gaps.append(
            _gap(
                "target_inventory",
                "stale",
                "target_inventory_authority_target_mismatch",
                [authority.authority_id, blueprint.target.target_system_id],
                "target inventory authority does not govern the exact blueprint target, revision, and boundary",
                "supply the frozen authority issued for this exact target revision",
            )
        )
    if authority_observation.status != "pass":
        gaps.append(
            _gap(
                "target_inventory",
                "stale" if authority_observation.status == "stale" else "blocked",
                "target_inventory_authority_not_verified",
                [authority.authority_id, authority.provider_id],
                "; ".join(authority_observation.findings)
                or "target inventory authority has no current replay result",
                "replay the exact frozen authority through its current registered execution owner",
            )
        )
    for provider in blueprint.providers:
        if provider.target_system_id != blueprint.target.target_system_id or provider.subject_revision != blueprint.target.subject_revision:
            gaps.append(
                _gap(
                    "target_inventory",
                    "blocked",
                    "provider_target_identity_mismatch",
                    [provider.provider_id],
                    "provider result does not name the blueprint target and subject revision",
                    "refresh the provider result for the exact target revision",
                )
            )
    for capability_id in blueprint.required_capability_ids:
        provider_id = blueprint.capability_owners[capability_id]
        provider = providers[provider_id]
        if provider.status != "current":
            gaps.append(
                _gap(
                    "target_inventory",
                    "stale" if provider.status == "stale" else "blocked",
                    "required_provider_capability_not_current",
                    [capability_id, provider_id],
                    f"required capability {capability_id} is owned by a provider with status {provider.status}",
                    "refresh or resolve the declared provider without selecting a fallback",
                )
            )
    inventory_provider = providers[blueprint.inventory.provider_id]
    if "artifact_inventory" not in inventory_provider.capability_ids:
        gaps.append(
            _gap(
                "target_inventory",
                "blocked",
                "inventory_provider_missing_capability",
                [inventory_provider.provider_id],
                "independent inventory provider does not advertise artifact_inventory",
                "supply one current provider that explicitly owns artifact_inventory",
            )
        )
    expected_inventory_fingerprint = authority_observation.expected_inventory_fingerprint
    if (
        expected_inventory_fingerprint is not None
        and inventory_provider.payload_fingerprint != expected_inventory_fingerprint
    ):
        gaps.append(
            _gap(
                "target_inventory",
                "stale",
                "inventory_provider_payload_mismatch",
                [inventory_provider.provider_id, blueprint.inventory.inventory_id],
                "blueprint provider payload fingerprint does not equal the runtime-owned derived inventory fingerprint",
                "bind the blueprint provider observation to the current runtime-owned target-material request",
            )
        )

    blueprint_inventory = blueprint.inventory
    authority_inventory = authority_observation.inventory
    if authority_inventory is None:
        return [], []
    if (
        blueprint_inventory.inventory_id != authority_inventory.inventory_id
        or blueprint_inventory.provider_id != authority_inventory.provider_id
        or blueprint_inventory.target_system_id != authority_inventory.target_system_id
        or blueprint_inventory.subject_revision != authority_inventory.subject_revision
        or blueprint_inventory.boundary_fingerprint != authority_inventory.boundary_fingerprint
    ):
        gaps.append(
            _gap(
                "target_inventory",
                "stale",
                "blueprint_inventory_authority_identity_mismatch",
                [blueprint_inventory.inventory_id, authority_inventory.inventory_id],
                "blueprint inventory identity does not equal the frozen target inventory authority",
                "bind the blueprint to the exact externally issued inventory identity",
            )
        )
    blueprint_members = {item.member_id: item for item in blueprint_inventory.members}
    authority_members = {item.member_id: item for item in authority_inventory.members}
    missing_member_ids = sorted(set(authority_members) - set(blueprint_members))
    extra_member_ids = sorted(set(blueprint_members) - set(authority_members))
    if missing_member_ids:
        gaps.append(
            _gap(
                "target_inventory",
                "incomplete",
                "target_inventory_authority_member_missing",
                missing_member_ids,
                "caller blueprint omits members present in the frozen target inventory authority",
                "restore every authoritative member and give it one explicit disposition",
            )
        )
    if extra_member_ids:
        gaps.append(
            _gap(
                "target_inventory",
                "blocked",
                "blueprint_inventory_member_not_authorized",
                extra_member_ids,
                "caller blueprint invents inventory members absent from the frozen target authority",
                "refresh the external authority or remove the unauthorized caller member",
            )
        )
    changed_member_ids = sorted(
        member_id
        for member_id in set(authority_members) & set(blueprint_members)
        if authority_members[member_id].model_dump(mode="json", exclude_none=True)
        != blueprint_members[member_id].model_dump(mode="json", exclude_none=True)
    )
    if changed_member_ids:
        gaps.append(
            _gap(
                "target_inventory",
                "blocked",
                "blueprint_inventory_member_disposition_mismatch",
                changed_member_ids,
                "caller inventory changes the authoritative member identity, disposition, or binding",
                "copy the exact frozen member disposition or refresh the independent authority",
            )
        )
    if blueprint_inventory.inventory_fingerprint != authority_inventory.inventory_fingerprint:
        gaps.append(
            _gap(
                "target_inventory",
                "stale",
                "blueprint_inventory_authority_fingerprint_mismatch",
                [blueprint_inventory.inventory_id, authority_inventory.inventory_id],
                "caller inventory fingerprint does not equal the frozen authority denominator",
                "bind the current blueprint to the current target inventory authority",
            )
        )

    for caller_member in blueprint_inventory.members:
        if caller_member.blueprint_element_id is None:
            continue
        foreign_bindings = sorted(
            binding_id
            for binding_id in caller_member.binding_ids
            if binding_id in bindings
            and bindings[binding_id].owner_element_id
            != caller_member.blueprint_element_id
        )
        if foreign_bindings:
            gaps.append(
                _gap(
                    "target_inventory",
                    "blocked",
                    "inventory_binding_owner_mismatch",
                    [
                        caller_member.member_id,
                        caller_member.blueprint_element_id,
                        *foreign_bindings,
                    ],
                    "caller inventory binds one physical element to artifacts owned by another element",
                    "restore the exact authoritative member or bind only artifacts owned by its declared element",
                )
            )

    governed: list[str] = []
    covered: list[str] = []
    all_element_ids = {item.element_id for item in blueprint.elements}
    whole_scope = selected_elements == all_element_ids
    for member in authority_inventory.members:
        binding_owner_ids = {
            bindings[binding_id].owner_element_id
            for binding_id in member.binding_ids
            if binding_id in bindings
        }
        member_touches_scope = (
            member.blueprint_element_id in selected_elements
            or bool(binding_owner_ids & selected_elements)
        )
        if not whole_scope and not member_touches_scope:
            continue
        governed.append(member.member_id)
        if member.blueprint_element_id is not None:
            foreign_bindings = sorted(
                binding_id
                for binding_id in member.binding_ids
                if binding_id in bindings
                and bindings[binding_id].owner_element_id
                != member.blueprint_element_id
            )
            if foreign_bindings:
                gaps.append(
                    _gap(
                        "target_inventory",
                        "blocked",
                        "inventory_binding_owner_mismatch",
                        [member.member_id, member.blueprint_element_id, *foreign_bindings],
                        "inventory member binds one physical element but points to native artifacts owned by another element",
                        "split the inventory observation or bind only artifacts owned by its declared blueprint element",
                    )
                )
        caller_member = blueprint_members.get(member.member_id)
        caller_member_exact = (
            caller_member is not None
            and caller_member.model_dump(mode="json", exclude_none=True)
            == member.model_dump(mode="json", exclude_none=True)
        )
        modeled_endpoint_current = (
            member.blueprint_element_id is not None
            and member.blueprint_element_id in all_element_ids
        )
        supporting_endpoints_current = bool(member.binding_ids) and all(
            binding_id in bindings for binding_id in member.binding_ids
        )
        if member.disposition == "modeled":
            if caller_member_exact and modeled_endpoint_current:
                covered.append(member.member_id)
        elif member.disposition == "supporting":
            if caller_member_exact and supporting_endpoints_current:
                covered.append(member.member_id)
        elif member.disposition == "excluded":
            stale_evidence = [
                reference
                for reference in member.disposition_evidence
                if not _artifact_reference_current(reference, authority_base_dir)
            ]
            if stale_evidence:
                gaps.append(
                    _gap(
                        "target_inventory",
                        "stale",
                        "excluded_member_evidence_not_current",
                        [member.member_id],
                        "excluded inventory member lacks current disposition evidence",
                        "refresh the exact exclusion evidence or return the member to unresolved",
                    )
                )
            elif caller_member_exact:
                covered.append(member.member_id)
        else:
            gaps.append(
                _gap(
                    "target_inventory",
                    "blocked" if member.disposition == "unsupported" else "incomplete",
                    f"inventory_member_{member.disposition}",
                    [member.member_id],
                    f"inventory member remains {member.disposition}: {member.reason}",
                    "model the member or record a current evidenced terminal disposition",
                )
            )
    for element_id in sorted(selected_elements):
        if not any(item.blueprint_element_id == element_id for item in authority_inventory.members):
            gaps.append(
                _gap(
                    "target_inventory",
                    "incomplete",
                    "element_missing_inventory_member",
                    [element_id],
                    "blueprint element is absent from the independent inventory",
                    "add the independently observed element to the inventory denominator",
                )
            )
    for member in authority_inventory.members:
        for binding_id in member.binding_ids:
            if binding_id not in bindings:
                gaps.append(
                    _gap(
                        "target_inventory",
                        "blocked",
                        "inventory_unknown_binding",
                        [member.member_id, binding_id],
                        "inventory member references an unknown native binding",
                        "bind the member to one exact current native artifact",
                    )
                )
    return governed, covered


def _review_hierarchy(
    blueprint: PhysicalModelBlueprint,
    selected_elements: set[str],
    gaps: list[BlueprintGap],
) -> None:
    roots = [item.element_id for item in blueprint.elements if item.parent_id is None]
    if len(roots) != 1:
        gaps.append(
            _gap(
                "hierarchy_ownership",
                "blocked",
                "root_count_invalid",
                roots,
                "physical blueprint must have exactly one root",
                "declare one root and attach every in-scope child",
            )
        )
    owned: dict[str, str] = {}
    for element in blueprint.elements:
        if element.element_id not in selected_elements:
            continue
        for behavior_id in element.owned_behavior_ids:
            previous = owned.get(behavior_id)
            if previous is not None:
                gaps.append(
                    _gap(
                        "hierarchy_ownership",
                        "blocked",
                        "duplicate_primary_behavior_owner",
                        [behavior_id, previous, element.element_id],
                        "physical behavior has more than one primary owner",
                        "retain exactly one primary owner and use supporting relations elsewhere",
                    )
                )
            owned[behavior_id] = element.element_id


def _review_interfaces(
    blueprint: PhysicalModelBlueprint,
    selected_elements: set[str],
    ports: dict[str, PhysicalPort],
    semantics: dict[str, object],
    observations: dict[str, NativeAuthorityObservation],
    gaps: list[BlueprintGap],
) -> None:
    element_by_id = {item.element_id: item for item in blueprint.elements}
    for refinement in blueprint.refinements:
        if refinement.parent_element_id not in selected_elements:
            continue
        mapping_by_target = defaultdict(list)
        mapping_by_source = defaultdict(list)
        for mapping in refinement.port_mappings:
            mapping_by_target[mapping.target_port_id].append(mapping)
            if mapping.source_port_id:
                mapping_by_source[mapping.source_port_id].append(mapping)
                _review_mapping_compatibility(mapping, ports, semantics, observations, gaps)
        for child_id in refinement.child_element_ids:
            child = element_by_id[child_id]
            for port_id in child.port_ids:
                port = ports[port_id]
                if port.direction == "input" and port.required and not mapping_by_target[port_id]:
                    gaps.append(
                        _gap(
                            "typed_interfaces",
                            "incomplete",
                            "required_child_input_unmapped",
                            [refinement.refinement_id, port_id],
                            "required child input has no parent, sibling, state, or external source",
                            "add one exact typed source mapping",
                        )
                    )
                elif port.direction == "output" and not mapping_by_source[port_id] and port_id not in refinement.terminal_output_ids:
                    gaps.append(
                        _gap(
                            "typed_interfaces",
                            "incomplete",
                            "child_output_unconsumed",
                            [refinement.refinement_id, port_id],
                            "child output is neither consumed, exported, retained, nor terminally dispositioned",
                            "map or explicitly disposition the child output with evidence",
                        )
                    )
                elif port.direction == "state" and not mapping_by_source[port_id] and port_id not in refinement.child_local_state_ids:
                    gaps.append(
                        _gap(
                            "typed_interfaces",
                            "incomplete",
                            "child_state_not_accounted",
                            [refinement.refinement_id, port_id],
                            "child state disappears at the parent boundary",
                            "map it to parent state or declare it child-local",
                        )
                    )
                elif port.direction == "effect" and not mapping_by_source[port_id] and port_id not in refinement.terminal_effect_ids:
                    gaps.append(
                        _gap(
                            "typed_interfaces",
                            "incomplete",
                            "child_effect_not_propagated",
                            [refinement.refinement_id, port_id],
                            "child effect has no visible parent or terminal boundary",
                            "map the effect or record its terminal disposition",
                        )
                    )
        parent = element_by_id[refinement.parent_element_id]
        for port_id in parent.port_ids:
            port = ports[port_id]
            if port.direction == "output" and port.required:
                produced_by_mapping = bool(mapping_by_target[port_id])
                produced_by_semantic = any(port_id in semantic.output_port_ids for semantic in semantics.values())
                if not produced_by_mapping and not produced_by_semantic:
                    gaps.append(
                        _gap(
                            "typed_interfaces",
                            "incomplete",
                            "parent_output_has_no_source",
                            [parent.element_id, port_id],
                            "required parent output has no child aggregation or parent-owned semantic source",
                            "bind a child output mapping or parent semantic producer",
                        )
                    )


def _review_mapping_compatibility(
    mapping: object,
    ports: dict[str, PhysicalPort],
    semantics: dict[str, object],
    observations: dict[str, NativeAuthorityObservation],
    gaps: list[BlueprintGap],
) -> None:
    source = ports[mapping.source_port_id]
    target = ports[mapping.target_port_id]
    mismatches = []
    for field_name in ("quantity_id", "unit", "time_basis", "value_shape", "reference_frame", "sign_convention"):
        if getattr(source, field_name) != getattr(target, field_name):
            mismatches.append(field_name)
    if mismatches and mapping.conversion_semantic_id is None:
        gaps.append(
            _gap(
                "typed_interfaces",
                "blocked",
                "interface_contract_mismatch",
                [mapping.mapping_id, source.port_id, target.port_id],
                f"connected interfaces differ in {', '.join(mismatches)} without a conversion semantic",
                "declare an exact conversion semantic or make the interface contracts agree",
            )
        )
    if mapping.conversion_semantic_id is not None:
        semantic = semantics[mapping.conversion_semantic_id]
        if semantic.semantic_kind != "conversion":
            gaps.append(
                _gap(
                    "typed_interfaces",
                    "blocked",
                    "invalid_conversion_semantic",
                    [mapping.mapping_id, mapping.conversion_semantic_id],
                    "interface conversion does not point to a conversion semantic",
                    "bind one source-independent conversion semantic",
                )
            )
    for binding_id in mapping.evidence_binding_ids:
        observation = observations[binding_id]
        if not observation.current:
            gaps.append(_binding_gap("typed_interfaces", observation, mapping.mapping_id))


def _review_physical_semantics(
    blueprint: PhysicalModelBlueprint,
    selected_elements: set[str],
    ports: dict[str, PhysicalPort],
    semantics: dict[str, object],
    gaps: list[BlueprintGap],
) -> None:
    for element in blueprint.elements:
        if element.element_id not in selected_elements or element.supporting_only:
            continue
        element_semantics = [semantics[item] for item in element.semantic_ids]
        independent_relations = [
            semantic
            for semantic in element_semantics
            if semantic.semantic_kind
            in {
                "equation",
                "residual",
                "constraint",
                "state_update",
                "invariant",
                "protected_failure",
                "conservation_law",
                "constitutive_relation",
                "conversion",
                "guarantee",
            }
        ]
        if not independent_relations:
            gaps.append(
                _gap(
                    "independent_physical_semantics",
                    "incomplete",
                    "element_has_no_independent_physical_relation",
                    [element.element_id],
                    "physical element lists structure or declarations but no source-independent equation, residual, constraint, update, invariant, conservation, or constitutive relation",
                    "state the applicable equations, residuals, constraints, assumptions, or validity semantics",
                )
            )
        referenced_ports = {
            port_id
            for semantic in element_semantics
            for port_id in (
                *semantic.input_port_ids,
                *semantic.output_port_ids,
                *semantic.state_port_ids,
                *semantic.effect_port_ids,
            )
        }
        for port_id in element.port_ids:
            port = ports[port_id]
            if port.required and port_id not in referenced_ports:
                gaps.append(
                    _gap(
                        "independent_physical_semantics",
                        "incomplete",
                        "required_port_has_no_semantic",
                        [element.element_id, port_id],
                        "required physical interface is not used by an independent semantic",
                        "bind the interface to the exact semantic that consumes or produces it",
                    )
                )
            if port.direction == "state":
                state_updates = [
                    semantic
                    for semantic in element_semantics
                    if semantic.semantic_kind == "state_update" and port_id in semantic.state_port_ids
                ]
                if not state_updates:
                    gaps.append(
                        _gap(
                            "independent_physical_semantics",
                            "blocked",
                            "state_port_has_no_update_semantic",
                            [element.element_id, port_id],
                            "stateful behavior has no state-update contract",
                            "bind an initial state, time basis, and explicit state-update semantic",
                        )
                    )
                if port.termination_semantic_id is None:
                    gaps.append(
                        _gap(
                            "independent_physical_semantics",
                            "incomplete",
                            "state_port_has_no_termination_semantic",
                            [element.element_id, port_id],
                            "stateful behavior has no declared terminal or handoff condition",
                            "bind an explicit termination semantic or keep the state lifecycle incomplete",
                        )
                    )


def _collect_source_census(
    observations: dict[str, NativeAuthorityObservation],
) -> tuple[dict[str, dict[str, object]], str | None, list[str]]:
    census: dict[str, dict[str, object]] = {}
    conflicts: list[str] = []
    for observation in observations.values():
        if not observation.qualifies_native_execution:
            continue
        if observation.source_census:
            observed_census_fingerprint = canonical_blueprint_fingerprint(
                list(observation.source_census)
            )
            if observation.source_census_fingerprint != observed_census_fingerprint:
                conflicts.append(f"{observation.binding_id}:source-census-fingerprint")
                continue
        for member in observation.source_census:
            source_member_id = member.get("source_member_id")
            if not isinstance(source_member_id, str) or not source_member_id:
                continue
            try:
                normalized_member = ObservedSourceMember.model_validate(member).model_dump(
                    mode="json", exclude_none=True
                )
            except ValueError:
                conflicts.append(f"{observation.binding_id}:{source_member_id}:invalid-source-member")
                continue
            previous = census.get(source_member_id)
            if previous is not None and previous != normalized_member:
                conflicts.append(source_member_id)
                continue
            census[source_member_id] = normalized_member
    if not census:
        return {}, None, sorted(set(conflicts))
    return (
        census,
        canonical_blueprint_fingerprint([census[item] for item in sorted(census)]),
        sorted(set(conflicts)),
    )


def _collect_native_case_universe(
    observations: dict[str, NativeAuthorityObservation],
) -> tuple[dict[str, dict[str, object]], str | None, list[str]]:
    universe: dict[str, dict[str, object]] = {}
    conflicts: list[str] = []
    for observation in observations.values():
        if not (
            observation.qualifies_native_execution
            and observation.object_dna_contract_verified
        ):
            continue
        observed_fingerprint = canonical_blueprint_fingerprint(
            list(observation.native_case_universe)
        )
        if observation.native_case_universe_fingerprint != observed_fingerprint:
            conflicts.append(f"{observation.binding_id}:native-case-universe-fingerprint")
            continue
        for item in observation.native_case_universe:
            case_id = item.get("native_case_id")
            if not isinstance(case_id, str) or not case_id:
                conflicts.append(f"{observation.binding_id}:native-case-without-id")
                continue
            try:
                normalized_case = ObservedNativeBehaviorCase.model_validate(item).model_dump(
                    mode="json", exclude_none=True
                )
            except ValueError:
                conflicts.append(f"{observation.binding_id}:{case_id}:invalid-native-case")
                continue
            previous = universe.get(case_id)
            if previous is not None and previous != normalized_case:
                conflicts.append(case_id)
                continue
            universe[case_id] = normalized_case
    if not universe:
        return {}, None, sorted(set(conflicts))
    return (
        universe,
        canonical_blueprint_fingerprint([universe[item] for item in sorted(universe)]),
        sorted(set(conflicts)),
    )


def _review_object_dna(
    blueprint: PhysicalModelBlueprint,
    selected_elements: set[str],
    observations: dict[str, NativeAuthorityObservation],
    source_census: dict[str, dict[str, object]],
    source_census_conflicts: list[str],
    native_case_universe: dict[str, dict[str, object]],
    native_case_universe_conflicts: list[str],
    layer_gaps: dict[BlueprintLayerName, list[BlueprintGap]],
) -> None:
    verified_object_dna_observations = {
        binding_id: observation
        for binding_id, observation in observations.items()
        if observation.qualifies_native_execution
        and observation.object_dna_contract_verified
    }
    if not verified_object_dna_observations:
        layer_gaps["target_inventory"].append(
            _gap(
                "target_inventory",
                "blocked",
                "object_dna_verified_native_adapter_missing",
                [blueprint.blueprint_id],
                "object-DNA readiness has no independently replayed, current provider-neutral native observation contract",
                "bind one verified native object-DNA observation; each provider must emit the same strict neutral contract",
            )
        )
    if not source_census:
        layer_gaps["target_inventory"].append(
            _gap(
                "target_inventory",
                "blocked",
                "object_dna_source_census_missing",
                [blueprint.blueprint_id],
                "object-DNA review has no current native-adapter-discovered source census",
                "run one current source-census-capable native adapter and bind its exact result",
            )
        )
        return
    if source_census_conflicts:
        layer_gaps["target_inventory"].append(
            _gap(
                "target_inventory",
                "blocked",
                "object_dna_source_census_conflict",
                source_census_conflicts,
                "native adapters disagree about source members with the same stable identity",
                "resolve the source identity collision instead of selecting one result by ordering",
            )
        )

    if not native_case_universe:
        layer_gaps["native_model_code_test"].append(
            _gap(
                "native_model_code_test",
                "blocked",
                "object_dna_native_case_universe_missing",
                [blueprint.blueprint_id],
                "the verified native adapter did not expose its complete governed behavior-case universe",
                "refresh the exact native observation and replay so the adapter, not source-mapping prose, owns the case denominator",
            )
        )
    if native_case_universe_conflicts:
        layer_gaps["native_model_code_test"].append(
            _gap(
                "native_model_code_test",
                "blocked",
                "object_dna_native_case_universe_conflict",
                native_case_universe_conflicts,
                "verified native adapters disagree about a behavior-case identity or universe fingerprint",
                "resolve the native case authority conflict without selecting a convenient denominator",
            )
        )

    mapping_by_source = {item.source_member_id: item for item in blueprint.source_mappings}
    missing_source_ids = sorted(set(source_census) - set(mapping_by_source))
    if missing_source_ids:
        layer_gaps["target_inventory"].append(
            _gap(
                "target_inventory",
                "incomplete",
                "object_dna_source_member_unmapped",
                missing_source_ids,
                "observed source members have no exact model mapping or terminal disposition",
                "map or explicitly disposition every observed source member without shrinking the census",
            )
        )
    for mapping in blueprint.source_mappings:
        observation = observations.get(mapping.source_binding_id)
        if mapping.source_binding_id not in verified_object_dna_observations:
            layer_gaps["target_inventory"].append(
                _gap(
                    "target_inventory",
                    "blocked",
                    "object_dna_mapping_adapter_not_licensed",
                    [mapping.mapping_id, mapping.source_binding_id],
                    "source mapping is not owned by a currently verified provider-neutral object-DNA adapter contract",
                    "use a verified native source census or keep this provider route explicitly non-licensing",
                )
            )
        observed_ids = {
            item.get("source_member_id")
            for item in observation.source_census
        } if observation is not None and observation.qualifies_native_execution else set()
        if mapping.source_member_id not in observed_ids:
            layer_gaps["target_inventory"].append(
                _gap(
                    "target_inventory",
                    "stale" if observation is not None and observation.status == "stale" else "blocked",
                    "object_dna_mapping_source_not_observed",
                    [mapping.mapping_id, mapping.source_binding_id, mapping.source_member_id],
                    "source mapping is not grounded in the current result of its declared native binding",
                    "refresh the exact native source observation or remove the stale mapping",
                )
            )

    selected_elements_by_id = {
        item.element_id: item
        for item in blueprint.elements
        if item.element_id in selected_elements and not item.supporting_only
    }
    required_reverse_targets = set(selected_elements_by_id)
    required_reverse_targets.update(
        port.port_id
        for port in blueprint.ports
        if port.owner_element_id in selected_elements_by_id and port.required
    )
    required_reverse_targets.update(
        semantic.semantic_id
        for semantic in blueprint.semantics
        if semantic.owner_element_id in selected_elements_by_id
    )
    required_reverse_targets.update(
        case.case_id
        for case in blueprint.behavior_cases
        if case.owner_element_id in selected_elements_by_id
    )
    mapped_targets = {
        target_id
        for mapping in blueprint.source_mappings
        if mapping.relation != "dispositioned" and mapping.source_member_id in source_census
        for target_id in mapping.target_ids
    }
    reverse_missing = sorted(required_reverse_targets - mapped_targets)
    if reverse_missing:
        layer_gaps["target_inventory"].append(
            _gap(
                "target_inventory",
                "incomplete",
                "object_dna_model_target_without_source",
                reverse_missing,
                "behavior-bearing model targets have no reverse mapping to an observed source member",
                "bind each target to the exact observed source that realizes, defines, exercises, or supports it",
            )
            )

    _review_object_dna_port_contracts(
        blueprint,
        selected_elements_by_id=set(selected_elements_by_id),
        source_census=source_census,
        gaps=layer_gaps["typed_interfaces"],
    )
    _review_object_dna_semantic_selectors(
        blueprint,
        selected_elements_by_id=set(selected_elements_by_id),
        source_census=source_census,
        gaps=layer_gaps["independent_physical_semantics"],
    )

    semantic_by_id = {item.semantic_id: item for item in blueprint.semantics}
    for mapping in blueprint.source_mappings:
        if mapping.relation != "defines":
            continue
        member = source_census.get(mapping.source_member_id)
        source_expression = None if member is None else member.get("semantic_expression")
        if not isinstance(source_expression, str):
            layer_gaps["independent_physical_semantics"].append(
                _gap(
                    "independent_physical_semantics",
                    "blocked",
                    "object_dna_semantic_fact_missing",
                    [mapping.mapping_id, mapping.source_member_id],
                    "a defining source mapping does not expose an independently owned semantic expression",
                    "use a source-census semantic fact or downgrade this relation to bounded support",
                )
            )
            continue
        for target_id in mapping.target_ids:
            semantic = semantic_by_id.get(target_id)
            if semantic is None:
                continue
            if semantic.expression is None or _normalized_expression_rhs(semantic.expression) != _normalized_expression_rhs(source_expression):
                layer_gaps["independent_physical_semantics"].append(
                    _gap(
                        "independent_physical_semantics",
                        "blocked",
                        "object_dna_semantic_expression_mismatch",
                        [mapping.mapping_id, mapping.source_member_id, semantic.semantic_id],
                        "blueprint semantic expression differs from its independently mapped source/oracle fact",
                        "correct the model expression or refresh the independently governed semantic fact",
                    )
                )

    selected_cases = [
        case for case in blueprint.behavior_cases if case.owner_element_id in selected_elements_by_id
    ]
    case_ids_by_native_id: dict[str, list[str]] = defaultdict(list)
    for case in selected_cases:
        case_ids_by_native_id[case.native_case_id].append(case.case_id)
    for native_case_id, native_case in sorted(native_case_universe.items()):
        if native_case.get("disposition") != "required":
            continue
        mapped_case_ids = case_ids_by_native_id.get(native_case_id, [])
        if len(mapped_case_ids) != 1:
            layer_gaps["native_model_code_test"].append(
                _gap(
                    "native_model_code_test",
                    "blocked",
                    "object_dna_native_case_universe_mapping_invalid",
                    [native_case_id, *mapped_case_ids],
                    "a required adapter-owned native case must map to exactly one selected blueprint behavior case",
                    "restore the exact one-to-one native-case mapping; source-mapping reasons cannot shrink or disposition this denominator",
                )
            )

    for case in selected_cases:
        native_universe_member = native_case_universe.get(case.native_case_id)
        if native_universe_member is None or native_universe_member.get("disposition") != "required":
            layer_gaps["native_model_code_test"].append(
                _gap(
                    "native_model_code_test",
                    "blocked",
                    "object_dna_model_case_not_in_native_universe",
                    [case.case_id, case.native_case_id],
                    "a blueprint behavior case is absent from the verified adapter-owned required case universe",
                    "bind the exact native case identity or remove the unsupported blueprint case claim",
                )
            )
        if case.native_result_binding_id is None:
            layer_gaps["native_model_code_test"].append(
                _gap(
                    "native_model_code_test",
                    "incomplete",
                    "object_dna_case_native_result_missing",
                    [case.case_id],
                    "object-DNA behavior case has no exact replayed native-result binding",
                    "bind the case to the native observation that returns its exact case id and values",
                )
            )
            continue
        observation = observations.get(case.native_result_binding_id)
        if observation is None or not observation.qualifies_native_execution:
            layer_gaps["native_model_code_test"].append(
                _gap(
                    "native_model_code_test",
                    "blocked",
                    "object_dna_case_native_result_not_current",
                    [case.case_id, case.native_result_binding_id],
                    "the behavior case native-result owner was not replayed to a current terminal receipt",
                    "replay the exact native owner and bind its current case result",
                )
            )
            continue
        native_results = {
            item.get("case_id"): item
            for item in observation.native_case_results
            if isinstance(item.get("case_id"), str)
        }
        native_result = native_results.get(case.native_case_id)
        if native_result is None:
            layer_gaps["native_model_code_test"].append(
                _gap(
                    "native_model_code_test",
                    "blocked",
                    "object_dna_native_case_not_observed",
                    [case.case_id, case.native_case_id],
                    "the current native replay did not return the model case's declared native case id",
                    "restore or explicitly revise the native case before claiming object-DNA readiness",
                )
            )
            continue
        if native_result.get("terminal_status") != case.expected_terminal_status:
            layer_gaps["native_model_code_test"].append(
                _gap(
                    "native_model_code_test",
                    "blocked",
                    "object_dna_native_case_terminal_mismatch",
                    [case.case_id, case.native_case_id],
                    "native terminal status differs from the model case expectation",
                    "correct the case contract or the governed native behavior",
                )
            )
        value_binding_by_port = {item.port_id: item for item in case.native_value_bindings}
        claimed_values = {**case.observed_output_values, **case.observed_post_state_values}
        expected_values = {**case.expected_output_values, **case.expected_post_state_values}
        native_values = native_result.get("observed_values", {})
        if not isinstance(native_values, dict):
            native_values = {}
        for port_id, expected_value in expected_values.items():
            value_binding = value_binding_by_port.get(port_id)
            if value_binding is None:
                layer_gaps["native_model_code_test"].append(
                    _gap(
                        "native_model_code_test",
                        "incomplete",
                        "object_dna_native_value_mapping_missing",
                        [case.case_id, port_id],
                        "model case output/state has no exact native variable mapping",
                        "map the model port to one native observed value and tolerance",
                    )
                )
                continue
            native_value = native_values.get(value_binding.native_variable_name)
            claimed_value = claimed_values.get(port_id)
            if not isinstance(native_value, (int, float)) or not isinstance(claimed_value, (int, float)):
                mismatch = True
            else:
                mismatch = not (
                    math.isclose(
                        float(native_value),
                        float(expected_value),
                        rel_tol=0.0,
                        abs_tol=value_binding.absolute_tolerance,
                    )
                    and math.isclose(
                        float(native_value),
                        float(claimed_value),
                        rel_tol=0.0,
                        abs_tol=value_binding.absolute_tolerance,
                    )
                )
            if mismatch:
                layer_gaps["native_model_code_test"].append(
                    _gap(
                        "native_model_code_test",
                        "blocked",
                        "object_dna_native_case_value_mismatch",
                        [case.case_id, port_id, value_binding.native_variable_name],
                        "native value, expected model value, and caller-claimed observed value do not agree within tolerance",
                        "correct the model case or the governed implementation; caller fingerprints cannot replace native evidence",
                    )
                )


def _review_object_dna_port_contracts(
    blueprint: PhysicalModelBlueprint,
    *,
    selected_elements_by_id: set[str],
    source_census: dict[str, dict[str, object]],
    gaps: list[BlueprintGap],
) -> None:
    port_by_id = {
        item.port_id: item
        for item in blueprint.ports
        if item.owner_element_id in selected_elements_by_id
    }
    semantic_by_id = {item.semantic_id: item for item in blueprint.semantics}
    for mapping in blueprint.source_mappings:
        member = source_census.get(mapping.source_member_id)
        target_port_ids = [target_id for target_id in mapping.target_ids if target_id in port_by_id]
        observed_contract = None if member is None else (
            member.get("interface_contract") or member.get("fmi_variable_contract")
        )
        declared_contract = mapping.source_interface_contract or mapping.fmi_variable_contract
        if not target_port_ids or not (
            mapping.source_member_id.startswith("fmi.variable:")
            or (member is not None and member.get("source_kind") == "variable")
            or observed_contract is not None
            or declared_contract is not None
        ):
            continue
        if declared_contract is None or not isinstance(observed_contract, dict):
            contract_label = "FMI variable" if mapping.fmi_variable_contract is not None else "native interface"
            missing_code = (
                "object_dna_fmi_variable_contract_missing"
                if mapping.fmi_variable_contract is not None
                else "object_dna_native_interface_contract_missing"
            )
            gaps.append(
                _gap(
                    "typed_interfaces",
                    "blocked",
                    missing_code,
                    [mapping.mapping_id, mapping.source_member_id, *target_port_ids],
                    f"a {contract_label}-to-port mapping lacks a typed source contract observed from the native object",
                    "bind source name/type, unit, quantity, lifecycle role, and any provider-specific references",
                )
            )
            continue
        declared_payload = declared_contract.model_dump(mode="json", exclude_none=True)
        observed_payload = dict(observed_contract)
        if mapping.source_interface_contract is not None:
            # The neutral contract is the only reviewer-facing shape.  Any
            # provider-specific details remain adapter-owned extensions.
            observed_payload = {
                key: value
                for key, value in observed_payload.items()
                if value is not None
            }
        if declared_payload != observed_payload:
            mismatch_code = (
                "object_dna_fmi_variable_contract_mismatch"
                if mapping.fmi_variable_contract is not None
                else "object_dna_native_interface_contract_mismatch"
            )
            gaps.append(
                _gap(
                    "typed_interfaces",
                    "blocked",
                    mismatch_code,
                    [mapping.mapping_id, mapping.source_member_id],
                    "the mapping's native interface meaning differs from the current adapter-observed source contract",
                    "refresh the exact typed source contract instead of relying on matching names",
                )
            )
        port_contract_by_id = {item.target_port_id: item for item in mapping.port_contracts}
        if set(port_contract_by_id) != set(target_port_ids):
            gaps.append(
                _gap(
                    "typed_interfaces",
                    "blocked",
                    "object_dna_port_contract_coverage_mismatch",
                    [mapping.mapping_id, *target_port_ids],
                    "the typed source mapping does not contract every and only its target ports",
                    "add one exact typed port contract per mapped target port",
                )
            )
        for port_id in target_port_ids:
            contract = port_contract_by_id.get(port_id)
            if contract is None:
                continue
            port = port_by_id[port_id]
            if (
                contract.expected_direction != port.direction
                or contract.expected_quantity_id != port.quantity_id
                or contract.expected_unit != port.unit
            ):
                gaps.append(
                    _gap(
                        "typed_interfaces",
                        "blocked",
                        "object_dna_target_port_contract_mismatch",
                        [mapping.mapping_id, mapping.source_member_id, port_id],
                        "the source mapping's target direction, physical quantity, or unit differs from the current port",
                        "correct the target contract and its exact source-to-target meaning",
                    )
                )
            expected_direction_by_role = {
                "parameter_input": "input",
                "constant_input": "input",
                "state_storage": "state",
                "state_read": "input",
                "derivative_output": "output",
                "event_post_state": "output",
            }
            if expected_direction_by_role[contract.port_state_role] != port.direction:
                gaps.append(
                    _gap(
                        "typed_interfaces",
                        "blocked",
                        "object_dna_port_state_role_mismatch",
                        [mapping.mapping_id, port_id, contract.port_state_role],
                        "the declared source-to-target state role is incompatible with the target port direction",
                        "correct the state role instead of treating direction as a name-only label",
                    )
                )
            source_unit = declared_contract.unit or "1"
            if contract.conversion.conversion_kind == "affine":
                gaps.append(
                    _gap(
                        "typed_interfaces",
                        "blocked",
                        "object_dna_unit_conversion_not_verified",
                        [mapping.mapping_id, port_id, contract.conversion.authority_binding_id or "missing"],
                        "affine unit conversion is declared but the native adapter does not independently execute conversion authority",
                        "add an independently replayed conversion contract before licensing this mapping",
                    )
                )
            elif source_unit != contract.expected_unit:
                gaps.append(
                    _gap(
                        "typed_interfaces",
                        "blocked",
                        "object_dna_source_target_unit_mismatch",
                        [mapping.mapping_id, mapping.source_member_id, port_id],
                        "source and target units differ without an independently verified conversion",
                        "correct the mapping or supply a verified conversion authority",
                    )
                )
            if (
                contract.quantity_relation == "identity"
                and declared_contract.physical_quantity_id != contract.expected_quantity_id
            ):
                gaps.append(
                    _gap(
                        "typed_interfaces",
                        "blocked",
                        "object_dna_source_target_quantity_mismatch",
                        [mapping.mapping_id, mapping.source_member_id, port_id],
                        "an identity mapping connects different physical quantities",
                        "correct the quantity identity or bind an explicit semantic transformation",
                    )
                )
            if contract.quantity_relation == "stateful_alias":
                governing_semantics = [
                    semantic_by_id.get(semantic_id)
                    for semantic_id in contract.governing_semantic_ids
                ]
                if not governing_semantics or any(
                    semantic is None
                    or port_id not in {
                        *semantic.input_port_ids,
                        *semantic.output_port_ids,
                        *semantic.state_port_ids,
                        *semantic.effect_port_ids,
                    }
                    for semantic in governing_semantics
                ):
                    gaps.append(
                        _gap(
                            "typed_interfaces",
                            "blocked",
                            "object_dna_quantity_alias_semantic_missing",
                            [mapping.mapping_id, port_id, *contract.governing_semantic_ids],
                            "a source-to-target quantity alias lacks an exact governing semantic that uses the target port",
                            "bind the state/update semantic that licenses the changed quantity role",
                        )
                    )
def _review_object_dna_semantic_selectors(
    blueprint: PhysicalModelBlueprint,
    *,
    selected_elements_by_id: set[str],
    source_census: dict[str, dict[str, object]],
    gaps: list[BlueprintGap],
) -> None:
    selected_semantics = {
        item.semantic_id: item
        for item in blueprint.semantics
        if item.owner_element_id in selected_elements_by_id
    }
    contracts_by_semantic: dict[str, list[tuple[object, object]]] = defaultdict(list)
    for mapping in blueprint.source_mappings:
        for contract in mapping.semantic_contracts:
            if contract.target_semantic_id in selected_semantics:
                contracts_by_semantic[contract.target_semantic_id].append((mapping, contract))
    for semantic_id, semantic in sorted(selected_semantics.items()):
        owners = contracts_by_semantic.get(semantic_id, [])
        if len(owners) != 1:
            gaps.append(
                _gap(
                    "independent_physical_semantics",
                    "blocked",
                    "object_dna_semantic_selector_ownership_invalid",
                    [semantic_id, *(mapping.mapping_id for mapping, _ in owners)],
                    "each selected physical semantic must have exactly one primary native source selector",
                    "bind one exact function/fragment selector or keep the semantic explicitly unresolved",
                )
            )
            continue
        mapping, contract = owners[0]
        member = source_census.get(mapping.source_member_id)
        observed_selectors = [] if member is None else member.get("semantic_selectors", [])
        if not isinstance(observed_selectors, list):
            observed_selectors = []
        selector_matches = [
            item
            for item in observed_selectors
            if isinstance(item, dict) and item.get("selector_id") == contract.selector_id
        ]
        if len(selector_matches) != 1:
            gaps.append(
                _gap(
                    "independent_physical_semantics",
                    "blocked",
                    "object_dna_semantic_selector_unobserved",
                    [mapping.mapping_id, semantic_id, contract.selector_id],
                    "the declared semantic selector was not uniquely resolved by the native adapter",
                    "resolve one exact source function and fragment; whole-file identity is insufficient",
                )
            )
            continue
        observed = selector_matches[0]
        if (
            observed.get("status") != "verified"
            or observed.get("selector_fingerprint") != contract.expected_selector_fingerprint
        ):
            gaps.append(
                _gap(
                    "independent_physical_semantics",
                    "blocked",
                    "object_dna_semantic_selector_not_current",
                    [mapping.mapping_id, semantic_id, contract.selector_id],
                    "the semantic selector is unresolved or its exact native fingerprint has changed",
                    "refresh the selector against current source bytes before updating the blueprint semantic",
                )
            )
            continue
        observed_expression = observed.get("semantic_expression")
        if (
            observed.get("semantic_kind") != semantic.semantic_kind
            or _normalized_semantic_text(str(observed.get("semantic_statement", "")))
            != _normalized_semantic_text(semantic.statement)
            or (
                None if observed_expression is None else _normalized_semantic_text(str(observed_expression))
            )
            != (None if semantic.expression is None else _normalized_semantic_text(semantic.expression))
        ):
            gaps.append(
                _gap(
                    "independent_physical_semantics",
                    "blocked",
                    "object_dna_semantic_selector_meaning_mismatch",
                    [mapping.mapping_id, semantic_id, contract.selector_id],
                    "the blueprint semantic kind, statement, or expression differs from its verified source selector fact",
                    "correct the blueprint meaning or refresh the independently observed selector contract",
                )
            )


def _normalized_semantic_text(value: str) -> str:
    return " ".join(value.strip().split())


def _normalized_expression_rhs(expression: str) -> str:
    normalized = "".join(expression.strip().split())
    if "=" in normalized and not normalized.startswith(("if", "0.0if")):
        normalized = normalized.split("=", 1)[1]
    while normalized.startswith("(") and normalized.endswith(")"):
        normalized = normalized[1:-1]
    return normalized


def _review_refinement(
    blueprint: PhysicalModelBlueprint,
    selected_elements: set[str],
    semantics: dict[str, object],
    observations: dict[str, NativeAuthorityObservation],
    gaps: list[BlueprintGap],
) -> None:
    element_by_id = {item.element_id: item for item in blueprint.elements}
    for refinement in blueprint.refinements:
        if refinement.parent_element_id not in selected_elements:
            continue
        contribution_by_child = defaultdict(list)
        for contribution in refinement.semantic_contributions:
            child_semantic = semantics[contribution.child_semantic_id]
            parent_semantic = semantics[contribution.parent_semantic_id]
            child_owner = child_semantic.owner_element_id
            if child_owner not in refinement.child_element_ids or parent_semantic.owner_element_id != refinement.parent_element_id:
                gaps.append(
                    _gap(
                        "parent_child_refinement",
                        "blocked",
                        "semantic_contribution_owner_mismatch",
                        [contribution.contribution_id],
                        "semantic contribution does not connect a declared child semantic to its parent semantic",
                        "bind the exact child and parent semantic owners",
                    )
                )
            contribution_by_child[child_owner].append(contribution)
            for binding_id in contribution.evidence_binding_ids:
                observation = observations[binding_id]
                if not observation.current:
                    gaps.append(_binding_gap("parent_child_refinement", observation, contribution.contribution_id))
        for child_id in refinement.child_element_ids:
            child = element_by_id[child_id]
            child_physical_semantics = [
                semantic_id
                for semantic_id in child.semantic_ids
                if semantics[semantic_id].semantic_kind not in {"assumption", "validity_limit", "operating_envelope"}
            ]
            contributed = {item.child_semantic_id for item in contribution_by_child[child_id]}
            missing = sorted(set(child_physical_semantics) - contributed)
            if missing:
                gaps.append(
                    _gap(
                        "parent_child_refinement",
                        "incomplete",
                        "child_semantics_not_refined",
                        [refinement.refinement_id, child_id, *missing],
                        "child physical semantics are linked structurally but do not refine a parent semantic",
                        "declare how each child semantic preserves, aggregates, constrains, or weakens the parent",
                    )
                )
            missing_validity = sorted(set(child.validity_boundary_ids) - set(refinement.propagated_validity_boundary_ids))
            if missing_validity:
                gaps.append(
                    _gap(
                        "parent_child_refinement",
                        "incomplete",
                        "child_validity_not_propagated",
                        [refinement.refinement_id, child_id, *missing_validity],
                        "child validity restrictions are absent from the parent refinement",
                        "propagate the restrictions or narrow the parent claim",
                    )
                )


def _review_native_model_code_test(
    blueprint: PhysicalModelBlueprint,
    selected_elements: set[str],
    semantics: dict[str, object],
    observations: dict[str, NativeAuthorityObservation],
    gaps: list[BlueprintGap],
) -> None:
    binding_by_id = {item.binding_id: item for item in blueprint.bindings}
    inventory_bound_ids = {binding_id for item in blueprint.inventory.members for binding_id in item.binding_ids}
    for element in blueprint.elements:
        if element.element_id not in selected_elements or element.supporting_only:
            continue
        element_bindings = [binding_by_id[item] for item in element.native_binding_ids]
        owner_bindings = [item for item in element_bindings if item.binding_kind in {"implementation", "workflow", "source"}]
        test_bindings = [item for item in element_bindings if item.binding_kind == "test"]
        if not owner_bindings:
            gaps.append(
                _gap(
                    "native_model_code_test",
                    "incomplete",
                    "element_missing_native_owner_binding",
                    [element.element_id],
                    "physical element has no exact implementation, workflow, or source owner binding",
                    "bind the element to one exact native owner artifact",
                )
            )
        if not test_bindings:
            gaps.append(
                _gap(
                    "native_model_code_test",
                    "incomplete",
                    "element_missing_test_binding",
                    [element.element_id],
                    "physical element has no exact test binding",
                    "bind a current test to the element and its physical obligations",
                )
            )
        else:
            present_modes = {
                mode
                for binding in test_bindings
                for mode in binding.validation_modes
            }
            required_modes = _required_validation_modes(blueprint, element, semantics)
            for mode in sorted(required_modes - present_modes):
                gaps.append(
                    _gap(
                        "native_model_code_test",
                        "incomplete",
                        f"validation_mode_missing_{mode}",
                        [element.element_id, mode],
                        f"applicable physical obligation has no {mode} test evidence",
                        "bind a current test with this exact validation mode or narrow the physical claim",
                    )
                )
        for binding in element_bindings:
            observation = observations[binding.binding_id]
            if not observation.current:
                gaps.append(_binding_gap("native_model_code_test", observation, element.element_id))
            if binding.binding_id not in inventory_bound_ids:
                gaps.append(
                    _gap(
                        "native_model_code_test",
                        "incomplete",
                        "binding_missing_reverse_inventory_trace",
                        [element.element_id, binding.binding_id],
                        "native binding has no reverse trace from the independent inventory",
                        "add the binding id to the matching independently inventoried artifact",
                    )
                )
        if not any(
            observations[binding.binding_id].qualifies_native_execution
            for binding in element_bindings
        ):
            gaps.append(
                _gap(
                    "native_model_code_test",
                    "blocked",
                    "element_missing_native_owner_replay",
                    [element.element_id, *[item.binding_id for item in element_bindings]],
                    "no current binding for this element was actually replayed by its PhysicsGuard native owner",
                    "bind an exact native execution expectation and reproduce its terminal receipt",
                )
            )
        for semantic_id in element.semantic_ids:
            owner_coverage = any(semantic_id in binding.semantic_ids for binding in owner_bindings)
            test_coverage = any(semantic_id in binding.semantic_ids for binding in test_bindings)
            if not owner_coverage or not test_coverage:
                missing = []
                if not owner_coverage:
                    missing.append("native owner")
                if not test_coverage:
                    missing.append("test")
                gaps.append(
                    _gap(
                        "native_model_code_test",
                        "incomplete",
                        "semantic_binding_incomplete",
                        [element.element_id, semantic_id],
                        f"physical semantic lacks exact {' and '.join(missing)} coverage",
                        "bind both native ownership and current test evidence to the semantic",
                    )
                )


def _required_validation_modes(
    blueprint: PhysicalModelBlueprint,
    element: object,
    semantics: dict[str, object],
) -> set[str]:
    """Derive evidence modes only from semantics that make them applicable."""

    element_semantics = [semantics[semantic_id] for semantic_id in element.semantic_ids]
    ports = [port for port in blueprint.ports if port.owner_element_id == element.element_id]
    required = {"pointwise"} if element_semantics else set()
    if any(port.direction == "state" for port in ports):
        required.add("temporal_stateful")
    if any(
        semantic.semantic_kind in {"conservation_law", "residual"}
        for semantic in element_semantics
    ):
        required.add("conservation_residual")
    if ports:
        required.add("interface_unit")
    if element.validity_boundary_ids:
        required.add("boundary_invalid_region")
    if any(
        refinement.parent_element_id == element.element_id
        and len(refinement.child_element_ids) > 1
        for refinement in blueprint.refinements
    ):
        required.add("cross_coupling")
    return required


def _review_resource_oracle(
    blueprint: PhysicalModelBlueprint,
    selected_elements: set[str],
    semantics: dict[str, object],
    observations: dict[str, NativeAuthorityObservation],
    gaps: list[BlueprintGap],
) -> None:
    binding_by_id = {item.binding_id: item for item in blueprint.bindings}
    for element in blueprint.elements:
        if element.element_id not in selected_elements or element.supporting_only:
            continue
        element_bindings = [binding_by_id[item] for item in element.native_binding_ids]
        by_kind = defaultdict(list)
        for binding in element_bindings:
            by_kind[binding.binding_kind].append(binding)
        for required_kind in ("resource", "oracle", "evidence"):
            if not by_kind[required_kind]:
                gaps.append(
                    _gap(
                        "resource_oracle",
                        "incomplete",
                        f"element_missing_{required_kind}_binding",
                        [element.element_id],
                        f"physical element has no exact {required_kind} binding",
                        f"bind the current {required_kind} identity required by the physical claim",
                    )
                )
        for semantic_id in element.semantic_ids:
            if not any(semantic_id in binding.semantic_ids for binding in by_kind["oracle"]):
                gaps.append(
                    _gap(
                        "resource_oracle",
                        "incomplete",
                        "semantic_missing_oracle",
                        [element.element_id, semantic_id],
                        "physical semantic has no exact oracle binding",
                        "bind an oracle that can judge this semantic inside its validity boundary",
                    )
                )
        for binding in (*by_kind["resource"], *by_kind["oracle"], *by_kind["evidence"]):
            observation = observations[binding.binding_id]
            if not observation.current:
                gaps.append(_binding_gap("resource_oracle", observation, element.element_id))
        executable_support = [
            binding
            for binding in (*by_kind["oracle"], *by_kind["evidence"])
            if observations[binding.binding_id].qualifies_native_execution
        ]
        if not executable_support:
            gaps.append(
                _gap(
                    "resource_oracle",
                    "blocked",
                    "element_missing_native_oracle_replay",
                    [
                        element.element_id,
                        *[
                            item.binding_id
                            for item in (*by_kind["oracle"], *by_kind["evidence"])
                        ],
                    ],
                    "resource/oracle identity is present, but no current native oracle or evidence owner was replayed",
                    "replay the exact native oracle/evidence owner and bind its terminal receipt",
                )
            )


def _derive_layer_results(
    layer_gaps: dict[BlueprintLayerName, list[BlueprintGap]],
    blueprint: PhysicalModelBlueprint,
    selected_elements: set[str],
) -> list[BlueprintLayerResult]:
    covered_by_layer: dict[BlueprintLayerName, list[str]] = {
        "target_inventory": [item.member_id for item in blueprint.inventory.members],
        "hierarchy_ownership": sorted(selected_elements),
        "typed_interfaces": [item.port_id for item in blueprint.ports if item.owner_element_id in selected_elements],
        "independent_physical_semantics": [item.semantic_id for item in blueprint.semantics if item.owner_element_id in selected_elements],
        "parent_child_refinement": [item.refinement_id for item in blueprint.refinements if item.parent_element_id in selected_elements],
        "native_model_code_test": [item.binding_id for item in blueprint.bindings if item.owner_element_id in selected_elements and item.binding_kind in {"implementation", "workflow", "source", "test"}],
        "resource_oracle": [item.binding_id for item in blueprint.bindings if item.owner_element_id in selected_elements and item.binding_kind in {"resource", "oracle", "evidence", "dataset", "observation"}],
        "static_blueprint": [blueprint.blueprint_id],
    }
    results: list[BlueprintLayerResult] = []
    for layer in BLUEPRINT_LAYER_ORDER:
        gaps = layer_gaps[layer]
        results.append(
            BlueprintLayerResult(
                layer=layer,
                status=_overall_status(gaps),
                gap_ids=[item.gap_id for item in gaps],
                covered_ids=covered_by_layer[layer],
            )
        )
    return results


def _static_closure_result(
    preceding: list[BlueprintLayerResult],
    gaps: list[BlueprintGap],
    blueprint: PhysicalModelBlueprint,
    selected_elements: set[str],
) -> BlueprintLayerResult:
    status = "pass" if all(item.status == "pass" for item in preceding) else _overall_status(gaps)
    return BlueprintLayerResult(
        layer="static_blueprint",
        status=status,
        gap_ids=[gap.gap_id for gap in gaps] if status != "pass" else [],
        covered_ids=[blueprint.blueprint_id, *sorted(selected_elements)],
    )


def _deepest_contiguous_layer(
    layers: list[BlueprintLayerResult],
) -> BlueprintLayerName | None:
    deepest: BlueprintLayerName | None = None
    for layer in layers:
        if layer.status != "pass":
            break
        deepest = layer.layer
    return deepest


def _overall_status(gaps: Iterable[BlueprintGap]) -> ReviewStatus:
    statuses = {gap.status for gap in gaps}
    if "blocked" in statuses:
        return "blocked"
    if "stale" in statuses:
        return "stale"
    if "incomplete" in statuses:
        return "incomplete"
    return "pass"


def _claims(
    blueprint: PhysicalModelBlueprint,
    status: ReviewStatus,
    deepest: BlueprintLayerName | None,
    scope: str,
    external_identity_only_binding_ids: list[str],
    byte_identity_only_binding_ids: list[str],
    understanding_target: str,
    declared_consistency_status: ReviewStatus,
) -> tuple[str, str]:
    if status == "pass":
        if understanding_target == "object_dna":
            safe = (
                f"The {scope} boundary of external physical target "
                f"{blueprint.target.target_system_id} passed declared consistency and bounded object-DNA "
                f"source/model/result closure at subject revision {blueprint.target.subject_revision}."
            )
        else:
            safe = (
                f"The {scope} declared boundary of external physical target "
                f"{blueprint.target.target_system_id} passed static physical-blueprint closure for declared "
                f"consistency at subject revision "
                f"{blueprint.target.subject_revision}; object-DNA readiness was not requested."
            )
    else:
        depth = deepest or "no licensed layer"
        safe = (
            f"The {scope} declared boundary of external physical target "
            f"{blueprint.target.target_system_id} is {status}; the deepest contiguous licensed layer is {depth}."
        )
        if understanding_target == "object_dna":
            safe += f" Declared consistency alone is {declared_consistency_status}."
    unsafe = (
        "Static blueprint closure describes declared physical semantics, composition, identities, and current "
        "bindings. It does not by itself prove physical truth, empirical equivalence, high-fidelity solver "
        "equivalence, universal target coverage, or reconstruction beyond the exact declared boundary."
    )
    if external_identity_only_binding_ids:
        unsafe += (
            " External bindings are current only as provider-bound identities; their content was not "
            "independently read or hashed: "
            + ", ".join(external_identity_only_binding_ids)
            + "."
        )
    if byte_identity_only_binding_ids:
        unsafe += (
            " Generic local bindings prove exact bytes only, not the declared subject or semantic content: "
            + ", ".join(byte_identity_only_binding_ids)
            + "."
        )
    return safe, unsafe


def _binding_gap(
    layer: BlueprintLayerName,
    observation: NativeAuthorityObservation,
    owner_id: str,
) -> BlueprintGap:
    status = "stale" if observation.status == "stale" else "blocked"
    message = "; ".join(observation.findings) or f"binding status is {observation.status}"
    return _gap(
        layer,
        status,
        "native_binding_not_current",
        [owner_id, observation.binding_id],
        message,
        "refresh the exact native owner artifact and its bound fingerprint",
    )


def _artifact_reference_current(reference: ArtifactReference, base_dir: Path | None) -> bool:
    if reference.external_uri is not None:
        return False
    if base_dir is None:
        return False
    root = base_dir.resolve()
    path = (root / str(reference.repo_path)).resolve()
    try:
        path.relative_to(root)
    except ValueError:
        return False
    if not path.is_file():
        return False
    return hashlib.sha256(path.read_bytes()).hexdigest() == reference.sha256


def _gap(
    layer: BlueprintLayerName,
    status: str,
    code: str,
    target_ids: list[str],
    message: str,
    next_action: str,
) -> BlueprintGap:
    normalized_targets = sorted(set(target_ids))
    suffix = hashlib.sha256("\n".join(normalized_targets).encode("utf-8")).hexdigest()[:12]
    return BlueprintGap(
        gap_id=f"gap:{layer}:{code}:{suffix}",
        layer=layer,
        status=status,
        code=code,
        message=message,
        target_ids=normalized_targets,
        next_action=next_action,
    )


__all__ = [
    "BLUEPRINT_LAYER_ORDER",
    "physical_model_blueprint_review_to_dict",
    "review_physical_model_blueprint",
]
