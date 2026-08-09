"""Deterministic affected and reverse traces over a physical blueprint."""

from __future__ import annotations

import hashlib
from collections import defaultdict, deque
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from physicsguard.core.physical_model_blueprint import (
    review_physical_model_blueprint,
)
from physicsguard.schema.physical_model_blueprint import (
    BlueprintGap,
    BlueprintProjection,
    BlueprintTraceEdge,
    BlueprintTraceNode,
    PhysicalModelBlueprint,
    PhysicalModelBlueprintReview,
    TargetInventoryAuthority,
    canonical_blueprint_fingerprint,
    fingerprint_blueprint,
    fingerprint_projection,
)


TRACE_RECIPE_VERSION = "physicsguard.physical-blueprint-trace.v3"


@dataclass(frozen=True)
class CompiledPhysicalBlueprintGraph:
    nodes: tuple[BlueprintTraceNode, ...]
    edges: tuple[BlueprintTraceEdge, ...]
    aliases: dict[str, tuple[str, ...]]


def compile_physical_blueprint_graph(
    blueprint: PhysicalModelBlueprint,
    review: PhysicalModelBlueprintReview | None = None,
) -> CompiledPhysicalBlueprintGraph:
    nodes: dict[str, BlueprintTraceNode] = {}
    edges: dict[str, BlueprintTraceEdge] = {}
    aliases: dict[str, set[str]] = defaultdict(set)

    def add_node(node_id: str, node_kind: str, *, raw_id: str | None = None, owner: str | None = None, fingerprint: str | None = None) -> None:
        nodes[node_id] = BlueprintTraceNode(
            node_id=node_id,
            node_kind=node_kind,
            owner_element_id=owner,
            fingerprint=fingerprint,
        )
        if raw_id is not None:
            aliases[raw_id].add(node_id)

    def add_edge(source: str, target: str, relation: str, *, propagates: bool = True) -> None:
        edge_id = f"edge:{relation}:{source}:{target}"
        edges[edge_id] = BlueprintTraceEdge(
            edge_id=edge_id,
            source_id=source,
            target_id=target,
            relation=relation,
            propagates_change=propagates,
        )

    blueprint_node = f"blueprint:{blueprint.blueprint_id}"
    add_node(
        blueprint_node,
        "physical_blueprint",
        raw_id=blueprint.blueprint_id,
        fingerprint=fingerprint_blueprint(blueprint),
    )
    target_node = f"target:{blueprint.target.target_system_id}"
    add_node(target_node, "target", raw_id=blueprint.target.target_system_id, fingerprint=blueprint.target.boundary_fingerprint)
    add_edge(blueprint_node, target_node, "declares_target")
    for provider in blueprint.providers:
        provider_node = f"provider:{provider.provider_id}"
        add_node(
            provider_node,
            "provider",
            raw_id=provider.provider_id,
            fingerprint=canonical_blueprint_fingerprint(provider),
        )
        # A target identity/revision change invalidates observations, while a
        # provider refresh does not mutate the external target itself.
        add_edge(target_node, provider_node, "requires_provider_observation")
        add_edge(blueprint_node, provider_node, "declares_provider")
        for capability_id in provider.capability_ids:
            capability_node = f"capability:{provider.provider_id}:{capability_id}"
            add_node(
                capability_node,
                "provider_capability",
                raw_id=f"{provider.provider_id}:{capability_id}",
            )
            aliases[capability_id].add(capability_node)
            add_edge(provider_node, capability_node, "provides_capability")

    inventory_node = f"inventory-set:{blueprint.inventory.inventory_id}"
    add_node(
        inventory_node,
        "independent_inventory",
        raw_id=blueprint.inventory.inventory_id,
        fingerprint=blueprint.inventory.inventory_fingerprint,
    )
    add_edge(blueprint_node, inventory_node, "declares_inventory")
    add_edge(target_node, inventory_node, "defines_inventory_boundary")
    add_edge(
        f"provider:{blueprint.inventory.provider_id}",
        inventory_node,
        "produces_inventory",
    )
    for member in blueprint.inventory.members:
        member_node = f"inventory:{member.member_id}"
        add_node(
            member_node,
            f"inventory_{member.member_kind}",
            raw_id=member.member_id,
            fingerprint=blueprint.inventory.inventory_fingerprint,
        )
        add_edge(inventory_node, member_node, "contains_inventory_member")

    for element in blueprint.elements:
        element_node = f"element:{element.element_id}"
        add_node(element_node, "physical_element", raw_id=element.element_id, owner=element.element_id)
        add_edge(target_node, element_node, "contains_element")
        if element.parent_id is not None:
            add_edge(element_node, f"element:{element.parent_id}", "refines")
        for behavior_id in element.owned_behavior_ids:
            obligation_node = f"obligation:{behavior_id}"
            if obligation_node not in nodes:
                add_node(obligation_node, "physical_obligation", raw_id=behavior_id, owner=element.element_id)
            add_edge(element_node, obligation_node, "owns_obligation")
    for port in blueprint.ports:
        port_node = f"port:{port.port_id}"
        add_node(port_node, f"physical_{port.direction}", raw_id=port.port_id, owner=port.owner_element_id)
        add_edge(f"element:{port.owner_element_id}", port_node, "owns_interface")
    for semantic in blueprint.semantics:
        semantic_node = f"semantic:{semantic.semantic_id}"
        add_node(semantic_node, f"physical_{semantic.semantic_kind}", raw_id=semantic.semantic_id, owner=semantic.owner_element_id)
        add_edge(f"element:{semantic.owner_element_id}", semantic_node, "owns_semantic")
        for port_id in semantic.input_port_ids:
            add_edge(f"port:{port_id}", semantic_node, "consumes_input")
        for port_id in semantic.state_port_ids:
            add_edge(f"port:{port_id}", semantic_node, "uses_state")
        for port_id in semantic.output_port_ids:
            add_edge(semantic_node, f"port:{port_id}", "produces_output")
        for port_id in semantic.effect_port_ids:
            add_edge(semantic_node, f"port:{port_id}", "produces_effect")
        for boundary_id in semantic.validity_boundary_ids:
            add_edge(f"validity:{boundary_id}", semantic_node, "bounds_semantic")
        for assumption_id in semantic.assumption_ids:
            add_edge(f"semantic:{assumption_id}", semantic_node, "assumption_support")
    for case in blueprint.behavior_cases:
        case_node = f"case:{case.case_id}"
        add_node(
            case_node,
            f"physical_behavior_case_{case.status}",
            raw_id=case.case_id,
            owner=case.owner_element_id,
            fingerprint=case.case_fingerprint,
        )
        aliases[case.native_case_id].add(case_node)
        add_edge(f"element:{case.owner_element_id}", case_node, "owns_behavior_case")
        for port_id in case.input_values:
            add_edge(f"port:{port_id}", case_node, "case_input")
        for port_id in case.pre_state_values:
            add_edge(f"port:{port_id}", case_node, "case_pre_state")
        for port_id in case.expected_output_values:
            add_edge(case_node, f"port:{port_id}", "case_expected_output")
        for port_id in case.expected_post_state_values:
            add_edge(case_node, f"port:{port_id}", "case_expected_post_state")
        for port_id in case.expected_effect_port_ids:
            add_edge(case_node, f"port:{port_id}", "case_expected_effect")
        for semantic_id in case.semantic_ids:
            add_edge(f"semantic:{semantic_id}", case_node, "case_checks_semantic")
        for binding_id in case.test_binding_ids:
            add_edge(f"binding:{binding_id}", case_node, "case_test_evidence")
        for binding_id in case.evidence_binding_ids:
            add_edge(f"binding:{binding_id}", case_node, "case_execution_evidence")
        for binding_id in case.oracle_binding_ids:
            add_edge(f"binding:{binding_id}", case_node, "case_oracle")
    for boundary in blueprint.validity_boundaries:
        boundary_node = f"validity:{boundary.boundary_id}"
        add_node(boundary_node, "validity_boundary", raw_id=boundary.boundary_id, owner=boundary.owner_element_id)
        add_edge(f"element:{boundary.owner_element_id}", boundary_node, "owns_validity")

    for binding in blueprint.bindings:
        binding_node = f"binding:{binding.binding_id}"
        add_node(binding_node, f"native_{binding.binding_kind}", raw_id=binding.binding_id, owner=binding.owner_element_id, fingerprint=binding.artifact.sha256)
        artifact_node = f"artifact:{binding.artifact.sha256}"
        if artifact_node not in nodes:
            add_node(
                artifact_node,
                "content_addressed_artifact",
                raw_id=artifact_node,
                fingerprint=binding.artifact.sha256,
            )
        aliases[binding.subject_id].add(binding_node)
        if binding.artifact.repo_path is not None:
            aliases[binding.artifact.repo_path].add(artifact_node)
        if binding.artifact.external_uri is not None:
            aliases[binding.artifact.external_uri].add(artifact_node)
        add_edge(artifact_node, binding_node, "materializes_binding")
        add_edge(binding_node, f"element:{binding.owner_element_id}", "binds_element")
        if binding.provider_id:
            add_edge(f"provider:{binding.provider_id}", binding_node, "observes_binding")
        for semantic_id in binding.semantic_ids:
            add_edge(binding_node, f"semantic:{semantic_id}", "supports_semantic")
        for obligation_id in binding.obligation_ids:
            obligation_node = f"obligation:{obligation_id}"
            if obligation_node not in nodes:
                add_node(obligation_node, "physical_obligation", raw_id=obligation_id)
            add_edge(binding_node, obligation_node, "supports_obligation")

    for member in blueprint.inventory.members:
        member_node = f"inventory:{member.member_id}"
        if member.blueprint_element_id:
            add_edge(member_node, f"element:{member.blueprint_element_id}", "inventory_maps_element")
        for binding_id in member.binding_ids:
            add_edge(member_node, f"binding:{binding_id}", "inventory_maps_binding")
        # When an inventory identity is also the exact identity of a modeled
        # object, record that equivalence explicitly.  This lets callers use
        # the natural raw id while still keeping the inventory observation and
        # modeled object as distinct typed nodes.
        exact_object_nodes = []
        if any(item.element_id == member.member_id for item in blueprint.elements):
            exact_object_nodes.append(f"element:{member.member_id}")
        if any(item.port_id == member.member_id for item in blueprint.ports):
            exact_object_nodes.append(f"port:{member.member_id}")
        if any(item.semantic_id == member.member_id for item in blueprint.semantics):
            exact_object_nodes.append(f"semantic:{member.member_id}")
        if any(item.boundary_id == member.member_id for item in blueprint.validity_boundaries):
            exact_object_nodes.append(f"validity:{member.member_id}")
        if any(item.binding_id == member.member_id for item in blueprint.bindings):
            exact_object_nodes.append(f"binding:{member.member_id}")
        for object_node in exact_object_nodes:
            add_edge(member_node, object_node, "inventory_observes_object")

    # Source members are discovered by a native authority independently of
    # the blueprint's declared mapping list.  Keep the observed member and the
    # mapping as separate typed nodes so that a caller can walk in both
    # directions without treating a declaration as observation evidence:
    #
    #   observed source -> mapping -> modeled target
    #                    ^
    #                    native observation binding
    #
    # A graph compiled without a review may still expose declared mappings,
    # but those source nodes are deliberately marked as declarations rather
    # than current observations.
    observed_source_by_id = {
        item.source_member_id: item
        for item in (review.source_census if review is not None else ())
    }
    declared_source_ids = {
        mapping.source_member_id for mapping in blueprint.source_mappings
    }
    for source_id in sorted(set(observed_source_by_id) | declared_source_ids):
        observation = observed_source_by_id.get(source_id)
        source_kind = (
            f"source_{observation.source_kind}"
            if observation is not None
            else "declared_source_member"
        )
        add_node(
            f"source:{source_id}",
            source_kind,
            raw_id=source_id,
            fingerprint=(
                observation.member_fingerprint if observation is not None else None
            ),
        )
        if observation is not None:
            for selector in observation.semantic_selectors:
                selector_node = f"source-selector:{selector.selector_id}"
                add_node(
                    selector_node,
                    f"source_semantic_selector_{selector.status}",
                    raw_id=selector.selector_id,
                    fingerprint=selector.selector_fingerprint,
                )
                add_edge(
                    f"source:{source_id}",
                    selector_node,
                    "source_semantic_selector",
                )

    target_node_by_raw_id: dict[str, str] = {}
    # Prefer the modeled object when an inventory observation shares its raw
    # identity.  Explicit inventory-only identities such as ``material.06``
    # still resolve to their independent-inventory node.
    for collection, prefix, identity_field in (
        (blueprint.elements, "element", "element_id"),
        (blueprint.ports, "port", "port_id"),
        (blueprint.semantics, "semantic", "semantic_id"),
        (blueprint.behavior_cases, "case", "case_id"),
        (blueprint.validity_boundaries, "validity", "boundary_id"),
        (blueprint.bindings, "binding", "binding_id"),
    ):
        for item in collection:
            raw_id = getattr(item, identity_field)
            target_node_by_raw_id.setdefault(raw_id, f"{prefix}:{raw_id}")
    for member in blueprint.inventory.members:
        target_node_by_raw_id.setdefault(
            member.member_id,
            f"inventory:{member.member_id}",
        )

    for mapping in blueprint.source_mappings:
        source_node = f"source:{mapping.source_member_id}"
        mapping_node = f"source-mapping:{mapping.mapping_id}"
        add_node(
            mapping_node,
            f"source_model_mapping_{mapping.relation}",
            raw_id=mapping.mapping_id,
            fingerprint=canonical_blueprint_fingerprint(mapping),
        )
        add_edge(source_node, mapping_node, "source_mapping_source")
        add_edge(
            f"binding:{mapping.source_binding_id}",
            mapping_node,
            "source_mapping_observation",
        )
        for contract in mapping.semantic_contracts:
            selector_node = f"source-selector:{contract.selector_id}"
            if selector_node in nodes:
                add_edge(
                    selector_node,
                    mapping_node,
                    "source_selector_contract",
                )
        for target_id in mapping.target_ids:
            add_edge(
                mapping_node,
                target_node_by_raw_id[target_id],
                "source_mapping_target",
            )

    for refinement in blueprint.refinements:
        refinement_node = f"refinement:{refinement.refinement_id}"
        add_node(refinement_node, "refinement_contract", raw_id=refinement.refinement_id, owner=refinement.parent_element_id)
        add_edge(refinement_node, f"element:{refinement.parent_element_id}", "qualifies_parent")
        for child_id in refinement.child_element_ids:
            add_edge(f"element:{child_id}", refinement_node, "declared_child")
        for mapping in refinement.port_mappings:
            mapping_node = f"mapping:{mapping.mapping_id}"
            add_node(mapping_node, "port_mapping", raw_id=mapping.mapping_id, owner=refinement.parent_element_id)
            add_edge(mapping_node, refinement_node, "belongs_to_refinement")
            if mapping.source_port_id:
                add_edge(f"port:{mapping.source_port_id}", mapping_node, "mapping_source")
            else:
                external_node = f"external:{mapping.external_source_id}"
                if external_node not in nodes:
                    add_node(external_node, "external_source", raw_id=mapping.external_source_id)
                add_edge(external_node, mapping_node, "mapping_source")
            add_edge(mapping_node, f"port:{mapping.target_port_id}", "mapping_target")
            if mapping.conversion_semantic_id:
                add_edge(f"semantic:{mapping.conversion_semantic_id}", mapping_node, "conversion_support")
            for binding_id in mapping.evidence_binding_ids:
                add_edge(f"binding:{binding_id}", mapping_node, "mapping_evidence")
        for contribution in refinement.semantic_contributions:
            contribution_node = f"contribution:{contribution.contribution_id}"
            add_node(contribution_node, "semantic_contribution", raw_id=contribution.contribution_id, owner=refinement.parent_element_id)
            add_edge(f"semantic:{contribution.child_semantic_id}", contribution_node, "child_semantic")
            add_edge(contribution_node, f"semantic:{contribution.parent_semantic_id}", f"semantic_{contribution.relation}")
            add_edge(contribution_node, refinement_node, "belongs_to_refinement")
            for binding_id in contribution.evidence_binding_ids:
                add_edge(f"binding:{binding_id}", contribution_node, "contribution_evidence")

    for unresolved in blueprint.unresolved_relations:
        relation_node = f"unresolved:{unresolved.relation_id}"
        add_node(relation_node, "unresolved_relation", raw_id=unresolved.relation_id)
        for source_id in unresolved.source_ids:
            for source_node in sorted(aliases.get(source_id, ())):
                add_edge(source_node, relation_node, "unresolved_source", propagates=False)
        for target_id in unresolved.target_ids:
            for target_node_id in sorted(aliases.get(target_id, ())):
                add_edge(relation_node, target_node_id, "unresolved_target", propagates=False)

    if review is not None:
        claim_node = f"claim:{review.review_id}"
        add_node(
            claim_node,
            "bounded_review_claim",
            raw_id=review.review_id,
            fingerprint=review.logical_report_fingerprint,
        )
        add_edge(target_node, claim_node, "review_claims_about", propagates=False)
        for layer in review.layer_results:
            layer_node = f"layer:{layer.layer}"
            add_node(layer_node, f"review_layer_{layer.status}", raw_id=layer.layer)
            add_edge(layer_node, claim_node, "supports_claim", propagates=False)
            for covered_id in layer.covered_ids:
                for covered_node in sorted(aliases.get(covered_id, ())):
                    add_edge(covered_node, layer_node, "qualifies_layer", propagates=False)

    return CompiledPhysicalBlueprintGraph(
        nodes=tuple(nodes[key] for key in sorted(nodes)),
        edges=tuple(edges[key] for key in sorted(edges)),
        aliases={key: tuple(sorted(value)) for key, value in sorted(aliases.items())},
    )


