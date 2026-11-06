"""One shared decision worth retaining across sessions, with its production home."""
from flowguard.intent import row, rule


@rule('EXTRAPOLATION', decides='allowed_map_modes', fields={
    'mode': ('error', 'hold', 'linear', 'unknown'), 'linear': bool},
    source='doc docs/development/flow-contracts.md "Maps accept error or hold; only LookupTable1D explicitly accepts linear."')
def EXTRAPOLATION(mode, linear):
    if mode in ('error', 'hold'):
        return True
    return linear and mode == 'linear'


EXTRAPOLATION.rows(
    row(mode='error', linear=False, expect=True, why='ordinary modules refuse out-of-range data'),
    row(mode='hold', linear=False, expect=True, why='holding the boundary is an explicit supported mode'),
    row(mode='linear', linear=False, expect=False, why='component maps must not gain implicit extrapolation'),
    row(mode='linear', linear=True, expect=True, why='LookupTable1D deliberately owns a linear continuation'),
    row(mode='unknown', linear=True, expect=False, why='the extra mode is not a general escape hatch'))


@EXTRAPOLATION.home('physicsguard.modules.components._common:extrapolation_allowed')
def map_modes(c, fn):
    return fn(c.mode, linear=c.linear)
