from __future__ import annotations

from types import SimpleNamespace

import numpy as np

import physicsguard.core.solver as solver_module
from physicsguard.core.residual import ResidualBuilder
from physicsguard.core.solver import BoundedSolver, SolverResult
from physicsguard.schema.system_spec import SystemSpec


def make_system(data: dict) -> SystemSpec:
    return SystemSpec.model_validate(data)


def test_dummy_target_system_converges() -> None:
    spec = make_system(
        {
            "system_name": "solve",
            "components": [
                {
                    "id": "a",
                    "type": "DummyResidualModule",
                    "parameters": {"target": 5.0, "initial_guess": 0.0},
                }
            ],
        }
    )
    result = BoundedSolver(ResidualBuilder(spec), spec.solver).solve()
    assert result.optimization_success
    assert result.audit_pass
    assert abs(result.variables["a.x"] - 5.0) < 1e-4


def test_bounds_are_respected() -> None:
    spec = make_system(
        {
            "system_name": "bounded",
            "components": [
                {
                    "id": "a",
                    "type": "DummyResidualModule",
                    "parameters": {
                        "target": 10.0,
                        "lower_bound": 0.0,
                        "upper_bound": 1.0,
                        "initial_guess": 0.5,
                    },
                }
            ],
        }
    )
    result = BoundedSolver(ResidualBuilder(spec), spec.solver).solve()
    assert 0.0 <= result.variables["a.x"] <= 1.0


def test_inconsistent_target_boundary_returns_nonzero_residual() -> None:
    spec = make_system(
        {
            "system_name": "conflict",
            "components": [
                {"id": "a", "type": "DummyResidualModule", "parameters": {"target": 5.0}},
            ],
            "boundaries": [{"variable": "a.x", "value": 10.0}],
        }
    )
    result = BoundedSolver(ResidualBuilder(spec), spec.solver).solve()
    assert result.residual_norm > 0
    assert result.max_abs_normalized_residual > 0
    assert result.optimization_success
    assert not result.audit_pass


def test_solver_result_includes_diagnostics_ready_fields() -> None:
    spec = make_system(
        {
            "system_name": "fields",
            "components": [
                {"id": "a", "type": "DummyResidualModule", "parameters": {"target": 1.0}},
            ],
        }
    )
    result = BoundedSolver(ResidualBuilder(spec), spec.solver).solve()
    assert isinstance(result, SolverResult)
    assert isinstance(result.optimization_success, bool)
    assert isinstance(result.audit_pass, bool)
    assert isinstance(result.audit_threshold, float)
    assert isinstance(result.variables, dict)
    assert isinstance(result.residual_norm, float)
    assert isinstance(result.max_abs_normalized_residual, float)
    assert isinstance(result.max_nfev, int)
    assert isinstance(result.x, np.ndarray)


def test_non_convergence_produces_solver_result_when_possible() -> None:
    spec = make_system(
        {
            "system_name": "limited",
            "components": [
                {
                    "id": "a",
                    "type": "DummyResidualModule",
                    "parameters": {"target": 50.0, "initial_guess": 0.0},
                }
            ],
            "solver": {"max_iterations": 1, "tolerance": 1e-12},
        }
    )
    result = BoundedSolver(ResidualBuilder(spec), spec.solver).solve()
    assert isinstance(result, SolverResult)
    assert not result.optimization_success


def test_max_iterations_maps_to_max_nfev(monkeypatch) -> None:
    spec = make_system(
        {
            "system_name": "max_nfev",
            "components": [
                {"id": "a", "type": "DummyResidualModule", "parameters": {"target": 0.0}},
                {"id": "b", "type": "DummyResidualModule", "parameters": {"target": 0.0}},
            ],
            "solver": {"max_iterations": 3},
        }
    )
    observed: dict[str, int] = {}

    def fake_least_squares(fun, x0, **kwargs):
        observed["max_nfev"] = kwargs["max_nfev"]
        fun(x0)
        return SimpleNamespace(
            success=True,
            status=1,
            message="ok",
            cost=0.0,
            optimality=0.0,
            nfev=1,
            x=x0,
        )

    monkeypatch.setattr(solver_module, "least_squares", fake_least_squares)
    result = BoundedSolver(ResidualBuilder(spec), spec.solver).solve()
    assert observed["max_nfev"] == 3 * (2 + 1)
    assert result.max_nfev == observed["max_nfev"]


