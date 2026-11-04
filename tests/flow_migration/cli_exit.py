"""Independent cli exit domain facts and production contracts."""
from dataclasses import dataclass, replace
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
import io, json
from ._audit_cases import ROOT

@dataclass(frozen=True)
class CliInput:
    case_id: str
    audit_pass: bool | None
    json_view: bool = False
CASES = (CliInput('pass', True), CliInput('json', True, True), CliInput('fail', False), CliInput('missing', None), CliInput('validation', False))

@dataclass(frozen=True)
class State:
    request: CliInput | None = None
    exit_code: int | None = None
    json_view: bool = False
    tree_shown: bool = True

def expected(request, state, mutation=''):
    code = 2 if request.audit_pass is None else 0 if request.audit_pass else 1
    if mutation is True and request.case_id == 'fail':
        code = 0
    result = State(request, code, request.json_view, not (mutation == 'validation_prints_json_by_default' and request.case_id == 'validation'))
    return result

def exit_code_follows_audit_pass(state, trace):
    if state.request:
        expected = 2 if state.request.audit_pass is None else 0 if state.request.audit_pass else 1
        if state.exit_code != expected or state.json_view != state.request.json_view:
            return False
    return True

def default_view_is_the_tree(state, trace):
    if state.request and state.request.case_id == 'validation' and (not state.tree_shown):
        return False
    return True

def native_case(request):
    from physicsguard.cli import main
    case = request.case_id
    tank = ROOT / 'examples/hierarchical/heated_tank'
    args = ['hierarchy', 'evaluate', str(tank / 'heated_tank.yaml'), str(tank / ('measured_k70.yaml' if case == 'fail' else 'measured_k30.yaml'))]
    if case == 'validation':
        args = ['validation', 'run', str(tank / 'validation_plan.yaml')]
    if case == 'missing':
        args[2] = str(tank / 'does-not-exist.yaml')
    if case == 'json':
        args.append('--json')
    output = io.StringIO()
    error = io.StringIO()
    with redirect_stdout(output), redirect_stderr(error):
        code = main(args)
    return (code, output.getvalue(), error.getvalue())
RULE_NAMES = ('default_view_is_the_tree', 'exit_code_follows_audit_pass')
RULES = (default_view_is_the_tree, exit_code_follows_audit_pass)


def assert_native_contract():
    for case in CASES:
        code,text,error=native_case(case)
        state=expected(case,State())
        assert code==state.exit_code,(case,code,error)
        if case.case_id!='missing':
            assert text.lstrip().startswith('{') is state.json_view,case
        if case.case_id=='validation':
            assert not text.lstrip().startswith('{')
            assert any('heater' in line and 'interval FAIL' in line for line in text.splitlines()),text
        if case.json_view:
            json.loads(text)
