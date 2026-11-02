"""The one conversion and reading check of observed rows, run by the snapshot and series validators.

A raw reading becomes a value in one place, convert_observed_rows, for snapshots and series points
alike. Every row, converted there or given in its model unit, is then checked the same way against
every reading its external_signal names. ObservedValuesSpec and ObservedSeriesSpec call
convert_observed_rows when they are validated, so a spec loaded from a file (io.observation_loader)
and one built in Python take the same route; the tool's refusals are ObservedConversionError.
"""

from __future__ import annotations

import math
import re
from types import SimpleNamespace
from typing import TYPE_CHECKING, NamedTuple

from physicsguard.core.units import (
    READABLE_HINT, describe_quantity, is_transducer_output, known_conversion, linking_quantity, property_conversion,
    property_link, read_unit, unit_conversion,
)

if TYPE_CHECKING:
    from physicsguard.schema.observation_spec import ObservedValueSpec, PhysicalPropertySpec


# Admit rounded recorded factors such as 0.016667, but reject physical value disagreement.
RAW_VALUE_REL_TOL = 5e-5
# A number in external_signal, not glued to a name before it (T_tank_C@70 holds no reading).
_NUMBER = re.compile(r"(?<![\w.^])([-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?)")
# Units are read from up to this many words after the number ("litres per minute").
_UNIT_WORDS = 3
# What makes a word after a number look like a unit, so the tool flags it when it cannot read it.
_MARK_CHARACTERS = "/^·⋅*⁻⁰¹²³⁴⁵⁶⁷⁸⁹"
_UNIT_MARK = re.compile(r"[/^·⋅*⁻⁰¹²³⁴⁵⁶⁷⁸⁹]|[A-Za-z]-\d+$")
_NEGATIVE_POWER = re.compile(r"[A-Za-z]+(?:\^?-\d+|⁻[⁰¹²³⁴⁵⁶⁷⁸⁹]+)")
# An external_signal that is nothing but its readings, with only these (and spaces) between them, is enforced.
WHOLE_SIGNAL_SEPARATORS = "()[],;:.="


class _Reading(NamedTuple):
    number: float
    unit: str

    def __str__(self) -> str:
        return f"{self.number:g} {self.unit}"


class ObservedConversionError(ValueError):
    """A raw reading, or a reading in external_signal, that the tool refuses while an observed spec is validated."""


def convert_observed_rows(variables: dict[str, ObservedValueSpec], properties: dict[str, PhysicalPropertySpec]) -> None:
    """Convert each raw reading once, then check every row against every reading its external_signal names.

    Called by the ObservedValuesSpec and ObservedSeriesSpec validators, so every route to a spec runs it; a
    spec built again from rows already checked checks them again, from a cleared state, with the same result.
    """
    for variable, row in variables.items():
        row._conversion_checked = None
        row._conversion_check = None
        row._signal_disagrees = False
        row._missing_property = None
        row._signal_unreadable = False
        raw_conversion = _convert_raw_row(variable, row, properties) if row.raw_value is not None else None
        _check_signal_reading(variable, row, raw_conversion, properties)


def _convert_raw_row(variable: str, row: ObservedValueSpec,
                     properties: dict[str, PhysicalPropertySpec]) -> tuple[float, float]:
    """raw_value in the model unit through the unit table (and a declared property), or a transducer calibration.

    Returns the factor and offset applied, so the signal check converts a reading of the raw unit the same way.
    """
    if not row.unit or not row.unit.strip():
        raise ObservedConversionError(f"unit_not_convertible:{variable}: raw input needs a target unit")
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


class _SignalText(NamedTuple):
    """What external_signal holds: its readings, each '<number> <unit>' whose unit the tool cannot read, and
    whether the text is nothing but its readings (with brackets, commas or '=' between them)."""

    readings: list[_Reading]
    unreadable: list[str]
    whole: bool