def affected_physical_blueprint_projection(
    blueprint: PhysicalModelBlueprint,
    review: PhysicalModelBlueprintReview,
    seed_ids: Iterable[str],
    *,
    target_inventory_authority: TargetInventoryAuthority | None = None,
    blueprint_base_dir: str | Path | None = None,
    authority_base_dir: str | Path | None = None,
) -> BlueprintProjection:
    gaps = _qualified_source_review_gaps(
        blueprint,
        review,
        target_inventory_authority,
        blueprint_base_dir,
        authority_base_dir,
    )
    if gaps:
        return _rejected_projection(
            "affected",
            blueprint,
            review,
            seed_ids,
            gaps,
            "Affected projection is empty because the supplied source review is not the one canonical exact-current passing review; no impact scope is licensed.",
        )
    graph = compile_physical_blueprint_graph(blueprint, review)
    resolved: set[str] = set()
    resolved, gaps = _resolve_seeds(blueprint, review, graph, seed_ids)
    if not gaps:
        included = _affected_closure(graph, resolved)
    else:
        # One unknown, stale, or ambiguous seed blocks the whole request.  A
        # mixed seed set must never look like a complete partial impact result.
        included = set()
    return _projection(
        "affected",
        blueprint,
        review,
        graph,
        seed_ids,
        included,
        gaps,
        "Affected projection selects only typed current dependency closure; omitted nodes are outside scope, not passed.",
    )


