"""Component-level drivetrain and vehicle longitudinal audit modules."""

from __future__ import annotations

import math
from typing import Any

import numpy as np

from physicsguard.core.registry import VariableRecord, VariableRegistry
from physicsguard.core.residual import ResidualRecord
from physicsguard.modules.base import BaseModule
from physicsguard.modules.components._common import (
    bounded_record,
    check_denominator,
    component_metadata,
    force_record,
    fraction_record,
    positive_float,
    power_record,
    residual_record,
    required_positive,
    scalar_record,
    speed_record,
    torque_record,
    value,
)


class GearboxSimpleModule(BaseModule):
    """Low-fidelity gearbox speed, torque, and power audit."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "GearboxSimpleModule", parameters)
        self.gear_ratio = required_positive(parameters, "gear_ratio")
        self.speed_scale = positive_float(parameters.get("residual_scale_speed", 1.0), "residual_scale_speed")
        self.torque_scale = positive_float(parameters.get("residual_scale_torque", 1.0), "residual_scale_torque")
        self.power_scale = positive_float(parameters.get("residual_scale_power_W", 1000.0), "residual_scale_power_W")
        self.records = [
            bounded_record(component_id, parameters, "omega_in_rad_s", "rad/s", "omega_in", -1e5, 1e5, 100.0, 100.0),
            torque_record(component_id, parameters, "torque_in_Nm", "torque_in"),
            bounded_record(component_id, parameters, "omega_out_rad_s", "rad/s", "omega_out", -1e5, 1e5, 50.0, 100.0),
            torque_record(component_id, parameters, "torque_out_Nm", "torque_out"),
            fraction_record(component_id, parameters, "efficiency", "efficiency", 0.95),
        ]

    def declare_variables(self) -> list[VariableRecord]:
        return list(self.records)

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        oi = value(x, registry, self.component_id, "omega_in_rad_s")
        ti = value(x, registry, self.component_id, "torque_in_Nm")
        oo = value(x, registry, self.component_id, "omega_out_rad_s")
        to = value(x, registry, self.component_id, "torque_out_Nm")
        eff = value(x, registry, self.component_id, "efficiency")
        return [
            residual_record(self, "gearbox_speed_ratio", oo - oi / self.gear_ratio, self.speed_scale, "gearbox_speed_ratio_mismatch", "Gearbox speed ratio residual."),
            residual_record(self, "gearbox_torque_ratio", to - ti * self.gear_ratio * eff, self.torque_scale, "gearbox_torque_ratio_mismatch", "Gearbox torque ratio residual."),
            residual_record(self, "gearbox_power_consistency", ti * oi * eff - to * oo, self.power_scale, "gearbox_power_consistency_mismatch", "Gearbox power consistency residual."),
        ]

    def metadata(self) -> dict[str, Any]:
        return component_metadata(self, "drivetrain_vehicle", ["fixed gear ratio", "algebraic efficiency", "no inertia", "no shifting dynamics", "no losses beyond efficiency"])


class WheelTorqueForceModule(BaseModule):
    """Wheel torque to longitudinal force audit."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "WheelTorqueForceModule", parameters)
        self.scale = positive_float(parameters.get("residual_scale_N", 100.0), "residual_scale_N")
        self.den_min = positive_float(parameters.get("denominator_min_abs", 1e-12), "denominator_min_abs")
        self.records = [
            torque_record(component_id, parameters, "wheel_torque_Nm", "wheel_torque"),
            bounded_record(component_id, parameters, "wheel_radius_m", "m", "wheel_radius", 1e-9, 10.0, 0.3, 0.1),
            force_record(component_id, parameters, "longitudinal_force_N", "longitudinal_force", 333.333333333),
        ]

    def declare_variables(self) -> list[VariableRecord]:
        return list(self.records)

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        torque = value(x, registry, self.component_id, "wheel_torque_Nm")
        radius = value(x, registry, self.component_id, "wheel_radius_m")
        check_denominator(radius, self.den_min, f"{self.component_id}.wheel_radius_m")
        force = value(x, registry, self.component_id, "longitudinal_force_N")
        return [residual_record(self, "wheel_torque_force", force - torque / radius, self.scale, "wheel_torque_force_mismatch", "Wheel torque-force residual.")]

    def metadata(self) -> dict[str, Any]:
        return component_metadata(self, "drivetrain_vehicle", ["no tire slip model", "no rolling resistance", "no traction limit"])


