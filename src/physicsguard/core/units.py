"""The only automatic test-data unit table (conversion occurs only at ingestion).

Each entry is (dimension, factor to base SI, offset to base SI). Temperature uses
K = degC + 273.15. Supported pairs: K/degC; W/kW/MW; m^3/s/L/s/L/min/m^3/h;
Pa/kPa/bar/MPa; rad/s/rpm; kg/s/g/s/kg/h; m/mm; s/min/h. Unicode m³ is an alias
for m^3. All other pairs require an explicit user factor and offset. Identical
unit labels need no conversion. Audit evaluation itself never converts values.
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
    'kg/s': ('mass_flow', 1., 0.), 'g/s': ('mass_flow', .001, 0.), 'kg/h': ('mass_flow', 1/3600, 0.),
    'm': ('length', 1., 0.), 'mm': ('length', .001, 0.),
    's': ('time', 1., 0.), 'min': ('time', 60., 0.), 'h': ('time', 3600., 0.),
}


def unit_conversion(source, target, explicit=None):
    """Return factor/offset or a stable finding code; never guess a dimension."""
    a = source.replace('³', '^3') if isinstance(source, str) else source
    b = target.replace('³', '^3') if isinstance(target, str) else target
    known = (1., 0.) if a == b else None
    if a in UNIT_TABLE and b in UNIT_TABLE and UNIT_TABLE[a][0] == UNIT_TABLE[b][0]:
        _, af, ao = UNIT_TABLE[a]
        _, bf, bo = UNIT_TABLE[b]
        known = (af/bf, (ao-bo)/bf)
    if explicit is not None:
        supplied = (explicit.factor, explicit.offset)
        if known is not None and not all(math.isclose(x, y, rel_tol=1e-9, abs_tol=1e-12) for x,y in zip(known, supplied)):
            raise ValueError('conversion_disagrees_with_unit_table')
        return supplied
    if known is None:
        raise ValueError('unit_not_convertible')
    return known
