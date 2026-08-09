"""Replay raw target material through the runtime-owned inventory adapter."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import yaml
from pydantic import ValidationError

from physicsguard.schema.physical_model_blueprint import (
    IndependentInventory,
    InventoryMember,
    ProviderRegistry,
    ProviderRegistryEntry,
    TARGET_MATERIAL_SCHEMA,
    TargetInventoryAuthority,
    TargetMaterialDocument,
    canonical_blueprint_fingerprint,
    fingerprint_inventory,
    fingerprint_provider_registry,
    fingerprint_provider_registry_entry,
)


LOCAL_TARGET_INVENTORY_ADAPTER_TOOL = "physicsguard.target-material-inventory"
LOCAL_TARGET_INVENTORY_ADAPTER_VERSION = "1"
TARGET_MATERIAL_INPUT_ID = "target_material"


@dataclass(frozen=True)
class TargetInventoryAuthorityObservation:
    status: Literal["pass", "unverified", "stale", "blocked"]
    inventory: IndependentInventory | None
    provider_registry_fingerprint: str
    expected_inventory_fingerprint: str | None
    findings: tuple[str, ...]


def current_target_inventory_provider_registry() -> ProviderRegistry:
    """Return the closed adapter-capability registry for this runtime.

    The registry owns executable adapter identity and schema support.  It does
    not whitelist target ids, revisions, locators, or content hashes; those are
    derived from each exact observable target-material snapshot.
    """

    entry_payload = {
        "registration_id": "physicsguard.target-material-inventory.local.v1",
        "status": "current",
        "capability_ids": ["artifact_inventory"],
        "owner_id": "physicsguard.target-material-inventory",
        "adapter_tool_id": LOCAL_TARGET_INVENTORY_ADAPTER_TOOL,
        "adapter_tool_version": LOCAL_TARGET_INVENTORY_ADAPTER_VERSION,
        "execution_mode": "local",
        "input_reference_ids": [TARGET_MATERIAL_INPUT_ID],
        "input_schema_version": TARGET_MATERIAL_SCHEMA,
    }
    entry_payload["entry_fingerprint"] = fingerprint_provider_registry_entry(
        entry_payload
    )
    entry = ProviderRegistryEntry.model_validate(entry_payload)
    registry_payload = {
        "schema_version": "physicsguard.provider-registry.v1",
        "registry_id": "physicsguard.target-inventory.capabilities.current",
        "registry_revision": "1",
        "status": "current",
        "entries": [entry.model_dump(mode="json")],
    }
    registry_payload["registry_fingerprint"] = fingerprint_provider_registry(
        registry_payload
    )
    return ProviderRegistry.model_validate(registry_payload)


def derive_target_inventory(material: TargetMaterialDocument) -> IndependentInventory:
    """Derive the governed denominator from raw material, never caller rows."""

    members: list[InventoryMember] = []
    members.extend(
        InventoryMember(
            member_id=item.element_id,
            member_kind="physical_element",
            disposition="modeled",
            blueprint_element_id=item.element_id,
        )
        for item in material.elements
    )
    members.extend(
        InventoryMember(
            member_id=item.port_id,
            member_kind="interface",
            disposition="modeled",
            blueprint_element_id=item.owner_element_id,
        )
        for item in material.ports
    )
    members.extend(
        InventoryMember(
            member_id=item.semantic_id,
            member_kind=item.member_kind,
            disposition="modeled",
            blueprint_element_id=item.owner_element_id,
        )
        for item in material.semantics
    )
    members.extend(
        InventoryMember(
            member_id=item.boundary_id,
            member_kind="parameter",
            disposition="modeled",
            blueprint_element_id=item.owner_element_id,
        )
        for item in material.validity_boundaries
    )
    members.extend(
        InventoryMember(
            member_id=item.material_id,
            member_kind=item.material_kind,
            disposition="supporting",
            binding_ids=item.binding_ids,
        )
        for item in material.materials
    )
    payload = {
        "inventory_id": material.inventory_id,
        "provider_id": material.provider_id,
        "target_system_id": material.target_system_id,
        "subject_revision": material.subject_revision,
        "boundary_fingerprint": material.boundary_fingerprint,
        "members": [item.model_dump(mode="json", exclude_none=True) for item in members],
    }
    payload["inventory_fingerprint"] = fingerprint_inventory(payload)
    return IndependentInventory.model_validate(payload)


def target_inventory_terminal_receipt(
    authority: TargetInventoryAuthority,
    *,
    input_fingerprints: dict[str, str],
    result_fingerprint: str,
    result_status: str = "pass",
    terminal_status: str = "success",
) -> dict[str, object]:
    """Return the deterministic terminal receipt replayed by the local owner."""

    execution = authority.execution
    return {
        "execution_id": execution.execution_id,
        "owner_id": execution.owner_id,
        "request_id": execution.request_id,
        "input_fingerprints": dict(sorted(input_fingerprints.items())),
        "target_system_id": execution.target_system_id,
        "subject_revision": execution.subject_revision,
        "adapter_tool_id": execution.adapter_tool_id,
        "adapter_tool_version": execution.adapter_tool_version,
        "result_status": result_status,
        "terminal_status": terminal_status,
        "result_fingerprint": result_fingerprint,
    }


def observe_target_inventory_authority(
    authority: TargetInventoryAuthority,
    *,
    base_dir: str | Path | None,
) -> TargetInventoryAuthorityObservation:
    """Derive and reconcile one exact observable target-material snapshot."""

    registry = current_target_inventory_provider_registry()
    tool_entries = [
        item
        for item in registry.entries
        if item.adapter_tool_id == authority.execution.adapter_tool_id
    ]
    entry = next(
        (
            item
            for item in tool_entries
            if item.adapter_tool_version == authority.execution.adapter_tool_version
        ),
        None,
    )

    def observed(
        status: Literal["pass", "unverified", "stale", "blocked"],
        *findings: str,
        inventory: IndependentInventory | None = None,
    ) -> TargetInventoryAuthorityObservation:
        return TargetInventoryAuthorityObservation(
            status=status,
            inventory=inventory,
            provider_registry_fingerprint=registry.registry_fingerprint,
            expected_inventory_fingerprint=(
                inventory.inventory_fingerprint if inventory is not None else None
            ),
            findings=tuple(findings),
        )

    if entry is None:
        if tool_entries:
            return observed(
                "stale",
                "target inventory adapter version differs from the runtime-owned current capability",
            )
        return observed(
            "unverified",
            "no runtime-owned current adapter capability can replay this target material",
        )
    if authority.status != "current" or registry.status != "current" or entry.status != "current":
        states = {authority.status, registry.status, entry.status}
        return observed(
            "stale" if "stale" in states else "blocked",
            "target inventory authority/runtime adapter capability is not current: "
            f"{authority.status}/{registry.status}/{entry.status}",
        )
    if "artifact_inventory" not in entry.capability_ids:
        return observed("blocked", "runtime adapter does not own artifact_inventory")
    if entry.execution_mode == "external":
        return observed(
            "unverified",
            "external target inventory adapter cannot be replayed by a current local execution owner",
        )
    if authority.owner_id != entry.owner_id or authority.execution.owner_id != entry.owner_id:
        return observed(
            "stale",
            "authority execution owner differs from the runtime-owned adapter owner",
        )
    if set(entry.input_reference_ids) != {TARGET_MATERIAL_INPUT_ID}:
        return observed(
            "blocked",
            "runtime adapter capability does not declare exactly one target_material input",
        )
    if base_dir is None:
        return observed(
            "unverified",
            "local target-material replay requires the explicit authority artifact directory",
        )

    references = {item.reference_id: item.artifact for item in authority.input_references}
    if set(references) != set(entry.input_reference_ids):
        return observed(
            "stale",
            "authority inputs differ from the runtime-owned adapter request shape",
        )
    reference = references[TARGET_MATERIAL_INPUT_ID]
    if reference.repo_path is None:
        return observed(
            "unverified",
            "external target material cannot be replayed by the local runtime owner",
        )
    root = Path(base_dir).resolve()
    material_path = (root / reference.repo_path).resolve()
    try:
        material_path.relative_to(root)
    except ValueError:
        return observed("blocked", "target material escapes the authority directory")
    try:
        payload_bytes = material_path.read_bytes()
    except OSError as exc:
        return observed("stale", f"target material cannot be read: {exc}")
    actual_sha256 = hashlib.sha256(payload_bytes).hexdigest()
    if actual_sha256 != reference.sha256:
        return observed("stale", "target material content fingerprint is stale")

    try:
        document = yaml.safe_load(payload_bytes.decode("utf-8"))
        material = TargetMaterialDocument.model_validate(document)
    except (UnicodeDecodeError, yaml.YAMLError, ValidationError) as exc:
        return observed("blocked", f"target material contract is invalid: {exc}")
    if material.schema_version != entry.input_schema_version:
        return observed(
            "blocked",
            "target material schema is not owned by the current runtime adapter",
        )

    replayed_inventory = derive_target_inventory(material)
    exact_pairs = {
        "provider_id": (material.provider_id, authority.provider_id),
        "request_id": (material.request_id, authority.request_id),
        "inventory_id": (material.inventory_id, authority.inventory.inventory_id),
        "target_system_id": (material.target_system_id, authority.target_system_id),
        "subject_revision": (material.subject_revision, authority.subject_revision),
        "boundary_fingerprint": (
            material.boundary_fingerprint,
            authority.boundary_fingerprint,
        ),
        "execution_request_id": (
            material.request_id,
            authority.execution.request_id,
        ),
        "execution_target_system_id": (
            material.target_system_id,
            authority.execution.target_system_id,
        ),
        "execution_subject_revision": (
            material.subject_revision,
            authority.execution.subject_revision,
        ),
    }
    mismatched = sorted(
        name for name, (expected, actual) in exact_pairs.items() if expected != actual
    )
    if mismatched:
        return observed(
            "stale",
            f"derived target-material request and authority disagree: {mismatched}",
            inventory=replayed_inventory,
        )
    if authority.execution.result_status != "pass" or authority.execution.terminal_status != "success":
        states = {
            authority.execution.result_status,
            authority.execution.terminal_status,
        }
        return observed(
            "stale" if "stale" in states else "unverified" if "unverified" in states else "blocked",
            "target inventory execution attestation has no terminal success result",
            inventory=replayed_inventory,
        )
    if replayed_inventory.model_dump(mode="json", exclude_none=True) != authority.inventory.model_dump(
        mode="json", exclude_none=True
    ):
        return observed(
            "stale",
            "runtime-derived target inventory does not equal the frozen authority projection",
            inventory=replayed_inventory,
        )

    input_fingerprints = {TARGET_MATERIAL_INPUT_ID: actual_sha256}
    receipt = target_inventory_terminal_receipt(
        authority,
        input_fingerprints=input_fingerprints,
        result_fingerprint=replayed_inventory.inventory_fingerprint,
    )
    terminal_fingerprint = canonical_blueprint_fingerprint(receipt)
    if terminal_fingerprint != authority.execution.terminal_receipt_fingerprint:
        return observed(
            "stale",
            "replayed target inventory terminal receipt does not match the frozen attestation",
            inventory=replayed_inventory,
        )
    return observed("pass", inventory=replayed_inventory)


__all__ = [
    "LOCAL_TARGET_INVENTORY_ADAPTER_TOOL",
    "LOCAL_TARGET_INVENTORY_ADAPTER_VERSION",
    "TARGET_MATERIAL_INPUT_ID",
    "TargetInventoryAuthorityObservation",
    "current_target_inventory_provider_registry",
    "derive_target_inventory",
    "observe_target_inventory_authority",
    "target_inventory_terminal_receipt",
]
