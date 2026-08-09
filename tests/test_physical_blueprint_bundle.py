from __future__ import annotations

import json
import os
import site
import subprocess
import sys
from pathlib import Path

from physicsguard.cli import main
from physicsguard.core.physical_blueprint_bundle import (
    COMPACT_PROJECTION_BYTE_LIMIT,
    DEEP_PROJECTION_BYTE_LIMIT,
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


def test_bundle_materialization_is_byte_identical_and_path_independent(
    complete_physical_blueprint,
    tmp_path: Path,
) -> None:
    _, review, bundle = _reviewed_bundle(complete_physical_blueprint)
    first = tmp_path / "one" / "bundle.json"
    second = tmp_path / "two" / "bundle.json"

    first_size = materialize_physical_blueprint_export_bundle(bundle, first)
    second_size = materialize_physical_blueprint_export_bundle(bundle, second)
    loaded = load_physical_blueprint_export_bundle(first)

    assert first.read_bytes() == second.read_bytes() == canonical_portable_bytes(bundle)
    assert first_size == second_size == len(first.read_bytes())
    assert loaded.bundle_fingerprint == bundle.bundle_fingerprint
    assert loaded.review.status == review.status
    assert str(first) not in first.read_text(encoding="utf-8")
    assert str(second) not in first.read_text(encoding="utf-8")


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


def test_separate_installed_consumer_uses_only_bundle_from_isolated_working_directory(
    complete_physical_blueprint,
    tmp_path: Path,
) -> None:
    _, _, bundle = _reviewed_bundle(complete_physical_blueprint)
    isolated = tmp_path / "isolated-consumer"
    isolated.mkdir()
    installed_package = isolated / "installed-package"
    package_root = Path(__file__).resolve().parents[1]
    dependency_site = Path(site.getusersitepackages()).resolve()
    bundle_path = isolated / "physical-dna.json"
    materialize_physical_blueprint_export_bundle(bundle, bundle_path)
    install_environment = os.environ.copy()
    install_environment["PYTHONDONTWRITEBYTECODE"] = "1"
    installed = subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
            "--no-build-isolation",
            "--no-cache-dir",
            "--no-compile",
            "--no-deps",
            "--target",
            str(installed_package),
            str(package_root),
        ],
        cwd=tmp_path,
        env=install_environment,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
        check=False,
    )
    assert installed.returncode == 0, installed.stderr
    code = (
        "import json, pathlib, sys; "
        f"installed_site=pathlib.Path({str(installed_package)!r}).resolve(); "
        f"dependency_site=pathlib.Path({str(dependency_site)!r}).resolve(); "
        f"source_root=pathlib.Path({str(package_root)!r}).resolve(); "
        "sys.path[:0]=[str(installed_site),str(dependency_site)]; "
        "from physicsguard.core.physical_blueprint_bundle import "
        "load_physical_blueprint_export_bundle, query_physical_blueprint_export_bundle; "
        "cwd=pathlib.Path.cwd(); "
        "import physicsguard; "
        "assert sorted(p.name for p in cwd.iterdir())==['installed-package','physical-dna.json']; "
        "assert pathlib.Path(physicsguard.__file__).resolve().is_relative_to(installed_site); "
        "assert all(pathlib.Path(p or '.').resolve()!=source_root for p in sys.path); "
        "b=load_physical_blueprint_export_bundle(cwd/'physical-dna.json'); "
        "element=query_physical_blueprint_export_bundle(b, selector_kind='element', selector_id='pipe'); "
        "impact=query_physical_blueprint_export_bundle(b, selector_kind='impact', selector_id='port.pipe.flow'); "
        "reverse=query_physical_blueprint_export_bundle(b, selector_kind='reverse', selector_id='port.loop.flow'); "
        "missing=query_physical_blueprint_export_bundle(b, selector_kind='element', selector_id='outside.bundle'); "
        "assert element.payload['parent_id']=='pump_loop'; "
        "assert {p['port_id'] for p in element.payload['ports']}=={'port.pipe.inlet_pressure','port.pipe.flow','port.pipe.mass','port.pipe.heat_loss'}; "
        "assert 'port.pipe.mass' in element.payload['behavior_contract']['pre_state_port_ids']; "
        "assert 'element:pipe' in impact.payload['included_member_ids']; "
        "assert 'element:pump_loop' in reverse.payload['included_member_ids']; "
        "assert missing.gaps[0].code=='portable_query_not_in_bundle'; "
        "assert all(q.source_review_status==b.review.status for q in (element,impact,reverse,missing)); "
        "print(json.dumps({'element':element.payload['element']['element_id'],"
        "'bundle':element.bundle_fingerprint,'bytes':element.projection_canonical_bytes,"
        "'impact':impact.query_id,'reverse':reverse.query_id,'missing':missing.first_gap_code,"
        "'package':str(pathlib.Path(physicsguard.__file__).resolve())},sort_keys=True))"
    )
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    completed = subprocess.run(
        [sys.executable, "-I", "-c", code],
        cwd=isolated,
        env=environment,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    result = json.loads(completed.stdout)
    assert result["element"] == "pipe"
    assert result["impact"] == "port.pipe.flow"
    assert result["reverse"] == "port.loop.flow"
    assert result["missing"] == "portable_query_not_in_bundle"
    assert Path(result["package"]).is_relative_to(installed_package)
    assert sorted(path.name for path in isolated.iterdir()) == [
        "installed-package",
        "physical-dna.json",
    ]


def test_cli_export_prints_only_compact_status_and_query_requires_one_id(
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
    assert compact["query_kind"] == "status"
    assert "blueprint" not in compact["payload"]
    assert bundle_path.is_file()

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
    assert detail["query_kind"] == "element"
    assert detail["query_id"] == "pipe"
    assert detail["payload"]["element"]["element_id"] == "pipe"
