"""An explicit assumption override has an applied card and a visible warning.

The other schema/report boundaries live in independent unit contracts; this model
covers the real manager's repeatable apply/reset lifecycle only.
"""
from flowguard.flow import Model
m = Model('explicit assumption lifecycle', covers=['src/physicsguard/core/assumptions.py:AssumptionManager'])
m.field('stage', ('fresh', 'applied'), 'fresh')
m.field('applied', (False, True), False)
m.field('warned', (False, True), False)
@m.action()
def apply(s):
    s['stage'], s['applied'], s['warned'] = 'applied', True, True
@m.action()
def reset(s):
    s['stage'], s['applied'], s['warned'] = 'fresh', False, False
m.always('assumption_overrides_are_warned', lambda s: not s['applied'] or s['warned'])
m.always('fresh cards have not been applied', lambda s: s['stage'] != 'fresh' or not s['applied'])
m.after('a new manager has fresh cards', 'reset',
        lambda before, after: after['stage'] == 'fresh' and not after['applied'] and not after['warned'])
m.reach('the real override is observable', lambda s: s['applied'] and s['warned'])
MODEL = m

from flowguard.flow.adapter import fields
m.bind_adapter({'system':'tests.flow_migration.native_assumptions:AssumptionWorld',
                'classes':[
                    'physicsguard.core.assumptions:AssumptionCard',
                    'physicsguard.core.assumptions:AssumptionManager',
                    'physicsguard.schema.assumption_spec:AssumptionSpec',
                    'physicsguard.schema.system_spec:ComponentInstanceSpec',
                    'physicsguard.schema.system_spec:SolverSpec',
                    'physicsguard.schema.system_spec:SystemSpec',
                    'pydantic.main:BaseModel',
                    'tests.flow_migration.native_assumptions:AssumptionWorld',
                ],
                'refusal':['builtins:ValueError']},
               state=lambda snapshot:fields(snapshot,names=('stage','applied','warned')),
               operations={'apply':'apply','reset':'reset'})
