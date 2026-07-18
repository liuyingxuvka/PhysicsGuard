"""Bounded least-squares solver for normalized residuals."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.optimize import least_squares

from physicsguard.core.residual import ResidualBuilder
from physicsguard.schema.system_spec import SolverSpec


@dataclass(frozen=True)
class SolverResult:
    optimization_success: bool
    audit_pass: bool
    audit_threshold: float
    status: int
    message: str
    cost: float
    optimality: float
    nfev: int
    max_nfev: int
    x: np.ndarray
    variables: dict[str, float]
    residual_norm: float
    max_abs_normalized_residual: float


class BoundedSolver:
    def __init__(self, builder: ResidualBuilder, solver_spec: SolverSpec) -> None:
        self.builder = builder
        self.solver_spec = solver_spec

    def solve(self) -> SolverResult:
        registry = self.builder.build_registry()
        x0 = registry.initial_vector()
        lower_bounds = registry.lower_bounds()
        upper_bounds = registry.upper_bounds()
        x_scale = registry.scales()
        if not np.all(np.isfinite(x_scale)) or np.any(x_scale <= 0):
            raise ValueError("x_scale values must be finite and positive")
        max_nfev = self.solver_spec.max_iterations * (registry.size() + 1)

        def objective(x: np.ndarray) -> np.ndarray:
            residuals = self.builder.residual_vector(x)
            if residuals.ndim != 1 or not np.all(np.isfinite(residuals)):
                raise ValueError("solver objective produced invalid residuals")
            return residuals

        result = least_squares(
            objective,
            x0,
            bounds=(lower_bounds, upper_bounds),
            max_nfev=max_nfev,
            ftol=self.solver_spec.tolerance,
            xtol=self.solver_spec.tolerance,
            gtol=self.solver_spec.tolerance,
            x_scale=x_scale,
            verbose=2 if self.solver_spec.verbose else 0,
        )
        residuals = objective(result.x)
        residual_norm = float(np.linalg.norm(residuals))
        max_abs = float(np.max(np.abs(residuals))) if residuals.size else 0.0
        audit_pass = max_abs <= self.solver_spec.audit_threshold
        return SolverResult(
            optimization_success=bool(result.success),
            audit_pass=audit_pass,
            audit_threshold=float(self.solver_spec.audit_threshold),
            status=int(result.status),
            message=str(result.message),
            cost=float(result.cost),
            optimality=float(result.optimality),
            nfev=int(result.nfev),
            max_nfev=max_nfev,
            x=np.asarray(result.x, dtype=float),
            variables=registry.vector_to_dict(result.x),
            residual_norm=residual_norm,
            max_abs_normalized_residual=max_abs,
        )
