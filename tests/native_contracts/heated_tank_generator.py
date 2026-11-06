"""Preserved direct heated tank generator contracts."""
from ._audit_cases import ROOT
CASES = ('generate',)


def assert_native_contract():
    mismatches = []
    import importlib.util, tempfile, sys, io
    from contextlib import redirect_stdout
    from pathlib import Path
    source = ROOT / 'examples/hierarchical/heated_tank/sim_tank.py'
    with tempfile.TemporaryDirectory(prefix='pg-generator-model-') as directory:
        output = Path(directory) / 'run.csv'
        unexpected = Path(directory) / 'import.csv'
        previous = sys.argv
        spec = importlib.util.spec_from_file_location('pg_native_tank_generator', source)
        module = importlib.util.module_from_spec(spec)
        try:
            sys.argv = [str(source), str(unexpected)]
            spec.loader.exec_module(module)
        finally:
            sys.argv = previous
        if unexpected.exists():
            mismatches.append('import generated a file')
        with redirect_stdout(io.StringIO()):
            code = module.main([str(output)])
        if code != 0 or output.read_bytes() != (source.parent / 'tank_run.csv').read_bytes():
            mismatches.append('CSV generation drifted')
    assert not mismatches, mismatches

