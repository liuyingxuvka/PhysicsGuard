"""Reset/apply stimuli around the actual mutable AssumptionManager owner."""
from physicsguard.core.assumptions import AssumptionManager
from physicsguard.schema.system_spec import SystemSpec

class AssumptionWorld:
    def __init__(self):
        self.system=SystemSpec.model_validate({'system_name':'native-assumption-cards',
            'components':[{'id':'conductor','type':'ThermalConductorModule','parameters':{'G_W_K':50.0}}],
            'assumptions':[{'id':'conductance','target_type':'parameter','target':'conductor.G_W_K',
                'value':60.0,'allow_override':True,'reason':'explicit override fixture','impact':'low'}]})
        self.manager=AssumptionManager(self.system)
        self._observe()

    def _observe(self):
        card,=self.manager.assumption_cards()
        self.applied=card.applied
        self.warned=any('overridden' in warning for warning in card.warnings)
        self.stage='applied' if self.applied else 'fresh'

    def apply(self):
        self.manager.apply_parameter_assumptions(self.system)
        self._observe()

    def reset(self):
        self.manager=AssumptionManager(self.system)
        self._observe()
