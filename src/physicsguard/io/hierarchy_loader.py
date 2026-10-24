"""YAML loader for hierarchical PhysicsGuard audit specs."""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from physicsguard.schema.hierarchy_spec import HierarchicalAuditSpec
from physicsguard.schema.system_spec import SystemSpec


def _wrap_single_system(data: dict[str, Any]) -> dict[str, Any]:
    """Validate one system and describe it as a single, level-zero audit block."""
    if "system" in data:
        system = SystemSpec.model_validate(data["system"])
        wrapped = dict(data)
    else:
        system = SystemSpec.model_validate(data)
        wrapped = {"system": system}
    name = system.system_name
    root_id = name if not any(character.isspace() for character in name) else (
        "single_system_" + sha256(name.encode("utf-8")).hexdigest()[:16]
    )
    metadata = wrapped.get("metadata", {})
    if not isinstance(metadata, dict):
        raise ValueError("hierarchical audit metadata must contain a mapping")
    wrapped.update(
        audit_name=name,
        system=system,
        hierarchy={"blocks": [{"id": root_id, "name": name, "level": 0,
                               "components": [component.id for component in system.components]}]},
        metadata={**metadata, "wrapped_single_block": True},
    )
    return wrapped


def load_hierarchical_audit_spec(path: str | Path) -> HierarchicalAuditSpec:
    yaml_path = Path(path)
    if not yaml_path.exists():
        raise FileNotFoundError(f"hierarchical audit YAML file not found: {yaml_path}")
    try:
        data: Any = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ValueError(f"invalid YAML in {yaml_path}: {exc}") from exc
    if data is None:
        raise ValueError(f"hierarchical audit YAML file is empty: {yaml_path}")
    if not isinstance(data, dict):
        raise ValueError(f"hierarchical audit YAML must contain a mapping: {yaml_path}")
    try:
        if "hierarchy" not in data:
            data = _wrap_single_system(data)
        return HierarchicalAuditSpec.model_validate(data)
    except ValidationError as exc:
        raise ValueError(f"invalid hierarchical audit schema in {yaml_path}: {exc}") from exc


__all__ = ["load_hierarchical_audit_spec"]
