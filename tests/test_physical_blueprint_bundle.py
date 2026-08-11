from __future__ import annotations

import json
from pathlib import Path

import pytest

from physicsguard.cli import main
from physicsguard.core.physical_blueprint_bundle import (
    COMPACT_PROJECTION_BYTE_LIMIT,
    DEEP_PROJECTION_BYTE_LIMIT,
    PhysicalBlueprintBundleError,
    build_module_behavior_contract_index,
    build_physical_blueprint_export_bundle,
    load_physical_blueprint_export_bundle,
    materialize_physical_blueprint_export_bundle,
    query_physical_blueprint_export_bundle,
)
from physicsguard.schema.physical_blueprint_bundle import canonical_portable_bytes


def _reviewed_bundle(complete_physical_blueprint):
    blueprint, base_dir = complete_physical_blueprint()
    review = complete_physical_blueprint.review(blueprint, base_dir=base_dir)
    bundle = build_physical_blueprint_export_bundle(
        blueprint,
        review,
        complete_physical_blueprint.target_inventory_authority,
    )
    return blueprint, review, bundle


def _behavior_contract(module_type: str, *, large: bool = False) -> dict:
    payload = {
        "schema": "physicsguard.module_behavior_contract.v1",
        "contract_id": f"physicsguard.module_behavior.{module_type}",
        "module_type": module_type,
        "signature": "Input + PreState -> Output + PostState + Effect",
        "direction_model": {
            "scope": "exact_instantiation_scenario",
            "relation_directionality": "direction_neutral",
        },
        "inputs": [{"name": "x", "role": "input", "unit": "1"}],
        "pre_state": {"previous": [], "current": [], "source_declared": True},
        "outputs": [{"name": "y", "kind": "declared_variable", "unit": "1"}],
        "post_state": {"next": [], "source_declared": True},
        "effects": {"members": [], "source_declared": True},
        "protected_failures": {"members": [], "source_declared": True},
        "termination": {"statement": "finite"},
        "behavior_cases": [
            {
                "case_kind": "positive",
                "pytest_nodeid": f"tests/test_demo.py::test_{module_type.lower()}_positive",
                "case_fingerprint": ("1" if module_type == "ResolvedModule" else "2") * 64,
            }
        ],
        "verification": {
            "status": "blocked",
            "claim_boundary": "fixture contract remains unlicensed",
        },
        "padding": "x" * 150_000 if large else "",
        "contract_fingerprint": ("a" if module_type == "ResolvedModule" else "b") * 64,
    }
    return payload


def _module_index(*, large: bool = False):
    dimensions_pass = {
        name: {"status": "pass", "finding_count": 0, "findings": []}
        for name in (
            "registry_inventory",
            "function_block",
            "equation_dependency",
            "unit",
            "constraint_valid_region",
            "behavioral_test",
            "counterexample",
            "independent_oracle",
            "independent_review",
        )
    }
    dimensions_blocked = {
        **dimensions_pass,
        "equation_dependency": {
            "status": "blocked",
            "finding_count": 1,
            "findings": [
                {
                    "code": "source_semantic_ir_binding_missing",
                    "message": "source semantic IR is missing",
                }
            ],
        },
        "independent_review": {
            "status": "blocked",
            "finding_count": 1,
            "findings": [
                {
                    "code": "independent_review_pending",
                    "message": "independent review is pending",
                }
            ],
        },
    }
    review = {
        "checker_identity": "physicsguard.module_semantics_ledger_check.v3",
        "record_results": [
            {
                "module_type": "ResolvedModule",
                "category": "physical_module",
                "physical_claim_licensed": False,
                "behavior_contract": _behavior_contract("ResolvedModule", large=large),
                "first_gap": {
                    "dimension": "independent_review",
                    "code": "independent_review_pending",
                    "message": "independent review is pending",
                },
                "dimensions": dimensions_pass,
            },
            {
                "module_type": "UnresolvedModule",
                "category": "physical_module",
                "physical_claim_licensed": False,
                "behavior_contract": _behavior_contract("UnresolvedModule"),
                "first_gap": {
                    "dimension": "equation_dependency",
                    "code": "source_semantic_ir_binding_missing",
                    "message": "source semantic IR is missing",
                },
                "dimensions": dimensions_blocked,
            },
        ],
        "summary": {
            "registered_type_count": 2,
            "registry_inventory_reconciled": True,
        },
    }
    registry = {
        "live_registry_fingerprint": "c" * 64,
        "modules": [
            {
                "module_type": "ResolvedModule",
                "disposition": "resolved",
                "direction_scope": "exact_instantiation_scenario",
                "relation_directionality": "direction_neutral",
                "first_gap": None,
            },
            {
                "module_type": "UnresolvedModule",
                "disposition": "unresolved",
                "first_gap": {
                    "code": "runtime_port_direction_unavailable",
                    "message": "role authority is missing",
                },
            },
        ],
    }
    return build_module_behavior_contract_index(review, registry)