def reverse_trace_physical_blueprint_projection(
    blueprint: PhysicalModelBlueprint,
    review: PhysicalModelBlueprintReview,
    seed_ids: Iterable[str],
    *,
    target_inventory_authority: TargetInventoryAuthority | None = None,
    blueprint_base_dir: str | Path | None = None,
    authority_base_dir: str | Path | None = None,
) -> BlueprintProjection:
    gaps = _qualified_source_review_gaps(
        blueprint,
        review,
        target_inventory_authority,
        blueprint_base_dir,
        authority_base_dir,
    )
    if gaps:
        return _rejected_projection(
            "reverse_trace",
            blueprint,
            review,
            seed_ids,
            gaps,
            "Reverse trace is empty because the supplied source review is not the one canonical exact-current passing review; no physical-ground path is licensed.",
        )
    graph = compile_physical_blueprint_graph(blueprint, review)
    resolved: set[str] = set()
    resolved, gaps = _resolve_seeds(blueprint, review, graph, seed_ids)
    if not gaps:
        included = _walk(resolved, _reverse_trace_adjacency(graph))
        terminal_inputs, terminal_bindings, terminal_resources = _terminal_groups(
            graph,
            included,
        )
        if not (terminal_inputs or terminal_bindings or terminal_resources):
            gaps.append(
                _trace_gap(
                    "trace_non_terminal_dead_end",
                    sorted(resolved),
                    "reverse trace reaches no explicit input, binding, or resource terminal",
                    "start from a business output, semantic, test, evidence, or other traceable terminal-bearing identity",
                )
            )
    else:
        # Reverse-trace queries are atomic just like affected queries.  A
        # mixed known/unknown request must not look like a complete trace for
        # the known subset while silently dropping the invalid seed.
        included = set()
    return _projection(
        "reverse_trace",
        blueprint,
        review,
        graph,
        seed_ids,
        included,
        gaps,
        "Reverse trace stops at every missing, stale, unsupported, or ambiguous physical ground and invents no predecessor.",
    )


