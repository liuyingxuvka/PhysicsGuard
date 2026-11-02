"""The only automatic test-data unit table (conversion occurs only at ingestion).

Each entry is (quantity, factor to base SI, offset to base SI). Temperature uses
K = degC + 273.15. Supported pairs: K/degC; W/kW/MW; m^3/s/L/s/L/min/m^3/h;
Pa/kPa/bar/MPa; rad/s/rpm; kg/s/g/s/kg/min/kg/h; m/mm; s/min/h; kg/m^3/kg/L/g/cm^3.
Unicode m³ is an alias for m^3. Identical unit labels need no conversion.

A conversion between two different quantities in the table (for example L/min to
kg/s) is never taken from a recorded factor: it is computed from the table and one
declared physical property whose quantity links them (a density turns a volume
flow into a mass flow and back). Units outside the table need an explicit
factor and offset, which no table can check. Audit evaluation itself never
converts values.
"""
import math

UNIT_TABLE = {
    'K': ('temperature', 1., 0.), 'degC': ('temperature', 1., 273.15),
    'W': ('power', 1., 0.), 'kW': ('power', 1000., 0.), 'MW': ('power', 1e6, 0.),
    'm^3/s': ('volume_flow', 1., 0.), 'L/s': ('volume_flow', .001, 0.),
    'L/min': ('volume_flow', .001/60, 0.), 'm^3/h': ('volume_flow', 1/3600, 0.),
    'Pa': ('pressure', 1., 0.), 'kPa': ('pressure', 1000., 0.),
    'bar': ('pressure', 1e5, 0.), 'MPa': ('pressure', 1e6, 0.),
    'rad/s': ('angular_speed', 1., 0.), 'rpm': ('angular_speed', math.pi/30, 0.),
    'kg/s': ('mass_flow', 1., 0.), 'g/s': ('mass_flow', .001, 0.), 'kg/min': ('mass_flow', 1/60, 0.),
    'kg/h': ('mass_flow', 1/3600, 0.),
    'm': ('length', 1., 0.), 'mm': ('length', .001, 0.),
    's': ('time', 1., 0.), 'min': ('time', 60., 0.), 'h': ('time', 3600., 0.),
    'kg/m^3': ('density', 1., 0.), 'kg/L': ('density', 1000., 0.), 'g/cm^3': ('density', 1000., 0.),
}

# Exponents of kg, m, s and K for each quantity; a declared property links two
# quantities when multiplying or dividing by it turns one exponent set into the other.
QUANTITY_EXPONENTS = {
    'temperature': (0, 0, 0, 1), 'power': (1, 2, -3, 0), 'volume_flow': (0, 3, -1, 0),
    'pressure': (1, -1, -2, 0), 'angular_speed': (0, 0, -1, 0), 'mass_flow': (1, 0, -1, 0),
    'length': (0, 1, 0, 0), 'time': (0, 0, 1, 0), 'density': (1, -3, 0, 0),
}


def _label(unit):
    return unit.replace('³', '^3') if isinstance(unit, str) else unit


def unit_quantity(unit):
    """The quantity a table unit measures, or None for a unit outside the table."""
    entry = UNIT_TABLE.get(_label(unit))
    return entry[0] if entry else None


def known_conversion(source, target):
    """The table's factor/offset for identical labels or two units of one quantity, else None."""
    a, b = _label(source), _label(target)
    if a in UNIT_TABLE and b in UNIT_TABLE and UNIT_TABLE[a][0] == UNIT_TABLE[b][0]:
        _, af, ao = UNIT_TABLE[a]
        _, bf, bo = UNIT_TABLE[b]
        return (af/bf, (ao-bo)/bf)
    return (1., 0.) if a == b else None


def unit_conversion(source, target, explicit=None):
    """Return factor/offset or a stable finding code; never guess a dimension."""
    a, b = _label(source), _label(target)
    known = known_conversion(a, b)
    if known is None and a in UNIT_TABLE and b in UNIT_TABLE:
        # Two different quantities: only property_conversion may link them.
        raise ValueError('unit_not_convertible')
    if explicit is not None:
        supplied = (explicit.factor, explicit.offset)
        if known is not None and not all(math.isclose(x, y, rel_tol=1e-9, abs_tol=1e-12) for x,y in zip(known, supplied)):
            raise ValueError('conversion_disagrees_with_unit_table')
        return supplied
    if known is None:
        raise ValueError('unit_not_convertible')
    return known


def property_conversion(source, target, property_value, property_unit):
    """Factor/offset that turn source into target through one declared property (times or divided by it).

    Raises ValueError with a sentence naming why the property cannot link the two units.
    """
    a, b, p = _label(source), _label(target), _label(property_unit)
    for unit in (a, b, p):
        if unit not in UNIT_TABLE:
            raise ValueError(f'{unit} is not in the unit table')
    for unit in (a, b, p):
        if UNIT_TABLE[unit][2]:
            raise ValueError(f'{unit} has an offset from SI, so no property can scale it')
    (qa, fa, _), (qb, fb, _), (qp, fp, _) = UNIT_TABLE[a], UNIT_TABLE[b], UNIT_TABLE[p]
    ea, eb, ep = QUANTITY_EXPONENTS[qa], QUANTITY_EXPONENTS[qb], QUANTITY_EXPONENTS[qp]
    value = property_value * fp
    if tuple(x + y for x, y in zip(ea, ep)) == eb:
        return fa * value / fb, 0.0
    if tuple(x - y for x, y in zip(ea, ep)) == eb:
        return fa / value / fb, 0.0
    raise ValueError(f'a {qp} ({p}) does not turn {qa} ({a}) into {qb} ({b})')
