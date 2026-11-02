"""YAML loader for observed value files.

A raw reading becomes a value in one place, convert_observed_rows, for snapshots and series
points alike; a row already given in its model unit is checked as far as the tool can check it.
"""

from __future__ import annotations

import math
from pathlib import Path
import re
from types import SimpleNamespace
from typing import Any

from pydantic import ValidationError
import yaml

from physicsguard.core.units import known_conversion, property_conversion, unit_conversion, unit_quantity
from physicsguard.schema.observation_spec import ObservedValueSpec, ObservedValuesSpec, PhysicalPropertySpec


# Admit rounded recorded factors such as 0.016667, but reject physical value disagreement.
RAW_VALUE_REL_TOL = 5e-5
# An external_signal that is exactly a number and a unit from the table, such as "6 L/min", is a reading.
_READING = re.compile(r"\s*([-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?)\s*(\S+)\s*")


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

    convert_observed_rows(observed.variables, observed.properties)
    return observed


def convert_observed_rows(variables: dict[str, ObservedValueSpec], properties: dict[str, PhysicalPropertySpec]) -> None:
    """Convert each raw reading once with the unit table (and a declared property), or check a converted row."""
    for variable, row in variables.items():
        if row.raw_value is None:
            _check_converted_row(row)
            continue
        if not row.unit or not row.unit.strip():
            raise ValueError(f"unit_not_convertible:{variable}: raw input needs a target unit")
        if row.conversion_property is not None:
            factor, offset, evidence = _property_conversion(variable, row, properties)
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
        row._conversion_check = (f"converted by the tool: {row._raw_conversion}" if checked else
                                 f"{row.raw_unit} is outside the unit table, so the recorded conversion was applied unchecked")


def _signal_reading(text: str | None) -> tuple[float, str] | None:
    """An external_signal that is exactly '<number> <unit from the table>', else None."""
    match = _READING.fullmatch(text or "")
    if match is None or unit_quantity(match.group(2)) is None:
        return None
    return float(match.group(1)), match.group(2)


def _check_converted_row(row: ObservedValueSpec) -> None:
    """A row given in its model unit: check it against a reading in external_signal, or say it is unchecked."""
    recorded = [name for name in ("conversion_factor", "conversion_offset", "conversion_note") if getattr(row, name) is not None]
    reading = _signal_reading(row.external_signal)
    if reading is not None:
        number, unit = reading
        known = known_conversion(unit, row.unit) if row.unit else None
        if known is None:
            row._conversion_checked = False
            row._conversion_check = (f"external_signal reads {number:g} {unit} ({unit_quantity(unit)}), but the value is given "
                                     f"in {row.unit or 'no unit'} without raw_value, so the tool cannot check the conversion")
            return
        converted = number * known[0] + known[1]
        factor_ok = row.conversion_factor is None or math.isclose(row.conversion_factor, known[0], rel_tol=RAW_VALUE_REL_TOL)
        offset_ok = row.conversion_offset is None or math.isclose(row.conversion_offset, known[1], rel_tol=RAW_VALUE_REL_TOL,
                                                                  abs_tol=1e-9)
        if math.isclose(row.value, converted, rel_tol=RAW_VALUE_REL_TOL, abs_tol=0.0) and factor_ok and offset_ok:
            row._conversion_checked = True
            row._conversion_check = f"value agrees with external_signal {number:g} {unit} through the unit table"
            return
        row._conversion_checked = False
        row._signal_disagrees = True
        recorded_text = "".join(f"; recorded {name} {getattr(row, name):g}" for name in ("conversion_factor", "conversion_offset")
                                if getattr(row, name) is not None)
        row._conversion_check = (f"external_signal reads {number:g} {unit} = {converted:g} {row.unit} through the unit table "
                                 f"(x {known[0]:g} + {known[1]:g}), but the value is {row.value:g} {row.unit}{recorded_text}")
        return
    if recorded:
        row._conversion_checked = False
        row._conversion_check = (f"{', '.join(recorded)} recorded without raw_value: a conversion done outside the tool, "
                                 "which it cannot check")


def _property_conversion(variable: str, row: ObservedValueSpec,
                         properties: dict[str, PhysicalPropertySpec]) -> tuple[float, float, str]:
    """Compose the factor from the unit table and the declared property; a recorded factor is only compared."""
    name = row.conversion_property
    if name not in properties:
        raise ValueError(f"{variable}: conversion_property {name} is not declared under properties")
    prop = properties[name]
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
    """Validate a series (from a file or testfile series) and convert each point's raw readings like a snapshot."""
    from physicsguard.schema.validation_depth import ObservedSeriesSpec

    series = ObservedSeriesSpec.model_validate(data, context={"raw_snapshot_ingestion": True})
    for point in series.points:
        convert_observed_rows(point.variables, series.properties)
    return series


__all__ = ["convert_observed_rows", "load_observed_series", "load_observed_values", "observed_series_from_mapping"]
