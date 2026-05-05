from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from physicsguard.core.diagnostics import DiagnosticReporter
from physicsguard.core.residual import ResidualBuilder
from physicsguard.core.solver import BoundedSolver
from physicsguard.io.yaml_loader import load_system_spec
from physicsguard.modules.registry import default_module_registry
from physicsguard.schema.system_spec import SystemSpec


ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples" / "components" / "control_sensor_actuator"


def one_module(module_type: str, parameters: dict) -> SystemSpec:
    return SystemSpec.model_validate(
        {"system_name": module_type, "components": [{"id": "m", "type": module_type, "parameters": parameters}]}
    )


def solve_system(spec: SystemSpec):
    builder = ResidualBuilder(spec)
    result = BoundedSolver(builder, spec.solver).solve()
    report = DiagnosticReporter().generate(spec, builder, result, top_n=80)
    return result, report


def solve_example(name: str):
    return solve_system(load_system_spec(EXAMPLES / name))


def test_registry_includes_control_sensor_actuator_modules() -> None:
    assert {
        "GainScheduledPIDModule",
        "AntiWindupClampModule",
        "MapAxisBoundsCheckModule",
        "MapMonotonicityCheckModule",
        "SensorLowPassFilterStepModule",
        "ActuatorDeadZoneModule",
        "ActuatorPositionFeedbackModule",
        "SignalDelayStepModule",
        "SampleAndHoldModule",
        "UnitConversionAuditModule",
    }.issubset(set(default_module_registry().registered_types()))


@pytest.mark.parametrize(
    "name",
    [
        "gain_scheduled_pid.yaml",
        "anti_windup_clamp.yaml",
        "map_axis_bounds_check.yaml",
        "map_monotonicity_check.yaml",
        "sensor_low_pass_filter_step.yaml",
        "actuator_dead_zone.yaml",
        "actuator_position_feedback.yaml",
        "signal_delay_step.yaml",
        "sample_and_hold.yaml",
        "unit_conversion_audit.yaml",
    ],
)
def test_control_sensor_actuator_clean_examples_solve(name: str) -> None:
    result, report = solve_example(name)
    assert result.optimization_success
    assert result.audit_pass
    assert np.isfinite(result.residual_norm)
    assert all(item.role in {"equation", "boundary", "post_check"} for item in report.top_residuals)


@pytest.mark.parametrize(
    ("name", "expected_key"),
    [
        ("conflict_actuator_position_feedback.yaml", "actuator_command_position_mismatch"),
        ("conflict_unit_conversion_audit.yaml", "unit_conversion_audit_mismatch"),
    ],
)
def test_control_sensor_actuator_conflict_examples_fail_audit(name: str, expected_key: str) -> None:
    result, report = solve_example(name)
    assert result.optimization_success
    assert not result.audit_pass
    assert report.top_residuals[0].diagnostic_key == expected_key


