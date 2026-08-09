from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LEDGER = ROOT / ".physicsguard" / "module_equation_ledger.yaml"
DEFAULT_OUTPUT = ROOT / ".physicsguard" / "module_runtime_port_contracts.yaml"
SCHEMA = "physicsguard.module_runtime_port_contract_registry.v2"
PRODUCER_IDENTITY = "physicsguard.module_runtime_port_contract.v1"

# These four source-independent project formulas explicitly own intrinsic
# input/output direction for their bounded low-fidelity relations.  Port names
# and directions are parsed from the current formula resource, never copied
# from the semantic ledger or repeated here.
INTRINSIC_ROLE_AUTHORITY_RESOURCES: dict[str, str] = {
    "BrakeSimpleModule": ".physicsguard/module_formulas/BrakeSimpleModule.yaml",
    "ChargerSimpleModule": ".physicsguard/module_formulas/ChargerSimpleModule.yaml",
    "DCDCConverterSimpleModule": ".physicsguard/module_formulas/DCDCConverterSimpleModule.yaml",
    "InverterSimpleModule": ".physicsguard/module_formulas/InverterSimpleModule.yaml",
}

# This set says only that a stateless algebraic module has been reviewed as
# eligible for mechanical scenario-role derivation.  It does not contain ports.
# The generator derives fixed inputs and solved outputs from one exact current
# example, fingerprints that scenario, and keeps the underlying relation
# direction-neutral.  Another legal boundary set must produce another scenario
# contract; these roles cannot be promoted to an intrinsic module direction.
BOUNDARY_DERIVED_ROLE_MODULES = frozenset(
    {
        "AirOxygenMolarFlowModule",
        "CellVoltageStackVoltageModule",
        "ChemicalPowerLHVModule",
        "CurrentDensityModule",
        "DensityMassVolumeModule",
        "EfficiencyModule",
        "ForceVelocityPowerModule",
        "IdealGasDensityModule",
        "LinearRelationModule",
        "LinearSpringForceModule",
        "MassMolarFlowConversionModule",
        "MoleFractionFlowModule",
        "PressureRatioModule",
        "SpecificEnthalpyFlowModule",
        "StackChemicalEfficiencyModule",
    }
)

# Category-A members whose current semantics can be mechanically projected
# from maintained source, one exact example, and bound tests.  These resources
# are deliberately *draft* role contracts: they make current data flow
# explicit, but they never license physical meaning or substitute for the
# separate reviewer recorded by the module-semantics ledger.
MECHANICAL_DRAFT_ROLE_AUTHORITY_RESOURCES: dict[str, str] = {
    module_type: f".physicsguard/module_formulas/{module_type}.yaml"
    for module_type in {
        "AggregateEfficiencyModule",
        "BooleanSwitchModule",
        "ConservationSumModule",
        "DiscreteIntegratorModule",
        "FirstOrderLagModule",
        "GainBiasModule",
        "HysteresisStateCheckModule",
        "MapBoundsCheckModule",
        "MassBalanceRateModule",
        "ProductModule",
        "RangeCheckModule",
        "RatioModule",
        "RotationalInertiaTorqueModule",
        "SumModule",
        "TankLevelVolumeModule",
        "TankVolumeRateModule",
        "ThresholdStateCheckModule",
        "TorqueSpeedPowerModule",
        "TranslationalInertiaForceModule",
        "ViscousDamperForceModule",
        "VolumetricMassFlowConversionModule",
        "WaterProductionFaradayModule",
    }
}

