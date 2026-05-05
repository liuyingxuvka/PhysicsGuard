"""Core execution primitives for PhysicsGuard."""

from physicsguard.core.diagnostics import DiagnosticReporter
from physicsguard.core.evaluator import (
    AuditEvaluator,
    ComparisonResult,
    ObservedEvaluationResult,
    VariableDeviationDiagnostic,
)
from physicsguard.core.registry import VariableRecord, VariableRegistry
from physicsguard.core.residual import ResidualBuilder, ResidualRecord
from physicsguard.core.solver import BoundedSolver, SolverResult
from physicsguard.modules.registry import ModuleRegistry

__all__ = [
    "BoundedSolver",
    "AuditEvaluator",
    "ComparisonResult",
    "DiagnosticReporter",
    "ModuleRegistry",
    "ObservedEvaluationResult",
    "ResidualBuilder",
    "ResidualRecord",
    "SolverResult",
    "VariableRecord",
    "VariableDeviationDiagnostic",
    "VariableRegistry",
]
