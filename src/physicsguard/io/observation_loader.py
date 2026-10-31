"""YAML loader for observed value files."""

from __future__ import annotations

import math
from pathlib import Path
from types import SimpleNamespace

from pydantic import ValidationError
import yaml

from physicsguard.core.units import unit_conversion
from physicsguard.schema.observation_spec import ObservedValueSpec, ObservedValuesSpec


# Admit rounded recorded factors such as 0.016667, but reject physical value disagreement.
RAW_VALUE_REL_TOL = 5e-5


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
        observed = ObservedValuesSpec.model_validate(data, context={"raw_snapshot_ingestion": True})
    except ValidationError as exc:
        raise ValueError(f"invalid ObservedValuesSpec in '{yaml_path}': {exc}") from exc

    for variable, row in observed.variables.items():
        if row.raw_value is None:
            continue
        if not row.unit or not row.unit.strip():
            raise ValueError(f"unit_not_convertible:{variable}: raw input needs a target unit")
        try:
            known = unit_conversion(row.raw_unit, row.unit)
        except ValueError:
            known = None
        if known is None and row.conversion_factor is None:
            raise ValueError(f"unit_not_convertible:{variable}: {row.raw_unit} -> {row.unit} requires an explicit conversion_factor")
        explicit = None
        if row.conversion_factor is not None or row.conversion_offset is not None:
            explicit = SimpleNamespace(
                factor=row.conversion_factor if row.conversion_factor is not None else known[0],
                offset=row.conversion_offset if row.conversion_offset is not None else known[1] if known is not None else 0.0,
            )
        try:
            factor, offset = unit_conversion(row.raw_unit, row.unit, explicit)
        except ValueError as exc:
            if str(exc) == "conversion_disagrees_with_unit_table":
                converted = row.raw_value * known[0] + known[1]
                raise _conversion_disagreement(variable, row, converted, "recorded factor/offset disagrees with the unit table") from exc
            raise ValueError(f"unit_not_convertible:{variable}: {row.raw_unit} -> {row.unit}") from exc
        converted = row.raw_value * factor + offset
        if not math.isfinite(converted):
            raise _conversion_disagreement(variable, row, converted, "converted value must be finite")
        if row.value is not None and not math.isclose(row.value, converted, rel_tol=RAW_VALUE_REL_TOL, abs_tol=0.0):
            raise _conversion_disagreement(variable, row, converted, "supplied value disagrees with the raw conversion")
        row.value = converted
        adjustment = f" + {offset:g}" if offset else ""
        row._raw_conversion = f"{row.raw_value:g} {row.raw_unit} x {factor:g}{adjustment} -> {converted:g} {row.unit}"
    return observed


def _conversion_disagreement(
    variable: str, row: ObservedValueSpec, converted: float, reason: str
) -> ValueError:
    return ValueError(
        f"observed_value_disagrees_with_conversion:{variable}: "
        f"value={row.value!r} {row.unit}; raw_value={row.raw_value:g} {row.raw_unit}; "
        f"converted={converted:g} {row.unit}; {reason}"
    )


def load_observed_series(path: str | Path) -> ObservedSeriesSpec:
    """Load a bounded pointwise observation series for validation-depth checks."""
    from physicsguard.schema.validation_depth import ObservedSeriesSpec

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
