"""The only automatic test-data unit table (conversion occurs only at ingestion).

The table is a list of symbols, each with its exponents of kg, m, s, K and rad and its
factor to SI. read_unit reads a unit written with them, joined by '/' or '*' (also '·', '⋅',
or '.' between two symbols) with '^n' powers (kg/s, L/min, m^3/h, kg/m^3, g/cm^3), in the
spellings listed in SPELLINGS (l or litre for L, sec for s, minute for min, hr for h, m3 for
m^3, 'per', 'a' or 'an' between words for '/') and the shorthands in SHORTHANDS (rpm, LPM),
and computes its quantity, factor and offset. A power can be written min-1 or with
superscripts (min⁻¹), a space joins two symbols only when the second carries a power
(L min^-1, kg m^-3; 'L min' is not read), and a unit inside one pair of brackets, (L/min) or
[L/min], is the unit itself.
Temperature uses K = degC + 273.15 (written degC, °C, deg C or C) and degF; a unit with
an offset stands alone. Two units of one quantity convert through the table.

A conversion between two different quantities (for example L/min to kg/s) is never taken from a
recorded factor: it is computed from the table and one declared physical property whose quantity
links them (a density turns a volume flow into a mass flow and back). A unit the tool cannot read
is refused, so a spelling it does not know cannot carry a factor past the check; the one
exception is a transducer output (TRANSDUCER_OUTPUTS: V, mV, A, mA, ohm), whose calibration
factor no table can know: it is applied and reported as unchecked. Identical unit labels need
no conversion. Audit evaluation itself never converts values.
"""
from __future__ import annotations

import math
import re
from typing import NamedTuple

# Symbol: (exponents of kg, m, s, K, rad; factor to SI).
SYMBOLS = {
    'one': ((0, 0, 0, 0, 0), 1.0),
    'kg': ((1, 0, 0, 0, 0), 1.0), 'g': ((1, 0, 0, 0, 0), 1e-3),
    't': ((1, 0, 0, 0, 0), 1000.0),
    'm': ((0, 1, 0, 0, 0), 1.0), 'mm': ((0, 1, 0, 0, 0), 1e-3), 'cm': ((0, 1, 0, 0, 0), 1e-2),
    'dm': ((0, 1, 0, 0, 0), 1e-1), 'km': ((0, 1, 0, 0, 0), 1e3),
    'L': ((0, 3, 0, 0, 0), 1e-3), 'mL': ((0, 3, 0, 0, 0), 1e-6),
    'Ml': ((0, 3, 0, 0, 0), 1e3), 'ML': ((0, 3, 0, 0, 0), 1e3),
    's': ((0, 0, 1, 0, 0), 1.0), 'min': ((0, 0, 1, 0, 0), 60.0), 'h': ((0, 0, 1, 0, 0), 3600.0),
    'd': ((0, 0, 1, 0, 0), 86400.0),
    'W': ((1, 2, -3, 0, 0), 1.0), 'kW': ((1, 2, -3, 0, 0), 1e3), 'MW': ((1, 2, -3, 0, 0), 1e6),
    'J': ((1, 2, -2, 0, 0), 1.0), 'kJ': ((1, 2, -2, 0, 0), 1e3), 'MJ': ((1, 2, -2, 0, 0), 1e6),
    'Wh': ((1, 2, -2, 0, 0), 3600.0), 'kWh': ((1, 2, -2, 0, 0), 3.6e6),
    'MWh': ((1, 2, -2, 0, 0), 3.6e9), 'GWh': ((1, 2, -2, 0, 0), 3.6e12),
    'Pa': ((1, -1, -2, 0, 0), 1.0), 'kPa': ((1, -1, -2, 0, 0), 1e3), 'MPa': ((1, -1, -2, 0, 0), 1e6),
    'bar': ((1, -1, -2, 0, 0), 1e5),
    'K': ((0, 0, 0, 1, 0), 1.0),
    'rad': ((0, 0, 0, 0, 1), 1.0), 'rev': ((0, 0, 0, 0, 1), 2 * math.pi),
}
# Other spellings of a symbol.
SPELLINGS = {
    'kilogram': 'kg', 'kilograms': 'kg', 'gram': 'g', 'grams': 'g',
    'tonne': 't', 'tonnes': 't', 'kilometre': 'km', 'kilometres': 'km', 'kilometer': 'km', 'kilometers': 'km',
    'kilowatt': 'kW', 'kilowatts': 'kW', 'metre': 'm', 'metres': 'm', 'meter': 'm', 'meters': 'm',
    'joule': 'J', 'joules': 'J', 'kilojoule': 'kJ', 'kilojoules': 'kJ', 'megajoule': 'MJ', 'megajoules': 'MJ',
    'megalitre': 'ML', 'megalitres': 'ML', 'megaliter': 'ML', 'megaliters': 'ML',
    'l': 'L', 'liter': 'L', 'litre': 'L', 'liters': 'L', 'litres': 'L', 'ml': 'mL',
    'sec': 's', 'secs': 's', 'second': 's', 'seconds': 's',
    'mins': 'min', 'minute': 'min', 'minutes': 'min',
    'hr': 'h', 'hrs': 'h', 'hour': 'h', 'hours': 'h',
    'day': 'd', 'days': 'd',
    'kelvin': 'K', 'watt': 'W', 'watts': 'W',
}
# Natural compound energy names are spellings of the same symbols, including in a quotient.
SPELLINGS.update({name + joiner + suffix: symbol
                  for name, symbol in [('watt', 'Wh'), ('kilowatt', 'kWh'), ('megawatt', 'MWh'), ('gigawatt', 'GWh')]
                  for joiner in ('-', ' ') for suffix in ('hour', 'hours')})
