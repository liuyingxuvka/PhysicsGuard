"""module_descriptions: native component contract with fresh scratch conformance."""
from dataclasses import dataclass,replace
from flowguard import FunctionResult,Invariant,InvariantResult,Workflow
from flowguard.explorer import Explorer
from _core_fixture import ROOT,ReplayReport
MODEL_ID='module_descriptions'
PARENT='modules'
IMPLEMENTED_BY={'Describe': 'src/physicsguard/modules/registry.py:describe_module_type'}
TESTED_BY={'description_never_solves': ['tests/test_cli.py:test_every_registered_module_has_a_native_readable_description'], 'description_restores_the_profiler': ['tests/test_cli.py:test_module_description_restores_existing_profiler_on_success_and_failure']}
MUTATIONS={'description_marks_solver_attempted': 'description_never_solves', 'description_leaves_profiler_installed': 'description_restores_the_profiler'}
CASES=('TankVolumeRateModule','MappedSignalModule','SumModule')

@dataclass(frozen=True)
class State:
    done:bool=False
    solver_attempted:bool=False
    profiler_restored:bool=True

class Check:
    name='Check'
    reads=()
    writes=('done', 'solver_attempted', 'profiler_restored')
    def __init__(self,defect=''):self.defect=defect
    def apply(self,request,state):
        result=State(True,self.defect=='description_marks_solver_attempted',self.defect!='description_leaves_profiler_installed')
        yield FunctionResult(result,result,label=str(request))

def description_never_solves(state,trace):
    return InvariantResult.fail('Description attempted a solve') if state.done and state.solver_attempted else InvariantResult.pass_()

def description_restores_the_profiler(state,trace):
    return InvariantResult.fail('Description left its profiler installed') if state.done and not state.profiler_restored else InvariantResult.pass_()

INVARIANTS=(
    Invariant('description_never_solves','description never solves',description_never_solves),
    Invariant('description_restores_the_profiler','description restores the profiler',description_restores_the_profiler),
)

def make(defect='',names=None):
    return Explorer(Workflow((Check(defect),)),(State(),),CASES,
                    tuple(rule for rule in INVARIANTS if names is None or rule.name in names),max_sequence_length=1,progress_steps=0)
def build_explorer():return make()
def broken_variants():return {name:make(name,{rule}) for name,rule in MUTATIONS.items()}

def conformance():
    mismatches=[]
    import sys
    from physicsguard.modules.registry import describe_module_type
    for name in CASES:
        previous=sys.getprofile()
        parameters={'input_variables':['pump.P_W'],'output_variable':'meter.sum_W'} if name=='SumModule' else None
        report=describe_module_type(name,parameters=parameters)
        if report['description_context']['solver_attempted'] is not False:mismatches.append(name+': description attempted a solve')
        if sys.getprofile() is not previous:mismatches.append(name+': description changed the profiler')
    return ReplayReport(len(CASES),mismatches)