@pytest.mark.parametrize(
    ("module_type", "parameters", "message"),
    [
        (
            "GainScheduledPIDModule",
            {"schedule_points": [0.0, 0.0], "Kp_points": [1.0, 1.0], "Ki_points": [0.0, 0.0], "Kd_points": [0.0, 0.0]},
            "schedule_points",
        ),
        (
            "GainScheduledPIDModule",
            {"schedule_points": [0.0, 1.0], "Kp_points": [1.0], "Ki_points": [0.0, 0.0], "Kd_points": [0.0, 0.0]},
            "Kp_points",
        ),
        ("AntiWindupClampModule", {"integral_lower": 1.0, "integral_upper": 0.0, "output_lower": 0.0, "output_upper": 1.0}, "integral_lower"),
        ("MapAxisBoundsCheckModule", {"variables": ["x.y"], "lower_bounds": [1.0], "upper_bounds": [0.0]}, "lower bound"),
        ("MapMonotonicityCheckModule", {"values": [1.0, 2.0], "expected": "flat"}, "expected"),
        ("SensorLowPassFilterStepModule", {"tau_s": 0.0, "dt_s": 1.0}, "tau_s"),
        ("SensorLowPassFilterStepModule", {"tau_s": 1.0, "dt_s": 0.0}, "dt_s"),
        ("ActuatorDeadZoneModule", {"dead_zone": -1.0}, "dead_zone"),
        ("UnitConversionAuditModule", {"factor": float("nan")}, "factor"),
    ],
)
def test_control_sensor_actuator_invalid_parameters_fail(module_type: str, parameters: dict, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        ResidualBuilder(one_module(module_type, parameters)).build_registry()


def test_gain_scheduled_pid_interpolation_zero_residual() -> None:
    spec = one_module(
        "GainScheduledPIDModule",
        {
            "schedule_points": [0.0, 1.0],
            "Kp_points": [1.0, 3.0],
            "Ki_points": [0.0, 0.0],
            "Kd_points": [0.0, 0.0],
        },
    )
    builder = ResidualBuilder(spec)
    registry = builder.build_registry()
    vector = registry.dict_to_vector(
        {
            "m.schedule_variable": 0.5,
            "m.setpoint": 10.0,
            "m.measurement": 8.0,
            "m.error": 2.0,
            "m.integral_error": 0.0,
            "m.derivative_error": 0.0,
            "m.output": 4.0,
        }
    )
    records = builder.diagnostic_residual_records(vector)
    assert {record.diagnostic_key for record in records} == {
        "gain_scheduled_pid_error_mismatch",
        "gain_scheduled_pid_output_mismatch",
    }
    assert all(record.role == "equation" for record in records)
    assert all(record.normalized_value == pytest.approx(0.0) for record in records)


def test_anti_windup_post_check_does_not_pull_solution() -> None:
    spec = SystemSpec.model_validate(
        {
            "system_name": "anti_windup_violation",
            "components": [
                {
                    "id": "aw",
                    "type": "AntiWindupClampModule",
                    "parameters": {"integral_lower": -1.0, "integral_upper": 1.0, "output_lower": 0.0, "output_upper": 1.0},
                }
            ],
            "boundaries": [
                {"variable": "aw.integral_state", "value": 2.0},
                {"variable": "aw.output_unsaturated", "value": 2.0},
                {"variable": "aw.output_saturated", "value": 1.5},
            ],
        }
    )
    result, report = solve_system(spec)
    assert result.audit_pass
    assert report.top_residuals[0].diagnostic_key == "anti_windup_integral_clamp_violation"
    assert report.top_residuals[0].role == "post_check"


def test_map_axis_bounds_post_check_and_missing_variable_behavior() -> None:
    spec = SystemSpec.model_validate(
        {
            "system_name": "map_axis_violation",
            "components": [
                {"id": "d", "type": "DummyResidualModule", "parameters": {"target": 2.0}},
                {
                    "id": "bounds",
                    "type": "MapAxisBoundsCheckModule",
                    "parameters": {"variables": ["d.x"], "lower_bounds": [0.0], "upper_bounds": [1.0]},
                },
            ],
            "boundaries": [{"variable": "d.x", "value": 2.0}],
        }
    )
    result, report = solve_system(spec)
    assert result.audit_pass
    assert report.top_residuals[0].diagnostic_key == "map_axis_bounds_violation"
    assert report.top_residuals[0].role == "post_check"

    missing = one_module("MapAxisBoundsCheckModule", {"variables": ["missing.x"], "lower_bounds": [0.0], "upper_bounds": [1.0]})
    builder = ResidualBuilder(missing)
    registry = builder.build_registry()
    with pytest.raises(KeyError, match="missing.x"):
        builder.diagnostic_residual_records(registry.initial_vector())


def test_map_monotonicity_post_check_reports_violation_without_solver_pull() -> None:
    spec = SystemSpec.model_validate(
        {
            "system_name": "map_monotonicity_violation",
            "components": [
                {"id": "d", "type": "DummyResidualModule", "parameters": {"target": 0.0}},
                {"id": "m", "type": "MapMonotonicityCheckModule", "parameters": {"values": [1.0, 0.5, 2.0], "expected": "increasing"}},
            ],
            "boundaries": [{"variable": "d.x", "value": 0.0}],
        }
    )
    result, report = solve_system(spec)
    assert result.audit_pass
    assert report.top_residuals[0].diagnostic_key == "map_monotonicity_violation"
    assert report.top_residuals[0].role == "post_check"


@pytest.mark.parametrize(
    ("module_type", "values", "expected_key"),
    [
        ("ActuatorDeadZoneModule", {"m.command": 0.05, "m.output": 0.0}, "actuator_dead_zone_mismatch"),
        ("ActuatorDeadZoneModule", {"m.command": 0.2, "m.output": 0.1}, "actuator_dead_zone_mismatch"),
        ("SampleAndHoldModule", {"m.input_current": 10.0, "m.output_previous": 4.0, "m.output_current": 4.0, "m.hold_flag": 1.0}, "sample_and_hold_mismatch"),
        ("SampleAndHoldModule", {"m.input_current": 10.0, "m.output_previous": 4.0, "m.output_current": 10.0, "m.hold_flag": 0.0}, "sample_and_hold_mismatch"),
    ],
)
def test_piecewise_control_relations_zero_residual(module_type: str, values: dict[str, float], expected_key: str) -> None:
    parameters = {"dead_zone": 0.1} if module_type == "ActuatorDeadZoneModule" else {}
    builder = ResidualBuilder(one_module(module_type, parameters))
    registry = builder.build_registry()
    vector = registry.dict_to_vector(values)
    records = builder.diagnostic_residual_records(vector)
    assert records[0].diagnostic_key == expected_key
    assert records[0].normalized_value == pytest.approx(0.0)
