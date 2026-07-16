"""YAML loader for observed value files."""

from __future__ import annotations

from pathlib import Path

from pydantic import ValidationError
import yaml

from physicsguard.schema.observation_spec import ObservedValuesSpec
from physicsguard.schema.validation_depth import ObservedSeriesSpec


def load_observed_values(path: str | Path) -> ObservedValuesSpec:
    yaml_path = Path(path)
    try:
        text = yaml_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ValueError(f"failed to read observed values file '{yaml_path}': {exc}") from exc
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise ValueError(f"malformed YAML in '{yaml_path}': {exc}") from exc
    if data is None:
        raise ValueError(f"empty observed values YAML file: {yaml_path}")
    if not isinstance(data, dict):
        raise ValueError(f"observed values YAML root must be a mapping: {yaml_path}")
    if "variables" not in data:
        raise ValueError(f"observed values YAML missing variables: {yaml_path}")
    try:
        return ObservedValuesSpec.model_validate(data)
    except ValidationError as exc:
        raise ValueError(f"invalid ObservedValuesSpec in '{yaml_path}': {exc}") from exc


def load_observed_series(path: str | Path) -> ObservedSeriesSpec:
    """Load a bounded pointwise observation series for validation-depth checks."""

    yaml_path = Path(path)
    try:
        text = yaml_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ValueError(f"failed to read observed series file '{yaml_path}': {exc}") from exc
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise ValueError(f"malformed YAML in '{yaml_path}': {exc}") from exc
    if data is None:
        raise ValueError(f"empty observed series YAML file: {yaml_path}")
    if not isinstance(data, dict):
        raise ValueError(f"observed series YAML root must be a mapping: {yaml_path}")
    try:
        return ObservedSeriesSpec.model_validate(data)
    except ValidationError as exc:
        raise ValueError(f"invalid ObservedSeriesSpec in '{yaml_path}': {exc}") from exc


__all__ = ["load_observed_series", "load_observed_values"]
