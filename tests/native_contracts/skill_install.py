"""Preserved direct skill install contracts."""
from ._audit_cases import ROOT
CASES = ('install',)


def assert_native_contract():
    mismatches = []
    import importlib.util, tempfile, io
    from contextlib import redirect_stdout
    from pathlib import Path
    source = ROOT / 'scripts/install_physicsguard_skills.py'
    spec = importlib.util.spec_from_file_location('pg_native_installer', source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    with tempfile.TemporaryDirectory(prefix='pg-install-model-') as directory:
        target = Path(directory) / 'skills'
        args = ['--target', str(target)]
        output = io.StringIO()
        with redirect_stdout(output):
            dry = module.main(args + ['--dry-run'])
        if dry != 0 or target.exists():
            mismatches.append('dry run changed its target or failed')
        with redirect_stdout(output):
            before = module.main(args + ['--check'])
        if before != 1:
            mismatches.append('check accepted an absent installation')
        with redirect_stdout(output):
            installed = module.main(args)
        with redirect_stdout(output):
            after = module.main(args + ['--check'])
        if installed != 0 or after != 0:
            mismatches.append('fresh installation does not check current')
    assert not mismatches, mismatches

