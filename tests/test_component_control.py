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
        {"system_name": module_type, "components": [{"id": "m", "type": module_type, "parameters": parameters}]}
    )


def records_for(spec: SystemSpec, values: dict[str, float]):
    builder = ResidualBuilder(spec)
    x = builder.build_registry().dict_to_vector(values)
    return builder.diagnostic_residual_records(x)


def test_registry_includes_component_control_modules() -> None:
    assert {"PIDControllerStepModule", "ActuatorFirstOrderSaturationModule"}.issubset(
        set(default_module_registry().registered_types())
    )


def test_pid_controller_step_p_pi_pid_and_saturation() -> None:
    p_only = records_for(
        one_module("PIDControllerStepModule", {"Kp": 2.0, "dt_s": 1.0}),
        {
            "m.setpoint": 10.0,
            "m.measurement": 7.0,
            "m.error": 3.0,
            "m.error_previous": 3.0,
            "m.integral_previous": 0.0,
            "m.integral_current": 3.0,
            "m.derivative_error": 0.0,
            "m.output_unsaturated": 6.0,
            "m.output": 6.0,
        },
    )
    assert all(record.value == pytest.approx(0.0) for record in p_only)
    assert {record.role for record in p_only} == {"equation"}

    pid = records_for(
        one_module("PIDControllerStepModule", {"Kp": 2.0, "Ki": 0.5, "Kd": 0.1, "bias": 1.0, "dt_s": 0.5}),
        {
            "m.setpoint": 10.0,
            "m.measurement": 7.0,
            "m.error": 3.0,
            "m.error_previous": 2.0,
            "m.integral_previous": 1.0,
            "m.integral_current": 2.5,
            "m.derivative_error": 2.0,
            "m.output_unsaturated": 8.45,
            "m.output": 8.45,
        },
    )
    assert all(record.value == pytest.approx(0.0) for record in pid)

    saturated = records_for(
        one_module(
            "PIDControllerStepModule",
            {"Kp": 10.0, "dt_s": 1.0, "output_lower": 0.0, "output_upper": 5.0},
        ),
        {
            "m.setpoint": 10.0,
            "m.measurement": 9.0,
            "m.error": 1.0,
            "m.error_previous": 1.0,
            "m.integral_previous": 0.0,
            "m.integral_current": 1.0,
            "m.derivative_error": 0.0,
            "m.output_unsaturated": 10.0,
            "m.output": 5.0,
        },
    )
    assert saturated[-1].value == pytest.approx(0.0)
    assert saturated[-1].diagnostic_key == "pid_saturated_output_mismatch"


def test_pid_controller_invalid_parameters_fail() -> None:
    with pytest.raises(ValueError, match="dt_s"):
        ResidualBuilder(one_module("PIDControllerStepModule", {"dt_s": 0.0})).build_registry()
    with pytest.raises(ValueError, match="output_lower"):
        ResidualBuilder(
            one_module("PIDControllerStepModule", {"dt_s": 1.0, "output_lower": 1.0, "output_upper": 1.0})
        ).build_registry()


def test_actuator_first_order_saturation_zero_and_invalid_parameters() -> None:
    record = records_for(
        one_module("ActuatorFirstOrderSaturationModule", {"tau_s": 2.0, "dt_s": 1.0, "lower": 0.0, "upper": 1.0}),
        {"m.command": 2.0, "m.actual_previous": 0.0, "m.actual_current": 0.5},
    )[0]
    assert record.value == pytest.approx(0.0)
    assert record.diagnostic_key == "actuator_first_order_saturation_mismatch"
    assert record.role == "equation"

    with pytest.raises(ValueError, match="tau_s"):
        ResidualBuilder(
            one_module("ActuatorFirstOrderSaturationModule", {"tau_s": 0.0, "dt_s": 1.0, "lower": 0.0, "upper": 1.0})
        ).build_registry()


@pytest.mark.parametrize(
    "name",
    ["pid_controller_step.yaml", "actuator_first_order_saturation.yaml"],
)
def test_component_control_yaml_examples_solve(name: str) -> None:
    spec = load_system_spec(ROOT / "examples" / "components" / "control" / name)
    result = BoundedSolver(ResidualBuilder(spec), spec.solver).solve()
    assert result.optimization_success
    assert result.audit_pass


def test_conflict_pid_controller_step_fails_audit() -> None:
    spec = load_system_spec(ROOT / "examples" / "components" / "control" / "conflict_pid_controller_step.yaml")
    builder = ResidualBuilder(spec)
    result = BoundedSolver(builder, spec.solver).solve()
    report = DiagnosticReporter().generate(spec, builder, result)
    assert result.optimization_success
    assert not result.audit_pass
    assert report.top_residuals[0].diagnostic_key == "pid_saturated_output_mismatch"
