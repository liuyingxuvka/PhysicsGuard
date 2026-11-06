"""Preserved direct module descriptions contracts."""
from ._audit_cases import ROOT
CASES = ('TankVolumeRateModule', 'MappedSignalModule', 'SumModule')


def assert_native_contract():
    mismatches = []
    import sys
    from physicsguard.modules.registry import describe_module_type
    for name in CASES:
        previous = sys.getprofile()
        parameters = {'input_variables': ['pump.P_W'], 'output_variable': 'meter.sum_W'} if name == 'SumModule' else None
        report = describe_module_type(name, parameters=parameters)
        if report['description_context']['solver_attempted'] is not False:
            mismatches.append(name + ': description attempted a solve')
        if sys.getprofile() is not previous:
            mismatches.append(name + ': description changed the profiler')
    assert not mismatches, mismatches

