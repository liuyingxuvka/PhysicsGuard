from __future__ import annotations

from pathlib import Path

import pytest

from physicsguard.core.diagnostics import DiagnosticReporter
from physicsguard.core.residual import ResidualBuilder
from physicsguard.core.solver import BoundedSolver
from physicsguard.io.yaml_loader import load_system_spec
from physicsguard.modules.registry import default_module_registry
from physicsguard.schema.system_spec import SystemSpec


ROOT = Path(__file__).resolve().parents[1]


def one_module(module_type: str, parameters: dict) -> SystemSpec:
    return SystemSpec.model_validate(
        {
            "system_name": module_type,
            "components": [{"id": "m", "type": module_type, "parameters": parameters}],
        }
    )


def record_for(spec: SystemSpec, values: dict[str, float]):
    builder = ResidualBuilder(spec)
    x = builder.build_registry().dict_to_vector(values)
    return builder.diagnostic_residual_records(x)[0]


def solve_control_example(name: str):
    spec = load_system_spec(ROOT / "examples" / "control" / name)
    builder = ResidualBuilder(spec)
    result = BoundedSolver(builder, spec.solver).solve()
    return spec, builder, result


def test_default_registry_includes_batch3_control_modules() -> None:
    registered = set(default_module_registry().registered_types())
    assert {
        "ControlErrorModule",
        "PIDAlgebraicModule",
        "DiscreteIntegratorModule",
        "HysteresisStateCheckModule",
        "BooleanSwitchModule",
        "ThresholdStateCheckModule",
    }.issubset(registered)


def test_control_error_zero_residual_and_sign() -> None:
    record = record_for(
        one_module("ControlErrorModule", {}),
        {"m.setpoint": 10.0, "m.measurement": 7.0, "m.error": 3.0},
    )
    assert record.value == pytest.approx(0.0)
    assert record.diagnostic_key == "control_error_mismatch"
    assert record.role == "equation"

    negative = record_for(
        one_module("ControlErrorModule", {}),
        {"m.setpoint": 10.0, "m.measurement": 7.0, "m.error": -3.0},
    )
    assert negative.value == pytest.approx(-6.0)


def test_control_error_invalid_parameter_fails() -> None:
    with pytest.raises(ValueError, match="residual_scale"):
        ResidualBuilder(one_module("ControlErrorModule", {"residual_scale": 0.0})).build_registry()


def test_pid_algebraic_p_only_and_pid_zero_residual() -> None:
    p_only = record_for(
        one_module("PIDAlgebraicModule", {"Kp": 2.0}),
        {
            "m.error": 3.0,
            "m.integral_error": 0.0,
            "m.derivative_error": 0.0,
            "m.output": 6.0,
        },
    )
    assert p_only.value == pytest.approx(0.0)
    assert p_only.diagnostic_key == "pid_algebraic_mismatch"
    assert p_only.role == "equation"

    pid = record_for(
        one_module("PIDAlgebraicModule", {"Kp": 2.0, "Ki": 0.5, "Kd": 0.1, "bias": 1.0}),
        {
            "m.error": 3.0,
            "m.integral_error": 4.0,
            "m.derivative_error": 5.0,
            "m.output": 9.5,
        },
    )
    assert pid.value == pytest.approx(0.0)


def test_pid_algebraic_conflict_residual() -> None:
    record = record_for(
        one_module("PIDAlgebraicModule", {"Kp": 2.0, "Ki": 0.5, "Kd": 0.1, "bias": 1.0}),
        {
            "m.error": 3.0,
            "m.integral_error": 4.0,
            "m.derivative_error": 5.0,
            "m.output": 30.0,
        },
    )
    assert record.value == pytest.approx(20.5)


def test_pid_invalid_parameter_fails() -> None:
    with pytest.raises(ValueError, match="residual_scale"):
        ResidualBuilder(one_module("PIDAlgebraicModule", {"residual_scale": 0.0})).build_registry()


def test_discrete_integrator_zero_residual_and_invalid_dt() -> None:
    record = record_for(
        one_module("DiscreteIntegratorModule", {"dt_s": 0.5, "gain": 2.0}),
        {"m.state_previous": 1.0, "m.input": 3.0, "m.state_current": 4.0},
    )
    assert record.value == pytest.approx(0.0)
    assert record.diagnostic_key == "discrete_integrator_mismatch"
    assert record.role == "equation"

    with pytest.raises(ValueError, match="dt_s"):
        ResidualBuilder(one_module("DiscreteIntegratorModule", {"dt_s": 0.0})).build_registry()