def summary_physical_blueprint_projection(
    blueprint: PhysicalModelBlueprint,
    review: PhysicalModelBlueprintReview,
) -> BlueprintProjection:
    graph = compile_physical_blueprint_graph(blueprint, review)
    included = {
        node.node_id
        for node in graph.nodes
        if node.node_kind in {"target", "physical_element", "refinement_contract"}
    }
    return _projection(
        "summary",
        blueprint,
        review,
        graph,
        [],
        included,
        [],
        "Summary preserves the current depth, first gap, and claim boundary; omitted details are not passed.",
    )


def full_physical_blueprint_projection(
    blueprint: PhysicalModelBlueprint,
    review: PhysicalModelBlueprintReview,
) -> BlueprintProjection:
    graph = compile_physical_blueprint_graph(blueprint, review)
    return _projection(
        "full",
        blueprint,
        review,
        graph,
        [],
        {node.node_id for node in graph.nodes},
        [],
        "Full projection preserves the native review result and does not upgrade physical truth or empirical evidence.",
    )


def _resolve_seeds(
    blueprint: PhysicalModelBlueprint,
    review: PhysicalModelBlueprintReview,
    graph: CompiledPhysicalBlueprintGraph,
    seed_ids: Iterable[str],
) -> tuple[set[str], list[BlueprintGap]]:
    requested = sorted(set(seed_ids))
    node_ids = {node.node_id for node in graph.nodes}
    resolved: set[str] = set()
    gaps: list[BlueprintGap] = []
    if review.blueprint_fingerprint != fingerprint_blueprint(blueprint):
        gaps.append(
            _trace_gap(
                "trace_blueprint_fingerprint_mismatch",
                [review.blueprint_fingerprint, fingerprint_blueprint(blueprint)],
                "trace review belongs to another blueprint identity",
                "run the native reviewer on the exact current blueprint",
                status="stale",
            )
        )
        return resolved, gaps
    if review.subject_revision != blueprint.target.subject_revision:
        gaps.append(
            _trace_gap(
                "trace_subject_revision_mismatch",
                [review.subject_revision, blueprint.target.subject_revision],
                "trace review belongs to another target subject revision",
                "refresh the blueprint review for the current target revision",
                status="stale",
            )
        )
        return resolved, gaps
    if not requested:
        gaps.append(
            _trace_gap(
                "trace_seed_missing",
                [],
                "affected or reverse trace requires at least one exact seed identity",
                "supply an element, interface, semantic, binding, artifact, mapping, or refinement identity",
            )
        )
        return resolved, gaps
    for seed_id in requested:
        if seed_id in node_ids:
            resolved.add(seed_id)
            continue
        candidates = graph.aliases.get(seed_id, ())
        if not candidates:
            gaps.append(
                _trace_gap(
                    "trace_seed_unknown",
                    [seed_id],
                    "seed identity is absent from the current physical blueprint graph",
                    "supply an exact current identity; do not broaden automatically",
                )
            )
        elif len(candidates) > 1 and not _one_declared_public_identity(graph, candidates):
            gaps.append(
                _trace_gap(
                    "trace_seed_ambiguous",
                    [seed_id, *candidates],
                    "seed identity resolves to more than one typed blueprint node",
                    "supply the exact namespaced node identity",
                )
            )
        else:
            resolved.update(candidates)
    return resolved, gaps