def _looks_like_unit(word: str) -> bool:
    """A word that starts with a letter and carries a unit mark: '/', '^', '·', '⋅', '*', a superscript, or a
    trailing negative power such as min-1."""
    word = word.strip("()[],;:.")
    return word[:1].isalpha() and _UNIT_MARK.search(word) is not None


def _continues_unit(word: str) -> bool:
    """A word that carries on the unit before it: it starts with a separator or a power, it is a symbol with a
    negative power (min^-1, min-1, min⁻¹), or it is 'per'."""
    word = word.strip("()[],;:.")
    return bool(word) and (word[0] in _MARK_CHARACTERS or _NEGATIVE_POWER.fullmatch(word) is not None
                           or word.lower() == "per")


def _signal_readings(text: str | None) -> _SignalText:
    """Every '<number> <unit>' in external_signal; none is dropped.

    A unit counts when the unit table reads it or it is a transducer output (V, mV, A, mA, ohm). A number
    followed by a word that looks like a unit (_looks_like_unit) the table cannot read, or by a unit the table
    reads only in part because the next word carries it on (_continues_unit, as in '6 L fortnight^-1'), is
    listed as unreadable instead of being read as a shorter unit.
    """
    text = text or ""
    readings: list[_Reading] = []
    unreadable: list[str] = []
    spans: list[tuple[int, int]] = []
    for match in _NUMBER.finditer(text):
        if spans and match.start() < spans[-1][1]:
            continue  # a power inside a unit already read, such as the 1 of min-1
        words = list(re.finditer(r"\S+", text[match.end():]))
        tokens = [word.group() for word in words]
        if not tokens:
            continue
        read = None
        for count in range(min(_UNIT_WORDS, len(tokens)), 0, -1):
            unit = _unit_text(tokens[:count])
            if read_unit(unit) is not None or is_transducer_output(unit):
                read = count, unit
                break
        if read is not None and not (read[0] < len(tokens) and _continues_unit(tokens[read[0]])):
            used = read[0]
            readings.append(_Reading(float(match.group(1)), read[1]))
        elif read is not None or _looks_like_unit(tokens[0]):
            used = read[0] + 1 if read is not None else 1
            unreadable.append(f"{match.group(1)} {_unit_text(tokens[:used])}")
        else:
            continue
        spans.append((match.start(), match.end() + words[used - 1].end()))
    rest, position = [], 0
    for start, stop in spans:
        rest.append(text[position:start])
        position = stop
    rest.append(text[position:])
    whole = bool(readings) and not unreadable and all(
        character.isspace() or character in WHOLE_SIGNAL_SEPARATORS for character in "".join(rest))
    return _SignalText(readings, unreadable, whole)


def _unit_text(words: list[str]) -> str:
    """The words after a number as a unit: without trailing punctuation or a closing bracket opened before it."""
    unit = " ".join(words).rstrip(",;:.")
    while unit[-1:] in (")", "]") and unit.count(unit[-1]) > unit.count("(" if unit[-1] == ")" else "["):
        unit = unit[:-1].rstrip(",;:.")
    return unit


def _reading_routes(reading: _Reading, row: ObservedValueSpec, raw_conversion: tuple[float, float] | None,
                    properties: dict[str, PhysicalPropertySpec]) -> list[tuple[float, float, str]]:
    """Each factor, offset and wording that turn a signal reading into the model unit; empty when the tool has none.

    A reading of the model unit's quantity goes through the unit table. On a row the tool converted from
    raw_value, a reading of the raw unit's quantity goes through the table to raw_unit and then through the
    row's own conversion (its declared property or transducer calibration), the same way as raw_value. A
    reading of another quantity goes through a declared property that links it to the model unit: the row's
    conversion_property, or, when the row names none, each declared property that links them.
    """
    known = known_conversion(reading.unit, row.unit)
    if known is not None:
        return [(known[0], known[1], "through the unit table")]
    if raw_conversion is not None:
        to_raw = known_conversion(reading.unit, row.raw_unit)
        if to_raw is not None:
            factor, offset = raw_conversion
            return [(to_raw[0] * factor, to_raw[1] * factor + offset,
                     f"through the unit table to {row.raw_unit}, then as raw_value")]
    names = [row.conversion_property] if row.conversion_property is not None else sorted(properties)
    routes = []
    for name in names:
        prop = properties[name]
        factor = property_link(reading.unit, row.unit, prop.value, prop.unit)
        if factor is not None:
            routes.append((factor, 0.0, f"through {name} ({prop.value:g} {prop.unit})"))
    return routes


