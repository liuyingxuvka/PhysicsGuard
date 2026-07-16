"""Diff utilities for test-file contracts."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from physicsguard.core.data_file_manifest import field_signature_hash
from physicsguard.core.test_file_contract import resolve_test_file_contract
from physicsguard.schema.data_file_manifest import FieldSummarySpec


@dataclass(frozen=True)
class ContractDiff:
    artifact_kind: str
    status: str
    old_contract: str
    new_contract: str
    changes: list[dict[str, Any]] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def diff_test_file_contracts(old_contract: str | Path, new_contract: str | Path) -> ContractDiff:
    old = resolve_test_file_contract(old_contract)
    new = resolve_test_file_contract(new_contract)
    changes: list[dict[str, Any]] = []
    old_fields = {field.name: field for field in old.manifest.value.fields}
    new_fields = {field.name: field for field in new.manifest.value.fields}

    for field_name in sorted(set(new_fields) - set(old_fields)):
        changes.append({"type": "field_added", "field_name": field_name})
    for field_name in sorted(set(old_fields) - set(new_fields)):
        changes.append({"type": "field_removed", "field_name": field_name})
    changes.extend(_possible_renames(old_fields, new_fields))
    for field_name in sorted(set(old_fields) & set(new_fields)):
        old_field = old_fields[field_name]
        new_field = new_fields[field_name]
        if old_field.unit != new_field.unit:
            changes.append(
                {
                    "type": "field_unit_changed",
                    "field_name": field_name,
                    "old": old_field.unit,
                    "new": new_field.unit,
                }
            )
        if old_field.data_type != new_field.data_type:
            changes.append(
                {
                    "type": "field_type_changed",
                    "field_name": field_name,
                    "old": old_field.data_type,
                    "new": new_field.data_type,
                }
            )
    if old.manifest.value.time.model_dump(mode="json") != new.manifest.value.time.model_dump(mode="json"):
        changes.append(
            {
                "type": "time_basis_changed",
                "old": old.manifest.value.time.model_dump(mode="json", exclude_none=True),
                "new": new.manifest.value.time.model_dump(mode="json", exclude_none=True),
            }
        )
    if old.manifest.value.extractor.script_hash != new.manifest.value.extractor.script_hash:
        changes.append(
            {
                "type": "extractor_changed",
                "old": old.manifest.value.extractor.script_hash,
                "new": new.manifest.value.extractor.script_hash,
            }
        )
    old_binding = old.model_binding.value.binding_id if old.model_binding is not None else None
    new_binding = new.model_binding.value.binding_id if new.model_binding is not None else None
    if old_binding != new_binding:
        changes.append(
            {
                "type": "model_binding_changed",
                "old": old_binding,
                "new": new_binding,
            }
        )
    old_signature = field_signature_hash(old.manifest.value)
    new_signature = field_signature_hash(new.manifest.value)
    if old_signature != new_signature:
        changes.append(
            {
                "type": "field_signature_changed",
                "old": old_signature,
                "new": new_signature,
            }
        )
    status = "changed" if changes else "unchanged"
    return ContractDiff(
        artifact_kind="test_file_contract_diff",
        status=status,
        old_contract=str(old.contract_path),
        new_contract=str(new.contract_path),
        changes=changes,
        summary={
            "change_count": len(changes),
            "old_field_count": len(old_fields),
            "new_field_count": len(new_fields),
            "added_field_count": sum(1 for change in changes if change["type"] == "field_added"),
            "removed_field_count": sum(1 for change in changes if change["type"] == "field_removed"),
            "possible_rename_count": sum(1 for change in changes if change["type"] == "possible_field_rename"),
        },
    )


def _possible_renames(
    old_fields: dict[str, FieldSummarySpec],
    new_fields: dict[str, FieldSummarySpec],
) -> list[dict[str, Any]]:
    removed = [old_fields[name] for name in sorted(set(old_fields) - set(new_fields))]
    added = [new_fields[name] for name in sorted(set(new_fields) - set(old_fields))]
    changes: list[dict[str, Any]] = []
    for old_field in removed:
        for new_field in added:
            if old_field.data_type != new_field.data_type:
                continue
            same_unit = old_field.unit == new_field.unit and old_field.unit is not None
            similar_name = bool(_name_tokens(old_field.name) & _name_tokens(new_field.name))
            if same_unit or similar_name:
                changes.append(
                    {
                        "type": "possible_field_rename",
                        "old_field_name": old_field.name,
                        "new_field_name": new_field.name,
                        "reason": (
                            "same data_type plus matching unit or name token overlap; "
                            "requires evidence before treating as rename"
                        ),
                    }
                )
    return changes


def _name_tokens(name: str) -> set[str]:
    return {token for token in name.lower().replace("-", "_").split("_") if len(token) >= 3}


__all__ = ["ContractDiff", "diff_test_file_contracts"]
