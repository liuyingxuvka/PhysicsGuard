"""The CLI's actual outcome, view and input-error contract."""
from pathlib import Path
import json
from physicsguard.cli import main

TANK = Path(__file__).resolve().parents[1] / 'examples/hierarchical/heated_tank'


def test_cli_exit_codes_follow_the_audit(capsys):
    passing = ['hierarchy', 'evaluate', str(TANK / 'heated_tank.yaml'), str(TANK / 'measured_k30.yaml')]
    assert main(passing) == 0
    assert not capsys.readouterr().out.lstrip().startswith('{')
    assert main([*passing, '--json']) == 0
    assert json.loads(capsys.readouterr().out)['audit_pass'] is True
    failing = ['hierarchy', 'evaluate', str(TANK / 'heated_tank.yaml'), str(TANK / 'measured_k70.yaml')]
    assert main(failing) == 1
    assert not capsys.readouterr().out.lstrip().startswith('{')
    assert main(['hierarchy', 'evaluate', str(TANK / 'absent.yaml'), str(TANK / 'measured_k30.yaml')]) == 2
    assert capsys.readouterr().err
