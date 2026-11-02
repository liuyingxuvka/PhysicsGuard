"""YAML loader for observed value and series files.

The conversion of raw readings and the check of every row against its external_signal run in the
snapshot and series validators (physicsguard.schema.observed_conversion), so a file loaded here and a
spec built in Python take the same route; the loaders only unwrap the tool's refusal from pydantic's
ValidationError so its code leads the message.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import ValidationError
import yaml

from physicsguard.schema.observation_spec import ObservedValuesSpec
from physicsguard.schema.observed_conversion import ObservedConversionError, convert_observed_rows


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
        return ObservedValuesSpec.model_validate(data, context={"raw_snapshot_ingestion": True})
    except ValidationError as exc:
        refusal = _conversion_refusal(exc)
        if refusal is not None:
            raise refusal from exc
        raise ValueError(f"invalid ObservedValuesSpec in '{yaml_path}': {exc}") from exc


def _conversion_refusal(exc: ValidationError) -> ObservedConversionError | None:
    """The tool's own refusal inside a ValidationError (raised by convert_observed_rows in a spec validator)."""
    for detail in exc.errors():
        if "ctx" in detail and isinstance(detail["ctx"].get("error"), ObservedConversionError):
            return detail["ctx"]["error"]
    return None


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
        return observed_series_from_mapping(data)
    except ValidationError as exc:
        raise ValueError(f"invalid ObservedSeriesSpec in '{yaml_path}': {exc}") from exc


def observed_series_from_mapping(data: dict[str, Any]) -> ObservedSeriesSpec:
    """Validate a series (from a file or testfile series); its validator converts and checks each point like a
    snapshot, and the tool's refusal comes out unwrapped."""
    from physicsguard.schema.validation_depth import ObservedSeriesSpec

    try:
        return ObservedSeriesSpec.model_validate(data, context={"raw_snapshot_ingestion": True})
    except ValidationError as exc:
        refusal = _conversion_refusal(exc)
        if refusal is not None:
            raise refusal from exc
        raise


__all__ = ["ObservedConversionError", "convert_observed_rows", "load_observed_series", "load_observed_values",
           "observed_series_from_mapping"]
