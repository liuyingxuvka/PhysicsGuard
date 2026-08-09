"""Deterministic portable physical-DNA export and bundle-only queries."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from pydantic import ValidationError

from physicsguard.core.physical_blueprint_trace import (
    CompiledPhysicalBlueprintGraph,
    _affected_closure,
    _one_declared_public_identity,
    _reverse_trace_adjacency,
    _walk,
    compile_physical_blueprint_graph,
)
from physicsguard.schema.physical_blueprint_bundle import (
    MODULE_BEHAVIOR_CONTRACT_INDEX_SCHEMA,
    PHYSICAL_BLUEPRINT_EXPORT_BUNDLE_SCHEMA,
    ModuleBehaviorContractIndex,
    PhysicalBlueprintExportBundle,
    PortableBundleQueryGap,
    PortableBundleQueryResult,
    PortableCoverageLayer,
    PortableElementBehaviorContract,
    PortableEvidenceManifest,
    PortableEvidenceManifestEntry,
    PortableGraph,
    PortableModuleBehaviorContract,
    PortableSelectorKind,
    canonical_portable_bytes,
    portable_fingerprint,
)
from physicsguard.schema.physical_model_blueprint import (
    PhysicalModelBlueprint,
    PhysicalModelBlueprintReview,
    TargetInventoryAuthority,
    fingerprint_blueprint,
)


COMPACT_PROJECTION_BYTE_LIMIT = 8_192
DEEP_PROJECTION_BYTE_LIMIT = 131_072

MACHINE_SEMANTIC_DIMENSIONS = (
    "function_block",
    "equation_dependency",
    "unit",
    "constraint_valid_region",
    "behavioral_test",
    "counterexample",
    "independent_oracle",
)


class PhysicalBlueprintBundleError(ValueError):
    """Visible current-schema bundle failure with a stable category."""

    def __init__(self, category: str, message: str) -> None:
        super().__init__(message)
        self.category = category


def build_module_behavior_contract_index(
    module_review: Mapping[str, Any],
    runtime_port_registry: Mapping[str, Any],
) -> ModuleBehaviorContractIndex:
    """Freeze the exact module review plus scenario-role registry into one index.

    This adapter does not review modules.  It preserves the supplied checker
    results, including blocked/not-run states, and separately binds the live
    runtime-port registry that owns exact-scenario direction.
    """

    record_results = module_review.get("record_results")
    runtime_modules = runtime_port_registry.get("modules")
    if not isinstance(record_results, list) or not isinstance(runtime_modules, list):
        raise PhysicalBlueprintBundleError(
            "module_behavior_index_invalid",
            "module review record_results and runtime port registry modules must be lists",
        )
    runtime_by_type = {
        str(item.get("module_type")): item
        for item in runtime_modules
        if isinstance(item, Mapping) and item.get("module_type")
    }
    if len(runtime_by_type) != len(runtime_modules):
        raise PhysicalBlueprintBundleError(
            "module_behavior_index_invalid",
            "runtime port registry contains a missing or duplicate module type",
        )

    contracts: list[PortableModuleBehaviorContract] = []
    for result in sorted(record_results, key=lambda item: str(item.get("module_type"))):
        if not isinstance(result, Mapping):
            raise PhysicalBlueprintBundleError(
                "module_behavior_index_invalid",
                "module review contains a non-mapping record result",
            )
        module_type = str(result.get("module_type") or "")
        runtime = runtime_by_type.get(module_type)
        behavior_contract = result.get("behavior_contract")
        dimensions = result.get("dimensions")
        if runtime is None or not isinstance(behavior_contract, Mapping) or not isinstance(dimensions, Mapping):
            raise PhysicalBlueprintBundleError(
                "module_behavior_index_incomplete",
                f"module {module_type!r} is missing its runtime role, behavior contract, or dimension results",
            )
        embedded_fingerprint = behavior_contract.get("contract_fingerprint")
        if not isinstance(embedded_fingerprint, str):
            raise PhysicalBlueprintBundleError(
                "module_behavior_contract_fingerprint_missing",
                f"module {module_type!r} behavior contract has no current fingerprint",
            )
        dimension_statuses: dict[str, str] = {}
        for dimension, dimension_result in dimensions.items():
            if isinstance(dimension_result, Mapping):
                status = dimension_result.get("status")
                if status in {"pass", "incomplete", "stale", "blocked", "not_run"}:
                    dimension_statuses[str(dimension)] = str(status)
        direction_scope = runtime.get("direction_scope")
        scenario_role_resolved = (
            runtime.get("disposition") == "resolved"
            and isinstance(direction_scope, str)
            and bool(direction_scope.strip())
        )
        contracts.append(
            PortableModuleBehaviorContract(
                module_type=module_type,
                category=str(result.get("category") or "unclassified"),
                behavior_contract=dict(behavior_contract),
                dimension_statuses=dimension_statuses,
                scenario_role_status="resolved" if scenario_role_resolved else "unresolved",
                direction_scope=direction_scope,
                relation_directionality=runtime.get("relation_directionality"),
                first_gap=(dict(result["first_gap"]) if isinstance(result.get("first_gap"), Mapping) else None),
                physical_claim_licensed=result.get("physical_claim_licensed") is True,
                contract_fingerprint=embedded_fingerprint,
            )
        )

    module_types = {item.module_type for item in contracts}
    if module_types != set(runtime_by_type):
        missing = sorted(set(runtime_by_type) - module_types)
        foreign = sorted(module_types - set(runtime_by_type))
        raise PhysicalBlueprintBundleError(
            "module_behavior_index_denominator_mismatch",
            f"module behavior index differs from runtime registry; missing={missing}, foreign={foreign}",
        )

    summary = module_review.get("summary") if isinstance(module_review.get("summary"), Mapping) else {}
    total = len(contracts)
    inventory_pass = bool(summary.get("registry_inventory_reconciled")) and int(
        summary.get("registered_type_count", -1)
    ) == total
    role_count = sum(item.scenario_role_status == "resolved" for item in contracts)
    semantic_count = sum(
        all(item.dimension_statuses.get(dimension) == "pass" for dimension in MACHINE_SEMANTIC_DIMENSIONS)
        for item in contracts
    )
    review_count = sum(item.dimension_statuses.get("independent_review") == "pass" for item in contracts)
    licensed_count = sum(item.physical_claim_licensed for item in contracts)

    unresolved_runtime = next(
        (
            (
                runtime_by_type[item.module_type].get("first_gap", {}).get("code")
                if isinstance(runtime_by_type[item.module_type].get("first_gap"), Mapping)
                else None
            )
            or (
                "runtime_port_direction_scope_missing"
                if runtime_by_type[item.module_type].get("disposition") == "resolved"
                else "runtime_port_direction_unavailable"
            )
            for item in contracts
            if item.scenario_role_status == "unresolved"
        ),
        None,
    )
    semantic_gap = next(
        (
            str(item.first_gap.get("code"))
            for item in contracts
            if item.first_gap and item.first_gap.get("code")
        ),
        "module_domain_semantics_incomplete" if semantic_count < total else None,
    )
    review_gap = (
        "independent_module_semantic_review_pending" if review_count < total else None
    )
    claim_gap = "physical_claim_licensing_incomplete" if licensed_count < total else None
    layers = [
        _coverage_layer(
            "structural_inventory",
            total if inventory_pass else 0,
            total,
            None if inventory_pass else "module_inventory_not_reconciled",
        ),
        _coverage_layer("scenario_role", role_count, total, unresolved_runtime),
        _coverage_layer("domain_semantics", semantic_count, total, semantic_gap),
        _coverage_layer("independent_review", review_count, total, review_gap),
        _coverage_layer("claim_licensing", licensed_count, total, claim_gap),
    ]
    first_gap = next((layer.first_gap_code for layer in layers if layer.status != "pass"), None)
    payload = {
        "schema_version": MODULE_BEHAVIOR_CONTRACT_INDEX_SCHEMA,
        "checker_identity": str(module_review.get("checker_identity") or "unknown-checker"),
        "live_registry_fingerprint": str(runtime_port_registry.get("live_registry_fingerprint") or ""),
        "contracts": [item.model_dump(mode="json", exclude_none=True) for item in contracts],
        "coverage_layers": [item.model_dump(mode="json", exclude_none=True) for item in layers],
        "first_gap_code": first_gap,
    }
    payload["index_fingerprint"] = portable_fingerprint(
        payload,
        fingerprint_field="index_fingerprint",
    )
    try:
        return ModuleBehaviorContractIndex.model_validate(payload)
    except ValidationError as exc:
        raise PhysicalBlueprintBundleError(
            "module_behavior_index_invalid",
            f"invalid module behavior contract index: {exc}",
        ) from exc


def build_physical_blueprint_export_bundle(
    blueprint: PhysicalModelBlueprint,
    review: PhysicalModelBlueprintReview,
    target_inventory_authority: TargetInventoryAuthority,
    *,
    module_behavior_contract_index: ModuleBehaviorContractIndex | None = None,
) -> PhysicalBlueprintExportBundle:
    """Build one frozen bundle without reading any referenced artifact path."""

    graph = compile_physical_blueprint_graph(blueprint, review)
    portable_graph = _portable_graph(graph)
    element_contracts = _element_behavior_contracts(blueprint)
    evidence_manifest = _evidence_manifest(blueprint, target_inventory_authority)

    first_gap = review.gaps[0].code if review.gaps else None
    if first_gap is None and module_behavior_contract_index is not None:
        first_gap = module_behavior_contract_index.first_gap_code
    if first_gap is None:
        first_gap = next(
            (item.first_gap_code for item in element_contracts if item.first_gap_code),
            None,
        )
    source_fingerprints = {
        "blueprint": fingerprint_blueprint(blueprint),
        "review": review.logical_report_fingerprint,
        "target_inventory_authority": target_inventory_authority.authority_fingerprint,
        "relation_graph": portable_graph.graph_fingerprint,
        "evidence_manifest": evidence_manifest.manifest_fingerprint,
        "source_mappings": fingerprint_blueprint(blueprint.source_mappings),
    }
    if review.source_census_fingerprint is not None:
        source_fingerprints["source_census"] = review.source_census_fingerprint
    if review.native_behavior_case_universe_fingerprint is not None:
        source_fingerprints["native_behavior_case_universe"] = (
            review.native_behavior_case_universe_fingerprint
        )
    if module_behavior_contract_index is not None:
        source_fingerprints["module_behavior_contract_index"] = (
            module_behavior_contract_index.index_fingerprint
        )
    payload = {
        "schema_version": PHYSICAL_BLUEPRINT_EXPORT_BUNDLE_SCHEMA,
        "bundle_id": f"bundle.{blueprint.blueprint_id}.{review.logical_report_fingerprint[:16]}",
        "target_system_id": blueprint.target.target_system_id,
        "subject_revision": blueprint.target.subject_revision,
        "blueprint": blueprint.model_dump(mode="json", exclude_none=False),
        "target_inventory_authority": target_inventory_authority.model_dump(
            mode="json", exclude_none=False
        ),
        "review": review.model_dump(mode="json", exclude_none=False),
        "understanding_target": blueprint.understanding_target,
        "declared_consistency_status": review.declared_consistency_status,
        "object_dna_readiness": review.object_dna_readiness,
        "source_census": [
            item.model_dump(mode="json", exclude_none=False)
            for item in review.source_census
        ],
        "source_mappings": [
            item.model_dump(mode="json", exclude_none=False)
            for item in blueprint.source_mappings
        ],
        "element_behavior_contracts": [
            item.model_dump(mode="json", exclude_none=False) for item in element_contracts
        ],
        "module_behavior_contract_index": (
            module_behavior_contract_index.model_dump(mode="json", exclude_none=True)
            if module_behavior_contract_index is not None
            else None
        ),
        "relation_graph": portable_graph.model_dump(mode="json", exclude_none=True),
        "evidence_manifest": evidence_manifest.model_dump(mode="json", exclude_none=True),
        "source_fingerprints": source_fingerprints,
        "execution_trust_status": "observed_at_export_unlicensed",
        "first_gap_code": first_gap,
        "safe_claim": review.safe_claim,
        "claim_boundary": (
            f"{review.unsafe_claim_boundary} The portable bundle preserves frozen identities only; "
            "it performs no provider replay, native execution, empirical validation, or evidence refresh. "
            "Unsigned FMI execution results are observed-at-export only and do not license an isolated consumer to claim fresh execution."
        ),
    }
    payload["bundle_fingerprint"] = portable_fingerprint(
        payload,
        fingerprint_field="bundle_fingerprint",
    )
    try:
        return PhysicalBlueprintExportBundle.model_validate(payload)
    except ValidationError as exc:
        raise PhysicalBlueprintBundleError(
            "portable_bundle_invalid",
            f"invalid PhysicalBlueprintExportBundle: {exc}",
        ) from exc


def materialize_physical_blueprint_export_bundle(
    bundle: PhysicalBlueprintExportBundle,
    path: str | Path,
) -> int:
    """Write exact canonical bytes and return the byte count."""

    output_path = Path(path)
    if output_path.suffix.lower() != ".json":
        raise PhysicalBlueprintBundleError(
            "unsupported_bundle_format",
            "portable physical blueprint bundles use only the current canonical .json format",
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    content = canonical_portable_bytes(bundle)
    output_path.write_bytes(content)
    return len(content)


def load_physical_blueprint_export_bundle(
    path: str | Path,
) -> PhysicalBlueprintExportBundle:
    """Load one current portable bundle without following any embedded locator."""

    bundle_path = Path(path)
    if bundle_path.suffix.lower() != ".json":
        raise PhysicalBlueprintBundleError(
            "unsupported_bundle_format",
            "portable physical blueprint bundles use only the current canonical .json format",
        )
    try:
        payload = json.loads(bundle_path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise PhysicalBlueprintBundleError(
            "bundle_read_error",
            f"failed to read portable bundle '{bundle_path}': {exc}",
        ) from exc
    except json.JSONDecodeError as exc:
        raise PhysicalBlueprintBundleError(
            "malformed_bundle",
            f"malformed portable bundle '{bundle_path}': {exc}",
        ) from exc
    if not isinstance(payload, dict):
        raise PhysicalBlueprintBundleError(
            "invalid_bundle_root",
            "portable bundle root must be an object",
        )
    if payload.get("schema_version") != PHYSICAL_BLUEPRINT_EXPORT_BUNDLE_SCHEMA:
        raise PhysicalBlueprintBundleError(
            "unsupported_bundle_schema",
            f"expected {PHYSICAL_BLUEPRINT_EXPORT_BUNDLE_SCHEMA!r}",
        )
    try:
        return PhysicalBlueprintExportBundle.model_validate(payload)
    except ValidationError as exc:
        raise PhysicalBlueprintBundleError(
            "invalid_bundle_contract",
            f"invalid portable bundle '{bundle_path}': {exc}",
        ) from exc


def query_physical_blueprint_export_bundle(
    bundle: PhysicalBlueprintExportBundle,
    *,
    selector_kind: PortableSelectorKind = "status",
    selector_id: str | None = None,
) -> PortableBundleQueryResult:
    """Answer one bounded query from bundle content only."""

    if selector_kind == "status":
        if selector_id is not None:
            raise PhysicalBlueprintBundleError(
                "portable_query_selector_invalid",
                "status query accepts no selector id",
            )
        payload, gaps = _status_payload(bundle), _source_gaps(bundle)
        return _bounded_query_result(bundle, "status", None, payload, gaps)
    if selector_id is None or not selector_id.strip():
        raise PhysicalBlueprintBundleError(
            "portable_query_selector_missing",
            f"{selector_kind} query requires one exact id",
        )
    exact_id = selector_id.strip()
    if selector_kind == "module":
        payload, gaps = _module_query(bundle, exact_id)
    elif selector_kind == "element":
        payload, gaps = _element_query(bundle, exact_id)
    elif selector_kind == "case":
        payload, gaps = _case_query(bundle, exact_id)
    elif selector_kind in {"impact", "reverse"}:
        payload, gaps = _graph_query(bundle, selector_kind, exact_id)
    else:  # pragma: no cover - Pydantic/literal callers prevent this branch.
        raise PhysicalBlueprintBundleError(
            "portable_query_selector_invalid",
            f"unsupported portable selector kind: {selector_kind}",
        )
    return _bounded_query_result(bundle, selector_kind, exact_id, payload, gaps)


def _portable_graph(graph: CompiledPhysicalBlueprintGraph) -> PortableGraph:
    payload = {
        "nodes": [item.model_dump(mode="json", exclude_none=True) for item in graph.nodes],
        "edges": [item.model_dump(mode="json", exclude_none=True) for item in graph.edges],
        "aliases": {key: sorted(values) for key, values in sorted(graph.aliases.items())},
    }
    payload["graph_fingerprint"] = portable_fingerprint(
        payload,
        fingerprint_field="graph_fingerprint",
    )
    return PortableGraph.model_validate(payload)


def _element_behavior_contracts(
    blueprint: PhysicalModelBlueprint,
) -> list[PortableElementBehaviorContract]:
    ports_by_owner: dict[str, list[Any]] = {}
    for port in blueprint.ports:
        ports_by_owner.setdefault(port.owner_element_id, []).append(port)
    semantics_by_owner: dict[str, list[Any]] = {}
    for semantic in blueprint.semantics:
        semantics_by_owner.setdefault(semantic.owner_element_id, []).append(semantic)
    bindings_by_owner: dict[str, list[Any]] = {}
    for binding in blueprint.bindings:
        bindings_by_owner.setdefault(binding.owner_element_id, []).append(binding)
    cases_by_owner: dict[str, list[Any]] = {}
    for case in blueprint.behavior_cases:
        cases_by_owner.setdefault(case.owner_element_id, []).append(case)

    contracts: list[PortableElementBehaviorContract] = []
    for element in blueprint.elements:
        ports = ports_by_owner.get(element.element_id, [])
        semantics = semantics_by_owner.get(element.element_id, [])
        bindings = bindings_by_owner.get(element.element_id, [])
        behavior_cases = sorted(cases_by_owner.get(element.element_id, []), key=lambda item: item.case_id)
        failures = sorted(
            semantic.semantic_id
            for semantic in semantics
            if semantic.semantic_kind == "protected_failure"
        )
        termination_ids = sorted(
            semantic.semantic_id
            for semantic in semantics
            if semantic.semantic_kind == "termination"
        )
        oracle_ids = sorted(
            binding.binding_id
            for binding in bindings
            if binding.binding_kind == "oracle"
        )
        first_gap = None
        if not failures:
            first_gap = "element_protected_failure_contract_missing"
        elif not termination_ids:
            first_gap = "element_termination_contract_missing"
        elif not oracle_ids:
            first_gap = "element_independent_oracle_binding_missing"
        elif any(case.status != "pass" for case in behavior_cases):
            first_gap = next(
                case.first_gap_code or "element_behavior_case_not_pass"
                for case in behavior_cases
                if case.status != "pass"
            )
        payload = {
            "contract_id": f"element-behavior:{element.element_id}",
            "element_id": element.element_id,
            "input_port_ids": sorted(port.port_id for port in ports if port.direction == "input"),
            "pre_state_port_ids": sorted(port.port_id for port in ports if port.direction == "state"),
            "output_port_ids": sorted(port.port_id for port in ports if port.direction == "output"),
            "post_state_port_ids": sorted(port.port_id for port in ports if port.direction == "state"),
            "effect_port_ids": sorted(port.port_id for port in ports if port.direction == "effect"),
            "semantic_ids": sorted(semantic.semantic_id for semantic in semantics),
            "preconditions": sorted({item for semantic in semantics for item in semantic.preconditions}),
            "postconditions": sorted({item for semantic in semantics for item in semantic.postconditions}),
            "protected_failures": failures,
            "termination_semantic_ids": termination_ids,
            "oracle_binding_ids": oracle_ids,
            "behavior_cases": [
                case.model_dump(mode="json", exclude_none=False) for case in behavior_cases
            ],
            "status": "pass" if first_gap is None else "incomplete",
            "first_gap_code": first_gap,
        }
        payload["contract_fingerprint"] = portable_fingerprint(
            payload,
            fingerprint_field="contract_fingerprint",
        )
        contracts.append(PortableElementBehaviorContract.model_validate(payload))
    return contracts


def _evidence_manifest(
    blueprint: PhysicalModelBlueprint,
    authority: TargetInventoryAuthority,
) -> PortableEvidenceManifest:
    entries: list[PortableEvidenceManifestEntry] = []
    for binding in blueprint.bindings:
        artifact = binding.artifact
        locator_kind = "repo_path" if artifact.repo_path is not None else "external_uri"
        locator = artifact.repo_path or artifact.external_uri
        assert locator is not None
        status = "pass" if binding.status == "current" else "stale" if binding.status == "stale" else "blocked"
        entries.append(
            PortableEvidenceManifestEntry(
                manifest_id=f"binding:{binding.binding_id}",
                artifact_kind=binding.binding_kind,
                subject_id=binding.subject_id,
                subject_revision=binding.subject_revision,
                sha256=artifact.sha256,
                locator_kind=locator_kind,
                locator=locator,
                status=status,
                claim_boundary="identity only; artifact bytes are not embedded and the portable consumer must not follow this locator",
            )
        )
    for reference in authority.input_references:
        artifact = reference.artifact
        locator_kind = "repo_path" if artifact.repo_path is not None else "external_uri"
        locator = artifact.repo_path or artifact.external_uri
        assert locator is not None
        entries.append(
            PortableEvidenceManifestEntry(
                manifest_id=f"authority-input:{reference.reference_id}",
                artifact_kind="target_inventory_input",
                subject_id=reference.reference_id,
                subject_revision=authority.subject_revision,
                sha256=artifact.sha256,
                locator_kind=locator_kind,
                locator=locator,
                status="pass" if authority.status == "current" else "stale" if authority.status == "stale" else "blocked",
                claim_boundary="identity only; authority input bytes are not embedded and are not replayed by bundle queries",
            )
        )
    entries.sort(key=lambda item: item.manifest_id)
    payload = {"entries": [item.model_dump(mode="json") for item in entries]}
    payload["manifest_fingerprint"] = portable_fingerprint(
        payload,
        fingerprint_field="manifest_fingerprint",
    )
    return PortableEvidenceManifest.model_validate(payload)


def _coverage_layer(
    layer_id: str,
    covered_count: int,
    total_count: int,
    first_gap_code: str | None,
) -> PortableCoverageLayer:
    return PortableCoverageLayer(
        layer_id=layer_id,
        status="pass" if covered_count == total_count else "incomplete",
        covered_count=covered_count,
        total_count=total_count,
        first_gap_code=None if covered_count == total_count else first_gap_code,
    )


def _bundle_coverage_layers(
    bundle: PhysicalBlueprintExportBundle,
) -> list[PortableCoverageLayer]:
    if bundle.module_behavior_contract_index is not None:
        return bundle.module_behavior_contract_index.coverage_layers
    total = len(bundle.element_behavior_contracts)
    structural_covered = len(bundle.review.coverage.covered_member_ids)
    structural_total = len(bundle.review.coverage.governed_member_ids)
    role_covered = sum(
        bool(
            item.input_port_ids
            or item.output_port_ids
            or item.pre_state_port_ids
            or item.effect_port_ids
        )
        for item in bundle.element_behavior_contracts
    )
    semantic_covered = sum(item.status == "pass" for item in bundle.element_behavior_contracts)
    reviewed = total if bundle.review.status == "pass" and semantic_covered == total else 0
    licensed = reviewed
    return [
        _coverage_layer(
            "structural_inventory",
            structural_covered,
            structural_total,
            "target_inventory_coverage_incomplete",
        ),
        _coverage_layer("scenario_role", role_covered, total, "element_port_roles_missing"),
        _coverage_layer(
            "domain_semantics",
            semantic_covered,
            total,
            next(
                (item.first_gap_code for item in bundle.element_behavior_contracts if item.first_gap_code),
                "element_domain_semantics_incomplete",
            ),
        ),
        _coverage_layer(
            "independent_review",
            reviewed,
            total,
            "element_behavior_independent_review_incomplete",
        ),
        _coverage_layer(
            "claim_licensing",
            licensed,
            total,
            "element_behavior_claim_licensing_incomplete",
        ),
    ]


def _status_payload(bundle: PhysicalBlueprintExportBundle) -> dict[str, Any]:
    return {
        "bundle_id": bundle.bundle_id,
        "target_system_id": bundle.target_system_id,
        "subject_revision": bundle.subject_revision,
        "source_fingerprints": bundle.source_fingerprints,
        "understanding_target": bundle.understanding_target,
        "declared_consistency_status": bundle.declared_consistency_status,
        "object_dna_readiness": bundle.object_dna_readiness,
        "source_census_fingerprint": bundle.review.source_census_fingerprint,
        "native_behavior_case_universe_fingerprint": (
            bundle.review.native_behavior_case_universe_fingerprint
        ),
        "source_mapping_count": len(bundle.source_mappings),
        "execution_trust_status": bundle.execution_trust_status,
        "target_counts": {
            "inventory_members": len(bundle.blueprint.inventory.members),
            "elements": len(bundle.blueprint.elements),
            "ports": len(bundle.blueprint.ports),
            "semantics": len(bundle.blueprint.semantics),
            "bindings": len(bundle.blueprint.bindings),
            "source_census_members": len(bundle.source_census),
            "source_mappings": len(bundle.source_mappings),
            "native_behavior_cases": len(bundle.review.native_behavior_case_universe),
            "graph_nodes": len(bundle.relation_graph.nodes),
            "graph_edges": len(bundle.relation_graph.edges),
        },
        "module_contract_index_present": bundle.module_behavior_contract_index is not None,
    }


def _source_gaps(bundle: PhysicalBlueprintExportBundle) -> list[PortableBundleQueryGap]:
    if bundle.first_gap_code is None:
        return []
    return [
        PortableBundleQueryGap(
            code=bundle.first_gap_code,
            status=(bundle.review.status if bundle.review.status != "pass" else "incomplete"),
            target_ids=[],
            message="the frozen bundle retains this first unresolved understanding or licensing gap",
            claim_boundary=bundle.claim_boundary,
        )
    ]


def _module_query(
    bundle: PhysicalBlueprintExportBundle,
    module_type: str,
) -> tuple[dict[str, Any], list[PortableBundleQueryGap]]:
    index = bundle.module_behavior_contract_index
    if index is None:
        return {}, [_not_in_bundle_gap(module_type, "module behavior contract index was not supplied to this bundle")]
    contract = next((item for item in index.contracts if item.module_type == module_type), None)
    if contract is None:
        return {}, [_not_in_bundle_gap(module_type, "module id is not present in the frozen module denominator")]
    gaps: list[PortableBundleQueryGap] = []
    if contract.first_gap:
        gaps.append(
            PortableBundleQueryGap(
                code=str(contract.first_gap.get("code") or "module_contract_incomplete"),
                status="incomplete",
                target_ids=[module_type],
                message=str(contract.first_gap.get("message") or "module behavior contract is incomplete"),
                claim_boundary="this module detail preserves the frozen checker gap and does not independently license physical semantics",
            )
        )
    return contract.model_dump(mode="json", exclude_none=True), gaps


def _element_query(
    bundle: PhysicalBlueprintExportBundle,
    element_id: str,
) -> tuple[dict[str, Any], list[PortableBundleQueryGap]]:
    element = next((item for item in bundle.blueprint.elements if item.element_id == element_id), None)
    if element is None:
        return {}, [_not_in_bundle_gap(element_id, "physical element id is not present in the frozen blueprint")]
    children = sorted(
        item.element_id for item in bundle.blueprint.elements if item.parent_id == element_id
    )
    ports = [
        item.model_dump(mode="json", exclude_none=True)
        for item in bundle.blueprint.ports
        if item.owner_element_id == element_id
    ]
    semantics = [
        item.model_dump(mode="json", exclude_none=True)
        for item in bundle.blueprint.semantics
        if item.owner_element_id == element_id
    ]
    boundaries = [
        item.model_dump(mode="json", exclude_none=True)
        for item in bundle.blueprint.validity_boundaries
        if item.owner_element_id == element_id
    ]
    binding_ids = sorted(
        item.binding_id for item in bundle.blueprint.bindings if item.owner_element_id == element_id
    )
    contract = next(
        item for item in bundle.element_behavior_contracts if item.element_id == element_id
    )
    gaps = []
    if contract.first_gap_code:
        gaps.append(
            PortableBundleQueryGap(
                code=contract.first_gap_code,
                status=contract.status,
                target_ids=[element_id],
                message="element transition-and-oracle contract is not yet complete",
                claim_boundary="the bundle exposes only declared element behavior and does not infer missing failures, termination, or oracle meaning",
            )
        )
    return {
        "element": element.model_dump(mode="json", exclude_none=True),
        "parent_id": element.parent_id,
        "child_ids": children,
        "ports": ports,
        "semantics": semantics,
        "validity_boundaries": boundaries,
        "binding_ids": binding_ids,
        "behavior_contract": contract.model_dump(mode="json", exclude_none=True),
    }, gaps


def _case_query(
    bundle: PhysicalBlueprintExportBundle,
    case_id: str,
) -> tuple[dict[str, Any], list[PortableBundleQueryGap]]:
    element_matches: list[tuple[PortableElementBehaviorContract, Any]] = []
    for contract in bundle.element_behavior_contracts:
        for case in contract.behavior_cases:
            aliases = {case.case_id, case.native_case_id, case.case_fingerprint}
            if case_id in aliases:
                element_matches.append((contract, case))
    if len(element_matches) > 1:
        return {}, [
            PortableBundleQueryGap(
                code="portable_query_ambiguous",
                status="blocked",
                target_ids=[case_id, *sorted(item[0].element_id for item in element_matches)],
                message="case id resolves to more than one frozen physical behavior case",
                claim_boundary="portable queries never choose an arbitrary case",
            )
        ]
    if element_matches:
        contract, case = element_matches[0]
        return {
            "element_id": contract.element_id,
            "contract_fingerprint": contract.contract_fingerprint,
            "case": case.model_dump(mode="json", exclude_none=False),
            "element_first_gap_code": contract.first_gap_code,
            "frozen_case_status": case.status,
            "execution_claim_licensed": False,
            "physical_claim_licensed": False,
            "execution_trust_status": bundle.execution_trust_status,
            "claim_boundary": "The isolated bundle preserves an export-time case result but does not replay FMI bytes or carry a trusted signed terminal receipt.",
        }, []

    index = bundle.module_behavior_contract_index
    if index is None:
        return {}, [_not_in_bundle_gap(case_id, "behavior case id is not present in the frozen element contracts and no module case index was supplied")]
    matches: list[tuple[PortableModuleBehaviorContract, dict[str, Any]]] = []
    for contract in index.contracts:
        cases = contract.behavior_contract.get("behavior_cases")
        if not isinstance(cases, list):
            continue
        for case in cases:
            if not isinstance(case, Mapping):
                continue
            aliases = {
                str(case.get("case_fingerprint") or ""),
                str(case.get("pytest_nodeid") or ""),
                f"{contract.module_type}:{case.get('case_kind')}",
            }
            if case_id in aliases:
                matches.append((contract, dict(case)))
    if not matches:
        return {}, [_not_in_bundle_gap(case_id, "behavior case id is not present in the frozen contract index")]
    if len(matches) > 1:
        return {}, [
            PortableBundleQueryGap(
                code="portable_query_ambiguous",
                status="blocked",
                target_ids=[case_id, *sorted(item[0].module_type for item in matches)],
                message="case id resolves to more than one frozen behavior case",
                claim_boundary="portable queries never choose an arbitrary case",
            )
        ]
    contract, case = matches[0]
    return {
        "module_type": contract.module_type,
        "contract_fingerprint": contract.contract_fingerprint,
        "case": case,
        "module_first_gap": contract.first_gap,
        "physical_claim_licensed": contract.physical_claim_licensed,
    }, []


def _graph_query(
    bundle: PhysicalBlueprintExportBundle,
    query_kind: str,
    seed_id: str,
) -> tuple[dict[str, Any], list[PortableBundleQueryGap]]:
    graph = CompiledPhysicalBlueprintGraph(
        nodes=tuple(bundle.relation_graph.nodes),
        edges=tuple(bundle.relation_graph.edges),
        aliases={key: tuple(values) for key, values in bundle.relation_graph.aliases.items()},
    )
    node_ids = {item.node_id for item in graph.nodes}
    if seed_id in node_ids:
        resolved = {seed_id}
    else:
        candidates = set(graph.aliases.get(seed_id, ()))
        if not candidates:
            return {}, [_not_in_bundle_gap(seed_id, "graph seed id is not present in the frozen bundle")]
        if len(candidates) > 1 and not _one_declared_public_identity(graph, candidates):
            return {}, [
                PortableBundleQueryGap(
                    code="portable_query_ambiguous",
                    status="blocked",
                    target_ids=[seed_id, *sorted(candidates)],
                    message="graph seed resolves to more than one typed node",
                    claim_boundary="portable queries never broaden or choose an arbitrary graph identity",
                )
            ]
        resolved = candidates
    if query_kind == "impact":
        included = _affected_closure(graph, resolved)
    else:
        included = _walk(resolved, _reverse_trace_adjacency(graph))
    nodes = [
        item.model_dump(mode="json", exclude_none=True)
        for item in graph.nodes
        if item.node_id in included
    ]
    edges = [
        item.model_dump(mode="json", exclude_none=True)
        for item in graph.edges
        if item.source_id in included and item.target_id in included
    ]
    gaps: list[PortableBundleQueryGap] = []
    selected_kinds = {item.node_id: item.node_kind for item in graph.nodes}
    identity_only = sorted(
        node_id for node_id in included if selected_kinds.get(node_id) == "content_addressed_artifact"
    )
    if identity_only:
        gaps.append(
            PortableBundleQueryGap(
                code="portable_query_identity_only_terminal",
                status="incomplete",
                target_ids=identity_only,
                message="the closure reaches artifact identities whose bytes are not embedded in the bundle",
                claim_boundary="the consumer may name these identities but must not follow their locators or claim their bytes were replayed",
            )
        )
    return {
        "seed_id": seed_id,
        "resolved_seed_ids": sorted(resolved),
        "included_member_ids": sorted(included),
        "outside_scope_ids": sorted(node_ids - included),
        "nodes": nodes,
        "edges": edges,
        "relation_graph_fingerprint": bundle.relation_graph.graph_fingerprint,
    }, gaps


def _not_in_bundle_gap(target_id: str, message: str) -> PortableBundleQueryGap:
    return PortableBundleQueryGap(
        code="portable_query_not_in_bundle",
        status="blocked",
        target_ids=[target_id],
        message=message,
        claim_boundary="the portable consumer cannot scan a repository, invoke a provider, or guess a replacement identity",
    )


def _bounded_query_result(
    bundle: PhysicalBlueprintExportBundle,
    query_kind: PortableSelectorKind,
    query_id: str | None,
    payload: dict[str, Any],
    gaps: Sequence[PortableBundleQueryGap],
) -> PortableBundleQueryResult:
    layers = _bundle_coverage_layers(bundle)
    first_gap = gaps[0].code if gaps else bundle.first_gap_code
    status = _query_status(bundle, gaps, first_gap)
    limit = COMPACT_PROJECTION_BYTE_LIMIT if query_kind == "status" else DEEP_PROJECTION_BYTE_LIMIT
    result_payload = {
        "bundle_fingerprint": bundle.bundle_fingerprint,
        "query_kind": query_kind,
        "query_id": query_id,
        "status": status,
        "source_review_status": bundle.review.status,
        "deepest_licensed_layer": bundle.review.deepest_licensed_layer,
        "coverage_layers": [item.model_dump(mode="json", exclude_none=True) for item in layers],
        "first_gap_code": first_gap,
        "safe_claim": bundle.safe_claim,
        "claim_boundary": bundle.claim_boundary,
        "payload": payload,
        "gaps": [item.model_dump(mode="json", exclude_none=True) for item in gaps],
        "bundle_canonical_bytes": len(canonical_portable_bytes(bundle)),
        "projection_canonical_bytes": 1,
        "projection_byte_limit": limit,
    }
    result = _with_stable_projection_size(result_payload)
    if result.projection_canonical_bytes <= limit:
        return result
    budget_gap = PortableBundleQueryGap(
        code="portable_projection_budget_exceeded",
        status="blocked",
        target_ids=[query_id] if query_id else [],
        message=(
            f"{query_kind} projection requires {result.projection_canonical_bytes} canonical bytes, "
            f"exceeding its {limit}-byte hard budget"
        ),
        claim_boundary="the oversized projection is not returned and the query never falls back to the full bundle",
    )
    result_payload.update(
        {
            "status": "blocked",
            "first_gap_code": budget_gap.code,
            "payload": {
                "requested_projection_bytes": result.projection_canonical_bytes,
                "projection_byte_limit": limit,
            },
            "gaps": [budget_gap.model_dump(mode="json")],
            "projection_canonical_bytes": 1,
        }
    )
    return _with_stable_projection_size(result_payload)


def _with_stable_projection_size(payload: dict[str, Any]) -> PortableBundleQueryResult:
    current = dict(payload)
    for _ in range(8):
        result = PortableBundleQueryResult.model_validate(current)
        measured = len(canonical_portable_bytes(result))
        if measured == result.projection_canonical_bytes:
            return result
        current["projection_canonical_bytes"] = measured
    raise PhysicalBlueprintBundleError(
        "portable_projection_size_unstable",
        "canonical projection byte count did not converge",
    )


def _query_status(
    bundle: PhysicalBlueprintExportBundle,
    gaps: Sequence[PortableBundleQueryGap],
    first_gap: str | None,
) -> str:
    statuses = {item.status for item in gaps}
    if "blocked" in statuses or bundle.review.status == "blocked":
        return "blocked"
    if "stale" in statuses or bundle.review.status == "stale":
        return "stale"
    if "incomplete" in statuses or bundle.review.status == "incomplete" or first_gap is not None:
        return "incomplete"
    return "pass"


__all__ = [
    "COMPACT_PROJECTION_BYTE_LIMIT",
    "DEEP_PROJECTION_BYTE_LIMIT",
    "PhysicalBlueprintBundleError",
    "build_module_behavior_contract_index",
    "build_physical_blueprint_export_bundle",
    "load_physical_blueprint_export_bundle",
    "materialize_physical_blueprint_export_bundle",
    "query_physical_blueprint_export_bundle",
]