def _qualified_source_review_gaps(
    blueprint: PhysicalModelBlueprint,
    review: PhysicalModelBlueprintReview,
    authority: TargetInventoryAuthority | None,
    blueprint_base_dir: str | Path | None,
    authority_base_dir: str | Path | None,
) -> list[BlueprintGap]:
    """Require one exact canonical passing review before any query processing.

    The supplied review is untrusted input even when its self-fingerprint is
    internally valid.  Every affected/reverse query therefore executes the
    sole native reviewer exactly once against the exact blueprint, target
    authority, blueprint artifact root, and authority artifact root.  The
    supplied review must then equal that current result field-for-field.  This
    helper never repairs, replaces, or partially accepts the supplied review.
    """

    missing_context: list[str] = []
    if authority is None:
        missing_context.append("target_inventory_authority")
    if blueprint_base_dir is None:
        missing_context.append("blueprint_base_dir")
    if authority_base_dir is None:
        missing_context.append("authority_base_dir")
    if missing_context:
        return [
            _trace_gap(
                "trace_source_review_context_missing",
                [review.review_id, *missing_context],
                "affected and reverse projections require the exact target authority, blueprint artifact root, and authority artifact root used by the source review",
                "supply all three exact source inputs and rerun the native review explicitly if any input has changed",
                status="stale",
            )
        ]

    canonical_review = review_physical_model_blueprint(
        blueprint,
        target_inventory_authority=authority,
        base_dir=blueprint_base_dir,
        authority_base_dir=authority_base_dir,
    )
    if canonical_review.status != "pass":
        return [
            _trace_gap(
                "trace_source_review_not_qualified",
                [
                    review.review_id,
                    canonical_review.review_id,
                    canonical_review.first_gap_id or canonical_review.status,
                ],
                f"canonical exact-current source review is {canonical_review.status}; the supplied review cannot license a bounded query",
                "resolve the canonical source gap, then explicitly issue and supply the new exact passing review",
                status=canonical_review.status,
            )
        ]

    supplied_payload = review.model_dump(mode="json", exclude_none=False)
    canonical_payload = canonical_review.model_dump(mode="json", exclude_none=False)
    mismatched = sorted(
        key
        for key in set(supplied_payload) | set(canonical_payload)
        if supplied_payload.get(key) != canonical_payload.get(key)
    )
    if mismatched:
        return [
            _trace_gap(
                "trace_source_review_identity_mismatch",
                [review.review_id, canonical_review.review_id, *mismatched],
                f"supplied source review differs from the canonical exact-current passing review in fields: {mismatched}",
                "supply the canonical review result unchanged; a foreign, stale, incomplete, or self-rehashed review is not query authority",
                status="stale",
            )
        ]
    return []


