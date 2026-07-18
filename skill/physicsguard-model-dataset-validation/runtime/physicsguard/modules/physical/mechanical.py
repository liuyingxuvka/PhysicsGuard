"""Low-fidelity mechanical helper audit modules."""

from __future__ import annotations

from typing import Any

import numpy as np

from physicsguard.core.registry import VariableRecord, VariableRegistry
from physicsguard.core.residual import ResidualRecord
from physicsguard.modules.base import BaseModule
from physicsguard.modules.physical._common import (
    metadata,
    nonnegative_float,
    owned_record,
    positive_float,
    required,
    required_positive,
    value,
)


class ForceVelocityPowerModule(BaseModule):
    """Translational mechanical power relation P = force * velocity."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "ForceVelocityPowerModule", parameters)
        self.residual_scale_W = positive_float(
            parameters.get("residual_scale_W", 1000.0),
            "residual_scale_W",
        )
        self.records = [
            _force_record(component_id, parameters),
            owned_record(
                component_id,
                parameters,
                "velocity_m_s",
                "m/s",
                "velocity_lower_bound",
                "velocity_upper_bound",
                "velocity_initial_guess",
                "velocity_scale",
                -1e5,
                1e5,
                1.0,
                1.0,
            ),
            _power_record(component_id, parameters, "P_W", "P", 1000.0),
        ]

    def declare_variables(self) -> list[VariableRecord]:
        return list(self.records)

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        force = value(x, registry, self.component_id, "force_N")
        velocity = value(x, registry, self.component_id, "velocity_m_s")
        power = value(x, registry, self.component_id, "P_W")
        return [
            ResidualRecord(
                name=f"{self.component_id}.force_velocity_power",
                value=power - force * velocity,
                scale=self.residual_scale_W,
                source=self.component_id,
                role="equation",
                diagnostic_key="force_velocity_power_mismatch",
                description="Translational power residual P - force*velocity.",
            )
        ]

    def metadata(self) -> dict[str, Any]:
        return metadata(
            self,
            "mechanical",
            ["algebraic mechanical power relation", "no losses", "no dynamics"],
        )


class LinearSpringForceModule(BaseModule):
    """Linear spring force relation."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "LinearSpringForceModule", parameters)
        self.stiffness_N_m = nonnegative_float(required(parameters, "stiffness_N_m"), "stiffness_N_m")
        self.residual_scale_N = positive_float(
            parameters.get("residual_scale_N", 1.0),
            "residual_scale_N",
        )
        self.records = [
            owned_record(
                component_id,
                parameters,
                "displacement_m",
                "m",
                "displacement_lower_bound",
                "displacement_upper_bound",
                "displacement_initial_guess",
                "displacement_scale",
                -1e3,
                1e3,
                0.0,
                1.0,
            ),
            _force_record(component_id, parameters),
        ]

    def declare_variables(self) -> list[VariableRecord]:
        return list(self.records)

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        displacement = value(x, registry, self.component_id, "displacement_m")
        force = value(x, registry, self.component_id, "force_N")
        return [
            ResidualRecord(
                name=f"{self.component_id}.linear_spring_force",
                value=force - self.stiffness_N_m * displacement,
                scale=self.residual_scale_N,
                source=self.component_id,
                role="equation",
                diagnostic_key="linear_spring_force_mismatch",
                description="Linear spring residual force - stiffness*displacement.",
            )
        ]

    def metadata(self) -> dict[str, Any]:
        return metadata(
            self,
            "mechanical",
            ["linear spring", "no preload unless modeled separately", "no nonlinear stiffness"],
        )


