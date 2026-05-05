"""PhysicsGuard module implementations and registry."""

from physicsguard.modules.base import BaseModule
from physicsguard.modules.registry import ModuleRegistry, default_module_registry

__all__ = [
    "BaseModule",
    "ConservationSumModule",
    "DummyResidualModule",
    "LinearRelationModule",
    "ModuleRegistry",
    "RangeCheckModule",
    "default_module_registry",
]


def __getattr__(name: str):
    if name == "DummyResidualModule":
        from physicsguard.modules.dummy import DummyResidualModule

        return DummyResidualModule
    if name in {"ConservationSumModule", "LinearRelationModule", "RangeCheckModule"}:
        from physicsguard.modules.generic import (
            ConservationSumModule,
            LinearRelationModule,
            RangeCheckModule,
        )

        return {
            "ConservationSumModule": ConservationSumModule,
            "LinearRelationModule": LinearRelationModule,
            "RangeCheckModule": RangeCheckModule,
        }[name]
    raise AttributeError(name)
