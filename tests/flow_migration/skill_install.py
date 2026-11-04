"""Independent skill install domain facts and production contracts."""
from dataclasses import dataclass, replace
from ._audit_cases import ROOT
MUTATIONS = {'dry_run_writes_the_target': 'check_and_dry_run_change_nothing'}
CASES = ('install',)

@dataclass(frozen=True)
class State:
    done: bool = False
    dry_clean: bool = True
    before_code: int = 1
    after_code: int = 0

def expected(request, state, mutation=''):
    result = State(True, mutation != 'dry_run_writes_the_target', 1, 0)
    return result

def check_and_dry_run_change_nothing(state, trace):
    return False if state.done and (not state.dry_clean or state.before_code != 1 or state.after_code != 0) else True
RULE_NAMES = ('check_and_dry_run_change_nothing',)
RULES = (check_and_dry_run_change_nothing,)

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