def _missing_property_sentence(reading: _Reading, row: ObservedValueSpec, linking: str,
                               properties: dict[str, PhysicalPropertySpec]) -> str:
    """Which property the reading needs and what the file declares instead."""
    if row.conversion_property is not None:
        declared = f"the row's conversion_property {row.conversion_property} is not one"
    elif properties:
        declared = f"the file declares {', '.join(sorted(properties))} under properties, none of them a {linking} that links them"
    else:
        declared = "the file declares no property under properties"
    return (f"converting {reading} ({describe_quantity(reading.unit)}) to {row.unit} ({describe_quantity(row.unit)}) "
            f"needs a {linking}, and {declared}")


def _quantity_words(unit: str) -> str:
    return "a transducer output" if is_transducer_output(unit) else describe_quantity(unit)


def _check_signal_reading(variable: str, row: ObservedValueSpec, raw_conversion: tuple[float, float] | None,
                          properties: dict[str, PhysicalPropertySpec]) -> None:
    """Every row: compare every reading its external_signal names with the row's value, and with each other,
    all in the model unit.

    raw_conversion is the factor and offset the tool applied to raw_value, or None for a row given in its
    model unit (a conversion done outside the tool, whose recorded factor/offset is compared too). A reading
    of another quantity is converted through a declared property (see _reading_routes); a reading the tool
    cannot convert (no declared property links it, or no single property can) leaves the row unchecked with
    why. A number followed by a unit the tool cannot read is flagged signal_reading_unreadable. When the
    whole external_signal is its readings, a disagreement stops the run like a raw_value disagreement; a
    reading found inside a longer text is reported, because such a text can name other numbers.
    """
    raw = raw_conversion is not None
    recorded = [] if raw else [name for name in ("conversion_factor", "conversion_offset", "conversion_note")
                               if getattr(row, name) is not None]
    signal = _signal_readings(row.external_signal)
    origin = f"raw_value {row.raw_value:g} {row.raw_unit}" if raw else "the value"
    note = ""
    if signal.unreadable:
        row._signal_unreadable = True
        note = (f"signal_reading_unreadable:{variable}: {', '.join(f'{chr(34)}{text}{chr(34)}' for text in signal.unreadable)} "
                f"in external_signal is a number followed by a unit the tool cannot read, so it is not compared with "
                f"{origin}; write the unit as the unit table does ({READABLE_HINT})")
    tail = f"; {note}" if note else ""
    if not signal.readings:
        if recorded:
            _mark_unchecked(row, f"{', '.join(recorded)} recorded without raw_value: a conversion done outside the tool, "
                                 "which it cannot check" + tail)
        elif note:
            row._conversion_check = f"{row._conversion_check}; {note}" if raw else note
        return
    compared: list[tuple[_Reading, list[tuple[float, float, float, str]]]] = []
    unusable: list[tuple[_Reading, str | None]] = []
    for reading in signal.readings:
        routes = _reading_routes(reading, row, raw_conversion, properties)
        if routes:
            compared.append((reading, [(reading.number * factor + offset, factor, offset, how) for factor, offset, how in routes]))
        else:
            unusable.append((reading, linking_quantity(reading.unit, row.unit)))
    problems = _reading_problems(row, compared, raw, origin)
    if problems:
        sentence = (f"external_signal reads {' and '.join(_converted_words(reading, routes, row.unit) for reading, routes in compared)}, "
                    f"but {('; ' if len(compared) > 1 else ' and ').join(problems)}")
        if signal.whole:
            remedy = ("correct raw_value and raw_unit or the external_signal, so both name the same reading" if raw else
                      "correct the value or the external_signal, or give the reading as raw_value and raw_unit so the tool "
                      "converts it")
            raise ObservedConversionError(f"signal_reading_disagrees:{variable}: {sentence}; {remedy}")
        unused = f"; external_signal also reads {_unusable_words(row, unusable, properties, origin, raw)}" if unusable else ""
        _mark_unchecked(row, f"{sentence} (a reading inside a longer external_signal is reported, not enforced; write the "
                             f"reading alone{'' if raw else ', or as raw_value and raw_unit,'} to have it enforced)"
                             + unused + tail)
        row._signal_disagrees = True
        return
    agreed = " and ".join(f"{reading} {_agreeing_route(row, routes)}" for reading, routes in compared)
    if raw:
        # The raw conversion keeps its own status: an agreeing reading does not check a transducer calibration.
        check = f"{row._conversion_check}; agrees with external_signal {agreed}" if compared else row._conversion_check
    else:
        check = f"value agrees with external_signal {agreed}" if compared else ""
    if unusable:
        linking = sorted({quantity for _reading, quantity in unusable if quantity is not None})
        row._missing_property = ", ".join(linking) if linking else None
        unused = f"external_signal {'also ' if compared else ''}reads {_unusable_words(row, unusable, properties, origin, raw)}"
        _mark_unchecked(row, (f"{check}; but {unused}" if check else unused) + tail)
        return
    if not raw:
        row._conversion_checked = True
    row._conversion_check = check + tail


