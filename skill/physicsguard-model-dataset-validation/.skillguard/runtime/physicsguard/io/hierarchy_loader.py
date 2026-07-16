"""YAML loader for hierarchical PhysicsGuard audit specs."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from physicsguard.schema.hierarchy_spec import HierarchicalAuditSpec


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
    if "system" not in data:
        raise ValueError("hierarchical audit YAML is missing required 'system' section")
    if "hierarchy" not in data:
        raise ValueError("hierarchical audit YAML is missing required 'hierarchy' section")
    try:
        return HierarchicalAuditSpec.model_validate(data)
    except ValidationError as exc:
        raise ValueError(f"invalid hierarchical audit schema in {yaml_path}: {exc}") from exc


__all__ = ["load_hierarchical_audit_spec"]
