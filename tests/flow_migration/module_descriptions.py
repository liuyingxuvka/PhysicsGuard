"""Independent module descriptions domain facts and production contracts."""
from dataclasses import dataclass, replace
from ._audit_cases import ROOT
MUTATIONS = {'description_marks_solver_attempted': 'description_never_solves', 'description_leaves_profiler_installed': 'description_restores_the_profiler'}
CASES = ('TankVolumeRateModule', 'MappedSignalModule', 'SumModule')

@dataclass(frozen=True)
class State:
    done: bool = False
    solver_attempted: bool = False
    profiler_restored: bool = True

def expected(request, state, mutation=''):
    result = State(True, mutation == 'description_marks_solver_attempted', mutation != 'description_leaves_profiler_installed')
    return result

def description_never_solves(state, trace):
    return False if state.done and state.solver_attempted else True

def description_restores_the_profiler(state, trace):
    return False if state.done and (not state.profiler_restored) else True
RULE_NAMES = ('description_never_solves', 'description_restores_the_profiler')
RULES = (description_never_solves, description_restores_the_profiler)

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
