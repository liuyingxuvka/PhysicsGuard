"""Run preserved native inputs directly; no abstract fact enumerator."""
from importlib import import_module
import pytest

TOPICS = ('assumptions', 'cli_exit', 'core', 'fault_variants', 'heated_tank_generator',
          'model_dataset_validation', 'module_descriptions', 'observed_derivation',
          'skill_install', 'solver_audit', 'file_contract', 'tree_verdicts')

@pytest.mark.parametrize('topic', TOPICS)
def test_native_contract(topic):
    import_module(__package__ + '.' + topic).assert_native_contract()
