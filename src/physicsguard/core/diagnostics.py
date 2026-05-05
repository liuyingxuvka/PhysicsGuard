"""Machine-readable diagnostics for PhysicsGuard audits."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
from typing import Any, Literal, Optional

from physicsguard.core.assumptions import AssumptionSummary
from physicsguard.core.residual import ResidualBuilder
from physicsguard.core.solver import SolverResult
from physicsguard.schema.system_spec import SystemSpec


@dataclass(frozen=True)
class ResidualDiagnostic:
    name: str
    source: str
    role: str
    raw_value: float
    scale: float
    normalized_value: float
    abs_normalized_value: float
    diagnostic_key: Optional[str]
    description: Optional[str]


@dataclass(frozen=True)
class BoundHitDiagnostic:
    variable: str
    value: float
    lower_bound: float
    upper_bound: float
    hit_type: Literal["lower", "upper"]
    distance_normalized: float


@dataclass(frozen=True)
class DiagnosticReport:
    system_name: str
    optimization_success: bool
    audit_pass: bool
    audit_threshold: float
    solver_message: str
    residual_norm: float
    max_abs_normalized_residual: float
    variables: dict[str, float]
    top_residuals: list[ResidualDiagnostic]
    bound_hits: list[BoundHitDiagnostic]
    warnings: list[str]
    assumptions: AssumptionSummary
    metadata: dict[str, Any] = field(default_factory=dict)


class DiagnosticReporter:
    def __init__(self, bound_hit_tolerance: float = 1e-6) -> None:
        self.bound_hit_tolerance = bound_hit_tolerance

    def generate(
        self,
        system: SystemSpec,
        builder: ResidualBuilder,
        solver_result: SolverResult,
        top_n: int = 20,
    ) -> DiagnosticReport:
        residuals = sorted(
            builder.diagnostic_residual_records(solver_result.x),
            key=lambda record: record.abs_normalized_value,
            reverse=True,
        )
        top_residuals = [
            ResidualDiagnostic(
                name=record.name,
                source=record.source,
                role=record.role,
                raw_value=float(record.value),
                scale=float(record.scale),
                normalized_value=float(record.normalized_value),
                abs_normalized_value=float(record.abs_normalized_value),
                diagnostic_key=record.diagnostic_key,
                description=record.description,
            )
            for record in residuals[:top_n]
        ]
        assumption_summary = builder.assumption_summary()
        warnings = _dedupe([*self._warnings(solver_result), *assumption_summary.warnings])
        return DiagnosticReport(
            system_name=system.system_name,
            optimization_success=solver_result.optimization_success,
            audit_pass=solver_result.audit_pass,
            audit_threshold=solver_result.audit_threshold,
            solver_message=solver_result.message,
            residual_norm=float(solver_result.residual_norm),
            max_abs_normalized_residual=float(solver_result.max_abs_normalized_residual),
            variables={key: float(value) for key, value in solver_result.variables.items()},
            top_residuals=top_residuals,
            bound_hits=self._bound_hits(builder, solver_result),
            warnings=warnings,
            assumptions=assumption_summary,
            metadata={
                "solver": {
                    "method": system.solver.method,
                    "status": solver_result.status,
                    "nfev": solver_result.nfev,
                    "max_nfev": solver_result.max_nfev,
                    "cost": solver_result.cost,
                    "optimality": solver_result.optimality,
                    "max_iterations": system.solver.max_iterations,
                    "tolerance": system.solver.tolerance,
                    "audit_threshold": system.solver.audit_threshold,
                },
                "component_count": len(system.components),
                "connection_count": len(system.connections),
                "boundary_count": len(system.boundaries),
            },
        )

    def to_dict(self, report: Any) -> dict[str, Any]:
        return asdict(report)

    def to_json(self, report: Any) -> str:
        return json.dumps(self.to_dict(report), sort_keys=True)

    def _bound_hits(
        self,
        builder: ResidualBuilder,
        solver_result: SolverResult,
    ) -> list[BoundHitDiagnostic]:
        registry = builder.build_registry()
        hits: list[BoundHitDiagnostic] = []
        for name, value in solver_result.variables.items():
            record = registry.get_record(name)
            width = record.upper_bound - record.lower_bound
            lower_distance = (value - record.lower_bound) / width
            upper_distance = (record.upper_bound - value) / width
            if lower_distance <= self.bound_hit_tolerance:
                hits.append(
                    BoundHitDiagnostic(
                        variable=name,
                        value=float(value),
                        lower_bound=float(record.lower_bound),
                        upper_bound=float(record.upper_bound),
                        hit_type="lower",
                        distance_normalized=float(lower_distance),
                    )
                )
            if upper_distance <= self.bound_hit_tolerance:
                hits.append(
                    BoundHitDiagnostic(
                        variable=name,
                        value=float(value),
                        lower_bound=float(record.lower_bound),
                        upper_bound=float(record.upper_bound),
                        hit_type="upper",
                        distance_normalized=float(upper_distance),
                    )
                )
        return hits

    @staticmethod
    def _warnings(solver_result: SolverResult) -> list[str]:
        warnings: list[str] = []
        if not solver_result.optimization_success:
            warnings.append("optimizer did not converge")
        if not solver_result.audit_pass:
            warnings.append("audit did not pass")
        if solver_result.max_abs_normalized_residual > solver_result.audit_threshold:
            warnings.append("max normalized residual exceeds audit threshold")
        if solver_result.max_abs_normalized_residual > 10:
            warnings.append("max normalized residual exceeds 10")
        return warnings


def _dedupe(items: list[str]) -> list[str]:
    result: list[str] = []
    for item in items:
        if item and item not in result:
            result.append(item)
    return result
