"""skill_install: native component contract with fresh scratch conformance."""
from dataclasses import dataclass,replace
from flowguard import FunctionResult,Invariant,InvariantResult,Workflow
from flowguard.explorer import Explorer
from _core_fixture import ROOT,ReplayReport
MODEL_ID='skill_install'
PARENT='maintenance'
IMPLEMENTED_BY={'Install': 'scripts/install_physicsguard_skills.py:main'}
TESTED_BY={'check_and_dry_run_change_nothing': ['tests/test_install_physicsguard_skills.py:test_cli_dry_run_changes_nothing_and_check_fails_until_installed']}
MUTATIONS={'dry_run_writes_the_target': 'check_and_dry_run_change_nothing'}
CASES=('install',)

@dataclass(frozen=True)
class State:
    done:bool=False
    dry_clean:bool=True
    before_code:int=1
    after_code:int=0

class Check:
    name='Check'
    reads=()
    writes=('done', 'dry_clean', 'before_code', 'after_code')
    def __init__(self,defect=''):self.defect=defect
    def apply(self,request,state):
        result=State(True,self.defect!='dry_run_writes_the_target',1,0)
        yield FunctionResult(result,result,label=str(request))

def check_and_dry_run_change_nothing(state,trace):
    return InvariantResult.fail('Dry run wrote files or check did not follow installation') if state.done and (not state.dry_clean or state.before_code!=1 or state.after_code!=0) else InvariantResult.pass_()

INVARIANTS=(
    Invariant('check_and_dry_run_change_nothing','check and dry run change nothing',check_and_dry_run_change_nothing),
)

def make(defect='',names=None):
    return Explorer(Workflow((Check(defect),)),(State(),),CASES,
                    tuple(rule for rule in INVARIANTS if names is None or rule.name in names),max_sequence_length=1,progress_steps=0)
def build_explorer():return make()
def broken_variants():return {name:make(name,{rule}) for name,rule in MUTATIONS.items()}

def conformance():
    mismatches=[]
    import importlib.util,tempfile,io
    from contextlib import redirect_stdout
    from pathlib import Path
    source=ROOT/'scripts/install_physicsguard_skills.py'
    spec=importlib.util.spec_from_file_location('pg_native_installer',source);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    with tempfile.TemporaryDirectory(prefix='pg-install-model-') as directory:
        target=Path(directory)/'skills';args=['--target',str(target)];output=io.StringIO()
        with redirect_stdout(output):dry=module.main(args+['--dry-run'])
        if dry!=0 or target.exists():mismatches.append('dry run changed its target or failed')
        with redirect_stdout(output):before=module.main(args+['--check'])
        if before!=1:mismatches.append('check accepted an absent installation')
        with redirect_stdout(output):installed=module.main(args)
        with redirect_stdout(output):after=module.main(args+['--check'])
        if installed!=0 or after!=0:mismatches.append('fresh installation does not check current')
    return ReplayReport(4,mismatches)