def test_retired_disk_materialization_is_hard_blocked(
    complete_physical_blueprint,
    tmp_path: Path,
) -> None:
    _, review, bundle = _reviewed_bundle(complete_physical_blueprint)
    output = tmp_path / "bundle.json"

    with pytest.raises(PhysicalBlueprintBundleError) as materialize_error:
        materialize_physical_blueprint_export_bundle(bundle, output)
    assert materialize_error.value.category == "native_directory_only"
    assert not output.exists()

    with pytest.raises(PhysicalBlueprintBundleError) as load_error:
        load_physical_blueprint_export_bundle(output)
    assert load_error.value.category == "native_directory_only"
    assert review.status == bundle.review.status


def test_default_projection_is_compact_and_never_contains_the_full_bundle(
    complete_physical_blueprint,
) -> None:
    _, _, bundle = _reviewed_bundle(complete_physical_blueprint)

    result = query_physical_blueprint_export_bundle(bundle)
    rendered = canonical_portable_bytes(result)

    assert result.query_kind == "status"
    assert result.projection_canonical_bytes == len(rendered)
    assert result.projection_canonical_bytes <= COMPACT_PROJECTION_BYTE_LIMIT
    assert result.bundle_canonical_bytes == len(canonical_portable_bytes(bundle))
    assert "blueprint" not in result.payload
    assert "relation_graph" not in result.payload
    assert result.payload["target_counts"]["elements"] == len(bundle.blueprint.elements)


def test_exact_element_impact_and_reverse_queries_use_only_frozen_bundle_content(
    complete_physical_blueprint,
) -> None:
    _, _, bundle = _reviewed_bundle(complete_physical_blueprint)

    element = query_physical_blueprint_export_bundle(
        bundle,
        selector_kind="element",
        selector_id="pipe",
    )
    impact = query_physical_blueprint_export_bundle(
        bundle,
        selector_kind="impact",
        selector_id="port.pipe.flow",
    )
    reverse = query_physical_blueprint_export_bundle(
        bundle,
        selector_kind="reverse",
        selector_id="port.loop.flow",
    )

    assert element.payload["element"]["element_id"] == "pipe"
    assert "port.pipe.mass" in element.payload["behavior_contract"]["pre_state_port_ids"]
    assert "element:pipe" in impact.payload["included_member_ids"]
    assert "element:pump_loop" in reverse.payload["included_member_ids"]
    assert all(
        result.projection_canonical_bytes <= DEEP_PROJECTION_BYTE_LIMIT
        for result in (element, impact, reverse)
    )


def test_module_and_case_queries_preserve_scenario_role_and_unlicensed_gap(
    complete_physical_blueprint,
) -> None:
    blueprint, base_dir = complete_physical_blueprint()
    review = complete_physical_blueprint.review(blueprint, base_dir=base_dir)
    bundle = build_physical_blueprint_export_bundle(
        blueprint,
        review,
        complete_physical_blueprint.target_inventory_authority,
        module_behavior_contract_index=_module_index(),
    )

    status = query_physical_blueprint_export_bundle(bundle)
    module = query_physical_blueprint_export_bundle(
        bundle,
        selector_kind="module",
        selector_id="ResolvedModule",
    )
    case = query_physical_blueprint_export_bundle(
        bundle,
        selector_kind="case",
        selector_id="ResolvedModule:positive",
    )

    layers = {item.layer_id: item for item in status.coverage_layers}
    assert layers["structural_inventory"].covered_count == 2
    assert layers["scenario_role"].covered_count == 1
    assert layers["scenario_role"].total_count == 2
    assert status.first_gap_code == "runtime_port_direction_unavailable"
    assert module.payload["direction_scope"] == "exact_instantiation_scenario"
    assert module.payload["relation_directionality"] == "direction_neutral"
    assert module.payload["physical_claim_licensed"] is False
    assert case.payload["module_type"] == "ResolvedModule"
    assert case.payload["physical_claim_licensed"] is False
    assert module.projection_canonical_bytes <= DEEP_PROJECTION_BYTE_LIMIT
    assert case.projection_canonical_bytes <= DEEP_PROJECTION_BYTE_LIMIT