# Whole units written as one word.
SHORTHANDS = {'rpm': 'rev/min', 'RPM': 'rev/min', 'LPM': 'L/min', 'lpm': 'L/min'}
# Units with an offset from SI: (factor, offset) to K. They stand alone, never inside a compound unit.
OFFSET_UNITS = {
    'degC': (1.0, 273.15), '°C': (1.0, 273.15), 'ºC': (1.0, 273.15), 'C': (1.0, 273.15),
    'celsius': (1.0, 273.15), 'Celsius': (1.0, 273.15),
    'degF': (5 / 9, 459.67 * 5 / 9), '°F': (5 / 9, 459.67 * 5 / 9), 'ºF': (5 / 9, 459.67 * 5 / 9),
}
# Electrical outputs of a transducer: their calibration to a physical quantity is recorded, never computed.
TRANSDUCER_OUTPUTS = ('V', 'mV', 'A', 'mA', 'ohm')

# Exponents of kg, m, s, K and rad for each named quantity; a declared property links two
# quantities when multiplying or dividing by it turns one exponent set into the other.
QUANTITY_EXPONENTS = {
    'temperature': (0, 0, 0, 1, 0), 'power': (1, 2, -3, 0, 0), 'volume_flow': (0, 3, -1, 0, 0),
    'pressure': (1, -1, -2, 0, 0), 'angular_speed': (0, 0, -1, 0, 1), 'mass_flow': (1, 0, -1, 0, 0),
    'length': (0, 1, 0, 0, 0), 'time': (0, 0, 1, 0, 0), 'density': (1, -3, 0, 0, 0),
}
_QUANTITY_NAMES = {exponents: name for name, exponents in QUANTITY_EXPONENTS.items()}
_BASE_NAMES = ('kg', 'm', 's', 'K', 'rad')

# The spellings the refusal messages name, so the reader can rewrite a unit the tool did not read.
READABLE_HINT = ("kg/s, g/s, kg/min, kg/h, L/s, L/min (l/min, LPM, litres per minute, L min^-1), m^3/s, m^3/h, W, kW, MW, "
                 "Pa, kPa, MPa, bar, degC (°C, C), degF, K, rad/s, rpm, m, mm, s, min, h, kg/m^3, kg/L, g/cm^3")


class Unit(NamedTuple):
    """A unit the tool has read: exponents of kg, m, s, K, rad; factor and offset to SI."""

    exponents: tuple[int, ...]
    factor: float
    offset: float = 0.0


_TERM = re.compile(r"([A-Za-z]+)(?:\^?([-+]?\d+))?")
# A symbol with an explicit power (min^-1, min-1, m3): only such a term may follow another after a space.
_POWERED_TERM = re.compile(r"[A-Za-z]+\^?[-+]?\d+")
_SUPERSCRIPT_POWER = re.compile(r"[⁻⁺]?[⁰¹²³⁴⁵⁶⁷⁸⁹]+")
_SUPERSCRIPT_DIGITS = str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹⁻⁺", "0123456789-+")
_BRACKETED = re.compile(r"\((.*)\)|\[(.*)\]")


