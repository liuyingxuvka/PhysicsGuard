"""Pydantic schemas for PhysicsGuard Core."""

from physicsguard.schema.module_spec import (
    DiagnosticHint,
    ModuleSpec,
    ParameterSpec,
    PortSpec,
    ResidualSpec,
    VariableSpec,
)
from physicsguard.schema.assumption_spec import AssumptionDeckSpec, AssumptionSpec
from physicsguard.schema.hierarchy_spec import (
    AuditBlockSpec,
    BlockScoringSpec,
    ConfidenceScoringSpec,
    HierarchicalAuditSpec,
    HierarchySpec,
    RefinementRuleSpec,
)
from physicsguard.schema.observation_spec import ObservedValueSpec, ObservedValuesSpec
from physicsguard.schema.system_spec import (
    BoundarySpec,
    ComponentInstanceSpec,
    ConnectionSpec,
    InputSpec,
    SolverSpec,
    SystemSpec,
    VariableOverrideSpec,
)

__all__ = [
    "AuditBlockSpec",
    "AssumptionDeckSpec",
    "AssumptionSpec",
    "BoundarySpec",
    "BlockScoringSpec",
    "ComponentInstanceSpec",
    "ConfidenceScoringSpec",
    "ConnectionSpec",
    "DiagnosticHint",
    "HierarchicalAuditSpec",
    "HierarchySpec",
    "InputSpec",
    "ModuleSpec",
    "ObservedValueSpec",
    "ObservedValuesSpec",
    "ParameterSpec",
    "PortSpec",
    "RefinementRuleSpec",
    "ResidualSpec",
    "SolverSpec",
    "SystemSpec",
    "VariableOverrideSpec",
    "VariableSpec",
]