def _one_declared_public_identity(
    graph: CompiledPhysicalBlueprintGraph,
    candidates: Iterable[str],
) -> bool:
    """Return true only when aliases are explicitly joined as one identity."""

    candidate_set = set(candidates)
    if len(candidate_set) < 2:
        return True
    equivalent: dict[str, set[str]] = defaultdict(set)
    for edge in graph.edges:
        if edge.relation != "inventory_observes_object":
            continue
        equivalent[edge.source_id].add(edge.target_id)
        equivalent[edge.target_id].add(edge.source_id)
    return _walk({min(candidate_set)}, equivalent) >= candidate_set


def _walk(seeds: set[str], adjacency: dict[str, set[str]]) -> set[str]:
    visited = set(seeds)
    queue = deque(sorted(seeds))
    while queue:
        current = queue.popleft()
        for neighbor in sorted(adjacency.get(current, ())):
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append(neighbor)
    return visited


def _reverse_trace_adjacency(
    graph: CompiledPhysicalBlueprintGraph,
) -> dict[str, set[str]]:
    """Orient each typed edge toward the physical grounds of a selected result.

    A blanket reversal would lose the owner-to-ancestor chain, while treating
    every relation as bidirectional would turn one trace into a whole-target
    traversal.  The table below is therefore the executable ownership rule for
    reverse tracing.
    """

    reverse: dict[str, set[str]] = defaultdict(set)
    reverse_only = {
        "owns_interface",
        "owns_semantic",
        "owns_behavior_case",
        "consumes_input",
        "uses_state",
        "produces_output",
        "produces_effect",
        "case_input",
        "case_pre_state",
        "case_expected_output",
        "case_expected_post_state",
        "case_expected_effect",
        "case_checks_semantic",
        "case_test_evidence",
        "case_execution_evidence",
        "case_oracle",
        "bounds_semantic",
        "assumption_support",
        "materializes_binding",
        "supports_semantic",
        "supports_obligation",
        "owns_obligation",
        "observes_binding",
        "observes_inventory",
        "observes_target",
        "mapping_source",
        "mapping_target",
        "conversion_support",
        "mapping_evidence",
        "child_semantic",
        "semantic_preserves",
        "semantic_aggregates",
        "semantic_constrains",
        "semantic_weakens",
        "contribution_evidence",
        "inventory_maps_binding",
        "inventory_observes_object",
        "source_mapping_source",
        "source_mapping_observation",
        "source_mapping_target",
        "source_semantic_selector",
        "source_selector_contract",
        "qualifies_layer",
        "supports_claim",
        "review_claims_about",
    }
    forward_only = {
        "refines",
        "binds_element",
        "belongs_to_refinement",
        "declared_child",
        "qualifies_parent",
    }
    bidirectional: set[str] = set()
    for edge in graph.edges:
        if edge.relation in reverse_only:
            reverse[edge.target_id].add(edge.source_id)
        elif edge.relation in forward_only:
            reverse[edge.source_id].add(edge.target_id)
        elif edge.relation in bidirectional:
            reverse[edge.source_id].add(edge.target_id)
            reverse[edge.target_id].add(edge.source_id)
    return reverse


def _affected_adjacency(
    graph: CompiledPhysicalBlueprintGraph,
) -> dict[str, set[str]]:
    """Compile relation-specific, directional change propagation.

    Graph edges describe typed facts; they are not automatically undirected
    impact links.  In particular, a child can affect its parent abstraction,
    but merely reaching that parent must not fan back out into unrelated
    siblings.  Local ownership has an explicit reverse direction because a
    changed owned interface/semantic/boundary invalidates its owner contract.
    """

    adjacency: dict[str, set[str]] = defaultdict(set)
    forward = {
        "declares_target",
        "declares_provider",
        "declares_inventory",
        "requires_provider_observation",
        "provides_capability",
        "defines_inventory_boundary",
        "produces_inventory",
        "contains_inventory_member",
        "contains_element",
        "refines",
        "consumes_input",
        "uses_state",
        "produces_output",
        "produces_effect",
        "case_input",
        "case_pre_state",
        "case_checks_semantic",
        "case_test_evidence",
        "case_execution_evidence",
        "case_oracle",
        "bounds_semantic",
        "assumption_support",
        "materializes_binding",
        "binds_element",
        "observes_binding",
        "supports_semantic",
        "supports_obligation",
        "inventory_maps_element",
        "inventory_maps_binding",
        "qualifies_parent",
        "declared_child",
        "belongs_to_refinement",
        "mapping_source",
        "mapping_target",
        "conversion_support",
        "mapping_evidence",
        "child_semantic",
        "semantic_preserves",
        "semantic_aggregates",
        "semantic_constrains",
        "semantic_weakens",
        "contribution_evidence",
        "source_mapping_source",
        "source_mapping_observation",
        "source_mapping_target",
        "source_semantic_selector",
        "source_selector_contract",
    }
    owner_reverse = {
        "owns_obligation",
        "owns_interface",
        "owns_semantic",
        "owns_validity",
        "owns_behavior_case",
    }
    producer_reverse = {
        "produces_output",
        "produces_effect",
        "case_expected_output",
        "case_expected_post_state",
        "case_expected_effect",
        "mapping_target",
    }
    for edge in graph.edges:
        if not edge.propagates_change:
            continue
        if edge.relation in forward:
            adjacency[edge.source_id].add(edge.target_id)
        if edge.relation in owner_reverse:
            adjacency[edge.target_id].add(edge.source_id)
        if edge.relation in producer_reverse:
            adjacency[edge.target_id].add(edge.source_id)
    return adjacency


