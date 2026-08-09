"""Single YAML/JSON loader for the canonical physical-model blueprint."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

import yaml
from pydantic import ValidationError

from physicsguard.schema.physical_model_blueprint import (
    PHYSICAL_MODEL_BLUEPRINT_SCHEMA,
    TARGET_INVENTORY_AUTHORITY_SCHEMA,
    PhysicalModelBlueprint,
    TargetInventoryAuthority,
    canonical_blueprint_json,
)


class BlueprintLoadError(ValueError):
    """Visible canonical-loader failure with a stable machine category."""

    def __init__(self, category: str, message: str) -> None:
        super().__init__(message)
        self.category = category


def load_physical_model_blueprint(path: str | Path) -> PhysicalModelBlueprint:
    """Load one blueprint whose directory is its declared local artifact root."""

    blueprint_path = Path(path)
    data = load_physical_model_blueprint_mapping(blueprint_path)
    schema_version = data.get("schema_version")
    if schema_version != PHYSICAL_MODEL_BLUEPRINT_SCHEMA:
        detected = "missing" if schema_version is None else repr(schema_version)
        raise BlueprintLoadError(
            "unsupported_schema",
            f"unsupported physical blueprint schema {detected}; expected {PHYSICAL_MODEL_BLUEPRINT_SCHEMA!r}",
        )
    try:
        return PhysicalModelBlueprint.model_validate(data)
    except ValidationError as exc:
        raise BlueprintLoadError(
            "invalid_contract",
            f"invalid PhysicalModelBlueprint in '{blueprint_path}': {exc}",
        ) from exc


def load_target_inventory_authority(path: str | Path) -> TargetInventoryAuthority:
    authority_path = Path(path)
    data = load_physical_model_blueprint_mapping(authority_path)
    schema_version = data.get("schema_version")
    if schema_version != TARGET_INVENTORY_AUTHORITY_SCHEMA:
        detected = "missing" if schema_version is None else repr(schema_version)
        raise BlueprintLoadError(
            "unsupported_authority_schema",
            f"unsupported target inventory authority schema {detected}; expected {TARGET_INVENTORY_AUTHORITY_SCHEMA!r}",
        )
    try:
        return TargetInventoryAuthority.model_validate(data)
    except ValidationError as exc:
        raise BlueprintLoadError(
            "invalid_authority_contract",
            f"invalid TargetInventoryAuthority in '{authority_path}': {exc}",
        ) from exc


def load_physical_model_blueprint_mapping(path: str | Path) -> dict[str, Any]:
    blueprint_path = Path(path)
    suffix = blueprint_path.suffix.lower()
    if suffix not in {".yaml", ".yml", ".json"}:
        raise BlueprintLoadError(
            "unsupported_format",
            f"physical blueprint must use .yaml, .yml, or .json: {blueprint_path}",
        )
    try:
        text = blueprint_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise BlueprintLoadError("read_error", f"failed to read physical blueprint '{blueprint_path}': {exc}") from exc
    try:
        data = json.loads(text) if suffix == ".json" else yaml.safe_load(text)
    except (json.JSONDecodeError, yaml.YAMLError) as exc:
        raise BlueprintLoadError("malformed_document", f"malformed {suffix[1:]} in '{blueprint_path}': {exc}") from exc
    if data is None:
        raise BlueprintLoadError("empty_document", f"physical blueprint is empty: {blueprint_path}")
    if not isinstance(data, dict):
        raise BlueprintLoadError("invalid_root", f"physical blueprint root must be a mapping: {blueprint_path}")
    return data


def physical_model_blueprint_to_mapping(blueprint: PhysicalModelBlueprint) -> dict[str, Any]:
    """Return a deterministic canonical mapping without creating an alternate format."""

    return json.loads(canonical_blueprint_json(blueprint))


def physical_model_blueprint_from_mapping(value: Mapping[str, Any]) -> PhysicalModelBlueprint:
    """Validate an already parsed canonical mapping for native adapters/tests."""

    schema_version = value.get("schema_version")
    if schema_version != PHYSICAL_MODEL_BLUEPRINT_SCHEMA:
        detected = "missing" if schema_version is None else repr(schema_version)
        raise BlueprintLoadError(
            "unsupported_schema",
            f"unsupported physical blueprint schema {detected}; expected {PHYSICAL_MODEL_BLUEPRINT_SCHEMA!r}",
        )
    try:
        return PhysicalModelBlueprint.model_validate(dict(value))
    except ValidationError as exc:
        raise BlueprintLoadError("invalid_contract", f"invalid PhysicalModelBlueprint mapping: {exc}") from exc


__all__ = [
    "BlueprintLoadError",
    "load_physical_model_blueprint",
    "load_physical_model_blueprint_mapping",
    "load_target_inventory_authority",
    "physical_model_blueprint_from_mapping",
    "physical_model_blueprint_to_mapping",
]