def _converted_words(reading: _Reading, routes: list[tuple[float, float, float, str]], unit: str) -> str:
    value, factor, offset, how = routes[0]
    adjustment = f" + {offset:g}" if offset else ""
    alternatives = "".join(f", or {other:g} {unit} {other_how}" for other, _f, _o, other_how in routes[1:])
    return f"{reading} = {value:g} {unit} {how} (x {factor:g}{adjustment}){alternatives}"


def _close(a: float, b: float) -> bool:
    return math.isclose(a, b, rel_tol=RAW_VALUE_REL_TOL, abs_tol=0.0)


def _agreeing_route(row: ObservedValueSpec, routes: list[tuple[float, float, float, str]]) -> str:
    return next(how for value, _factor, _offset, how in routes if _close(row.value, value))


def _reading_problems(row: ObservedValueSpec, compared: list[tuple[_Reading, list[tuple[float, float, float, str]]]],
                      raw: bool, origin: str) -> list[str]:
    """What disagrees: the row's value with a reading, a recorded factor/offset with every route that matches the
    value, or two readings with each other."""
    if not compared:
        return []
    problems = []
    off = [reading for reading, routes in compared if not any(_close(row.value, value) for value, *_rest in routes)]
    if off:
        text = f"{origin} converts to {row.value:g} {row.unit}" if raw else f"the value is {row.value:g} {row.unit}"
        if len(off) < len(compared):
            text += f", which {', '.join(map(str, off))} disagree{'s' if len(off) == 1 else ''} with"
        problems.append(text)
    if not raw and (row.conversion_factor is not None or row.conversion_offset is not None):
        routes = [route for _reading, readings in compared for route in readings]
        candidates = [route for route in routes if _close(row.value, route[0])] or routes
        factor_ok = lambda factor: row.conversion_factor is None or math.isclose(row.conversion_factor, factor,
                                                                                 rel_tol=RAW_VALUE_REL_TOL)
        offset_ok = lambda offset: row.conversion_offset is None or math.isclose(row.conversion_offset, offset,
                                                                                 rel_tol=RAW_VALUE_REL_TOL, abs_tol=1e-9)
        if not any(factor_ok(factor) and offset_ok(offset) for _value, factor, offset, _how in candidates):
            _value, factor, offset, _how = candidates[0]
            if not factor_ok(factor):
                problems.append(f"the recorded conversion_factor is {row.conversion_factor:g}")
            if not offset_ok(offset):
                problems.append(f"the recorded conversion_offset is {row.conversion_offset:g}")
    for position, (first, first_routes) in enumerate(compared):
        for second, second_routes in compared[position + 1:]:
            if not any(_close(a[0], b[0]) for a in first_routes for b in second_routes):
                problems.append(f"the readings disagree with each other ({first} = {first_routes[0][0]:g} {row.unit}, "
                                f"{second} = {second_routes[0][0]:g} {row.unit})")
    return problems