# Historical grouped coverage is not current semantic authority.  The two
# intrinsic formula members remain owned above; these other 37 members use an
# exact-instantiation, source-first reconstruction that is deliberately
# unlicensed until an independent semantic reviewer accepts it.
SOURCE_FIRST_ROLE_AUTHORITY_RESOURCES: dict[str, str] = {
    module_type: f".physicsguard/module_formulas/{module_type}.yaml"
    for module_type in {
        "AggregateElectricalBusBalanceModule",
        "AggregateMassBalanceModule",
        "AggregatePowerBalanceModule",
        "AggregateThermalBalanceModule",
        "ControlErrorModule",
        "ConvectiveHeatTransferModule",
        "CoolantHeatBalanceModule",
        "EfficiencyMap2DModule",
        "ElectricalPowerModule",
        "ElectrochemicalFaradayRateModule",
        "ElectrochemicalStackPowerModule",
        "ElectrolyzerGasProductionModule",
        "ElectrolyzerStackBalanceModule",
        "FuelCellCathodeAirSupplyModule",
        "FuelCellStackBalanceModule",
        "HVBusPowerBalanceModule",
        "IncompressibleOrificeModule",
        "IncompressiblePressureDropModule",
        "LookupTable1DModule",
        "LookupTable2DModule",
        "MapAxisBoundsCheckModule",
        "MapMonotonicityCheckModule",
        "MappedSignalModule",
        "OhmicRelationModule",
        "PIDAlgebraicModule",
        "PIDControllerStepModule",
        "PipeSegmentSimpleModule",
        "PumpHydraulicPowerModule",
        "PumpSimpleModule",
        "RadiativeHeatTransferModule",
        "RateLimiterModule",
        "SaturationModule",
        "SensorScaleOffsetModule",
        "ThermalCapacitanceRateModule",
        "ThermalConductorModule",
        "UnitConversionAuditModule",
        "UnitScaleModule",
    }
}


def _canonical_hash(value: Any) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def resolved_role_authority_binding(entry: dict[str, Any]) -> dict[str, Any]:
    """Project the exact ledger binding for one resolved runtime-port entry.

    This projection deliberately carries only observed declarations plus an
    explicit role authority.  It does not infer equations, units, validity
    regions, test expectations, or physical meaning.
    """

    if entry.get("disposition") != "resolved" or entry.get("first_gap") is not None:
        raise ValueError("a role-authority binding requires one resolved port entry")
    ports = entry.get("ports")
    authority_evidence = entry.get("authority_evidence")
    configuration_only = (
        entry.get("role_authority_basis") == "source_first_formula_role"
        and isinstance(authority_evidence, dict)
        and authority_evidence.get("kind") == "source_first_formula_role_contract"
        and authority_evidence.get("port_contract") == "configuration_only"
        and entry.get("declared_ports") == []
        and entry.get("external_ports") == []
    )
    if not isinstance(ports, list) or (not ports and not configuration_only):
        raise ValueError("a resolved port entry must contain explicit ports")
    subject: dict[str, Any] = {
        "schema": SCHEMA,
        "producer_identity": PRODUCER_IDENTITY,
        "module_type": entry.get("module_type"),
        "instantiation_fingerprint": entry.get("instantiation_fingerprint"),
        "declared_ports_fingerprint": entry.get("declared_ports_fingerprint"),
        "role_authority_basis": entry.get("role_authority_basis"),
        "ports": sorted(
            (
                {"name": item.get("name"), "direction": item.get("direction")}
                for item in ports
            ),
            key=lambda item: str(item["name"]),
        ),
    }
    if entry.get("role_authority_basis") in {
        "mechanical_draft_formula_role",
        "source_first_formula_role",
    }:
        subject["external_ports_fingerprint"] = entry.get("external_ports_fingerprint")
        subject["external_ports"] = entry.get("external_ports", [])
    if authority_evidence is not None:
        if not isinstance(authority_evidence, dict):
            raise ValueError("runtime-port authority evidence must be a mapping")
        subject.update(
            {
                "authority_evidence": authority_evidence,
                "direction_scope": entry.get("direction_scope"),
                "relation_directionality": entry.get("relation_directionality"),
                "direction_claim_boundary": entry.get("direction_claim_boundary"),
            }
        )
    binding = {
        "kind": "runtime_port_contract",
        "producer_identity": PRODUCER_IDENTITY,
        "contract_fingerprint": _canonical_hash(subject),
    }
    if authority_evidence is not None:
        binding.update(
            {
                "direction_scope": entry.get("direction_scope"),
                "relation_directionality": entry.get("relation_directionality"),
                "claim_boundary": entry.get("direction_claim_boundary"),
                "authority_evidence_fingerprint": _canonical_hash(authority_evidence),
            }
        )
    return binding


def _formula_port_role(item: dict[str, Any], default: str, module_type: str) -> str:
    role = item.get("role", default)
    if role not in {"input", "output", "state_previous", "state_current", "state_next"}:
        raise ValueError(f"mechanical draft for {module_type} has invalid port role {role!r}")
    return str(role)