def _label(unit):
    """The unit as written, stripped, with superscript powers as ^n and one pair of enclosing brackets removed."""
    if not isinstance(unit, str):
        return unit
    label = _SUPERSCRIPT_POWER.sub(lambda power: "^" + power.group().translate(_SUPERSCRIPT_DIGITS), unit.strip())
    bracketed = _BRACKETED.fullmatch(label)
    return (bracketed.group(1) if bracketed.group(1) is not None else bracketed.group(2)).strip() if bracketed else label


def read_unit(unit) -> Unit | None:
    """The unit's exponents, factor and offset computed from the table, or None for a unit the tool cannot read."""
    label = _label(unit)
    if label in ('1', 'dimensionless'):
        return Unit((0, 0, 0, 0, 0), 1.0)
    if label in ('%', 'percent'):
        return Unit((0, 0, 0, 0, 0), 0.01)
    label = {'degrees Celsius': 'degC', 'degree Celsius': 'degC',
             'degrees Fahrenheit': 'degF', 'degree Fahrenheit': 'degF'}.get(label, label)
    if not label:
        return None
    label = re.sub(r"^deg\s+([CF])$", r"deg\1", label)
    if label in OFFSET_UNITS:
        factor, offset = OFFSET_UNITS[label]
        return Unit(QUANTITY_EXPONENTS['temperature'], factor, offset)
    label = SHORTHANDS.get(label, label)
    for spelling, symbol in SPELLINGS.items():
        if not spelling.isalpha():
            label = re.sub(r'(?<!\w)' + re.escape(spelling) + r'(?!\w)', symbol, label)
    label = re.sub(r'\b(square|cubic)\s+([A-Za-z]+)\b',
                   lambda m: m[2] + ('^2' if m[1] == 'square' else '^3'), label)
    label = re.sub(r"\s+(?:per|an?)\s+", "/", label)
    label = re.sub(r"(?<=[A-Za-z0-9])\.(?=[A-Za-z])", "*", label)
    label = re.sub(r"\s*([/*·⋅])\s*", r"\1", label)
    if re.search(r"\s", label):
        terms = label.split()
        if not all(_POWERED_TERM.fullmatch(term) for term in terms[1:]):
            return None
        label = "*".join(terms)
    exponents, factor, power_sign = [0] * len(_BASE_NAMES), 1.0, 1
    for position, part in enumerate(re.split(r"([/*·⋅])", label)):
        if position % 2:
            power_sign = -1 if part == '/' else 1
            continue
        match = _TERM.fullmatch(part)
        if match is None:
            return None
        name = SPELLINGS.get(match.group(1), match.group(1))
        if name not in SYMBOLS:
            return None
        power = int(match.group(2) or 1) * power_sign
        dims, scale = SYMBOLS[name]
        exponents = [have + dim * power for have, dim in zip(exponents, dims)]
        factor *= scale ** power
    return Unit(tuple(exponents), factor, 0.0)


def is_transducer_output(unit) -> bool:
    return _label(unit) in TRANSDUCER_OUTPUTS


def unit_quantity(unit):
    """The named quantity a unit measures, or None for a unit the tool cannot read or a quantity without a name."""
    read = read_unit(unit)
    return _QUANTITY_NAMES.get(read.exponents) if read else None


def describe_quantity(unit) -> str:
    """The quantity's name, or its base-unit exponents when it has none, or 'unreadable'."""
    read = read_unit(unit)
    if read is None:
        return 'unreadable'
    name = _QUANTITY_NAMES.get(read.exponents)
    if name:
        return name
    terms = [base + ('' if power == 1 else f'^{power}') for base, power in zip(_BASE_NAMES, read.exponents) if power]
    return ' '.join(terms) or 'dimensionless'


def linking_quantity(source, target) -> str | None:
    """The named quantity that multiplies or divides source into target (a density links volume and mass flow)."""
    a, b = read_unit(source), read_unit(target)
    if a is None or b is None or a.exponents == b.exponents:
        return None
    difference = tuple(y - x for x, y in zip(a.exponents, b.exponents))
    return _QUANTITY_NAMES.get(difference) or _QUANTITY_NAMES.get(tuple(-x for x in difference))