def test_resolved_runtime_role_without_scope_remains_an_explicit_gap() -> None:
    dimensions = {
        name: {"status": "pass", "finding_count": 0, "findings": []}
        for name in (
            "registry_inventory",
            "function_block",
            "equation_dependency",
            "unit",
            "constraint_valid_region",
            "behavioral_test",
            "counterexample",
            "independent_oracle",
            "independent_review",
        )
    }
    review = {
        "checker_identity": "physicsguard.module_semantics_ledger_check.v3",
        "record_results": [
            {
                "module_type": "ScopeMissingModule",
                "category": "physical_module",
                "physical_claim_licensed": False,
                "behavior_contract": _behavior_contract("ScopeMissingModule"),
                "first_gap": None,
                "dimensions": dimensions,
            }
        ],
        "summary": {
            "registered_type_count": 1,
            "registry_inventory_reconciled": True,
        },
    }
    registry = {
        "live_registry_fingerprint": "d" * 64,
        "modules": [
            {
                "module_type": "ScopeMissingModule",
                "disposition": "resolved",
                "ports": [{"name": "x", "direction": "input"}],
                "first_gap": None,
            }
        ],
    }

    index = build_module_behavior_contract_index(review, registry)

    role_layer = next(
        item for item in index.coverage_layers if item.layer_id == "scenario_role"
    )
    assert role_layer.covered_count == 0
    assert role_layer.total_count == 1
    assert role_layer.first_gap_code == "runtime_port_direction_scope_missing"
    assert index.contracts[0].scenario_role_status == "unresolved"
    assert index.first_gap_code == "runtime_port_direction_scope_missing"


def test_unknown_id_and_oversized_deep_projection_fail_without_full_bundle_fallback(
    complete_physical_blueprint,
) -> None:
    blueprint, base_dir = complete_physical_blueprint()
    review = complete_physical_blueprint.review(blueprint, base_dir=base_dir)
    ordinary = build_physical_blueprint_export_bundle(
        blueprint,
        review,
        complete_physical_blueprint.target_inventory_authority,
    )
    oversized = build_physical_blueprint_export_bundle(
        blueprint,
        review,
        complete_physical_blueprint.target_inventory_authority,
        module_behavior_contract_index=_module_index(large=True),
    )

    missing = query_physical_blueprint_export_bundle(
        ordinary,
        selector_kind="element",
        selector_id="does-not-exist",
    )
    blocked = query_physical_blueprint_export_bundle(
        oversized,
        selector_kind="module",
        selector_id="ResolvedModule",
    )

    assert missing.gaps[0].code == "portable_query_not_in_bundle"
    assert missing.payload == {}
    assert blocked.gaps[0].code == "portable_projection_budget_exceeded"
    assert "behavior_contract" not in blocked.payload
    assert blocked.projection_canonical_bytes <= DEEP_PROJECTION_BYTE_LIMIT


def test_retired_disk_loader_does_not_read_an_existing_file(
    complete_physical_blueprint,
    tmp_path: Path,
) -> None:
    _, _, bundle = _reviewed_bundle(complete_physical_blueprint)
    existing = tmp_path / "physical-dna.json"
    existing.write_bytes(canonical_portable_bytes(bundle))

    with pytest.raises(PhysicalBlueprintBundleError) as error:
        load_physical_blueprint_export_bundle(existing)
    assert error.value.category == "native_directory_only"
    assert existing.is_file()


def test_cli_disk_routes_report_native_directory_only_without_writing(
    complete_physical_blueprint,
    tmp_path: Path,
    capsys,
) -> None:
    blueprint, base_dir = complete_physical_blueprint()
    blueprint_path = base_dir / "blueprint.json"
    blueprint_path.write_text(
        json.dumps(blueprint.model_dump(mode="json", exclude_none=False), sort_keys=True),
        encoding="utf-8",
    )
    bundle_path = tmp_path / "handoff" / "bundle.json"

    assert main(
        [
            "blueprint",
            "bundle-export",
            str(blueprint_path),
            "--target-authority",
            str(complete_physical_blueprint.target_inventory_authority_path),
            "--output",
            str(bundle_path),
        ]
    ) == 3
    compact = json.loads(capsys.readouterr().out)
    assert compact["code"] == "native_directory_only"
    assert compact["status"] == "blocked"
    assert not bundle_path.exists()

    assert main(
        [
            "blueprint",
            "bundle-query",
            str(bundle_path),
            "--element",
            "pipe",
        ]
    ) == 3
    detail = json.loads(capsys.readouterr().out)
    assert detail["code"] == "native_directory_only"
    assert detail["status"] == "blocked"
