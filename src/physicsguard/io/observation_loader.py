"""YAML loader for observed value files."""

from __future__ import annotations

import math
from pathlib import Path
from types import SimpleNamespace

from pydantic import ValidationError
import yaml

from physicsguard.core.units import known_conversion, property_conversion, unit_conversion, unit_quantity
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
            row._conversion_checked = False if _records_a_conversion(row) else None
            continue
        if not row.unit or not row.unit.strip():
            raise ValueError(f"unit_not_convertible:{variable}: raw input needs a target unit")
        if row.conversion_property is not None:
            factor, offset, evidence = _property_conversion(variable, row, observed)
            checked = True
        else:
            factor, offset, checked = _table_or_recorded_conversion(variable, row)
            evidence = ""
        converted = row.raw_value * factor + offset
        if not math.isfinite(converted):
            raise _conversion_disagreement(variable, row, converted, "converted value must be finite")
        if row.value is not None and not math.isclose(row.value, converted, rel_tol=RAW_VALUE_REL_TOL, abs_tol=0.0):
            raise _conversion_disagreement(variable, row, converted, "supplied value disagrees with the raw conversion")
        row.value = converted
        adjustment = f" + {offset:g}" if offset else ""
        row._raw_conversion = f"{row.raw_value:g} {row.raw_unit} x {factor:g}{adjustment}{evidence} -> {converted:g} {row.unit}"
        row._conversion_checked = checked
    return observed


def _records_a_conversion(row: ObservedValueSpec) -> bool:
    """A recorded factor or offset other than the identity: the conversion happened outside the tool."""
    return (row.conversion_factor not in (None, 1.0)) or (row.conversion_offset not in (None, 0.0))


def _property_conversion(variable: str, row: ObservedValueSpec, observed: ObservedValuesSpec) -> tuple[float, float, str]:
    """Compose the factor from the unit table and the declared property; a recorded factor is only compared."""
    name = row.conversion_property
    prop = observed.properties[name]
    try:
        factor, offset = property_conversion(row.raw_unit, row.unit, prop.value, prop.unit)
    except ValueError as exc:
        raise ValueError(f"unit_not_convertible:{variable}: {row.raw_unit} -> {row.unit} through {name} ({prop.value:g} {prop.unit}): {exc}") from exc
    evidence = f" ({name} {prop.value:g} {prop.unit})"
    recorded_factor = row.conversion_factor if row.conversion_factor is not None else factor
    recorded_offset = row.conversion_offset if row.conversion_offset is not None else offset
    if not math.isclose(recorded_factor, factor, rel_tol=RAW_VALUE_REL_TOL, abs_tol=0.0) or recorded_offset != offset:
        recorded = f"{recorded_factor:g}" + (f" + {recorded_offset:g}" if recorded_offset else "")
        raise _conversion_disagreement(
            variable, row, row.raw_value * factor + offset,
            f"recorded conversion {recorded} disagrees with {factor:g} computed from {name} = {prop.value:g} {prop.unit}",
        )
    return factor, offset, evidence


def _table_or_recorded_conversion(variable: str, row: ObservedValueSpec) -> tuple[float, float, bool]:
    """The unit table's conversion (checked), or the recorded one for units the table does not know (unchecked)."""
    source, target = unit_quantity(row.raw_unit), unit_quantity(row.unit)
    if source is not None and target is not None and source != target:
        raise ValueError(
            f"unit_not_convertible:{variable}: {row.raw_unit} ({source}) -> {row.unit} ({target}) are different quantities; "
            "declare the property that links them under properties (for example a density) and name it with "
            "conversion_property, so the tool computes the factor; a recorded conversion_factor is not checked and not used"
        )
    known = known_conversion(row.raw_unit, row.unit)
    if known is None and row.conversion_factor is None:
        raise ValueError(f"unit_not_convertible:{variable}: {row.raw_unit} -> {row.unit} requires an explicit conversion_factor")
    if row.conversion_factor is None and row.conversion_offset is None:
        return known[0], known[1], True
    factor = row.conversion_factor if row.conversion_factor is not None else known[0]
    offset = row.conversion_offset if row.conversion_offset is not None else known[1] if known is not None else 0.0
    if known is None:
        return factor, offset, False
    try:
        unit_conversion(row.raw_unit, row.unit, SimpleNamespace(factor=factor, offset=offset))
    except ValueError as exc:
        raise _conversion_disagreement(variable, row, row.raw_value * known[0] + known[1],
                                       "recorded factor/offset disagrees with the unit table") from exc
    return known[0], known[1], True


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
