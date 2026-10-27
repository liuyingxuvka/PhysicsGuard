"""Trace reuse must be bounded to one command and invalidate on every real input."""
from pathlib import Path
import numpy as np
import pytest
from physicsguard.cli import main
from physicsguard.core import _residual_dependencies as dependencies

ROOT = Path(__file__).resolve().parents[1]
TANK = ROOT / 'examples/hierarchical/heated_tank'


def _count_captures(monkeypatch):
    counts = []
    original = dependencies._Capture.__init__
    def counted(self, *args, **kwargs):
        counts.append(1)
        original(self, *args, **kwargs)
    monkeypatch.setattr(dependencies._Capture, '__init__', counted)
    return counts


@pytest.mark.parametrize(('arguments', 'limit'), [
    (['hierarchy', 'evaluate', str(TANK / 'heated_tank.yaml'), str(TANK / 'sparse_measured_k70.yaml'), '--json'], 150),
    (['validation', 'run', str(TANK / 'validation_plan.yaml'), '--json'], 300),
    (['hierarchy', 'variants', str(TANK / 'heated_tank.yaml'), str(TANK / 'measured_k30.yaml'), '--pairs', '--observed', str(TANK / 'measured_k70.yaml'), '--json'], 40),
], ids=['sparse', 'validation', 'variants'])
def test_commands_trace_each_input_once(monkeypatch, capsys, arguments, limit):
    counts = _count_captures(monkeypatch)
    assert main(arguments) in (0, 1)
    capsys.readouterr()
    assert len(counts) <= limit, f'{len(counts)} real traces exceed {limit}'


def test_reuse_tracks_values_parameters_and_fixed_tables(monkeypatch):
    from physicsguard.core.registry import VariableRegistry
    from physicsguard.core.residual import ResidualRecord
    from physicsguard.modules.control import LookupTable1DModule
    module = LookupTable1DModule('lookup', {'x_points': [0., 1.], 'y_points': [0., 2.]})
    registry = VariableRegistry()
    for record in module.declare_variables():
        registry.add_variable(record)
    vector = registry.dict_to_vector({'lookup.x': .5, 'lookup.y': 1.})
    counts = _count_captures(monkeypatch)
    @dependencies.residual_trace_scope
    def evaluate():
        def read():
            return dependencies.module_residual_dependencies(module, vector, registry, ResidualRecord)
        first = read()
        second = read()
        assert len(counts) == 1
        assert first[1:] == second[1:]
        assert first[0][0].value == second[0][0].value == 0.
        vector[registry.get_index('lookup.y')] = 3.
        assert read()[0][0].value == 2.
        assert len(counts) == 2
        module.y_points[1] = 4.
        assert read()[0][0].value == 1.
        assert len(counts) == 3
        module.parameters['residual_scale'] = 2.
        read()
        assert len(counts) == 4
    evaluate()


def test_scope_is_shared_by_nested_calls_and_discarded_on_return_or_error(monkeypatch):
    from physicsguard.core.registry import VariableRegistry
    from physicsguard.core.residual import ResidualRecord
    from physicsguard.modules.dummy import DummyResidualModule
    module = DummyResidualModule('d', {'target': 1.})
    registry = VariableRegistry()
    registry.add_variable(module.declare_variables()[0])
    vector = np.array([2.])
    counts = _count_captures(monkeypatch)
    @dependencies.residual_trace_scope
    def nested():
        return dependencies.module_residual_dependencies(module, vector, registry, ResidualRecord)
    @dependencies.residual_trace_scope
    def command(fail=False):
        first = nested()
        second = nested()
        assert first[1:] == second[1:]
        if fail:
            raise ValueError('leave scope')
    command()
    assert len(counts) == 1
    command()
    assert len(counts) == 2
    with pytest.raises(ValueError, match='leave scope'):
        command(fail=True)
    assert len(counts) == 3
    command()
    assert len(counts) == 4


def test_an_observation_array_cannot_be_reused_as_a_fixed_table(monkeypatch):
    from physicsguard.core.registry import VariableRegistry
    from physicsguard.core.residual import ResidualRecord
    from physicsguard.modules.control import LookupTable1DModule
    module = LookupTable1DModule('lookup', {'x_points': [0., 1.], 'y_points': [.5, 1.]})
    registry = VariableRegistry()
    for record in module.declare_variables():
        registry.add_variable(record)
    vector = registry.dict_to_vector({'lookup.x': .5, 'lookup.y': 1.})
    module.y_points = vector.copy()
    counts = _count_captures(monkeypatch)
    @dependencies.residual_trace_scope
    def command():
        first = dependencies.module_residual_dependencies(module, vector, registry, ResidualRecord)
        assert first[1][0] is not None
        module.y_points = vector
        second = dependencies.module_residual_dependencies(module, vector, registry, ResidualRecord)
        assert second[1][0] is None
    command()
    assert len(counts) == 2
