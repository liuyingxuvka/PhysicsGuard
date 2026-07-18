"""Observed-value evaluation and reference comparison."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

import numpy as np

from physicsguard.core.diagnostics import ResidualDiagnostic
from physicsguard.core.registry import VariableRegistry
from physicsguard.core.residual import ResidualBuilder, ResidualRecord
from physicsguard.core.solver import BoundedSolver
from physicsguard.schema.observation_spec import ObservedValuesSpec
from physicsguard.schema.system_spec import SystemSpec


@dataclass(frozen=True)
class VariableDeviationDiagnostic:
    variable: str
    reference_value: float
    observed_value: float
    raw_delta: float
    scale: float
    normalized_delta: float
    abs_normalized_delta: float
    unit: Optional[str]


@dataclass(frozen=True)
class ObservedEvaluationResult:
    system_name: str
    observation_name: Optional[str]
    audit_pass: bool
    residual_norm: float
    max_abs_normalized_residual: float
    variables: dict[str, float]
    top_residuals: list[ResidualDiagnostic]
    missing_variables: list[str]
    unknown_observed_variables: list[str]
    unit_warnings: list[str]
    warnings: list[str]
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ComparisonResult:
    system_name: str
    observation_name: Optional[str]
    reference_optimization_success: bool
    reference_audit_pass: bool
    observed_audit_pass: bool
    reference_residual_norm: float
    observed_residual_norm: float
    reference_variables: dict[str, float]
    observed_variables: dict[str, float]
    top_observed_residuals: list[ResidualDiagnostic]
    top_variable_deviations: list[VariableDeviationDiagnostic]
    missing_variables: list[str]
    unknown_observed_variables: list[str]
    unit_warnings: list[str]
    warnings: list[str]
    metadata: dict[str, Any] = field(default_factory=dict)


class AuditEvaluator:
    """Evaluate observed values against a PhysicsGuard residual system."""

    def __init__(self, system: SystemSpec) -> None:
        self.system = system
        self.builder = ResidualBuilder(system)

    def evaluate_observed(
        self,
        observed: ObservedValuesSpec,
        top_n: int = 20,
    ) -> ObservedEvaluationResult:
        registry = self.builder.build_registry()
        values, missing, unknown = self._observed_values_for_registry(observed, registry)
        if missing:
            raise ValueError(
                "observed values missing required registered variables: "
                + ", ".join(missing)
            )
        x = registry.dict_to_vector(values)
        diagnostic_records = self.builder.diagnostic_residual_records(x)
        solver_records = self.builder.solver_residual_records(x)
        normalized = np.array([record.normalized_value for record in solver_records], dtype=float)
        if normalized.ndim != 1 or not np.all(np.isfinite(normalized)):
            raise ValueError("observed residual vector contains NaN or inf")
        residual_norm = float(np.linalg.norm(normalized))
        max_abs = float(np.max(np.abs(normalized))) if normalized.size else 0.0
        audit_pass = max_abs <= self.system.solver.audit_threshold
        unit_warnings = self._unit_warnings(observed, registry)
        warnings = self._warnings(audit_pass, max_abs, unknown, unit_warnings)
        return ObservedEvaluationResult(
            system_name=self.system.system_name,
            observation_name=observed.observation_name,
            audit_pass=audit_pass,
            residual_norm=residual_norm,
            max_abs_normalized_residual=max_abs,
            variables=registry.vector_to_dict(x),
            top_residuals=_top_residual_diagnostics(diagnostic_records, top_n),
            missing_variables=missing,
            unknown_observed_variables=unknown,
            unit_warnings=unit_warnings,
            warnings=warnings,
            metadata={
                "mode": "evaluate",
                "audit_threshold": self.system.solver.audit_threshold,
                "observation_metadata": observed.metadata,
                "active_residual_count": len(solver_records),
                "diagnostic_residual_count": len(diagnostic_records),
            },
        )

    def compare_to_reference(
        self,
        observed: ObservedValuesSpec,
        top_n: int = 20,
    ) -> ComparisonResult:
        solver_result = BoundedSolver(self.builder, self.system.solver).solve()
        observed_result = self.evaluate_observed(observed, top_n=top_n)
        registry = self.builder.build_registry()
        deviations = self._variable_deviations(
            registry,
            solver_result.variables,
            observed_result.variables,
            top_n,
        )
        warnings = list(observed_result.warnings)
        if not solver_result.optimization_success:
            warnings.append("reference optimizer did not converge")
        if not solver_result.audit_pass:
            warnings.append("reference audit did not pass")
        return ComparisonResult(
            system_name=self.system.system_name,
            observation_name=observed.observation_name,
            reference_optimization_success=solver_result.optimization_success,
            reference_audit_pass=solver_result.audit_pass,
            observed_audit_pass=observed_result.audit_pass,
            reference_residual_norm=float(solver_result.residual_norm),
            observed_residual_norm=float(observed_result.residual_norm),
            reference_variables={
                key: float(value) for key, value in solver_result.variables.items()
            },
            observed_variables=observed_result.variables,
            top_observed_residuals=observed_result.top_residuals,
            top_variable_deviations=deviations,
            missing_variables=observed_result.missing_variables,
            unknown_observed_variables=observed_result.unknown_observed_variables,
            unit_warnings=observed_result.unit_warnings,
            warnings=warnings,
            metadata={
                "mode": "compare",
                "audit_threshold": self.system.solver.audit_threshold,
                "reference_solver": {
                    "status": solver_result.status,
                    "message": solver_result.message,
                    "nfev": solver_result.nfev,
                    "max_nfev": solver_result.max_nfev,
                    "cost": solver_result.cost,
                    "optimality": solver_result.optimality,
                },
                "observation_metadata": observed.metadata,
            },
        )

    def _observed_values_for_registry(
        self,
        observed: ObservedValuesSpec,
        registry: VariableRegistry,
    ) -> tuple[dict[str, float], list[str], list[str]]:
        registered = set(registry.names())
        observed_names = set(observed.variables)
        missing = sorted(registered - observed_names)
        unknown = sorted(observed_names - registered)
        values = {
            name: float(observed.variables[name].value)
            for name in registry.names()
            if name in observed.variables
        }
        return values, missing, unknown

    @staticmethod
    def _unit_warnings(
        observed: ObservedValuesSpec,
        registry: VariableRegistry,
    ) -> list[str]:
        warnings: list[str] = []
        for name in registry.names():
            if name not in observed.variables:
                continue
            expected_unit = registry.get_record(name).unit
            observed_unit = observed.variables[name].unit
            if expected_unit and observed_unit and expected_unit != observed_unit:
                warnings.append(
                    f"{name}: observed unit '{observed_unit}' differs from registry unit "
                    f"'{expected_unit}'; numeric value was used as SI"
                )
        return warnings

    def _warnings(
        self,
        audit_pass: bool,
        max_abs: float,
        unknown_observed_variables: list[str],
        unit_warnings: list[str],
    ) -> list[str]:
        warnings: list[str] = []
        if unknown_observed_variables:
            warnings.append(
                "unknown observed variables ignored: "
                + ", ".join(unknown_observed_variables)
            )
        warnings.extend(unit_warnings)
        if not audit_pass:
            warnings.append("observed audit did not pass")
        if max_abs > self.system.solver.audit_threshold:
            warnings.append("max observed normalized residual exceeds audit threshold")
        if max_abs > 10:
            warnings.append("max observed normalized residual exceeds 10")
        return warnings

    def _variable_deviations(
        self,
        registry: VariableRegistry,
        reference_variables: dict[str, float],
        observed_variables: dict[str, float],
        top_n: int,
    ) -> list[VariableDeviationDiagnostic]:
        deviations: list[VariableDeviationDiagnostic] = []
        for name in registry.names():
            record = registry.get_record(name)
            reference_value = float(reference_variables[name])
            observed_value = float(observed_variables[name])
            raw_delta = observed_value - reference_value
            normalized_delta = raw_delta / record.scale
            deviations.append(
                VariableDeviationDiagnostic(
                    variable=name,
                    reference_value=reference_value,
                    observed_value=observed_value,
                    raw_delta=float(raw_delta),
                    scale=float(record.scale),
                    normalized_delta=float(normalized_delta),
                    abs_normalized_delta=float(abs(normalized_delta)),
                    unit=record.unit,
                )
            )
        return sorted(
            deviations,
            key=lambda deviation: deviation.abs_normalized_delta,
            reverse=True,
        )[:top_n]


def _top_residual_diagnostics(
    records: list[ResidualRecord],
    top_n: int,
) -> list[ResidualDiagnostic]:
    ordered = sorted(records, key=lambda record: record.abs_normalized_value, reverse=True)
    return [
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
        for record in ordered[:top_n]
    ]