def _resolve_external_reference(
    instance: Any,
    item: dict[str, Any],
    module_type: str,
) -> tuple[str, str, int | None]:
    attribute = item.get("source_attribute")
    if not isinstance(attribute, str) or not attribute.strip() or not hasattr(instance, attribute):
        raise ValueError(
            f"mechanical draft for {module_type} has no current external source attribute"
        )
    value = getattr(instance, attribute)
    source_index = item.get("source_index")
    if source_index is not None:
        if (
            not isinstance(source_index, int)
            or isinstance(source_index, bool)
            or not isinstance(value, list)
            or source_index < 0
            or source_index >= len(value)
        ):
            raise ValueError(
                f"mechanical draft for {module_type} has stale external source index"
            )
        value = value[source_index]
    if not isinstance(value, str) or "." not in value:
        raise ValueError(
            f"mechanical draft for {module_type} external source is not a qualified variable"
        )
    expected = item.get("source_reference")
    if expected != value:
        raise ValueError(
            f"mechanical draft for {module_type} external source reference is stale: "
            f"expected={expected!r}, actual={value!r}"
        )
    return str(value), attribute, source_index


def _unlicensed_formula_role_authority_evidence(
    root: Path,
    module_type: str,
    relative_path: str,
    instance: Any,
    declared_ports: list[dict[str, Any]],
    *,
    expected_authoring_status: str,
    expected_direction_scope: str,
    evidence_kind: str,
    known_bad_code: str,
) -> tuple[list[dict[str, str]], list[dict[str, Any]], dict[str, Any]]:
    path = (root / relative_path).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError as exc:
        raise ValueError(
            f"mechanical role draft for {module_type} escapes the repository"
        ) from exc
    if not path.is_file():
        raise ValueError(
            f"mechanical role draft for {module_type} is missing: {relative_path}"
        )
    payload = yaml.load(path.read_text(encoding="utf-8"), Loader=yaml.CSafeLoader)
    if (
        not isinstance(payload, dict)
        or payload.get("schema") != "physicsguard.project_formula.v1"
        or payload.get("module_type") != module_type
        or payload.get("authoring_status") != expected_authoring_status
        or payload.get("separate_review_status") != "pending"
        or payload.get("physical_claim_licensed") is not False
        or payload.get("direction_scope") != expected_direction_scope
        or payload.get("relation_directionality") != "direction_neutral"
        or not isinstance(payload.get("owner"), str)
        or not payload["owner"].strip()
        or not isinstance(payload.get("claim_boundary"), str)
        or not payload["claim_boundary"].strip()
    ):
        raise ValueError(
            f"mechanical role draft for {module_type} is not an explicit current unlicensed draft"
        )

    declared_by_name = {str(item["name"]): item for item in declared_ports}
    local_names: set[str] = set()
    external_ports: list[dict[str, Any]] = []
    ports: list[dict[str, str]] = []
    for field, default_role in (
        ("scenario_inputs", "input"),
        ("scenario_outputs", "output"),
    ):
        items = payload.get(field)
        if not isinstance(items, list) or not all(isinstance(item, dict) for item in items):
            raise ValueError(f"mechanical role draft for {module_type} has malformed {field}")
        for item in items:
            name = item.get("name")
            unit = item.get("unit")
            if (
                not isinstance(name, str)
                or not name.strip()
                or not isinstance(unit, str)
                or not unit.strip()
                or any(port["name"] == name for port in ports)
            ):
                raise ValueError(
                    f"mechanical role draft for {module_type} has malformed or duplicate ports"
                )
            role = _formula_port_role(item, default_role, module_type)
            source_kind = item.get("source_kind", "local")
            if source_kind == "local":
                declared = declared_by_name.get(name)
                if declared is None or str(declared.get("unit")) != unit:
                    raise ValueError(
                        f"mechanical role draft for {module_type} has stale local port {name}"
                    )
                local_names.add(name)
            elif source_kind == "external":
                if role != "input":
                    raise ValueError(
                        f"mechanical role draft for {module_type} may only observe external ports"
                    )
                reference, attribute, source_index = _resolve_external_reference(
                    instance, item, module_type
                )
                projected = {
                    "name": name,
                    "unit": unit,
                    "direction": role,
                    "source_attribute": attribute,
                    "source_reference": reference,
                }
                if source_index is not None:
                    projected["source_index"] = source_index
                external_ports.append(projected)
            else:
                raise ValueError(
                    f"mechanical role draft for {module_type} has unknown source kind"
                )
            ports.append({"name": name, "direction": role})

    if local_names != set(declared_by_name):
        raise ValueError(
            f"mechanical role draft for {module_type} does not exactly cover local declarations"
        )
    if not ports and payload.get("port_contract") != "configuration_only":
        raise ValueError(f"mechanical role draft for {module_type} has no modeled ports")

    external_ports = sorted(external_ports, key=lambda item: item["name"])
    resource_sha256 = _file_sha256(path)
    external_fingerprint = _canonical_hash(external_ports)
    authority_subject = {
        "module_type": module_type,
        "resource_sha256": resource_sha256,
        "owner": payload["owner"],
        "declared_ports_fingerprint": _canonical_hash(declared_ports),
        "external_ports_fingerprint": external_fingerprint,
        "ports": sorted(ports, key=lambda item: item["name"]),
        "claim_boundary": payload["claim_boundary"],
        "authoring_status": payload["authoring_status"],
    }
    port_contract = payload.get("port_contract")
    if port_contract is not None:
        authority_subject["port_contract"] = port_contract
    authority_evidence = {
        "kind": evidence_kind,
        "path": relative_path.replace("\\", "/"),
        "sha256": resource_sha256,
        "schema": payload["schema"],
        "owner": payload["owner"],
        "selector": f"module_type: {module_type}",
        "subject_revision": _canonical_hash(authority_subject),
        "authoring_status": payload["authoring_status"],
        "separate_review_status": payload["separate_review_status"],
        "physical_claim_licensed": False,
        "derivation": (
            "project current port roles from maintained source, one exact instantiation, "
            "and this explicitly unlicensed mechanical formula draft"
        ),
        "claim_boundary": payload["claim_boundary"],
        "known_bad": {
            "code": known_bad_code,
            "message": (
                "the projected role contract describes current implementation flow only; "
                "it cannot license physical meaning or satisfy independent review"
            ),
        },
    }
    if port_contract is not None:
        authority_evidence["port_contract"] = port_contract
    return sorted(ports, key=lambda item: item["name"]), external_ports, authority_evidence


