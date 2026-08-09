from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest
import yaml

import physicsguard
from physicsguard.core.physical_model_blueprint import review_physical_model_blueprint
from physicsguard.core.signal_mapping import review_signal_mapping_ledger
from physicsguard.core.target_inventory_authority import (
    LOCAL_TARGET_INVENTORY_ADAPTER_TOOL,
    LOCAL_TARGET_INVENTORY_ADAPTER_VERSION,
    TARGET_MATERIAL_INPUT_ID,
)
from physicsguard.schema.physical_model_blueprint import (
    PhysicalModelBlueprint,
    TargetInventoryAuthority,
    canonical_blueprint_fingerprint,
    fingerprint_inventory,
    fingerprint_native_execution_evidence,
    fingerprint_target_material_revision,
    fingerprint_target_inventory_authority,
    fingerprint_target_inventory_execution,
    target_material_request_id,
)
from physicsguard.schema.signal_mapping import (
    SignalMappingLedgerSpec,
    fingerprint_signal_mapping_ledger,
)


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


@pytest.fixture
def complete_physical_blueprint(tmp_path: Path):
    def build(
        *,
        target_kind: str = "physical_system",
        provider_kind: str = "official-exchange-package",
    ) -> tuple[PhysicalModelBlueprint, Path]:
        artifact_dir = tmp_path / "artifacts"
        artifact_dir.mkdir(exist_ok=True)
        signal_mapping_payload = {
            "artifact_kind": "physicsguard_signal_mapping_ledger",
            "ledger_version": "1.0",
            "ledger_id": "signal-map.external-pump-loop.r1",
            "target_system_id": "external-pump-loop",
            "subject_revision": "bench-r1",
            "source_artifact_sha256": _sha256_bytes(b"external-pump-loop-signal-source-r1"),
            "entries": [
                {
                    "mapping_id": "mapping.external-pump-loop.flow",
                    "physics_variable": "pump_loop.flow",
                    "external_signal": "bench.flow",
                    "expected_unit": "kg/s",
                    "observed_unit": "kg/s",
                    "mapping_confidence": 1.0,
                    "mapping_status": "confirmed",
                    "source_revision": "bench-r1",
                    "temporal_boundary": "bench-r1",
                    "issue_codes": [],
                }
            ],
            "status": "pass",
            "safe_mapping_claim": "exact synthetic fixture mapping for bench-r1 only",
        }
        signal_mapping_payload["ledger_fingerprint"] = (
            fingerprint_signal_mapping_ledger(signal_mapping_payload)
        )
        signal_mapping = SignalMappingLedgerSpec.model_validate(
            signal_mapping_payload
        ).model_dump(mode="json", exclude_none=True)
        contents = {
            "implementation.txt": b"pump and pipe workflow revision bench-r1\n",
            "test.txt": b"steady and stateful pump loop checks pass\n",
            "resource.txt": b"pump curve and pipe resistance resource\n",
            "oracle.txt": b"mass balance and pressure-flow oracle\n",
            "evidence.yaml": yaml.safe_dump(
                signal_mapping,
                sort_keys=False,
            ).encode("utf-8"),
        }
        artifact_hashes: dict[str, str] = {}
        for name, content in contents.items():
            path = artifact_dir / name
            path.write_bytes(content)
            artifact_hashes[name] = _sha256_bytes(content)
        signal_mapping_terminal = review_signal_mapping_ledger(
            artifact_dir / "evidence.yaml"
        ).to_dict()
        native_execution = {
            "execution_id": "execution.external-pump-loop.signal-map.r1",
            "native_owner_id": "physicsguard.signal-mapping-review",
            "operation_id": "signal_mapping.review",
            "native_schema": "signal_mapping_ledger",
            "input_artifact_sha256": artifact_hashes["evidence.yaml"],
            "target_system_id": "external-pump-loop",
            "subject_revision": "bench-r1",
            "tool_id": "physicsguard",
            "tool_version": physicsguard.__version__,
            "expected_terminal_status": "pass",
            "terminal_receipt_fingerprint": canonical_blueprint_fingerprint(
                signal_mapping_terminal
            ),
        }
        native_execution["execution_fingerprint"] = (
            fingerprint_native_execution_evidence(native_execution)
        )

        boundary_fingerprint = _sha256_bytes(b"external-pump-loop-boundary-r1")
        element_semantics = {
            "pump_loop": ["sem.loop.mass", "sem.loop.energy", "sem.loop.initial_mass", "sem.loop.mass_step", "sem.loop.termination"],
            "pump": ["sem.pump.pressure_rise"],
            "pipe": ["sem.pipe.pressure_flow", "sem.pipe.initial_mass", "sem.pipe.mass_step", "sem.pipe.heat_loss", "sem.pipe.termination"],
        }
        element_ports = {
            "pump_loop": ["port.loop.voltage", "port.loop.inlet_pressure", "port.loop.flow", "port.loop.mass", "port.loop.heat_loss"],
            "pump": ["port.pump.voltage", "port.pump.suction_pressure", "port.pump.discharge_pressure"],
            "pipe": ["port.pipe.inlet_pressure", "port.pipe.flow", "port.pipe.mass", "port.pipe.heat_loss"],
        }
        binding_kinds = {
            "implementation": "implementation.txt",
            "test": "test.txt",
            "resource": "resource.txt",
            "oracle": "oracle.txt",
            "evidence": "evidence.yaml",
        }
        bindings: list[dict[str, Any]] = []
        binding_ids_by_element: dict[str, list[str]] = {}
        for element_id, semantic_ids in element_semantics.items():
            binding_ids_by_element[element_id] = []
            for binding_kind, file_name in binding_kinds.items():
                binding_id = f"binding.{element_id}.{binding_kind}"
                binding_ids_by_element[element_id].append(binding_id)
                bindings.append(
                    {
                        "binding_id": binding_id,
                        "owner_element_id": element_id,
                        "binding_kind": binding_kind,
                        "native_schema": (
                            "signal_mapping_ledger"
                            if binding_kind == "evidence"
                            else "generic_artifact"
                        ),
                        "subject_id": (
                            "signal-map.external-pump-loop.r1"
                            if binding_kind == "evidence"
                            else f"{element_id}.{binding_kind}.r1"
                        ),
                        "subject_revision": "bench-r1",
                        "artifact": {
                            "repo_path": f"artifacts/{file_name}",
                            "sha256": artifact_hashes[file_name],
                        },
                        "provider_id": "provider.pump-loop",
                        **(
                            {
                                "native_execution_id": "execution.external-pump-loop.signal-map.r1"
                            }
                            if binding_kind == "evidence"
                            else {}
                        ),
                        "status": "current",
                        "semantic_ids": semantic_ids,
                        "obligation_ids": [f"obligation.{element_id}"],
                        "validation_modes": (
                            {
                                "pump_loop": [
                                    "pointwise",
                                    "temporal_stateful",
                                    "conservation_residual",
                                    "interface_unit",
                                    "boundary_invalid_region",
                                    "cross_coupling",
                                ],
                                "pump": ["pointwise", "interface_unit", "boundary_invalid_region"],
                                "pipe": [
                                    "pointwise",
                                    "temporal_stateful",
                                    "interface_unit",
                                    "boundary_invalid_region",
                                ],
                            }[element_id]
                            if binding_kind == "test"
                            else []
                        ),
                    }
                )
        members: list[dict[str, Any]] = []
        for element_id in element_semantics:
            members.append(
                {
                    "member_id": element_id,
                    "member_kind": "physical_element",
                    "disposition": "modeled",
                    "blueprint_element_id": element_id,
                }
            )
        for element_id, port_ids in element_ports.items():
            for port_id in port_ids:
                members.append(
                    {
                        "member_id": port_id,
                        "member_kind": "interface",
                        "disposition": "modeled",
                        "blueprint_element_id": element_id,
                    }
                )
        for element_id, semantic_ids in element_semantics.items():
            for semantic_id in semantic_ids:
                members.append(
                    {
                        "member_id": semantic_id,
                        "member_kind": "equation",
                        "disposition": "modeled",
                        "blueprint_element_id": element_id,
                    }
                )
        validity_owners = {
            "validity.loop": "pump_loop",
            "validity.pump": "pump",
            "validity.pipe": "pipe",
        }
        for boundary_id, element_id in validity_owners.items():
            members.append(
                {
                    "member_id": boundary_id,
                    "member_kind": "parameter",
                    "disposition": "modeled",
                    "blueprint_element_id": element_id,
                }
            )
        for binding in bindings:
            members.append(
                {
                    "member_id": f"inventory.{binding['binding_id']}",
                    "member_kind": {
                        "implementation": "workflow",
                        "test": "test",
                        "resource": "resource",
                        "oracle": "oracle",
                        "evidence": "evidence",
                    }[binding["binding_kind"]],
                    "disposition": "supporting",
                    "binding_ids": [binding["binding_id"]],
                }
            )
        inventory = {
            "inventory_id": "inventory.external-pump-loop.r1",
            "provider_id": "provider.pump-loop",
            "target_system_id": "external-pump-loop",
            "subject_revision": "bench-r1",
            "boundary_fingerprint": boundary_fingerprint,
            "members": members,
        }
        inventory["inventory_fingerprint"] = fingerprint_inventory(inventory)

        data: dict[str, Any] = {
            "schema_version": "physicsguard.physical-model-blueprint.v1",
            "blueprint_id": "blueprint.external-pump-loop.r1",
            "qualification_target": "external_physical_target",
            "understanding_target": "declared_consistency",
            "artifact_root": "blueprint_directory",
            "target": {
                "target_system_id": "external-pump-loop",
                "target_kind": target_kind,
                "subject_revision": "bench-r1",
                "boundary_fingerprint": boundary_fingerprint,
                "purpose": "Qualify a bounded external pump-loop physical model and testbench.",
                "claim_boundary": "Static pump-loop semantics and current fixture bindings only.",
            },
            "required_capability_ids": ["artifact_inventory", "interface_topology", "native_binding_observation"],
            "capability_owners": {
                "artifact_inventory": "provider.pump-loop",
                "interface_topology": "provider.pump-loop",
                "native_binding_observation": "provider.pump-loop",
            },
            "providers": [
                {
                    "provider_id": "provider.pump-loop",
                    "provider_kind": provider_kind,
                    "provider_version": "1.0",
                    "target_system_id": "external-pump-loop",
                    "subject_revision": "bench-r1",
                    "capability_ids": ["artifact_inventory", "interface_topology", "native_binding_observation"],
                    "input_fingerprints": {"boundary": boundary_fingerprint},
                    "payload_fingerprint": inventory["inventory_fingerprint"],
                    "status": "current",
                    "claim_boundary": "Independent inventory and exact fixture artifact observation only.",
                }
            ],
            "inventory": inventory,
            "elements": [
                {
                    "element_id": "pump_loop",
                    "name": "Pump loop",
                    "element_kind": "system",
                    "depth": 0,
                    "description": "Bounded source-pump-pipe loop represented by pump and pipe children.",
                    "port_ids": element_ports["pump_loop"],
                    "semantic_ids": element_semantics["pump_loop"],
                    "validity_boundary_ids": ["validity.loop"],
                    "native_binding_ids": binding_ids_by_element["pump_loop"],
                    "owned_behavior_ids": ["behavior.loop.mass-pressure-flow"],
                },
                {
                    "element_id": "pump",
                    "name": "Pump",
                    "element_kind": "component",
                    "parent_id": "pump_loop",
                    "depth": 1,
                    "description": "Low-fidelity electrical input to pressure-rise relation.",
                    "port_ids": element_ports["pump"],
                    "semantic_ids": element_semantics["pump"],
                    "validity_boundary_ids": ["validity.pump"],
                    "native_binding_ids": binding_ids_by_element["pump"],
                    "owned_behavior_ids": ["behavior.pump.pressure-rise"],
                },
                {
                    "element_id": "pipe",
                    "name": "Pipe and storage",
                    "element_kind": "component",
                    "parent_id": "pump_loop",
                    "depth": 1,
                    "description": "Pressure-flow relation with one stored-mass state and heat-loss effect.",
                    "port_ids": element_ports["pipe"],
                    "semantic_ids": element_semantics["pipe"],
                    "validity_boundary_ids": ["validity.pipe"],
                    "native_binding_ids": binding_ids_by_element["pipe"],
                    "owned_behavior_ids": ["behavior.pipe.pressure-flow", "behavior.pipe.mass-state"],
                },
            ],
            "ports": [
                _port("port.loop.voltage", "pump_loop", "input", "voltage", "V"),
                _port("port.loop.inlet_pressure", "pump_loop", "input", "pressure", "Pa"),
                _port("port.loop.flow", "pump_loop", "output", "mass_flow", "kg/s"),
                _port("port.loop.mass", "pump_loop", "state", "mass", "kg", initial="sem.loop.initial_mass", termination="sem.loop.termination"),
                _port("port.loop.heat_loss", "pump_loop", "effect", "heat_flow", "W"),
                _port("port.pump.voltage", "pump", "input", "voltage", "V"),
                _port("port.pump.suction_pressure", "pump", "input", "pressure", "Pa"),
                _port("port.pump.discharge_pressure", "pump", "output", "pressure", "Pa"),
                _port("port.pipe.inlet_pressure", "pipe", "input", "pressure", "Pa"),
                _port("port.pipe.flow", "pipe", "output", "mass_flow", "kg/s"),
                _port("port.pipe.mass", "pipe", "state", "mass", "kg", initial="sem.pipe.initial_mass", termination="sem.pipe.termination"),
                _port("port.pipe.heat_loss", "pipe", "effect", "heat_flow", "W"),
            ],
            "semantics": [
                _semantic("sem.loop.mass", "pump_loop", "conservation_law", "Loop mass is conserved inside the declared boundary.", "dm_loop/dt = m_in - m_out", ["port.loop.inlet_pressure"], ["port.loop.flow"], ["port.loop.mass"], ["port.loop.heat_loss"], ["validity.loop"]),
                _semantic("sem.loop.energy", "pump_loop", "conservation_law", "Electrical pump input is balanced by hydraulic transfer and exposed heat loss.", "electrical_power = hydraulic_power + q_loss", ["port.loop.voltage"], ["port.loop.flow"], [], ["port.loop.heat_loss"], ["validity.loop"]),
                _semantic("sem.loop.initial_mass", "pump_loop", "parameter", "Initial loop mass is supplied by the testbench.", None, [], [], ["port.loop.mass"], [], ["validity.loop"]),
                _semantic("sem.loop.mass_step", "pump_loop", "state_update", "Loop stored mass advances on the declared discrete time basis.", "m_next = m + dt * (m_in - m_out)", ["port.loop.inlet_pressure"], ["port.loop.flow"], ["port.loop.mass"], [], ["validity.loop"]),
                _semantic("sem.loop.termination", "pump_loop", "termination", "Loop state terminates or hands off at the declared testbench stop time.", None, [], [], ["port.loop.mass"], [], ["validity.loop"]),
                _semantic("sem.pump.pressure_rise", "pump", "constitutive_relation", "Pump voltage and suction pressure determine the low-fidelity discharge pressure.", "p_out = p_in + k_v * voltage", ["port.pump.voltage", "port.pump.suction_pressure"], ["port.pump.discharge_pressure"], [], [], ["validity.pump"]),
                _semantic("sem.pipe.pressure_flow", "pipe", "constitutive_relation", "Pipe inlet pressure determines low-fidelity mass flow under the declared resistance.", "m_dot = (p_in - p_out) / resistance", ["port.pipe.inlet_pressure"], ["port.pipe.flow"], [], [], ["validity.pipe"]),
                _semantic("sem.pipe.initial_mass", "pipe", "parameter", "Initial stored mass is supplied by the external testbench.", None, [], [], ["port.pipe.mass"], [], ["validity.pipe"]),
                _semantic("sem.pipe.mass_step", "pipe", "state_update", "Pipe stored mass advances from the inlet and outlet mass-flow balance.", "m_next = m + dt * (m_in - m_out)", ["port.pipe.inlet_pressure"], ["port.pipe.flow"], ["port.pipe.mass"], [], ["validity.pipe"]),
                _semantic("sem.pipe.heat_loss", "pipe", "equation", "Pipe heat loss is exposed as an effect and not hidden in mass conservation.", "q_loss = conductance * (temperature - ambient)", ["port.pipe.inlet_pressure"], [], [], ["port.pipe.heat_loss"], ["validity.pipe"]),
                _semantic("sem.pipe.termination", "pipe", "termination", "Pipe stored mass hands off to the parent state at the testbench stop time.", None, [], [], ["port.pipe.mass"], [], ["validity.pipe"]),
            ],
            "validity_boundaries": [
                {"boundary_id": "validity.loop", "owner_element_id": "pump_loop", "statement": "Steady liquid properties and one-second discrete state steps."},
                {"boundary_id": "validity.pump", "owner_element_id": "pump", "statement": "Positive voltage and low-fidelity linear pressure rise only."},
                {"boundary_id": "validity.pipe", "owner_element_id": "pipe", "statement": "Single-phase incompressible flow and positive resistance only."},
            ],
            "refinements": [
                {
                    "refinement_id": "refinement.pump-loop",
                    "parent_element_id": "pump_loop",
                    "child_element_ids": ["pump", "pipe"],
                    "port_mappings": [
                        _mapping("map.loop-voltage.pump-voltage", "parent_input_to_child_input", "port.loop.voltage", "port.pump.voltage"),
                        _mapping("map.loop-pressure.pump-suction", "parent_input_to_child_input", "port.loop.inlet_pressure", "port.pump.suction_pressure"),
                        _mapping("map.pump-pressure.pipe-pressure", "sibling_output_to_child_input", "port.pump.discharge_pressure", "port.pipe.inlet_pressure"),
                        _mapping("map.pipe-flow.loop-flow", "child_output_to_parent_output", "port.pipe.flow", "port.loop.flow"),
                        _mapping("map.pipe-mass.loop-mass", "child_state_to_parent_state", "port.pipe.mass", "port.loop.mass"),
                        _mapping("map.pipe-heat.loop-heat", "child_effect_to_parent_effect", "port.pipe.heat_loss", "port.loop.heat_loss"),
                    ],
                    "semantic_contributions": [
                        _contribution("contribution.pump-pressure", "sem.pump.pressure_rise", "sem.loop.energy"),
                        _contribution("contribution.pipe-flow", "sem.pipe.pressure_flow", "sem.loop.mass"),
                        _contribution("contribution.pipe-initial", "sem.pipe.initial_mass", "sem.loop.initial_mass"),
                        _contribution("contribution.pipe-state", "sem.pipe.mass_step", "sem.loop.mass_step"),
                        _contribution("contribution.pipe-termination", "sem.pipe.termination", "sem.loop.termination"),
                        _contribution("contribution.pipe-heat", "sem.pipe.heat_loss", "sem.loop.energy"),
                    ],
                    "propagated_validity_boundary_ids": ["validity.pump", "validity.pipe"],
                }
            ],
            "native_executions": [native_execution],
            "bindings": bindings,
        }
        blueprint = PhysicalModelBlueprint.model_validate(data)

        target_material = {
            "schema_version": "physicsguard.target-material.v1",
            "inventory_id": blueprint.inventory.inventory_id,
            "provider_id": blueprint.inventory.provider_id,
            "target_system_id": blueprint.target.target_system_id,
            "subject_revision": blueprint.target.subject_revision,
            "boundary_fingerprint": blueprint.target.boundary_fingerprint,
            "elements": [
                {"element_id": item.element_id} for item in blueprint.elements
            ],
            "ports": [
                {
                    "port_id": item.port_id,
                    "owner_element_id": item.owner_element_id,
                }
                for item in blueprint.ports
            ],
            "semantics": [
                {
                    "semantic_id": item.semantic_id,
                    "owner_element_id": item.owner_element_id,
                }
                for item in blueprint.semantics
            ],
            "validity_boundaries": [
                {
                    "boundary_id": item.boundary_id,
                    "owner_element_id": item.owner_element_id,
                }
                for item in blueprint.validity_boundaries
            ],
            "materials": [
                {
                    "material_id": item.member_id,
                    "material_kind": item.member_kind,
                    "binding_ids": item.binding_ids,
                }
                for item in blueprint.inventory.members
                if item.disposition == "supporting"
            ],
        }
        target_material["material_revision_fingerprint"] = (
            fingerprint_target_material_revision(target_material)
        )
        target_material["request_id"] = target_material_request_id(
            target_material["material_revision_fingerprint"]
        )
        target_material_path = tmp_path / "target_material.json"
        target_material_bytes = json.dumps(
            target_material,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        target_material_path.write_bytes(target_material_bytes)
        target_material_sha256 = _sha256_bytes(target_material_bytes)
        authority_inputs = {TARGET_MATERIAL_INPUT_ID: target_material_sha256}
        target_inventory_execution = {
            "execution_id": "execution.external-pump-loop.target-inventory.r1",
            "owner_id": "physicsguard.target-material-inventory",
            "request_id": target_material["request_id"],
            "input_reference_ids": [TARGET_MATERIAL_INPUT_ID],
            "target_system_id": blueprint.target.target_system_id,
            "subject_revision": blueprint.target.subject_revision,
            "adapter_tool_id": LOCAL_TARGET_INVENTORY_ADAPTER_TOOL,
            "adapter_tool_version": LOCAL_TARGET_INVENTORY_ADAPTER_VERSION,
            "result_status": "pass",
            "terminal_status": "success",
            "result_fingerprint": blueprint.inventory.inventory_fingerprint,
            "terminal_receipt_fingerprint": canonical_blueprint_fingerprint(
                {
                    "execution_id": "execution.external-pump-loop.target-inventory.r1",
                    "owner_id": "physicsguard.target-material-inventory",
                    "request_id": target_material["request_id"],
                    "input_fingerprints": authority_inputs,
                    "target_system_id": blueprint.target.target_system_id,
                    "subject_revision": blueprint.target.subject_revision,
                    "adapter_tool_id": LOCAL_TARGET_INVENTORY_ADAPTER_TOOL,
                    "adapter_tool_version": LOCAL_TARGET_INVENTORY_ADAPTER_VERSION,
                    "result_status": "pass",
                    "terminal_status": "success",
                    "result_fingerprint": blueprint.inventory.inventory_fingerprint,
                }
            ),
        }
        target_inventory_execution["execution_fingerprint"] = (
            fingerprint_target_inventory_execution(target_inventory_execution)
        )
        authority_payload = {
            "schema_version": "physicsguard.target-inventory-authority.v1",
            "authority_id": "authority.external-pump-loop.target-inventory.r1",
            "status": "current",
            "owner_id": "physicsguard.target-material-inventory",
            "request_id": target_material["request_id"],
            "provider_id": blueprint.inventory.provider_id,
            "target_system_id": blueprint.target.target_system_id,
            "subject_revision": blueprint.target.subject_revision,
            "boundary_fingerprint": blueprint.target.boundary_fingerprint,
            "input_references": [
                {
                    "reference_id": TARGET_MATERIAL_INPUT_ID,
                    "artifact": {
                        "repo_path": target_material_path.name,
                        "sha256": target_material_sha256,
                    },
                }
            ],
            "inventory": blueprint.inventory.model_dump(mode="json", exclude_none=True),
            "execution": target_inventory_execution,
        }
        authority_payload["authority_fingerprint"] = (
            fingerprint_target_inventory_authority(authority_payload)
        )
        target_inventory_authority = TargetInventoryAuthority.model_validate(
            authority_payload
        )
        authority_path = tmp_path / "target_inventory_authority.yaml"
        authority_path.write_text(
            yaml.safe_dump(
                target_inventory_authority.model_dump(mode="json", exclude_none=True),
                sort_keys=False,
            ),
            encoding="utf-8",
        )
        build.target_inventory_authority = target_inventory_authority
        build.blueprint_base_dir = tmp_path
        build.authority_base_dir = tmp_path
        build.target_inventory_authority_path = authority_path
        build.target_material_path = target_material_path
        return blueprint, tmp_path

    def review_current(blueprint, *, base_dir, affected_element_ids=None):
        return review_physical_model_blueprint(
            blueprint,
            target_inventory_authority=build.target_inventory_authority,
            base_dir=base_dir,
            authority_base_dir=build.authority_base_dir,
            affected_element_ids=affected_element_ids,
        )

    build.review = review_current

    return build


def _port(
    port_id: str,
    owner: str,
    direction: str,
    quantity: str,
    unit: str,
    *,
    initial: str | None = None,
    termination: str | None = None,
) -> dict[str, Any]:
    value: dict[str, Any] = {
        "port_id": port_id,
        "owner_element_id": owner,
        "direction": direction,
        "quantity_id": quantity,
        "unit": unit,
        "time_basis": "discrete:1s",
        "value_shape": "scalar",
        "required": True,
        "reference_frame": "loop-positive-flow",
        "sign_convention": "positive-from-source-to-load",
        "validity_boundary_id": {
            "pump_loop": "validity.loop",
            "pump": "validity.pump",
            "pipe": "validity.pipe",
        }[owner],
    }
    if initial is not None:
        value["initial_state_semantic_id"] = initial
    if termination is not None:
        value["termination_semantic_id"] = termination
    return value


def _semantic(
    semantic_id: str,
    owner: str,
    kind: str,
    statement: str,
    expression: str | None,
    inputs: list[str],
    outputs: list[str],
    states: list[str],
    effects: list[str],
    boundaries: list[str],
) -> dict[str, Any]:
    return {
        "semantic_id": semantic_id,
        "owner_element_id": owner,
        "semantic_kind": kind,
        "statement": statement,
        "expression": expression,
        "input_port_ids": inputs,
        "output_port_ids": outputs,
        "state_port_ids": states,
        "effect_port_ids": effects,
        "validity_boundary_ids": boundaries,
    }


def _mapping(mapping_id: str, kind: str, source: str, target: str) -> dict[str, Any]:
    return {
        "mapping_id": mapping_id,
        "mapping_kind": kind,
        "source_port_id": source,
        "target_port_id": target,
    }


def _contribution(contribution_id: str, child: str, parent: str) -> dict[str, Any]:
    return {
        "contribution_id": contribution_id,
        "child_semantic_id": child,
        "parent_semantic_id": parent,
        "relation": "constrains",
        "rationale": "The child physical semantic constrains the parent loop balance.",
    }
