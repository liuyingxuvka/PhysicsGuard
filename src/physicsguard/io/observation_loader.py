"""YAML loader for observed value files.

A raw reading becomes a value in one place, convert_observed_rows, for snapshots and series
points alike. Every row, converted there or given in its model unit, is then checked the same
way against the reading its external_signal names, as far as the tool can read it.
"""

from __future__ import annotations

import math
from pathlib import Path
import re
from types import SimpleNamespace
from typing import Any, NamedTuple

from pydantic import ValidationError
import yaml

from physicsguard.core.units import (
    READABLE_HINT, describe_quantity, is_transducer_output, known_conversion, linking_quantity, property_conversion,
    read_unit, unit_conversion,
)
from physicsguard.schema.observation_spec import ObservedValueSpec, ObservedValuesSpec, PhysicalPropertySpec


# Admit rounded recorded factors such as 0.016667, but reject physical value disagreement.
RAW_VALUE_REL_TOL = 5e-5
# A number in external_signal, not glued to a name before it (T_tank_C@70 holds no reading).
_NUMBER = re.compile(r"(?<![\w.^])([-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?)")
# Units are read from up to this many words after the number ("litres per minute").
_UNIT_WORDS = 3


class _Reading(NamedTuple):
    number: float
    unit: str

    def __str__(self) -> str:
        return f"{self.number:g} {self.unit}"


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
    """Convert each raw reading once, then check every row against the reading its external_signal names."""
    for variable, row in variables.items():
        raw_conversion = _convert_raw_row(variable, row, properties) if row.raw_value is not None else None
        _check_signal_reading(variable, row, raw_conversion)


def _convert_raw_row(variable: str, row: ObservedValueSpec,
                     properties: dict[str, PhysicalPropertySpec]) -> tuple[float, float]:
    """raw_value in the model unit through the unit table (and a declared property), or a transducer calibration.

    Returns the factor and offset applied, so the signal check converts a reading of the raw unit the same way.
    """
    if not row.unit or not row.unit.strip():
        raise ValueError(f"unit_not_convertible:{variable}: raw input needs a target unit")
    if row.conversion_property is not None:
        factor, offset, evidence = _property_conversion(variable, row, properties)
        checked = True
    else:
        factor, offset, checked = _table_or_calibration(variable, row)
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
                             f"{row.raw_unit} is a transducer output, so its recorded calibration was applied unchecked")
    return factor, offset


def _signal_readings(text: str | None) -> tuple[list[_Reading], bool]:
    """Every '<number> <unit>' in external_signal, and whether the whole text is one such reading.

    A unit counts when the unit table reads it or it is a transducer output (V, mV, A, mA, ohm).
    """
    readings: list[_Reading] = []
    whole = False
    for match in _NUMBER.finditer(text or ""):
        rest = text[match.end():]
        words = rest.split()
        if not words:
            continue
        for count in range(min(_UNIT_WORDS, len(words)), 0, -1):
            unit = _unit_text(words[:count])
            if read_unit(unit) is not None or is_transducer_output(unit):
                readings.append(_Reading(float(match.group(1)), unit))
                whole = not text[:match.start()].strip() and unit == " ".join(words)
                break
    return readings, whole and len(readings) == 1


def _unit_text(words: list[str]) -> str:
    """The words after a number as a unit: without trailing punctuation or a closing bracket opened before it."""
    unit = " ".join(words).rstrip(",;:.")
    while unit[-1:] in (")", "]") and unit.count(unit[-1]) > unit.count("(" if unit[-1] == ")" else "["):
        unit = unit[:-1].rstrip(",;:.")
    return unit


def _reading_route(reading: _Reading, row: ObservedValueSpec,
                   raw_conversion: tuple[float, float] | None) -> tuple[float, float, str] | None:
    """Factor, offset and wording that turn a signal reading into the model unit, or None when the tool has none.

    A reading of the model unit's quantity goes through the unit table. On a row the tool converted from
    raw_value, a reading of the raw unit's quantity goes through the table to raw_unit and then through the
    row's own conversion (its declared property or transducer calibration), the same way as raw_value.
    """
    known = known_conversion(reading.unit, row.unit)
    if known is not None:
        return known[0], known[1], "through the unit table"
    if raw_conversion is not None:
        to_raw = known_conversion(reading.unit, row.raw_unit)
        if to_raw is not None:
            factor, offset = raw_conversion
            return (to_raw[0] * factor, to_raw[1] * factor + offset,
                    f"through the unit table to {row.raw_unit}, then as raw_value")
    return None