def _unusable_words(row: ObservedValueSpec, unusable: list[tuple[_Reading, str | None]],
                    properties: dict[str, PhysicalPropertySpec], origin: str, raw: bool) -> str:
    """Each reading the tool cannot convert to the model unit, and why it was not compared."""
    given = f" ({row.raw_value:g} {row.raw_unit} as given)" if raw else f" ({row.value:g} {row.unit} as given)"
    parts = []
    for reading, linking in unusable:
        if linking is None:
            parts.append(f"{reading} ({_quantity_words(reading.unit)}): neither the unit table nor one declared property "
                         f"turns it into {row.unit} ({describe_quantity(row.unit)}), so the tool cannot compare it with "
                         f"{origin}{given}")
        else:
            parts.append(f"{reading}: {_missing_property_sentence(reading, row, linking, properties)}; declare the {linking} "
                         f"under properties so the tool converts the reading and compares it with {origin}{given}")
    return "; and ".join(parts)


def _mark_unchecked(row: ObservedValueSpec, reason: str) -> None:
    row._conversion_checked = False
    row._conversion_check = reason


def _property_conversion(variable: str, row: ObservedValueSpec,
                         properties: dict[str, PhysicalPropertySpec]) -> tuple[float, float, str]:
    """Compose the factor from the unit table and the declared property; a recorded factor is only compared."""
    name = row.conversion_property
    if name not in properties:
        raise ObservedConversionError(f"{variable}: conversion_property {name} is not declared under properties")
    prop = properties[name]
    try:
        factor, offset = property_conversion(row.raw_unit, row.unit, prop.value, prop.unit)
    except ValueError as exc:
        raise ObservedConversionError(f"unit_not_convertible:{variable}: {row.raw_unit} -> {row.unit} through {name} ({prop.value:g} {prop.unit}): {exc}") from exc
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
        raise ObservedConversionError(
            f"unit_not_convertible:{variable}: {row.raw_unit} ({describe_quantity(row.raw_unit)}) -> {row.unit} "
            f"({describe_quantity(row.unit)}) are different quantities; declare the property that links them under "
            "properties (for example a density) and name it with conversion_property, so the tool computes the factor; "
            "a recorded conversion_factor is not checked and not used"
        )
    if known is None and not is_transducer_output(row.raw_unit):
        unreadable = row.raw_unit if source is None else row.unit
        raise ObservedConversionError(
            f"unit_not_convertible:{variable}: the tool cannot read the unit '{unreadable}', so it cannot check a conversion "
            f"from {row.raw_unit} to {row.unit} and does not apply a recorded one; write it as the unit table does "
            f"({READABLE_HINT}), or give a transducer output in V, mV, A, mA or ohm with its calibration factor"
        )
    if known is None:
        if row.conversion_factor is None:
            raise ObservedConversionError(f"unit_not_convertible:{variable}: {row.raw_unit} is a transducer output; {row.raw_unit} -> "
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
) -> ObservedConversionError:
    given = f"value={row.value!r} {row.unit}" if row.value is not None else "no value given"
    return ObservedConversionError(
        f"observed_value_disagrees_with_conversion:{variable}: "
        f"{given}; raw_value={row.raw_value:g} {row.raw_unit}; "
        f"converted={converted:g} {row.unit}; {reason}"
    )


__all__ = ["ObservedConversionError", "RAW_VALUE_REL_TOL", "WHOLE_SIGNAL_SEPARATORS", "convert_observed_rows"]