def test_hysteresis_state_check_cases_and_post_check_role() -> None:
    spec = one_module(
        "HysteresisStateCheckModule",
        {"low_threshold": 4.0, "high_threshold": 6.0},
    )
    on_ok = record_for(spec, {"m.input": 7.0, "m.state": 1.0})
    off_ok = record_for(spec, {"m.input": 3.0, "m.state": 0.0})
    bad = record_for(spec, {"m.input": 3.0, "m.state": 1.0})
    invalid_state = record_for(spec, {"m.input": 5.0, "m.state": 0.5})
    assert on_ok.value == pytest.approx(0.0)
    assert off_ok.value == pytest.approx(0.0)
    assert bad.value == pytest.approx(1.0)
    assert invalid_state.value == pytest.approx(0.5)
    assert bad.diagnostic_key == "hysteresis_state_violation"
    assert bad.role == "post_check"


def test_hysteresis_invalid_parameters_fail() -> None:
    with pytest.raises(ValueError, match="low_threshold"):
        ResidualBuilder(
            one_module(
                "HysteresisStateCheckModule",
                {"low_threshold": 1.0, "high_threshold": 1.0},
            )
        ).build_registry()


def test_boolean_switch_zero_residual_cases() -> None:
    spec = one_module("BooleanSwitchModule", {})
    true_record = record_for(
        spec,
        {"m.condition": 1.0, "m.true_value": 10.0, "m.false_value": -5.0, "m.output": 10.0},
    )
    false_record = record_for(
        spec,
        {"m.condition": 0.0, "m.true_value": 10.0, "m.false_value": -5.0, "m.output": -5.0},
    )
    fractional = record_for(
        spec,
        {"m.condition": 0.5, "m.true_value": 10.0, "m.false_value": -5.0, "m.output": 2.5},
    )
    assert true_record.value == pytest.approx(0.0)
    assert false_record.value == pytest.approx(0.0)
    assert fractional.value == pytest.approx(0.0)
    assert true_record.diagnostic_key == "boolean_switch_mismatch"
    assert true_record.role == "equation"


def test_boolean_switch_invalid_parameter_fails() -> None:
    with pytest.raises(ValueError, match="residual_scale"):
        ResidualBuilder(one_module("BooleanSwitchModule", {"residual_scale": 0.0})).build_registry()


def test_threshold_state_check_correct_wrong_and_invalid() -> None:
    spec = one_module("ThresholdStateCheckModule", {"threshold": 5.0})
    ok = record_for(spec, {"m.input": 6.0, "m.state": 1.0})
    bad = record_for(spec, {"m.input": 6.0, "m.state": 0.0})
    assert ok.value == pytest.approx(0.0)
    assert bad.value == pytest.approx(-1.0)
    assert bad.diagnostic_key == "threshold_state_violation"
    assert bad.role == "post_check"

    with pytest.raises(ValueError, match="threshold"):
        ResidualBuilder(one_module("ThresholdStateCheckModule", {})).build_registry()


@pytest.mark.parametrize(
    "example",
    [
        "control_error.yaml",
        "pid_algebraic.yaml",
        "discrete_integrator.yaml",
        "hysteresis_state_check.yaml",
        "boolean_switch.yaml",
        "threshold_state_check.yaml",
    ],
)
def test_control_pid_yaml_examples_solve(example: str) -> None:
    _, _, result = solve_control_example(example)
    assert result.optimization_success
    assert result.audit_pass


def test_conflict_pid_algebraic_fails_audit() -> None:
    spec, builder, result = solve_control_example("conflict_pid_algebraic.yaml")
    report = DiagnosticReporter().generate(spec, builder, result)
    assert result.optimization_success
    assert not result.audit_pass
    assert report.top_residuals[0].diagnostic_key == "pid_algebraic_mismatch"


def test_hysteresis_post_check_does_not_pull_solution() -> None:
    spec = SystemSpec.model_validate(
        {
            "system_name": "hysteresis_post_check",
            "components": [
                {
                    "id": "h",
                    "type": "HysteresisStateCheckModule",
                    "parameters": {"low_threshold": 4.0, "high_threshold": 6.0},
                }
            ],
            "boundaries": [
                {"variable": "h.input", "value": 3.0},
                {"variable": "h.state", "value": 1.0},
            ],
        }
    )
    builder = ResidualBuilder(spec)
    result = BoundedSolver(builder, spec.solver).solve()
    report = DiagnosticReporter().generate(spec, builder, result)
    assert result.audit_pass
    assert result.variables["h.state"] == pytest.approx(1.0)
    assert report.top_residuals[0].diagnostic_key == "hysteresis_state_violation"
    assert report.top_residuals[0].role == "post_check"
