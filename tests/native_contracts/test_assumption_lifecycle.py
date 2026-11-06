"""The original native action chains against actual assumption cards."""
import pytest
from physicsguard.core.assumptions import AssumptionManager
from physicsguard.schema.system_spec import SystemSpec

@pytest.mark.parametrize('actions', [
    ('reset',), ('reset', 'reset'), ('apply',), ('apply', 'apply'), ('apply', 'reset', 'apply')])
def test_assumption_cards_apply_repeat_and_reset(actions):
    system = SystemSpec.model_validate({'system_name':'native-assumption-cards',
        'components':[{'id':'conductor','type':'ThermalConductorModule','parameters':{'G_W_K':50.0}}],
        'assumptions':[{'id':'conductance','target_type':'parameter','target':'conductor.G_W_K',
            'value':60.0,'allow_override':True,'reason':'explicit override fixture','impact':'low'}]})
    manager = AssumptionManager(system)
    card, = manager.assumption_cards()
    assert card.applied is False and not card.warnings
    for action in actions:
        if action == 'reset':
            manager = AssumptionManager(system)
        else:
            manager.apply_parameter_assumptions(system)
        card, = manager.assumption_cards()
        assert card.applied is (action == 'apply')
        assert any('overridden' in warning for warning in card.warnings) is (action == 'apply')