def _mechanical_draft_role_authority_evidence(
    root: Path,
    module_type: str,
    relative_path: str,
    instance: Any,
    declared_ports: list[dict[str, Any]],
) -> tuple[list[dict[str, str]], list[dict[str, Any]], dict[str, Any]]:
    return _unlicensed_formula_role_authority_evidence(
        root,
        module_type,
        relative_path,
        instance,
        declared_ports,
        expected_authoring_status="mechanical_draft_pending_independent_review",
        expected_direction_scope="exact_instantiation_mechanical_draft",
        evidence_kind="mechanical_draft_formula_role_contract",
        known_bad_code="mechanical_draft_not_independently_reviewed",
    )


def _source_first_role_authority_evidence(
    root: Path,
    module_type: str,
    relative_path: str,
    instance: Any,
    declared_ports: list[dict[str, Any]],
) -> tuple[list[dict[str, str]], list[dict[str, Any]], dict[str, Any]]:
    return _unlicensed_formula_role_authority_evidence(
        root,
        module_type,
        relative_path,
        instance,
        declared_ports,
        expected_authoring_status=(
            "source_first_reconstruction_pending_independent_review"
        ),
        expected_direction_scope=(
            "exact_instantiation_source_first_reconstruction"
        ),
        evidence_kind="source_first_formula_role_contract",
        known_bad_code="source_first_reconstruction_not_independently_reviewed",
    )


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _intrinsic_role_authority_evidence(
    root: Path,
    module_type: str,
    relative_path: str,
    declared_ports: list[dict[str, Any]],
) -> tuple[list[dict[str, str]], dict[str, Any]]:
    path = (root / relative_path).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError as exc:
        raise ValueError(
            f"intrinsic role authority for {module_type} escapes the repository"
        ) from exc
    if not path.is_file():
        raise ValueError(
            f"intrinsic role authority for {module_type} is missing: {relative_path}"
        )
    payload = yaml.load(path.read_text(encoding="utf-8"), Loader=yaml.CSafeLoader)
    if (
        not isinstance(payload, dict)
        or payload.get("schema") != "physicsguard.project_formula.v1"
        or payload.get("module_type") != module_type
        or not isinstance(payload.get("owner"), str)
        or not payload["owner"].strip()
        or not isinstance(payload.get("claim_boundary"), str)
        or not payload["claim_boundary"].strip()
    ):
        raise ValueError(
            f"intrinsic role authority for {module_type} is not a current project formula"
        )
    formula_ports: list[dict[str, str]] = []
    formula_units: dict[str, str] = {}
    input_names: list[str] = []
    output_names: list[str] = []
    for field, direction, names in (
        ("inputs", "input", input_names),
        ("outputs", "output", output_names),
    ):
        items = payload.get(field)
        if not isinstance(items, list) or not items:
            raise ValueError(
                f"intrinsic role authority for {module_type} has no {field}"
            )
        for item in items:
            if (
                not isinstance(item, dict)
                or not isinstance(item.get("name"), str)
                or not item["name"].strip()
                or item.get("direction") != direction
                or not isinstance(item.get("unit"), str)
                or not item["unit"].strip()
            ):
                raise ValueError(
                    f"intrinsic role authority for {module_type} has malformed {field}"
                )
            name = str(item["name"])
            if name in formula_units:
                raise ValueError(
                    f"intrinsic role authority for {module_type} duplicates {name}"
                )
            formula_units[name] = str(item["unit"])
            names.append(name)
            formula_ports.append({"name": name, "direction": direction})

    declared_by_name = {str(item["name"]): item for item in declared_ports}
    if set(declared_by_name) != set(formula_units):
        raise ValueError(
            f"intrinsic role authority for {module_type} does not exactly cover live ports"
        )
    unit_mismatches = sorted(
        name
        for name, item in declared_by_name.items()
        if str(item.get("unit")) != formula_units[name]
    )
    if unit_mismatches:
        raise ValueError(
            f"intrinsic role authority for {module_type} has stale units: {unit_mismatches}"
        )

    resource_sha256 = _file_sha256(path)
    authority_subject = {
        "module_type": module_type,
        "resource_sha256": resource_sha256,
        "owner": payload["owner"],
        "declared_ports_fingerprint": _canonical_hash(declared_ports),
        "inputs": input_names,
        "outputs": output_names,
        "claim_boundary": payload["claim_boundary"],
    }
    return sorted(formula_ports, key=lambda item: item["name"]), {
        "kind": "project_formula_direction_contract",
        "path": relative_path.replace("\\", "/"),
        "sha256": resource_sha256,
        "schema": payload["schema"],
        "owner": payload["owner"],
        "selector": f"module_type: {module_type}",
        "input_names": input_names,
        "output_names": output_names,
        "subject_revision": _canonical_hash(authority_subject),
        "derivation": (
            "read intrinsic input/output direction from the exact current "
            "source-independent low-fidelity project formula"
        ),
        "claim_boundary": payload["claim_boundary"],
        "known_bad": {
            "code": "intrinsic_formula_direction_reversal_unlicensed",
            "message": (
                "reversing or reclassifying an intrinsic formula port requires a new "
                "current formula authority and cannot reuse this direction contract"
            ),
        },
    }