def test_solver_passes_variable_scales_as_x_scale(monkeypatch) -> None:
    spec = make_system(
        {
            "system_name": "x_scale",
            "components": [
                {
                    "id": "a",
                    "type": "DummyResidualModule",
                    "parameters": {"target": 0.0, "scale": 3.0},
                },
            ],
        }
    )
    observed: dict[str, np.ndarray] = {}

    def fake_least_squares(fun, x0, **kwargs):
        observed["x_scale"] = kwargs["x_scale"]
        fun(x0)
        return SimpleNamespace(
            success=True,
            status=1,
            message="ok",
            cost=0.0,
            optimality=0.0,
            nfev=1,
            x=x0,
        )

    monkeypatch.setattr(solver_module, "least_squares", fake_least_squares)
    BoundedSolver(ResidualBuilder(spec), spec.solver).solve()
    np.testing.assert_allclose(observed["x_scale"], np.array([3.0]))


def test_linear_relation_module_solves_y_equals_ax_plus_b() -> None:
    spec = make_system(
        {
            "system_name": "linear_solve",
            "components": [
                {
                    "id": "rel",
                    "type": "LinearRelationModule",
                    "parameters": {
                        "a": 2.0,
                        "b": 1.0,
                        "x_lower_bound": -10.0,
                        "x_upper_bound": 10.0,
                        "x_initial_guess": 0.0,
                        "x_scale": 1.0,
                        "y_lower_bound": -20.0,
                        "y_upper_bound": 20.0,
                        "y_initial_guess": 0.0,
                        "y_scale": 1.0,
                        "residual_scale": 1.0,
                    },
                }
            ],
            "boundaries": [{"variable": "rel.x", "value": 2.0}],
        }
    )
    result = BoundedSolver(ResidualBuilder(spec), spec.solver).solve()
    assert result.optimization_success
    assert result.audit_pass
    assert abs(result.variables["rel.x"] - 2.0) < 1e-6
    assert abs(result.variables["rel.y"] - 5.0) < 1e-5


def test_range_check_post_check_does_not_pull_solution() -> None:
    spec = make_system(
        {
            "system_name": "range_post_check_solver",
            "components": [
                {
                    "id": "rel",
                    "type": "LinearRelationModule",
                    "parameters": {
                        "a": 1.0,
                        "b": 0.0,
                        "x_lower_bound": -10.0,
                        "x_upper_bound": 10.0,
                        "x_initial_guess": 0.0,
                        "x_scale": 1.0,
                        "y_lower_bound": -10.0,
                        "y_upper_bound": 10.0,
                        "y_initial_guess": 0.0,
                        "y_scale": 1.0,
                        "residual_scale": 1.0,
                    },
                },
                {
                    "id": "range",
                    "type": "RangeCheckModule",
                    "parameters": {
                        "variable": "rel.x",
                        "upper_bound": 1.0,
                        "residual_scale": 1.0,
                    },
                },
            ],
            "boundaries": [{"variable": "rel.x", "value": 2.0}],
        }
    )
    result = BoundedSolver(ResidualBuilder(spec), spec.solver).solve()
    assert result.optimization_success
    assert result.audit_pass
    assert result.max_abs_normalized_residual < 1e-6
    assert abs(result.variables["rel.x"] - 2.0) < 1e-6
    assert abs(result.variables["rel.y"] - 2.0) < 1e-6
