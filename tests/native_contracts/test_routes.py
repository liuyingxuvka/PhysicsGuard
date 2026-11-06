"""Original target-existence contracts, using the shared source Map."""
from contextlib import closing
from pathlib import Path
import pytest
from flowguard.structure import build
ROOT=Path(__file__).resolve().parents[2]
ROUTES = [{'id': 'observed_audit', 'targets': ['src/physicsguard/cli.py:main', 'src/physicsguard/io/hierarchy_loader.py:load_hierarchical_audit_spec', 'src/physicsguard/core/hierarchy.py:HierarchicalAuditRunner.evaluate_observed']}, {'id': 'dataset_validation', 'targets': ['src/physicsguard/cli.py:main', 'src/physicsguard/core/model_dataset_validation.py:validate_model_dataset', 'src/physicsguard/core/test_file_contract.py:resolve_test_file_contract']}, {'id': 'diagnosis', 'targets': ['src/physicsguard/cli.py:main', 'src/physicsguard/core/diagnosability.py:evaluate_fault_variants', 'src/physicsguard/core/hierarchy.py:HierarchicalAuditRunner.evaluate_observed']}, {'id': 'data_binding', 'targets': ['src/physicsguard/cli.py:main', 'src/physicsguard/core/test_file_contract.py:check_test_file_contract', 'src/physicsguard/core/test_file_contract.py:testfile_snapshot', 'src/physicsguard/core/test_file_contract.py:testfile_series', 'src/physicsguard/core/signal_mapping.py:build_signal_mapping_ledger']}, {'id': 'growth', 'targets': ['src/physicsguard/cli.py:main', 'src/physicsguard/core/hierarchy.py:HierarchicalAuditRunner.evaluate_observed', 'src/physicsguard/core/hierarchy.py:_refinement_checks']}]

@pytest.mark.parametrize('route', ROUTES, ids=[route['id'] for route in ROUTES])
def test_original_system_route_targets_exist(route):
    with closing(build(ROOT, roots=['src', 'scripts', 'tests'])) as source:
        for target in route['targets']:
            path, symbol = target.split(':', 1)
            assert any(row['qual'] == symbol for row in source.nodes(file=path)), (route['id'], target)
