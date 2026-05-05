from __future__ import annotations

from pathlib import Path

import pytest

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


def test_default_registry_includes_mechanical_helpers() -> None:
    registered = set(default_module_registry().registered_types())
    assert {
        "ForceVelocityPowerModule",
        "LinearSpringForceModule",
        "ViscousDamperForceModule",
        "TranslationalInertiaForceModule",
        "RotationalInertiaTorqueModule",
    }.issubset(registered)


def test_force_velocity_power_zero_residual_and_sign() -> None:
    record = record_for(
        one_module("ForceVelocityPowerModule", {}),
        {"m.force_N": 100.0, "m.velocity_m_s": 2.0, "m.P_W": 200.0},
    )
    reverse = record_for(
        one_module("ForceVelocityPowerModule", {}),
        {"m.force_N": 100.0, "m.velocity_m_s": -2.0, "m.P_W": -200.0},
    )
    assert record.value == pytest.approx(0.0)
    assert reverse.value == pytest.approx(0.0)
    assert record.diagnostic_key == "force_velocity_power_mismatch"
    assert record.role == "equation"


def test_force_velocity_power_invalid_parameter_fails() -> None:
    with pytest.raises(ValueError, match="residual_scale_W"):
        ResidualBuilder(one_module("ForceVelocityPowerModule", {"residual_scale_W": 0.0})).build_registry()


def test_linear_spring_force_zero_residual_and_invalid_stiffness() -> None:
    record = record_for(
        one_module("LinearSpringForceModule", {"stiffness_N_m": 1000.0}),
        {"m.displacement_m": 0.01, "m.force_N": 10.0},
    )
    assert record.value == pytest.approx(0.0)
    assert record.diagnostic_key == "linear_spring_force_mismatch"
    assert record.role == "equation"

    with pytest.raises(ValueError, match="stiffness_N_m"):
        ResidualBuilder(one_module("LinearSpringForceModule", {"stiffness_N_m": -1.0})).build_registry()


def test_viscous_damper_force_zero_residual_and_invalid_damping() -> None:
    record = record_for(
        one_module("ViscousDamperForceModule", {"damping_N_s_m": 50.0}),
        {"m.velocity_m_s": 2.0, "m.force_N": 100.0},
    )
    assert record.value == pytest.approx(0.0)
    assert record.diagnostic_key == "viscous_damper_force_mismatch"
    assert record.role == "equation"

    with pytest.raises(ValueError, match="damping_N_s_m"):
        ResidualBuilder(one_module("ViscousDamperForceModule", {"damping_N_s_m": -1.0})).build_registry()


def test_translational_inertia_force_zero_residual_and_invalid_mass() -> None:
    record = record_for(
        one_module("TranslationalInertiaForceModule", {"mass_kg": 10.0}),
        {"m.acceleration_m_s2": 3.0, "m.force_N": 30.0},
    )
    assert record.value == pytest.approx(0.0)
    assert record.diagnostic_key == "translational_inertia_force_mismatch"
    assert record.role == "equation"

    with pytest.raises(ValueError, match="mass_kg"):
        ResidualBuilder(one_module("TranslationalInertiaForceModule", {"mass_kg": 0.0})).build_registry()


def test_rotational_inertia_torque_zero_residual_and_invalid_inertia() -> None:
    record = record_for(
        one_module("RotationalInertiaTorqueModule", {"inertia_kg_m2": 2.0}),
        {"m.angular_acceleration_rad_s2": 10.0, "m.torque_Nm": 20.0},
    )
    assert record.value == pytest.approx(0.0)
    assert record.diagnostic_key == "rotational_inertia_torque_mismatch"
    assert record.role == "equation"

    with pytest.raises(ValueError, match="inertia_kg_m2"):
        ResidualBuilder(one_module("RotationalInertiaTorqueModule", {"inertia_kg_m2": 0.0})).build_registry()


@pytest.mark.parametrize(
    "example",
    [
        "force_velocity_power.yaml",
        "linear_spring_force.yaml",
        "viscous_damper_force.yaml",
        "translational_inertia_force.yaml",
        "rotational_inertia_torque.yaml",
    ],
)
def test_mechanical_yaml_examples_solve(example: str) -> None:
    spec = load_system_spec(ROOT / "examples" / "foundation" / example)
    result = BoundedSolver(ResidualBuilder(spec), spec.solver).solve()
    assert result.optimization_success
    assert result.audit_pass
