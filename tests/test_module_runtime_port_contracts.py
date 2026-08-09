from __future__ import annotations

import hashlib
import importlib.util
from functools import lru_cache
from pathlib import Path
from types import ModuleType

import yaml

from physicsguard.core.physical_blueprint_bundle import (
    build_module_behavior_contract_index,
)


ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / ".physicsguard" / "module_equation_ledger.yaml"
REGISTRY = ROOT / ".physicsguard" / "module_runtime_port_contracts.yaml"


@lru_cache(maxsize=1)
def _load(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _generator() -> ModuleType:
    return _load(
        ROOT / "scripts" / "build_module_runtime_port_contracts.py",
        "module_runtime_port_contract_generator",
    )


def _checker() -> ModuleType:
    return _load(
        ROOT / "scripts" / "check_module_equation_ledger.py",
        "module_runtime_port_contract_checker",
    )


def _ledger_records() -> dict[str, dict]:
    payload = yaml.load(LEDGER.read_text(encoding="utf-8"), Loader=yaml.CSafeLoader)
    return {item["module_type"]: item for item in payload["module_records"]}


def test_generated_runtime_port_inventory_exactly_covers_live_registry() -> None:
    generator = _generator()

    payload = generator.build_registry_payload(ROOT, LEDGER)
    committed = yaml.load(
        REGISTRY.read_text(encoding="utf-8"), Loader=yaml.CSafeLoader
    )

    assert payload == committed
    assert payload["schema"] == generator.SCHEMA
    assert len(payload["modules"]) == 152
    assert len({item["module_type"] for item in payload["modules"]}) == 152
    assert sum(item["disposition"] == "resolved" for item in payload["modules"]) == 78
    assert sum(item["disposition"] == "unresolved" for item in payload["modules"]) == 74
    assert sum(len(item["declared_ports"]) for item in payload["modules"]) == 483
    assert payload["registry_fingerprint"] == generator._canonical_hash(
        {
            key: value
            for key, value in payload.items()
            if key != "registry_fingerprint"
        }
    )


def test_unresolved_runtime_roles_preserve_live_ports_and_exact_first_gap() -> None:
    generator = _generator()
    payload = generator.build_registry_payload(ROOT, LEDGER)
    actuator = next(
        item
        for item in payload["modules"]
        if item["module_type"] == "ActuatorDeadZoneModule"
    )

    assert actuator["disposition"] == "unresolved"
    assert {item["name"] for item in actuator["declared_ports"]} == {
        "command",
        "output",
    }
    assert actuator["first_gap"] == {
        "code": "runtime_port_direction_unavailable",
        "message": (
            "2 live declared port(s) have no independent input/output/state "
            "direction authority"
        ),
    }
    assert "ports" not in actuator


def test_resolved_runtime_roles_match_live_declarations_and_ledger_binding() -> None:
    checker = _checker()
    record = _ledger_records()["BrakeSimpleModule"]

    runtime = checker._compute_runtime_contract(ROOT, record, "BrakeSimpleModule")

    assert runtime["error"] is None
    assert runtime["port_contract_error"] is None
    assert {
        item["name"]: item["direction"]
        for item in runtime["declared_variables"]
    } == {
        "brake_force_N": "input",
        "vehicle_speed_m_s": "input",
        "brake_power_W": "output",
    }
    assert runtime["port_contract_fingerprint"] == record["function_block"][
        "role_authority"
    ]["contract_fingerprint"]
    assert runtime["direction_scope"] == "intrinsic_module_contract"
    assert runtime["relation_directionality"] == "directed"


def test_gold_roles_are_derived_from_current_intrinsic_formula_authorities() -> None:
    generator = _generator()
    payload = generator.build_registry_payload(ROOT, LEDGER)
    entries = {item["module_type"]: item for item in payload["modules"]}

    assert len(generator.INTRINSIC_ROLE_AUTHORITY_RESOURCES) == 4
    for module_type, relative_path in sorted(
        generator.INTRINSIC_ROLE_AUTHORITY_RESOURCES.items()
    ):
        entry = entries[module_type]
        formula_path = ROOT / relative_path
        formula = yaml.load(
            formula_path.read_text(encoding="utf-8"), Loader=yaml.CSafeLoader
        )
        evidence = entry["authority_evidence"]

        assert entry["disposition"] == "resolved"
        assert entry["role_authority_basis"] == (
            "intrinsic_project_formula_contract"
        )
        assert entry["direction_scope"] == "intrinsic_module_contract"
        assert entry["relation_directionality"] == "directed"
        assert evidence["kind"] == "project_formula_direction_contract"
        assert evidence["path"] == relative_path
        assert evidence["sha256"] == generator._file_sha256(formula_path)
        assert evidence["owner"] == formula["owner"]
        assert evidence["input_names"] == [
            item["name"] for item in formula["inputs"]
        ]
        assert evidence["output_names"] == [
            item["name"] for item in formula["outputs"]
        ]
        assert entry["direction_claim_boundary"] == formula["claim_boundary"]
        assert {item["name"]: item["direction"] for item in entry["ports"]} == {
            **{item["name"]: "input" for item in formula["inputs"]},
            **{item["name"]: "output" for item in formula["outputs"]},
        }


def test_every_resolved_role_has_portable_direction_scope_evidence() -> None:
    generator = _generator()
    payload = generator.build_registry_payload(ROOT, LEDGER)
    resolved = [
        item for item in payload["modules"] if item["disposition"] == "resolved"
    ]

    assert len(resolved) == 78
    assert all(item.get("direction_scope") for item in resolved)
    assert all(item.get("relation_directionality") for item in resolved)
    assert all(isinstance(item.get("authority_evidence"), dict) for item in resolved)
    assert sum(
        item["direction_scope"] == "intrinsic_module_contract"
        and item["relation_directionality"] == "directed"
        for item in resolved
    ) == 4
    assert sum(
        item["direction_scope"] == "exact_instantiation_scenario"
        and item["relation_directionality"] == "direction_neutral"
        for item in resolved
    ) == 15
    assert sum(
        item["direction_scope"] == "exact_instantiation_mechanical_draft"
        and item["relation_directionality"] == "direction_neutral"
        for item in resolved
    ) == 22
    assert sum(
        item["direction_scope"]
        == "exact_instantiation_source_first_reconstruction"
        and item["relation_directionality"] == "direction_neutral"
        for item in resolved
    ) == 37


def test_portable_index_counts_all_and_only_the_78_current_scoped_roles() -> None:
    generator = _generator()
    registry = generator.build_registry_payload(ROOT, LEDGER)
    record_results = []
    for entry in registry["modules"]:
        module_type = entry["module_type"]
        contract_fingerprint = hashlib.sha256(module_type.encode("utf-8")).hexdigest()
        record_results.append(
            {
                "module_type": module_type,
                "category": "physical_module",
                "physical_claim_licensed": False,
                "behavior_contract": {
                    "contract_fingerprint": contract_fingerprint,
                },
                "dimensions": {},
                "first_gap": {"code": "module_domain_semantics_incomplete"},
            }
        )
    review = {
        "checker_identity": "physicsguard.module_semantics_ledger.checker.v3",
        "record_results": record_results,
        "summary": {
            "registered_type_count": 152,
            "registry_inventory_reconciled": True,
        },
    }

    index = build_module_behavior_contract_index(review, registry)
    role_layer = next(
        item for item in index.coverage_layers if item.layer_id == "scenario_role"
    )
    resolved = [
        item for item in index.contracts if item.scenario_role_status == "resolved"
    ]

    assert role_layer.covered_count == 78
    assert role_layer.total_count == 152
    assert len(resolved) == 78
    assert sum(item.direction_scope == "intrinsic_module_contract" for item in resolved) == 4
    assert sum(item.direction_scope == "exact_instantiation_scenario" for item in resolved) == 15
    assert sum(
        item.direction_scope == "exact_instantiation_mechanical_draft"
        for item in resolved
    ) == 22
    assert sum(
        item.direction_scope == "exact_instantiation_source_first_reconstruction"
        for item in resolved
    ) == 37
    assert role_layer.first_gap_code != "runtime_port_direction_scope_missing"


def test_boundary_derived_roles_are_bound_to_current_example_inputs() -> None:
    generator = _generator()
    payload = generator.build_registry_payload(ROOT, LEDGER)
    pressure_ratio = next(
        item
        for item in payload["modules"]
        if item["module_type"] == "PressureRatioModule"
    )

    assert pressure_ratio["disposition"] == "resolved"
    assert pressure_ratio["role_authority_basis"] == (
        "canonical_reviewed_scenario_role"
    )
    evidence = pressure_ratio["authority_evidence"]
    assert evidence["kind"] == "current_example_boundary_contract"
    assert evidence["path"] == "examples/additional/pressure_ratio.yaml"
    assert evidence["sha256"] == generator._file_sha256(
        ROOT / "examples" / "additional" / "pressure_ratio.yaml"
    )
    assert evidence["component_id"] == "pr"
    assert evidence["boundary_variables"] == ["p_in_Pa", "p_out_Pa"]
    assert evidence["instantiation_fingerprint"] == pressure_ratio[
        "instantiation_fingerprint"
    ]
    assert evidence["subject_revision"]
    assert evidence["known_bad"]["code"] == (
        "alternate_boundary_direction_not_reusable"
    )
    assert pressure_ratio["direction_scope"] == "exact_instantiation_scenario"
    assert pressure_ratio["relation_directionality"] == "direction_neutral"
    assert pressure_ratio["direction_claim_boundary"] == evidence["claim_boundary"]
    assert pressure_ratio["ports"] == [
        {"name": "p_in_Pa", "direction": "input"},
        {"name": "p_out_Pa", "direction": "input"},
        {"name": "pressure_ratio", "direction": "output"},
    ]


def test_first_boundary_batch_matches_ledger_roles_and_outputs_exactly() -> None:
    checker = _checker()
    generator = _generator()
    records = _ledger_records()

    assert len(generator.BOUNDARY_DERIVED_ROLE_MODULES) == 15
    for module_type in sorted(generator.BOUNDARY_DERIVED_ROLE_MODULES):
        record = records[module_type]
        runtime = checker._compute_runtime_contract(ROOT, record, module_type)
        assert runtime["error"] is None
        assert runtime["port_contract_error"] is None
        runtime_roles = {
            item["name"]: item["direction"]
            for item in runtime["declared_variables"]
        }
        ledger_roles = {
            item["name"]: item["role"]
            for item in record["function_block"]["declared_variables"]
        }
        assert runtime_roles == ledger_roles
        assert set(record["function_block"]["outputs"]["declared_variables"]) == {
            name for name, direction in runtime_roles.items() if direction == "output"
        }
        assert record["function_block"]["role_authority"] == {
            "kind": "runtime_port_contract",
            "producer_identity": generator.PRODUCER_IDENTITY,
            "contract_fingerprint": runtime["port_contract_fingerprint"],
            "direction_scope": runtime["direction_scope"],
            "relation_directionality": runtime["relation_directionality"],
            "claim_boundary": runtime["direction_claim_boundary"],
            "authority_evidence_fingerprint": runtime[
                "authority_evidence_fingerprint"
            ],
        }


def test_mechanical_draft_roles_bind_all_22_without_licensing_physical_meaning() -> None:
    checker = _checker()
    generator = _generator()
    records = _ledger_records()
    payload = generator.build_registry_payload(ROOT, LEDGER)
    entries = {item["module_type"]: item for item in payload["modules"]}
    external_only = {
        "AggregateEfficiencyModule",
        "ConservationSumModule",
        "MapBoundsCheckModule",
        "MassBalanceRateModule",
        "ProductModule",
        "RangeCheckModule",
        "RatioModule",
        "SumModule",
    }

    assert len(generator.MECHANICAL_DRAFT_ROLE_AUTHORITY_RESOURCES) == 22
    for module_type, relative_path in sorted(
        generator.MECHANICAL_DRAFT_ROLE_AUTHORITY_RESOURCES.items()
    ):
        formula = yaml.load(
            (ROOT / relative_path).read_text(encoding="utf-8"),
            Loader=yaml.CSafeLoader,
        )
        entry = entries[module_type]
        evidence = entry["authority_evidence"]
        record = records[module_type]
        runtime = checker._compute_runtime_contract(ROOT, record, module_type)

        assert formula["authoring_status"] == (
            "mechanical_draft_pending_independent_review"
        )
        assert formula["separate_review_status"] == "pending"
        assert formula["physical_claim_licensed"] is False
        assert entry["disposition"] == "resolved"
        assert entry["role_authority_basis"] == "mechanical_draft_formula_role"
        assert entry["direction_scope"] == "exact_instantiation_mechanical_draft"
        assert entry["relation_directionality"] == "direction_neutral"
        assert evidence["kind"] == "mechanical_draft_formula_role_contract"
        assert evidence["authoring_status"] == (
            "mechanical_draft_pending_independent_review"
        )
        assert evidence["separate_review_status"] == "pending"
        assert evidence["physical_claim_licensed"] is False
        assert evidence["known_bad"]["code"] == (
            "mechanical_draft_not_independently_reviewed"
        )
        assert record["semantic_review"]["status"] == "pending"
        assert record["semantic_review"]["license"] == "unlicensed"
        assert record["bindings"]["oracle"]["independent_from_implementation"] is False
        assert runtime["error"] is None
        assert runtime["port_contract_error"] is None
        if module_type in external_only:
            assert entry["declared_ports"] == []
            assert entry["external_ports"]
            assert record["function_block"]["external_inputs"]
        else:
            assert entry["declared_ports"]
            assert entry["external_ports"] == []
            assert record["function_block"]["external_inputs"] == []


def test_alternate_legal_boundaries_require_a_new_scenario_role_contract(
    tmp_path: Path,
) -> None:
    generator = _generator()
    declared_ports = [
        {"name": "p_in_Pa"},
        {"name": "p_out_Pa"},
        {"name": "pressure_ratio"},
    ]
    subjects = []
    directions = []
    for index, boundary_variables in enumerate(
        (["p_in_Pa", "p_out_Pa"], ["p_in_Pa", "pressure_ratio"])
    ):
        relative_path = f"scenario_{index}.yaml"
        (tmp_path / relative_path).write_text(
            yaml.safe_dump(
                {
                    "components": [
                        {"id": "pr", "type": "PressureRatioModule", "parameters": {}}
                    ],
                    "boundaries": [
                        {"variable": f"pr.{name}", "value": 1.0}
                        for name in boundary_variables
                    ],
                },
                sort_keys=False,
            ),
            encoding="utf-8",
        )
        ports, evidence = generator._boundary_authority_evidence(
            tmp_path,
            "PressureRatioModule",
            "pr",
            {"kind": "yaml_component", "path": relative_path},
            "same-instantiation-fingerprint",
            declared_ports,
        )
        directions.append({item["name"]: item["direction"] for item in ports})
        subjects.append(evidence["subject_revision"])
        assert evidence["known_bad"]["code"] == (
            "alternate_boundary_direction_not_reusable"
        )

    assert directions[0] != directions[1]
    assert subjects[0] != subjects[1]


def test_unresolved_runtime_role_cannot_be_promoted_by_ledger_labels() -> None:
    checker = _checker()
    record = _ledger_records()["ActuatorDeadZoneModule"]

    runtime = checker._compute_runtime_contract(
        ROOT, record, "ActuatorDeadZoneModule"
    )

    assert runtime["port_contract_fingerprint"] is None
    assert runtime["port_contract_error"] == (
        "runtime_port_direction_unavailable: 2 live declared port(s) have no "
        "independent input/output/state direction authority"
    )
    assert all(item["direction"] is None for item in runtime["declared_variables"])
