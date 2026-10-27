"""CLI views and exits follow actual audit outcomes."""
from dataclasses import dataclass,replace
from contextlib import redirect_stdout,redirect_stderr
from pathlib import Path
import io,json
from flowguard import FunctionResult,Invariant,InvariantResult,Workflow
from flowguard.explorer import Explorer
from _core_fixture import ReplayReport,ROOT
MODEL_ID='cli_exit'
PARENT='interface'
IMPLEMENTED_BY={'ReportExit':'src/physicsguard/cli.py:main'}
TESTED_BY={'exit_code_follows_audit_pass':['tests/test_cli.py:test_module_cli_lists_registry_and_reports_unknown_type','tests/test_cli_exit.py:test_cli_exit_codes_follow_the_audit']}
@dataclass(frozen=True)
class CliInput:
    case_id:str
    audit_pass:bool|None
    json_view:bool=False

CASES=(CliInput('pass',True),CliInput('json',True,True),CliInput('fail',False),CliInput('missing',None))

@dataclass(frozen=True)
class State:
    request:CliInput|None=None
    exit_code:int|None=None
    json_view:bool=False

class ReportExit:
    name='ReportExit'
    reads=()
    writes=('request','exit_code','json_view')
    def __init__(self,broken=False):self.broken=broken
    def apply(self,request,state):
        code=2 if request.audit_pass is None else 0 if request.audit_pass else 1
        if self.broken and request.case_id=='fail':code=0
        result=State(request,code,request.json_view)
        yield FunctionResult(code,result,label=request.case_id)

def exit_code_follows_audit_pass(state,trace):
    if state.request:
        expected=2 if state.request.audit_pass is None else 0 if state.request.audit_pass else 1
        if state.exit_code!=expected or state.json_view!=state.request.json_view:
            return InvariantResult.fail('The CLI exit or default/text versus JSON format differs from the audit')
    return InvariantResult.pass_()

INVARIANTS=(Invariant('exit_code_follows_audit_pass','A passing audit exits zero, a non-pass one, an input error two; text is default and --json is JSON.',exit_code_follows_audit_pass),)
def make(broken=False):return Explorer(Workflow((ReportExit(broken),)),(State(),),CASES,INVARIANTS,max_sequence_length=1,progress_steps=0)
def build_explorer():return make()
def broken_variants():return {'failed_audit_exits_zero':make(True)}

def native_case(request):
    from physicsguard.cli import main
    case=request.case_id
    tank=ROOT/'examples/hierarchical/heated_tank'
    args=['hierarchy','evaluate',str(tank/'heated_tank.yaml'),str(tank/('measured_k70.yaml' if case=='fail' else 'measured_k30.yaml'))]
    if case=='missing':args[2]=str(tank/'does-not-exist.yaml')
    if case=='json':args.append('--json')
    output=io.StringIO();error=io.StringIO()
    with redirect_stdout(output),redirect_stderr(error):code=main(args)
    return code,output.getvalue(),error.getvalue()

def conformance():
    mismatches=[]
    for request in CASES:
        try:
            code,text,error=native_case(request)
            state=next(iter(ReportExit().apply(request,State()))).new_state
            if code!=state.exit_code:mismatches.append(f'{request}: native exit {code}, expected {state.exit_code}')
            if request.case_id!='missing' and text.lstrip().startswith('{')!=state.json_view:mismatches.append(f'{request}: incorrect output format')
            if request.json_view:json.loads(text)
        except Exception as exc:mismatches.append(f'{request}: native replay raised {type(exc).__name__}: {exc}')
    return ReplayReport(len(CASES),mismatches)