def _boundary_authority_evidence(
    root: Path,
    module_type: str,
    component_id: str,
    instantiation: dict[str, Any],
    instantiation_fingerprint: str,
    declared_ports: list[dict[str, Any]],
) -> tuple[list[dict[str, str]], dict[str, Any]]:
    relative_path = instantiation.get("path")
    if instantiation.get("kind") not in {"yaml_component", "json_component"}:
        raise ValueError(
            f"boundary-derived role authority for {module_type} needs a structured example"
        )
    if not isinstance(relative_path, str) or not relative_path:
        raise ValueError(
            f"boundary-derived role authority for {module_type} has no example path"
        )
    path = (root / relative_path).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError as exc:
        raise ValueError(
            f"boundary-derived role authority for {module_type} escapes the repository"
        ) from exc
    if not path.is_file():
        raise ValueError(
            f"boundary-derived role authority for {module_type} example is missing"
        )
    if path.suffix.lower() == ".json":
        payload = json.loads(path.read_text(encoding="utf-8"))
    else:
        payload = yaml.load(path.read_text(encoding="utf-8"), Loader=yaml.CSafeLoader)
    if not isinstance(payload, dict):
        raise ValueError(
            f"boundary-derived role authority for {module_type} example is malformed"
        )
    components = payload.get("components")
    matches = [
        item
        for item in components if isinstance(item, dict)
        and item.get("id") == component_id
        and item.get("type") == module_type
    ] if isinstance(components, list) else []
    if len(matches) != 1:
        raise ValueError(
            f"boundary-derived role authority for {module_type} has no unique component"
        )
    prefix = f"{component_id}."
    boundary_variables = sorted(
        {
            str(item["variable"])[len(prefix):]
            for item in payload.get("boundaries", [])
            if isinstance(item, dict)
            and isinstance(item.get("variable"), str)
            and str(item["variable"]).startswith(prefix)
        }
    )
    declared_names = {item["name"] for item in declared_ports}
    input_names = set(boundary_variables)
    output_names = declared_names - input_names
    if not input_names or not output_names:
        raise ValueError(
            f"boundary-derived role authority for {module_type} needs inputs and outputs"
        )
    if input_names - declared_names:
        raise ValueError(
            f"boundary-derived role authority for {module_type} is stale: "
            f"boundaries={boundary_variables}, declared={sorted(declared_names)}"
        )
    ports = sorted(
        [
            *(
                {"name": name, "direction": "input"}
                for name in input_names
            ),
            *(
                {"name": name, "direction": "output"}
                for name in output_names
            ),
        ],
        key=lambda item: item["name"],
    )
    example_sha256 = _file_sha256(path)
    subject_revision = _canonical_hash(
        {
            "module_type": module_type,
            "instantiation_fingerprint": instantiation_fingerprint,
            "example_sha256": example_sha256,
            "component_id": component_id,
            "declared_ports_fingerprint": _canonical_hash(declared_ports),
            "boundary_variables": boundary_variables,
        }
    )
    return ports, {
        "kind": "current_example_boundary_contract",
        "path": relative_path.replace("\\", "/"),
        "sha256": example_sha256,
        "component_id": component_id,
        "instantiation_fingerprint": instantiation_fingerprint,
        "subject_revision": subject_revision,
        "boundary_variables": boundary_variables,
        "derivation": "derive this scenario's fixed inputs and solved outputs from the exact current example",
        "claim_boundary": (
            "canonical reviewed scenario roles only; the module relation remains "
            "direction-neutral and another legal boundary set may solve it in another direction"
        ),
        "known_bad": {
            "code": "alternate_boundary_direction_not_reusable",
            "message": (
                "a different legal boundary-variable set must derive a new scenario role "
                "contract and cannot reuse this direction projection"
            ),
        },
    }


