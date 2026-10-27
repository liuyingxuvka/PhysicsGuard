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


def test_validation_run_prints_the_tree(capsys):
    assert main(['validation', 'run', str(TANK / 'validation_plan.yaml')]) == 1
    text = capsys.readouterr().out
    assert text.startswith('validation tank_run_validation on heated_tank: partial; 120 points, holdout ')
    assert any('heater [L' in line and 'interval FAIL step_60-step_119 worst 25.00' in line for line in text.splitlines())
    assert [line.split(':', 1)[0] for line in text.splitlines()[-3:]] == ['adequacy', 'next', 'safe claim']
    assert len(text.encode()) <= 3000
