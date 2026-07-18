"""YAML loader for SystemSpec files."""

from __future__ import annotations

from pathlib import Path

from pydantic import ValidationError
import yaml

from physicsguard.schema.system_spec import SystemSpec


def load_system_spec(path: str | Path) -> SystemSpec:
    yaml_path = Path(path)
    try:
        text = yaml_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ValueError(f"failed to read YAML file '{yaml_path}': {exc}") from exc
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise ValueError(f"malformed YAML in '{yaml_path}': {exc}") from exc
    if data is None:
        raise ValueError(f"empty YAML file: {yaml_path}")
    if not isinstance(data, dict):
        raise ValueError(f"YAML root must be a mapping: {yaml_path}")
    try:
        return SystemSpec.model_validate(data)
    except ValidationError as exc:
        raise ValueError(f"invalid SystemSpec in '{yaml_path}': {exc}") from exc
