"""heated_tank_generator: native component contract with fresh scratch conformance."""
from dataclasses import dataclass,replace
from flowguard import FunctionResult,Invariant,InvariantResult,Workflow
from flowguard.explorer import Explorer
from _core_fixture import ROOT,ReplayReport
MODEL_ID='heated_tank_generator'
PARENT='example_tools'
IMPLEMENTED_BY={'Generate': 'examples/hierarchical/heated_tank/sim_tank.py:main'}
TESTED_BY={'generator_reproduces_committed_csv': ['tests/test_heated_tank_example.py:test_generator_reproduces_committed_csv']}
MUTATIONS={'generator_drifts_from_committed_csv': 'generator_reproduces_committed_csv'}
CASES=('generate',)

@dataclass(frozen=True)
class State:
    done:bool=False
    import_clean:bool=True
    identical:bool=True

class Check:
    name='Check'
    reads=()
    writes=('done', 'import_clean', 'identical')
    def __init__(self,defect=''):self.defect=defect
    def apply(self,request,state):
        result=State(True,True,self.defect!='generator_drifts_from_committed_csv')
        yield FunctionResult(result,result,label=str(request))

def generator_reproduces_committed_csv(state,trace):
    return InvariantResult.fail('Import wrote files or generated CSV differs from the committed CSV') if state.done and (not state.import_clean or not state.identical) else InvariantResult.pass_()

INVARIANTS=(
    Invariant('generator_reproduces_committed_csv','generator reproduces committed csv',generator_reproduces_committed_csv),
)

def make(defect='',names=None):
    return Explorer(Workflow((Check(defect),)),(State(),),CASES,
                    tuple(rule for rule in INVARIANTS if names is None or rule.name in names),max_sequence_length=1,progress_steps=0)
def build_explorer():return make()
def broken_variants():return {name:make(name,{rule}) for name,rule in MUTATIONS.items()}

def conformance():
    mismatches=[]
    import importlib.util,tempfile,sys,io
    from contextlib import redirect_stdout
    from pathlib import Path
    source=ROOT/'examples/hierarchical/heated_tank/sim_tank.py'
    with tempfile.TemporaryDirectory(prefix='pg-generator-model-') as directory:
        output=Path(directory)/'run.csv';unexpected=Path(directory)/'import.csv';previous=sys.argv
        spec=importlib.util.spec_from_file_location('pg_native_tank_generator',source);module=importlib.util.module_from_spec(spec)
        try:
            sys.argv=[str(source),str(unexpected)];spec.loader.exec_module(module)
        finally:sys.argv=previous
        if unexpected.exists():mismatches.append('import generated a file')
        with redirect_stdout(io.StringIO()):code=module.main([str(output)])
        if code!=0 or output.read_bytes()!=(source.parent/'tank_run.csv').read_bytes():mismatches.append('CSV generation drifted')
    return ReplayReport(2,mismatches)
