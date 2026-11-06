"""Actual CLI command return codes and printed view contracts."""
from dataclasses import dataclass
from contextlib import redirect_stdout, redirect_stderr
import io, json
from ._audit_cases import ROOT
@dataclass(frozen=True)
class CliInput:
    case_id: str
    audit_pass: bool | None
    json_view: bool = False


CASES = (CliInput('pass', True), CliInput('json', True, True), CliInput('fail', False), CliInput('missing', None), CliInput('validation', False))


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


def assert_native_contract():
    for case in CASES:
        code,text,error=native_case(case)
        assert code=={'pass':0,'json':0,'fail':1,'missing':2,'validation':1}[case.case_id],(case,code,error)
        if case.case_id!='missing':
            assert text.lstrip().startswith('{') is case.json_view,case
        if case.case_id=='validation':
            assert not text.lstrip().startswith('{')
            assert any('heater' in line and 'interval FAIL' in line for line in text.splitlines()),text
        if case.json_view:
            json.loads(text)