def _load_ledger(path: Path) -> dict[str, dict[str, Any]]:
    payload = yaml.load(path.read_text(encoding="utf-8"), Loader=yaml.CSafeLoader)
    if not isinstance(payload, dict) or not isinstance(payload.get("module_records"), list):
        raise ValueError("the current per-module semantics ledger is missing or malformed")
    records: dict[str, dict[str, Any]] = {}
    for item in payload["module_records"]:
        if not isinstance(item, dict) or not isinstance(item.get("module_type"), str):
            raise ValueError("the current ledger contains an invalid module record")
        module_type = str(item["module_type"])
        if module_type in records:
            raise ValueError(f"the current ledger duplicates {module_type}")
        records[module_type] = item
    return records


def _variable_projection(variable: Any) -> dict[str, Any]:
    name = getattr(variable, "local_name", None) or str(
        getattr(variable, "name", "")
    ).rsplit(".", 1)[-1]
    return {
        "name": str(name),
        "unit": (
            "1"
            if getattr(variable, "unit", None) in {None, "", "dimensionless"}
            else str(getattr(variable, "unit"))
        ),
        "lower_bound": getattr(variable, "lower_bound", None),
        "upper_bound": getattr(variable, "upper_bound", None),
        "initial_guess": getattr(variable, "initial_guess", None),
        "scale": getattr(variable, "scale", None),
    }


def _external_variable_references(instance: Any) -> list[dict[str, str]]:
    references: list[dict[str, str]] = []
    for attribute, value in sorted(vars(instance).items()):
        if attribute.endswith("_variable") and isinstance(value, str) and "." in value:
            references.append({"attribute": attribute, "reference": value})
        elif attribute.endswith("_variables") and isinstance(value, list):
            for reference in value:
                if isinstance(reference, str) and "." in reference:
                    references.append(
                        {"attribute": attribute, "reference": reference}
                    )
    return sorted(
        references,
        key=lambda item: (item["attribute"], item["reference"]),
    )