def _affected_closure(
    graph: CompiledPhysicalBlueprintGraph,
    resolved: set[str],
) -> set[str]:
    """Return functional impact plus bounded evidence that must be refreshed.

    Ownership and evidence relations are deliberately not undirected graph
    links.  If a changed child port reaches its owner, walking back out through
    every ``owns_*`` edge would incorrectly select every sibling port and
    semantic.  Likewise, walking semantic -> binding -> every other semantic
    supported by that binding would turn a local change into a whole-target
    result.  We therefore compute the functional closure first, then attach
    exact supporting bindings and their content identities as terminal
    revalidation obligations without propagating through them again.
    """

    initial = _expand_explicit_affected_seeds(graph, resolved)
    included = _walk(initial, _affected_adjacency(graph))

    evidence_relations = {
        "supports_semantic",
        "supports_obligation",
        "case_test_evidence",
        "case_execution_evidence",
        "case_oracle",
        "mapping_evidence",
        "contribution_evidence",
    }
    direct_case_outputs = {
        "case_expected_output",
        "case_expected_post_state",
        "case_expected_effect",
    }
    supporting_bindings: set[str] = set()
    terminal_context: set[str] = set()
    source_mapping_context: set[str] = set()
    for edge in graph.edges:
        if edge.relation in evidence_relations and edge.target_id in included:
            supporting_bindings.add(edge.source_id)
        if edge.relation in direct_case_outputs and edge.source_id in included:
            terminal_context.add(edge.target_id)
        if edge.relation == "source_mapping_target" and edge.target_id in included:
            source_mapping_context.add(edge.source_id)

    included.update(supporting_bindings)
    included.update(terminal_context)
    included.update(source_mapping_context)
    for edge in graph.edges:
        if edge.relation == "materializes_binding" and edge.target_id in supporting_bindings:
            included.add(edge.source_id)
        if (
            edge.relation
            in {"source_mapping_source", "source_mapping_observation"}
            and edge.target_id in source_mapping_context
        ):
            included.add(edge.source_id)
    return included


def _expand_explicit_affected_seeds(
    graph: CompiledPhysicalBlueprintGraph,
    resolved: set[str],
) -> set[str]:
    """Expand only an explicitly selected aggregate, never one reached later."""

    expanded = set(resolved)
    node_kind = {node.node_id: node.node_kind for node in graph.nodes}
    incident_by_refinement: dict[str, set[str]] = defaultdict(set)
    directly_owned_by_element: dict[str, set[str]] = defaultdict(set)
    for edge in graph.edges:
        if edge.relation in {
            "declared_child",
            "belongs_to_refinement",
            "qualifies_parent",
        }:
            if node_kind.get(edge.source_id) == "refinement_contract":
                incident_by_refinement[edge.source_id].add(edge.target_id)
            if node_kind.get(edge.target_id) == "refinement_contract":
                incident_by_refinement[edge.target_id].add(edge.source_id)
        if edge.relation in {
            "owns_obligation",
            "owns_interface",
            "owns_semantic",
            "owns_validity",
            "owns_behavior_case",
        } and node_kind.get(edge.source_id) == "physical_element":
            directly_owned_by_element[edge.source_id].add(edge.target_id)
    for seed_id in resolved:
        if node_kind.get(seed_id) == "refinement_contract":
            expanded.update(incident_by_refinement[seed_id])
        if node_kind.get(seed_id) == "physical_element":
            expanded.update(directly_owned_by_element[seed_id])
    return expanded