class VehicleRoadLoadModule(BaseModule):
    """Low-fidelity vehicle road-load audit."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "VehicleRoadLoadModule", parameters)
        self.mass = required_positive(parameters, "mass_kg")
        self.c0 = float(parameters.get("C0_N", 0.0))
        self.c1 = float(parameters.get("C1_N_s_m", 0.0))
        self.c2 = float(parameters.get("C2_N_s2_m2", 0.0))
        self.g = positive_float(parameters.get("g_m_s2", 9.80665), "g_m_s2")
        self.scale = positive_float(parameters.get("residual_scale_N", 100.0), "residual_scale_N")
        self.records = [
            speed_record(component_id, parameters, "vehicle_speed_m_s", "vehicle_speed", 20.0),
            scalar_record(component_id, parameters, "road_grade_rad", "road_grade", 0.0, 0.1, "rad"),
            force_record(component_id, parameters, "road_load_force_N", "road_load_force", 500.0),
        ]

    def declare_variables(self) -> list[VariableRecord]:
        return list(self.records)

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        speed = value(x, registry, self.component_id, "vehicle_speed_m_s")
        grade = value(x, registry, self.component_id, "road_grade_rad")
        road_load = value(x, registry, self.component_id, "road_load_force_N")
        expected = self.c0 + self.c1 * speed + self.c2 * speed * abs(speed) + self.mass * self.g * math.sin(grade)
        return [residual_record(self, "vehicle_road_load", road_load - expected, self.scale, "vehicle_road_load_mismatch", "Vehicle road-load residual.")]

    def metadata(self) -> dict[str, Any]:
        return component_metadata(self, "drivetrain_vehicle", ["simple road load", "no tire slip", "no wind direction", "no drivetrain losses"])


class VehicleLongitudinalDynamicsStepModule(BaseModule):
    """Single-step vehicle speed audit."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "VehicleLongitudinalDynamicsStepModule", parameters)
        self.mass = required_positive(parameters, "mass_kg")
        self.dt = required_positive(parameters, "dt_s")
        self.scale = positive_float(parameters.get("residual_scale_m_s", 0.1), "residual_scale_m_s")
        self.records = [
            speed_record(component_id, parameters, "speed_previous_m_s", "speed_previous", 20.0),
            speed_record(component_id, parameters, "speed_current_m_s", "speed_current", 20.1),
            force_record(component_id, parameters, "drive_force_N", "drive_force", 1000.0),
            force_record(component_id, parameters, "brake_force_N", "brake_force", 0.0),
            force_record(component_id, parameters, "road_load_force_N", "road_load_force", 500.0),
        ]

    def declare_variables(self) -> list[VariableRecord]:
        return list(self.records)

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        prev = value(x, registry, self.component_id, "speed_previous_m_s")
        cur = value(x, registry, self.component_id, "speed_current_m_s")
        drive = value(x, registry, self.component_id, "drive_force_N")
        brake = value(x, registry, self.component_id, "brake_force_N")
        road = value(x, registry, self.component_id, "road_load_force_N")
        expected = prev + ((drive - brake - road) / self.mass) * self.dt
        return [residual_record(self, "vehicle_longitudinal_speed_step", cur - expected, self.scale, "vehicle_longitudinal_speed_step_mismatch", "Vehicle longitudinal speed step residual.")]

    def metadata(self) -> dict[str, Any]:
        return component_metadata(self, "drivetrain_vehicle", ["single-step longitudinal dynamics", "no tire slip", "no rotational inertia", "no drivetrain dynamics"])


class BrakeSimpleModule(BaseModule):
    """Low-fidelity brake force and power audit."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "BrakeSimpleModule", parameters)
        self.scale = positive_float(parameters.get("residual_scale_W", 1000.0), "residual_scale_W")
        self.records = [
            force_record(component_id, parameters, "brake_force_N", "brake_force", 1000.0),
            speed_record(component_id, parameters, "vehicle_speed_m_s", "vehicle_speed", 20.0),
            power_record(component_id, parameters, "brake_power_W", "brake_power", 20000.0),
        ]

    def declare_variables(self) -> list[VariableRecord]:
        return list(self.records)

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        force = value(x, registry, self.component_id, "brake_force_N")
        speed = value(x, registry, self.component_id, "vehicle_speed_m_s")
        power = value(x, registry, self.component_id, "brake_power_W")
        return [residual_record(self, "brake_power", power - force * speed, self.scale, "brake_power_mismatch", "Brake power residual.")]

    def metadata(self) -> dict[str, Any]:
        return component_metadata(self, "drivetrain_vehicle", ["algebraic braking power", "no thermal brake model", "no ABS/traction", "no tire slip"])


class RegenerativeBrakeSplitModule(BaseModule):
    """Low-fidelity regenerative and friction brake split audit."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "RegenerativeBrakeSplitModule", parameters)
        self.scale = positive_float(parameters.get("residual_scale_W", 1000.0), "residual_scale_W")
        self.records = [
            power_record(component_id, parameters, "brake_power_total_W", "brake_power_total", 10000.0),
            power_record(component_id, parameters, "regen_power_W", "regen_power", 4000.0),
            power_record(component_id, parameters, "friction_brake_power_W", "friction_brake_power", 6000.0),
            fraction_record(component_id, parameters, "regen_fraction", "regen_fraction", 0.4),
        ]

    def declare_variables(self) -> list[VariableRecord]:
        return list(self.records)

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        total = value(x, registry, self.component_id, "brake_power_total_W")
        regen = value(x, registry, self.component_id, "regen_power_W")
        friction = value(x, registry, self.component_id, "friction_brake_power_W")
        frac = value(x, registry, self.component_id, "regen_fraction")
        return [
            residual_record(self, "regen_brake_power_split", regen - frac * total, self.scale, "regen_brake_power_split_mismatch", "Regenerative brake split residual."),
            residual_record(self, "friction_brake_power_split", friction - (1.0 - frac) * total, self.scale, "friction_brake_power_split_mismatch", "Friction brake split residual."),
            residual_record(self, "brake_power_balance", total - regen - friction, self.scale, "brake_power_balance_mismatch", "Brake power balance residual."),
        ]

    def metadata(self) -> dict[str, Any]:
        return component_metadata(self, "drivetrain_vehicle", ["algebraic split", "no battery limit", "no motor limit", "no brake blending dynamics"])
