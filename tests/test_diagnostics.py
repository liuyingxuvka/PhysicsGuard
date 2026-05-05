from __future__ import annotations

import json

import numpy as np

from physicsguard.core.diagnostics import DiagnosticReporter
from physicsguard.core.residual import ResidualBuilder
from physicsguard.core.solver import SolverResult
from physicsguard.schema.system_spec import SystemSpec


def make_result(
    x: np.ndarray,
    variables: dict[str, float],
    optimization_success: bool = True,
    audit_pass: bool | None = None,
    max_abs: float = 0.0,
):
    threshold = 1.0
    return SolverResult(
        optimization_success=optimization_success,
        audit_pass=max_abs <= threshold if audit_pass is None else audit_pass,
        audit_threshold=threshold,
        status=1 if optimization_success else 0,
        message="ok" if optimization_success else "failed",
        cost=0.0,
        optimality=0.0,
        nfev=1,
        max_nfev=10,
        x=x,
        variables=variables,
        residual_norm=max_abs,
        max_abs_normalized_residual=max_abs,
    )


def test_top_residual_ranking_works() -> None:
    spec = SystemSpec.model_validate(
        {
            "system_name": "rank",
            "components": [
                {"id": "a", "type": "DummyResidualModule", "parameters": {"target": 0.0}},
            ],
            "boundaries": [{"variable": "a.x", "value": 10.0}],
        }
    )
    builder = ResidualBuilder(spec)
    result = make_result(np.array([0.0]), {"a.x": 0.0}, max_abs=10.0)
    report = DiagnosticReporter().generate(spec, builder, result, top_n=1)
    assert report.top_residuals[0].source == "boundary"
    assert report.top_residuals[0].role == "boundary"


def test_bound_hit_detection_works() -> None:
    spec = SystemSpec.model_validate(
        {
            "system_name": "bound",
            "components": [
                {
                    "id": "a",
                    "type": "DummyResidualModule",
                    "parameters": {
                        "target": 0.0,
                        "lower_bound": 0.0,
                        "upper_bound": 10.0,
                        "initial_guess": 0.0,
                    },
                },
            ],
        }
    )
    builder = ResidualBuilder(spec)
    result = make_result(np.array([0.0]), {"a.x": 0.0})
    report = DiagnosticReporter().generate(spec, builder, result)
    assert report.bound_hits[0].hit_type == "lower"


def test_json_serialization_works() -> None:
    spec = SystemSpec.model_validate(
        {
            "system_name": "json",
            "components": [
                {"id": "a", "type": "DummyResidualModule", "parameters": {"target": 0.0}},
            ],
        }
    )
    builder = ResidualBuilder(spec)
    result = make_result(np.array([0.0]), {"a.x": 0.0})
    json_text = DiagnosticReporter().to_json(DiagnosticReporter().generate(spec, builder, result))
    assert json.loads(json_text)["system_name"] == "json"
    assert "role" in json.loads(json_text)["top_residuals"][0]


def test_warnings_generated_for_high_residual() -> None:
    spec = SystemSpec.model_validate(
        {
            "system_name": "warn",
            "components": [
                {"id": "a", "type": "DummyResidualModule", "parameters": {"target": 0.0}},
            ],
        }
    )
    builder = ResidualBuilder(spec)
    result = make_result(np.array([11.0]), {"a.x": 11.0}, max_abs=11.0)
    report = DiagnosticReporter().generate(spec, builder, result)
    assert "audit did not pass" in report.warnings
    assert "max normalized residual exceeds audit threshold" in report.warnings
    assert "max normalized residual exceeds 10" in report.warnings


def test_warnings_generated_for_solver_failure() -> None:
    spec = SystemSpec.model_validate(
        {
            "system_name": "failure",
            "components": [
                {"id": "a", "type": "DummyResidualModule", "parameters": {"target": 0.0}},
            ],
        }
    )
    builder = ResidualBuilder(spec)
    result = make_result(np.array([0.0]), {"a.x": 0.0}, optimization_success=False)
    report = DiagnosticReporter().generate(spec, builder, result)
    assert "optimizer did not converge" in report.warnings


def test_report_distinguishes_optimization_success_from_audit_pass() -> None:
    spec = SystemSpec.model_validate(
        {
            "system_name": "conflict",
            "components": [
                {"id": "a", "type": "DummyResidualModule", "parameters": {"target": 5.0}},
            ],
            "boundaries": [{"variable": "a.x", "value": 10.0}],
        }
    )
    builder = ResidualBuilder(spec)
    result = make_result(
        np.array([7.5]),
        {"a.x": 7.5},
        optimization_success=True,
        audit_pass=False,
        max_abs=2.5,
    )
    report = DiagnosticReporter().generate(spec, builder, result)
    assert report.optimization_success
    assert not report.audit_pass
    assert report.audit_threshold == 1.0


def test_conflicting_generic_residual_ranking_reports_generic_mismatch() -> None:
    spec = SystemSpec.model_validate(
        {
            "system_name": "generic_conflict",
            "components": [
                {
                    "id": "rel",
                    "type": "LinearRelationModule",
                    "parameters": {
                        "a": 2.0,
                        "b": 1.0,
                        "x_lower_bound": -10.0,
                        "x_upper_bound": 10.0,
                        "x_initial_guess": 2.0,
                        "x_scale": 1.0,
                        "y_lower_bound": -20.0,
                        "y_upper_bound": 20.0,
                        "y_initial_guess": 0.0,
                        "y_scale": 1.0,
                        "residual_scale": 1.0,
                    },
                },
                {
                    "id": "sum",
                    "type": "ConservationSumModule",
                    "parameters": {
                        "input_variables": ["rel.y"],
                        "output_variables": [],
                        "target": 9.0,
                        "residual_scale": 1.0,
                    },
                },
            ],
            "boundaries": [{"variable": "rel.x", "value": 2.0, "scale": 0.1}],
        }
    )
    builder = ResidualBuilder(spec)
    from physicsguard.core.solver import BoundedSolver

    result = BoundedSolver(builder, spec.solver).solve()
    report = DiagnosticReporter().generate(spec, builder, result)
    assert result.optimization_success
    assert not result.audit_pass
    assert report.top_residuals[0].diagnostic_key in {
        "linear_relation_mismatch",
        "conservation_sum_mismatch",
    }


def test_post_check_residuals_appear_in_diagnostics_without_failing_audit() -> None:
    spec = SystemSpec.model_validate(
        {
            "system_name": "post_check_diagnostics",
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
    builder = ResidualBuilder(spec)
    from physicsguard.core.solver import BoundedSolver

    result = BoundedSolver(builder, spec.solver).solve()
    report = DiagnosticReporter().generate(spec, builder, result)
    assert result.audit_pass
    assert abs(result.variables["rel.x"] - 2.0) < 1e-6
    assert report.top_residuals[0].diagnostic_key == "range_check_violation"
    assert report.top_residuals[0].role == "post_check"