def _projection(
    kind: str,
    blueprint: PhysicalModelBlueprint,
    review: PhysicalModelBlueprintReview,
    graph: CompiledPhysicalBlueprintGraph,
    seed_ids: Iterable[str],
    included: set[str],
    operation_gaps: list[BlueprintGap],
    safe_claim: str,
) -> BlueprintProjection:
    all_nodes = {node.node_id for node in graph.nodes}
    selected_nodes = [node.model_dump(mode="json") for node in graph.nodes if node.node_id in included]
    selected_edges = [
        edge.model_dump(mode="json")
        for edge in graph.edges
        if edge.source_id in included and edge.target_id in included
    ]
    relevant_review_gaps = [
        gap
        for gap in review.gaps
        if not gap.target_ids or bool(set(gap.target_ids) & _raw_id_set(included))
    ]
    gaps_by_id = {gap.gap_id: gap for gap in (*relevant_review_gaps, *operation_gaps)}
    ordered_gaps = [gaps_by_id[key].model_dump(mode="json") for key in sorted(gaps_by_id)]
    terminal_inputs, terminal_bindings, terminal_resources = _terminal_groups(
        graph,
        included,
    )
    trace_status = _projection_status(ordered_gaps)
    relation_set = sorted(
        {
            (edge.relation, edge.propagates_change)
            for edge in graph.edges
        }
    )
    payload = {
        "schema_version": "physicsguard.physical-blueprint-projection.v1",
        "projection_kind": kind,
        "source_blueprint_fingerprint": review.blueprint_fingerprint,
        "source_review_fingerprint": review.logical_report_fingerprint,
        "relation_set_fingerprint": fingerprint_projection({"relations": relation_set}),
        "projection_recipe_fingerprint": fingerprint_projection(
            {"projection_kind": kind, "recipe_version": TRACE_RECIPE_VERSION}
        ),
        "target_system_id": blueprint.target.target_system_id,
        "subject_revision": blueprint.target.subject_revision,
        "seed_ids": sorted(set(seed_ids)),
        "nodes": selected_nodes,
        "edges": selected_edges,
        "included_member_ids": sorted(included),
        "outside_scope_ids": sorted(all_nodes - included),
        "gaps": ordered_gaps,
        "first_gap_id": ordered_gaps[0]["gap_id"] if ordered_gaps else None,
        "trace_status": trace_status,
        "terminal_input_ids": terminal_inputs,
        "terminal_binding_ids": terminal_bindings,
        "terminal_resource_ids": terminal_resources,
        "source_safe_claim": review.safe_claim,
        "safe_claim": safe_claim,
    }
    payload["projection_fingerprint"] = fingerprint_projection(payload)
    return BlueprintProjection.model_validate(payload)


def _rejected_projection(
    kind: str,
    blueprint: PhysicalModelBlueprint,
    review: PhysicalModelBlueprintReview,
    seed_ids: Iterable[str],
    operation_gaps: list[BlueprintGap],
    safe_claim: str,
) -> BlueprintProjection:
    """Return an atomic pre-graph rejection for an unqualified source review."""

    ordered_gaps = [
        gap.model_dump(mode="json")
        for gap in sorted(operation_gaps, key=lambda item: item.gap_id)
    ]
    payload = {
        "schema_version": "physicsguard.physical-blueprint-projection.v1",
        "projection_kind": kind,
        "source_blueprint_fingerprint": fingerprint_blueprint(blueprint),
        "source_review_fingerprint": review.logical_report_fingerprint,
        "relation_set_fingerprint": fingerprint_projection(
            {"qualified_source": False, "relations": []}
        ),
        "projection_recipe_fingerprint": fingerprint_projection(
            {"projection_kind": kind, "recipe_version": TRACE_RECIPE_VERSION}
        ),
        "target_system_id": blueprint.target.target_system_id,
        "subject_revision": blueprint.target.subject_revision,
        "seed_ids": sorted(set(seed_ids)),
        "nodes": [],
        "edges": [],
        "included_member_ids": [],
        "outside_scope_ids": [],
        "gaps": ordered_gaps,
        "first_gap_id": ordered_gaps[0]["gap_id"],
        "trace_status": _projection_status(ordered_gaps),
        "terminal_input_ids": [],
        "terminal_binding_ids": [],
        "terminal_resource_ids": [],
        "source_safe_claim": (
            "No supplied source-review claim is licensed because canonical "
            "exact-current qualification failed."
        ),
        "safe_claim": safe_claim,
    }
    payload["projection_fingerprint"] = fingerprint_projection(payload)
    return BlueprintProjection.model_validate(payload)


def _terminal_groups(
    graph: CompiledPhysicalBlueprintGraph,
    included: set[str],
) -> tuple[list[str], list[str], list[str]]:
    node_kind = {node.node_id: node.node_kind for node in graph.nodes}
    terminal_inputs = sorted(
        node_id
        for node_id in included
        if node_kind.get(node_id) in {"physical_input", "external_source"}
    )
    terminal_bindings = sorted(
        node_id
        for node_id in included
        if (node_kind.get(node_id) or "").startswith("native_")
    )
    terminal_resources = sorted(
        node_id
        for node_id in included
        if node_kind.get(node_id) == "content_addressed_artifact"
        or (node_kind.get(node_id) or "").startswith("source_")
    )
    return terminal_inputs, terminal_bindings, terminal_resources


def _projection_status(gaps: list[dict[str, object]]) -> str:
    statuses = {str(gap["status"]) for gap in gaps}
    if "blocked" in statuses:
        return "blocked"
    if "stale" in statuses:
        return "stale"
    if "incomplete" in statuses:
        return "incomplete"
    return "pass"


def _raw_id_set(node_ids: set[str]) -> set[str]:
    return {node_id.split(":", 1)[1] if ":" in node_id else node_id for node_id in node_ids}


def _trace_gap(
    code: str,
    target_ids: list[str],
    message: str,
    next_action: str,
    *,
    status: str = "blocked",
) -> BlueprintGap:
    normalized = sorted(set(target_ids))
    suffix = hashlib.sha256("\n".join(normalized).encode("utf-8")).hexdigest()[:12]
    return BlueprintGap(
        gap_id=f"gap:target_inventory:{code}:{suffix}",
        layer="target_inventory",
        status=status,
        code=code,
        message=message,
        target_ids=normalized,
        next_action=next_action,
    )


__all__ = [
    "CompiledPhysicalBlueprintGraph",
    "affected_physical_blueprint_projection",
    "compile_physical_blueprint_graph",
    "full_physical_blueprint_projection",
    "reverse_trace_physical_blueprint_projection",
    "summary_physical_blueprint_projection",
]
