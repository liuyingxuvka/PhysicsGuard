"""Core execution primitives for PhysicsGuard."""

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


def __getattr__(name: str):
    if name == "DiagnosticReporter":
        from physicsguard.core.diagnostics import DiagnosticReporter

        return DiagnosticReporter
    if name in {
        "AuditEvaluator",
        "ComparisonResult",
        "ObservedEvaluationResult",
        "VariableDeviationDiagnostic",
    }:
        from physicsguard.core.evaluator import (
            AuditEvaluator,
            ComparisonResult,
            ObservedEvaluationResult,
            VariableDeviationDiagnostic,
        )

        return {
            "AuditEvaluator": AuditEvaluator,
            "ComparisonResult": ComparisonResult,
            "ObservedEvaluationResult": ObservedEvaluationResult,
            "VariableDeviationDiagnostic": VariableDeviationDiagnostic,
        }[name]
    if name in {"VariableRecord", "VariableRegistry"}:
        from physicsguard.core.registry import VariableRecord, VariableRegistry

        return {
            "VariableRecord": VariableRecord,
            "VariableRegistry": VariableRegistry,
        }[name]
    if name in {"ResidualBuilder", "ResidualRecord"}:
        from physicsguard.core.residual import ResidualBuilder, ResidualRecord

        return {
            "ResidualBuilder": ResidualBuilder,
            "ResidualRecord": ResidualRecord,
        }[name]
    if name in {"BoundedSolver", "SolverResult"}:
        from physicsguard.core.solver import BoundedSolver, SolverResult

        return {
            "BoundedSolver": BoundedSolver,
            "SolverResult": SolverResult,
        }[name]
    if name == "ModuleRegistry":
        from physicsguard.modules.registry import ModuleRegistry

        return ModuleRegistry
    raise AttributeError(name)