class ViscousDamperForceModule(BaseModule):
    """Linear viscous damper force relation."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "ViscousDamperForceModule", parameters)
        self.damping_N_s_m = nonnegative_float(required(parameters, "damping_N_s_m"), "damping_N_s_m")
        self.residual_scale_N = positive_float(
            parameters.get("residual_scale_N", 1.0),
            "residual_scale_N",
        )
        self.records = [
            owned_record(
                component_id,
                parameters,
                "velocity_m_s",
                "m/s",
                "velocity_lower_bound",
                "velocity_upper_bound",
                "velocity_initial_guess",
                "velocity_scale",
                -1e5,
                1e5,
                1.0,
                1.0,
            ),
            _force_record(component_id, parameters),
        ]

    def declare_variables(self) -> list[VariableRecord]:
        return list(self.records)

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        velocity = value(x, registry, self.component_id, "velocity_m_s")
        force = value(x, registry, self.component_id, "force_N")
        return [
            ResidualRecord(
                name=f"{self.component_id}.viscous_damper_force",
                value=force - self.damping_N_s_m * velocity,
                scale=self.residual_scale_N,
                source=self.component_id,
                role="equation",
                diagnostic_key="viscous_damper_force_mismatch",
                description="Viscous damper residual force - damping*velocity.",
            )
        ]

    def metadata(self) -> dict[str, Any]:
        return metadata(
            self,
            "mechanical",
            ["linear viscous damping", "no nonlinear damping", "no friction model"],
        )


class TranslationalInertiaForceModule(BaseModule):
    """Newton's second law for a lumped translational inertia."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "TranslationalInertiaForceModule", parameters)
        self.mass_kg = required_positive(parameters, "mass_kg")
        self.residual_scale_N = positive_float(
            parameters.get("residual_scale_N", 1.0),
            "residual_scale_N",
        )
        self.records = [
            owned_record(
                component_id,
                parameters,
                "acceleration_m_s2",
                "m/s^2",
                "acceleration_lower_bound",
                "acceleration_upper_bound",
                "acceleration_initial_guess",
                "acceleration_scale",
                -1e5,
                1e5,
                1.0,
                1.0,
            ),
            _force_record(component_id, parameters),
        ]

    def declare_variables(self) -> list[VariableRecord]:
        return list(self.records)

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        acceleration = value(x, registry, self.component_id, "acceleration_m_s2")
        force = value(x, registry, self.component_id, "force_N")
        return [
            ResidualRecord(
                name=f"{self.component_id}.translational_inertia_force",
                value=force - self.mass_kg * acceleration,
                scale=self.residual_scale_N,
                source=self.component_id,
                role="equation",
                diagnostic_key="translational_inertia_force_mismatch",
                description="Translational inertia residual force - mass*acceleration.",
            )
        ]

    def metadata(self) -> dict[str, Any]:
        return metadata(
            self,
            "mechanical",
            ["lumped mass", "no friction", "no constraints", "no rotational coupling"],
        )


class RotationalInertiaTorqueModule(BaseModule):
    """Rotational inertia torque relation."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "RotationalInertiaTorqueModule", parameters)
        self.inertia_kg_m2 = required_positive(parameters, "inertia_kg_m2")
        self.residual_scale_Nm = positive_float(
            parameters.get("residual_scale_Nm", 1.0),
            "residual_scale_Nm",
        )
        self.records = [
            owned_record(
                component_id,
                parameters,
                "angular_acceleration_rad_s2",
                "rad/s^2",
                "angular_acceleration_lower_bound",
                "angular_acceleration_upper_bound",
                "angular_acceleration_initial_guess",
                "angular_acceleration_scale",
                -1e5,
                1e5,
                1.0,
                1.0,
            ),
            owned_record(
                component_id,
                parameters,
                "torque_Nm",
                "N*m",
                "torque_lower_bound",
                "torque_upper_bound",
                "torque_initial_guess",
                "torque_scale",
                -1e8,
                1e8,
                1.0,
                1.0,
            ),
        ]

    def declare_variables(self) -> list[VariableRecord]:
        return list(self.records)

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        acceleration = value(x, registry, self.component_id, "angular_acceleration_rad_s2")
        torque = value(x, registry, self.component_id, "torque_Nm")
        return [
            ResidualRecord(
                name=f"{self.component_id}.rotational_inertia_torque",
                value=torque - self.inertia_kg_m2 * acceleration,
                scale=self.residual_scale_Nm,
                source=self.component_id,
                role="equation",
                diagnostic_key="rotational_inertia_torque_mismatch",
                description="Rotational inertia residual torque - inertia*angular_acceleration.",
            )
        ]

    def metadata(self) -> dict[str, Any]:
        return metadata(
            self,
            "mechanical",
            ["lumped rotational inertia", "no friction", "no gearbox", "no drivetrain model"],
        )


def _force_record(component_id: str, parameters: dict[str, Any]) -> VariableRecord:
    return owned_record(
        component_id,
        parameters,
        "force_N",
        "N",
        "force_lower_bound",
        "force_upper_bound",
        "force_initial_guess",
        "force_scale",
        -1e8,
        1e8,
        1.0,
        1.0,
    )


def _power_record(
    component_id: str,
    parameters: dict[str, Any],
    local_name: str,
    prefix: str,
    initial_default: float,
) -> VariableRecord:
    return owned_record(
        component_id,
        parameters,
        local_name,
        "W",
        f"{prefix}_lower_bound",
        f"{prefix}_upper_bound",
        f"{prefix}_initial_guess",
        f"{prefix}_scale",
        -1e8,
        1e8,
        initial_default,
        1000.0,
    )