def _check_signal_reading(variable: str, row: ObservedValueSpec, raw_conversion: tuple[float, float] | None) -> None:
    """Every row: compare the reading its external_signal names with the row's value, both in the model unit.

    raw_conversion is the factor and offset the tool applied to raw_value, or None for a row given in its
    model unit (a conversion done outside the tool, whose recorded factor/offset is compared too). When the
    whole external_signal is the reading, a disagreement stops the run like a raw_value disagreement; a
    reading found inside a longer text is reported, because such a text can name other numbers. A reading
    of another quantity that the tool cannot convert, or several readings, leave the row unchecked.
    """
    raw = raw_conversion is not None
    recorded = [] if raw else [name for name in ("conversion_factor", "conversion_offset", "conversion_note")
                               if getattr(row, name) is not None]
    readings, whole = _signal_readings(row.external_signal)
    about = [reading for reading in readings
             if _reading_route(reading, row, raw_conversion) is not None or linking_quantity(reading.unit, row.unit)]
    if not about:
        if recorded:
            _mark_unchecked(row, f"{', '.join(recorded)} recorded without raw_value: a conversion done outside the tool, "
                                 "which it cannot check")
        return
    origin = f"raw_value {row.raw_value:g} {row.raw_unit}" if raw else "the value"
    if len(about) > 1:
        _mark_unchecked(row, f"external_signal names {len(about)} readings ({', '.join(map(str, about))}); the tool "
                             f"cannot tell which one {origin} came from, so it cannot check the conversion")
        return
    reading = about[0]
    route = _reading_route(reading, row, raw_conversion)
    if route is None:
        linking = linking_quantity(reading.unit, row.unit)
        if raw:
            _mark_unchecked(row, f"external_signal reads {reading} ({describe_quantity(reading.unit)}), but raw_unit is "
                                 f"{row.raw_unit} ({describe_quantity(row.raw_unit)}), so {origin} is not that reading and "
                                 f"the tool cannot check it; give the reading itself as raw_value and raw_unit, with the "
                                 f"{linking} that links it to {row.unit} declared and named as conversion_property")
        else:
            _mark_unchecked(row, f"external_signal reads {reading} ({describe_quantity(reading.unit)}), but the value is "
                                 f"given in {row.unit} ({describe_quantity(row.unit)}) without raw_value, so the tool cannot "
                                 f"check the conversion; a {linking} links them")
        return
    factor, offset, how = route
    converted = reading.number * factor + offset
    problems = []
    if not math.isclose(row.value, converted, rel_tol=RAW_VALUE_REL_TOL, abs_tol=0.0):
        problems.append(f"{origin} converts to {row.value:g} {row.unit}" if raw else f"the value is {row.value:g} {row.unit}")
    if row.conversion_factor is not None and not raw and not math.isclose(row.conversion_factor, factor,
                                                                           rel_tol=RAW_VALUE_REL_TOL):
        problems.append(f"the recorded conversion_factor is {row.conversion_factor:g}")
    if row.conversion_offset is not None and not raw and not math.isclose(row.conversion_offset, offset,
                                                                           rel_tol=RAW_VALUE_REL_TOL, abs_tol=1e-9):
        problems.append(f"the recorded conversion_offset is {row.conversion_offset:g}")
    if not problems:
        if raw:
            # The raw conversion keeps its own status: an agreeing reading does not check a transducer calibration.
            row._conversion_check += f"; agrees with external_signal {reading}"
        else:
            row._conversion_checked = True
            row._conversion_check = f"value agrees with external_signal {reading} through the unit table"
        return
    adjustment = f" + {offset:g}" if offset else ""
    sentence = (f"external_signal reads {reading} = {converted:g} {row.unit} {how} "
                f"(x {factor:g}{adjustment}), but {' and '.join(problems)}")
    if whole:
        remedy = ("correct raw_value and raw_unit or the external_signal, so both name the same reading" if raw else
                  "correct the value or the external_signal, or give the reading as raw_value and raw_unit so the tool "
                  "converts it")
        raise ValueError(f"signal_reading_disagrees:{variable}: {sentence}; {remedy}")
    _mark_unchecked(row, f"{sentence} (a reading inside a longer external_signal is reported, not enforced; write the "
                         f"reading alone{'' if raw else ', or as raw_value and raw_unit,'} to have it enforced)")
    row._signal_disagrees = True


def _mark_unchecked(row: ObservedValueSpec, reason: str) -> None:
    row._conversion_checked = False
    row._conversion_check = reason


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


def _table_or_calibration(variable: str, row: ObservedValueSpec) -> tuple[float, float, bool]:
    """The unit table's conversion (checked), or a transducer output's recorded calibration (unchecked); else refused."""
    source, target = read_unit(row.raw_unit), read_unit(row.unit)
    known = known_conversion(row.raw_unit, row.unit)
    if known is None and source is not None and target is not None:
        raise ValueError(
            f"unit_not_convertible:{variable}: {row.raw_unit} ({describe_quantity(row.raw_unit)}) -> {row.unit} "
            f"({describe_quantity(row.unit)}) are different quantities; declare the property that links them under "
            "properties (for example a density) and name it with conversion_property, so the tool computes the factor; "
            "a recorded conversion_factor is not checked and not used"
        )
    if known is None and not is_transducer_output(row.raw_unit):
        unreadable = row.raw_unit if source is None else row.unit
        raise ValueError(
            f"unit_not_convertible:{variable}: the tool cannot read the unit '{unreadable}', so it cannot check a conversion "
            f"from {row.raw_unit} to {row.unit} and does not apply a recorded one; write it as the unit table does "
            f"({READABLE_HINT}), or give a transducer output in V, mV, A, mA or ohm with its calibration factor"
        )
    if known is None:
        if row.conversion_factor is None:
            raise ValueError(f"unit_not_convertible:{variable}: {row.raw_unit} is a transducer output; {row.raw_unit} -> "
                             f"{row.unit} needs its calibration as conversion_factor (and conversion_offset)")
        return row.conversion_factor, row.conversion_offset or 0.0, False
    if row.conversion_factor is None and row.conversion_offset is None:
        return known[0], known[1], True
    factor = row.conversion_factor if row.conversion_factor is not None else known[0]
    offset = row.conversion_offset if row.conversion_offset is not None else known[1]
    try:
        unit_conversion(row.raw_unit, row.unit, SimpleNamespace(factor=factor, offset=offset))
    except ValueError as exc:
        raise _conversion_disagreement(variable, row, row.raw_value * known[0] + known[1],
                                       "recorded factor/offset disagrees with the unit table") from exc
    return known[0], known[1], True


def _conversion_disagreement(
    variable: str, row: ObservedValueSpec, converted: float, reason: str
) -> ValueError:
    given = f"value={row.value!r} {row.unit}" if row.value is not None else "no value given"
    return ValueError(
        f"observed_value_disagrees_with_conversion:{variable}: "
        f"{given}; raw_value={row.raw_value:g} {row.raw_unit}; "
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