def build_registry_payload(
    root: Path = ROOT,
    ledger_path: Path = DEFAULT_LEDGER,
) -> dict[str, Any]:
    root_text = str(root)
    source_root = str(root / "src")
    if root_text not in sys.path:
        sys.path.insert(0, root_text)
    if source_root not in sys.path:
        sys.path.insert(0, source_root)

    from physicsguard.modules.registry import default_module_registry

    records = _load_ledger(ledger_path)
    registry = default_module_registry()
    module_types = sorted(registry.registered_types())
    modules: list[dict[str, Any]] = []
    instantiation_subjects: dict[str, Any] = {}

    for module_type in module_types:
        record = records.get(module_type)
        bindings = record.get("bindings") if isinstance(record, dict) else None
        instantiation = (
            bindings.get("instantiation") if isinstance(bindings, dict) else None
        )
        component_id = (
            instantiation.get("component_id")
            if isinstance(instantiation, dict)
            else None
        )
        parameters = (
            instantiation.get("parameters")
            if isinstance(instantiation, dict)
            else None
        )
        instantiation_subject = {
            "module_type": module_type,
            "component_id": component_id,
            "parameters": parameters,
        }
        instantiation_subjects[module_type] = instantiation_subject
        common = {
            "module_type": module_type,
            "instantiation_fingerprint": _canonical_hash(instantiation_subject),
        }
        if not isinstance(component_id, str) or not component_id.strip() or not isinstance(parameters, dict):
            modules.append(
                {
                    **common,
                    "disposition": "unresolved",
                    "declared_ports": [],
                    "external_variable_references": [],
                    "first_gap": {
                        "code": "runtime_instantiation_unavailable",
                        "message": "no exact current instantiation payload is available",
                    },
                }
            )
            continue
        try:
            instance = registry.create(module_type, component_id, parameters)
            declared_ports = sorted(
                (_variable_projection(item) for item in instance.declare_variables()),
                key=lambda item: item["name"],
            )
        except Exception as exc:
            modules.append(
                {
                    **common,
                    "disposition": "unresolved",
                    "declared_ports": [],
                    "external_variable_references": [],
                    "first_gap": {
                        "code": "runtime_instantiation_unavailable",
                        "message": f"live registry instantiation failed: {type(exc).__name__}: {exc}",
                    },
                }
            )
            continue

        declared_fingerprint = _canonical_hash(declared_ports)
        external_references = _external_variable_references(instance)
        intrinsic_resource = INTRINSIC_ROLE_AUTHORITY_RESOURCES.get(module_type)
        mechanical_draft_resource = MECHANICAL_DRAFT_ROLE_AUTHORITY_RESOURCES.get(
            module_type
        )
        source_first_resource = SOURCE_FIRST_ROLE_AUTHORITY_RESOURCES.get(module_type)
        explicit_ports: list[dict[str, str]] | None = None
        external_ports: list[dict[str, Any]] = []
        boundary_role_selected = module_type in BOUNDARY_DERIVED_ROLE_MODULES
        authority_evidence: dict[str, Any] | None = None
        direction_scope: str | None = None
        relation_directionality: str | None = None
        role_authority_basis: str | None = None
        if intrinsic_resource is not None:
            role_authority_basis = "intrinsic_project_formula_contract"
            direction_scope = "intrinsic_module_contract"
            relation_directionality = "directed"
            explicit_ports, authority_evidence = _intrinsic_role_authority_evidence(
                root,
                module_type,
                intrinsic_resource,
                declared_ports,
            )
        elif boundary_role_selected:
            role_authority_basis = "canonical_reviewed_scenario_role"
            direction_scope = "exact_instantiation_scenario"
            relation_directionality = "direction_neutral"
            explicit_ports, authority_evidence = _boundary_authority_evidence(
                root,
                module_type,
                component_id,
                instantiation,
                common["instantiation_fingerprint"],
                declared_ports,
            )
        elif mechanical_draft_resource is not None:
            role_authority_basis = "mechanical_draft_formula_role"
            direction_scope = "exact_instantiation_mechanical_draft"
            relation_directionality = "direction_neutral"
            (
                explicit_ports,
                external_ports,
                authority_evidence,
            ) = _mechanical_draft_role_authority_evidence(
                root,
                module_type,
                mechanical_draft_resource,
                instance,
                declared_ports,
            )
        elif source_first_resource is not None:
            role_authority_basis = "source_first_formula_role"
            direction_scope = "exact_instantiation_source_first_reconstruction"
            relation_directionality = "direction_neutral"
            (
                explicit_ports,
                external_ports,
                authority_evidence,
            ) = _source_first_role_authority_evidence(
                root,
                module_type,
                source_first_resource,
                instance,
                declared_ports,
            )
        if explicit_ports is not None:
            declared_names = {item["name"] for item in declared_ports}
            explicit_names = {item["name"] for item in explicit_ports}
            external_names = {item["name"] for item in external_ports}
            if declared_names | external_names != explicit_names:
                raise ValueError(
                    f"explicit role authority for {module_type} is stale: "
                    f"declared={sorted(declared_names)}, external={sorted(external_names)}, "
                    f"authority={sorted(explicit_names)}"
                )
            resolved_entry = {
                **common,
                "disposition": "resolved",
                "declared_ports": declared_ports,
                "declared_ports_fingerprint": declared_fingerprint,
                "external_variable_references": external_references,
                "external_ports": external_ports,
                "external_ports_fingerprint": _canonical_hash(external_ports),
                "role_authority_basis": role_authority_basis,
                "ports": sorted(explicit_ports, key=lambda item: item["name"]),
                "first_gap": None,
            }
            if authority_evidence is not None:
                resolved_entry["authority_evidence"] = authority_evidence
                resolved_entry["direction_scope"] = direction_scope
                resolved_entry["relation_directionality"] = relation_directionality
                resolved_entry["direction_claim_boundary"] = authority_evidence[
                    "claim_boundary"
                ]
            modules.append(resolved_entry)
            continue

        gap = (
            {
                "code": "external_runtime_port_authority_unavailable",
                "message": (
                    "the live module owns no VariableRecord; externally referenced "
                    "variables have no independent input/output/state authority"
                ),
            }
            if not declared_ports
            else {
                "code": "runtime_port_direction_unavailable",
                "message": (
                    f"{len(declared_ports)} live declared port(s) have no independent "
                    "input/output/state direction authority"
                ),
            }
        )
        modules.append(
            {
                **common,
                "disposition": "unresolved",
                "declared_ports": declared_ports,
                "declared_ports_fingerprint": declared_fingerprint,
                "external_variable_references": external_references,
                "external_ports": [],
                "external_ports_fingerprint": _canonical_hash([]),
                "first_gap": gap,
            }
        )

    payload = {
        "schema": SCHEMA,
        "producer_identity": PRODUCER_IDENTITY,
        "purpose": (
            "Live registry and exact instantiation inventory for module-local ports; "
            "directions remain unresolved unless a current source-independent project "
            "formula owns an intrinsic directed contract or an exact scenario-role "
            "authority exists. Explicitly unlicensed mechanical drafts may additionally "
            "project current local or externally observed roles while separate physical "
            "review remains pending; no direction-neutral relation becomes intrinsically "
            "directional."
        ),
        "live_registry_owner": "physicsguard.modules.registry.default_module_registry",
        "live_registry_fingerprint": _canonical_hash(module_types),
        "instantiation_source": ".physicsguard/module_equation_ledger.yaml#bindings.instantiation",
        "instantiation_source_fingerprint": _canonical_hash(instantiation_subjects),
        "modules": modules,
    }
    return {
        **payload,
        "registry_fingerprint": _canonical_hash(payload),
    }


def _render(payload: dict[str, Any]) -> str:
    return yaml.safe_dump(
        payload,
        sort_keys=False,
        allow_unicode=True,
        width=110,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build the sole current live module runtime-port inventory."
    )
    parser.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    payload = build_registry_payload(ROOT, args.ledger)
    rendered = _render(payload)
    if args.check:
        if not args.output.is_file() or args.output.read_text(encoding="utf-8") != rendered:
            print("module runtime-port registry is stale", file=sys.stderr)
            return 1
        print(
            json.dumps(
                {
                    "status": "pass",
                    "module_count": len(payload["modules"]),
                    "resolved_count": sum(
                        item["disposition"] == "resolved"
                        for item in payload["modules"]
                    ),
                    "unresolved_count": sum(
                        item["disposition"] == "unresolved"
                        for item in payload["modules"]
                    ),
                    "registry_fingerprint": payload["registry_fingerprint"],
                },
                sort_keys=True,
            )
        )
        return 0
    print(
        "direct runtime-port writes are retired; use "
        "scripts/compile_module_semantics.py --apply",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