# The densest material at ordinary conditions is osmium, 22.59 g/cm^3 (22,590 kg/m^3).
DENSEST_MATERIAL_KG_M3 = 22590.0


def implausible_property(value, unit):
    """A sentence when a declared property is physically impossible at ordinary conditions, else None."""
    read = read_unit(unit)
    if read and read.exponents == QUANTITY_EXPONENTS['density'] and value * read.factor > DENSEST_MATERIAL_KG_M3:
        return (f'{value:g} {unit} is {value * read.factor:g} kg/m^3, denser than any material at ordinary '
                f'conditions (osmium, {DENSEST_MATERIAL_KG_M3:g} kg/m^3)')
    return None


def known_conversion(source, target):
    """The table's factor/offset for identical labels or two readable units of one quantity, else None."""
    if _label(source) == _label(target):
        return (1., 0.)
    a, b = read_unit(source), read_unit(target)
    if a is None or b is None or a.exponents != b.exponents:
        return None
    return (a.factor / b.factor, (a.offset - b.offset) / b.factor)


def unit_conversion(source, target, explicit=None):
    """Return factor/offset or a stable finding code; never guess a dimension or trust a factor the table can check.

    Raises ValueError('unit_not_convertible') for two readable units of different quantities (only
    property_conversion links them), for a unit the tool cannot read that is not a transducer output,
    and for a transducer output without its calibration; ValueError('conversion_disagrees_with_unit_table')
    when a recorded factor/offset disagrees with the table.
    """
    known = known_conversion(source, target)
    if known is None:
        if explicit is None or not is_transducer_output(source):
            raise ValueError('unit_not_convertible')
        # A transducer calibration: the tool applies it but cannot check it.
        return (explicit.factor, explicit.offset)
    if explicit is not None:
        supplied = (explicit.factor, explicit.offset)
        if not all(math.isclose(x, y, rel_tol=1e-9, abs_tol=1e-12) for x, y in zip(known, supplied)):
            raise ValueError('conversion_disagrees_with_unit_table')
    return known


def property_link(source, target, property_value, property_unit):
    """The factor that turns source into target through the property (times or divided by it), or None when one of
    the three units is unreadable or has an offset, or the property's quantity does not link the two."""
    a, b, p = read_unit(source), read_unit(target), read_unit(property_unit)
    if a is None or b is None or p is None or a.offset or b.offset or p.offset:
        return None
    value = property_value * p.factor
    if tuple(x + y for x, y in zip(a.exponents, p.exponents)) == b.exponents:
        return a.factor * value / b.factor
    if tuple(x - y for x, y in zip(a.exponents, p.exponents)) == b.exponents:
        return a.factor / value / b.factor
    return None


def property_conversion(source, target, property_value, property_unit):
    """Factor/offset that turn source into target through one declared property (times or divided by it).

    Raises ValueError with a sentence naming why the property cannot link the two units.
    """
    for unit in (source, target, property_unit):
        read = read_unit(unit)
        if read is None:
            raise ValueError(f'{unit} is not a unit the tool can read')
        if read.offset:
            raise ValueError(f'{unit} has an offset from SI, so no property can scale it')
    factor = property_link(source, target, property_value, property_unit)
    if factor is None:
        raise ValueError(f'a {describe_quantity(property_unit)} ({property_unit}) does not turn '
                         f'{describe_quantity(source)} ({source}) into {describe_quantity(target)} ({target})')
    return factor, 0.0


def unit_error_hypotheses() -> tuple[tuple[float, float], ...]:
    """Finite diagnostic transformations, computed from the sole unit table.

    These are counterfactual scale/offset trials, not a conversion or an inference
    of the observation's actual source unit. Labels keep the original diagnostic
    order; the numeric factors and temperature offsets belong only to this table.
    """
    pairs = (("W", "kW"), ("kW", "W"), ("mL", "m^3"), ("m^3", "mL"),
             ("h", "s"), ("s", "h"), ("min", "s"), ("s", "min"),
             ("Pa", "bar"), ("bar", "Pa"), ("rad/s", "rpm"), ("rpm", "rad/s"),
             ("degC", "K"), ("K", "degC"))
    transformations = tuple(known_conversion(source, target) for source, target in pairs)
    assert all(value is not None for value in transformations), "diagnostic unit pairs must be readable"
    return transformations
