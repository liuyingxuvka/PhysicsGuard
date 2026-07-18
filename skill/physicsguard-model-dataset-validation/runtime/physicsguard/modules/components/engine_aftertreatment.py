"""Component-level engine and aftertreatment sanity-check modules."""

from __future__ import annotations

from typing import Any

import numpy as np

from physicsguard.core.registry import VariableRecord, VariableRegistry
from physicsguard.core.residual import ResidualRecord
from physicsguard.modules.base import BaseModule
from physicsguard.modules.components._common import (
    bilinear_interp,
    bounded_record,
    check_denominator,
    component_metadata,
    finite_grid,
    force_record,
    fraction_record,
    mass_flow_record,
    positive_float,
    power_record,
    pressure_record,
    residual_record,
    required_nonnegative,
    required_positive,
    scalar_record,
    strictly_increasing_axis,
    temperature_record,
    torque_record,
    value,
)


class EngineTorqueMapModule(BaseModule):
    """Map-based engine torque audit."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "EngineTorqueMapModule", parameters)
        self.speed_points = strictly_increasing_axis(parameters, "speed_points_rad_s")
        self.load_points = strictly_increasing_axis(parameters, "load_points")
        self.torque_values = finite_grid(parameters, "torque_values_Nm", rows=len(self.load_points), cols=len(self.speed_points))
        self.extrapolation = parameters.get("extrapolation", "error")
        if self.extrapolation not in {"error", "hold"}:
            raise ValueError("extrapolation must be 'error' or 'hold'")
        self.scale = positive_float(parameters.get("residual_scale_Nm", 10.0), "residual_scale_Nm")
        self.records = [
            bounded_record(component_id, parameters, "speed_rad_s", "rad/s", "speed", 0.0, 1e5, 100.0, 100.0),
            fraction_record(component_id, parameters, "load_command", "load_command", 0.5),
            torque_record(component_id, parameters, "torque_Nm", "torque"),
        ]

    def declare_variables(self) -> list[VariableRecord]:
        return list(self.records)

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        speed = value(x, registry, self.component_id, "speed_rad_s")
        load = value(x, registry, self.component_id, "load_command")
        torque = value(x, registry, self.component_id, "torque_Nm")
        expected = bilinear_interp(speed, load, self.speed_points, self.load_points, self.torque_values, self.extrapolation, self.component_id)
        return [residual_record(self, "engine_torque_map", torque - expected, self.scale, "engine_torque_map_mismatch", "Engine torque map residual.")]

    def metadata(self) -> dict[str, Any]:
        metadata = component_metadata(self, "engine_aftertreatment", ["map consistency only", "no combustion model", "no transient dynamics"])
        metadata["extrapolation"] = self.extrapolation
        return metadata


class EngineAirFuelRatioModule(BaseModule):
    """Engine air-fuel ratio audit."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "EngineAirFuelRatioModule", parameters)
        self.scale = positive_float(parameters.get("residual_scale", 0.1), "residual_scale")
        self.den_min = positive_float(parameters.get("denominator_min_abs", 1e-12), "denominator_min_abs")
        self.records = [
            mass_flow_record(component_id, parameters, "m_dot_air_kg_s", "m_dot_air", 0.1),
            mass_flow_record(component_id, parameters, "m_dot_fuel_kg_s", "m_dot_fuel", 0.005),
            bounded_record(component_id, parameters, "AFR", None, "AFR", 0.0, 1e4, 20.0, 1.0),
        ]

    def declare_variables(self) -> list[VariableRecord]:
        return list(self.records)

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        air = value(x, registry, self.component_id, "m_dot_air_kg_s")
        fuel = value(x, registry, self.component_id, "m_dot_fuel_kg_s")
        check_denominator(fuel, self.den_min, f"{self.component_id}.m_dot_fuel_kg_s")
        afr = value(x, registry, self.component_id, "AFR")
        return [residual_record(self, "engine_air_fuel_ratio", afr - air / fuel, self.scale, "engine_air_fuel_ratio_mismatch", "Engine air-fuel ratio residual.")]

    def metadata(self) -> dict[str, Any]:
        return component_metadata(self, "engine_aftertreatment", ["algebraic AFR check", "no combustion chemistry", "no lambda calculation unless paired with stoichiometric AFR"])


class EngineVolumetricEfficiencyModule(BaseModule):
    """Low-fidelity engine air-flow audit from volumetric efficiency."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "EngineVolumetricEfficiencyModule", parameters)
        self.displacement = required_positive(parameters, "displacement_m3_per_rev")
        self.scale = positive_float(parameters.get("residual_scale_kg_s", 0.01), "residual_scale_kg_s")
        self.records = [
            bounded_record(component_id, parameters, "speed_rev_s", "rev/s", "speed_rev", 0.0, 1e5, 50.0, 10.0),
            bounded_record(component_id, parameters, "rho_air_kg_m3", "kg/m^3", "rho_air", 1e-9, 1e4, 1.2, 0.1),
            mass_flow_record(component_id, parameters, "m_dot_air_kg_s", "m_dot_air", 0.1),
            fraction_record(component_id, parameters, "volumetric_efficiency", "volumetric_efficiency", 0.8),
        ]

    def declare_variables(self) -> list[VariableRecord]:
        return list(self.records)

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        speed = value(x, registry, self.component_id, "speed_rev_s")
        rho = value(x, registry, self.component_id, "rho_air_kg_m3")
        flow = value(x, registry, self.component_id, "m_dot_air_kg_s")
        ve = value(x, registry, self.component_id, "volumetric_efficiency")
        return [residual_record(self, "engine_volumetric_efficiency_air_flow", flow - ve * rho * self.displacement * speed, self.scale, "engine_volumetric_efficiency_air_flow_mismatch", "Engine volumetric-efficiency air-flow residual.")]

    def metadata(self) -> dict[str, Any]:
        return component_metadata(self, "engine_aftertreatment", ["simplified volumetric efficiency", "caller chooses cycle convention", "no manifold dynamics", "no valve timing", "no turbo effects"])


class EngineExhaustHeatFlowModule(BaseModule):
    """Low-fidelity exhaust sensible heat-flow audit."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "EngineExhaustHeatFlowModule", parameters)
        self.cp = positive_float(parameters.get("cp_exhaust_J_kgK", 1100.0), "cp_exhaust_J_kgK")
        self.scale = positive_float(parameters.get("residual_scale_W", 1000.0), "residual_scale_W")
        self.records = [
            mass_flow_record(component_id, parameters, "m_dot_exhaust_kg_s", "m_dot_exhaust", 0.1),
            temperature_record(component_id, parameters, "T_exhaust_K", "T_exhaust", 800.0),
            temperature_record(component_id, parameters, "T_ref_K", "T_ref", 300.0),
            power_record(component_id, parameters, "Q_exhaust_W", "Q_exhaust", 55000.0),
        ]

    def declare_variables(self) -> list[VariableRecord]:
        return list(self.records)

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        m = value(x, registry, self.component_id, "m_dot_exhaust_kg_s")
        t = value(x, registry, self.component_id, "T_exhaust_K")
        tref = value(x, registry, self.component_id, "T_ref_K")
        q = value(x, registry, self.component_id, "Q_exhaust_W")
        return [residual_record(self, "engine_exhaust_heat_flow", q - m * self.cp * (t - tref), self.scale, "engine_exhaust_heat_flow_mismatch", "Engine exhaust sensible heat residual.")]

    def metadata(self) -> dict[str, Any]:
        return component_metadata(self, "engine_aftertreatment", ["sensible exhaust heat only", "constant cp", "no chemical enthalpy", "no heat loss unless modeled separately"])


class EGRMixingModule(BaseModule):
    """Low-fidelity EGR and fresh-air mixing audit."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "EGRMixingModule", parameters)
        self.mass_scale = positive_float(parameters.get("mass_residual_scale_kg_s", 0.01), "mass_residual_scale_kg_s")
        self.energy_scale = positive_float(parameters.get("energy_residual_scale_kgK_s", 1.0), "energy_residual_scale_kgK_s")
        self.frac_scale = positive_float(parameters.get("fraction_residual_scale", 0.01), "fraction_residual_scale")
        self.den_min = positive_float(parameters.get("denominator_min_abs", 1e-12), "denominator_min_abs")
        self.records = [
            mass_flow_record(component_id, parameters, "m_dot_fresh_air_kg_s", "m_dot_fresh_air", 0.08),
            temperature_record(component_id, parameters, "T_fresh_air_K", "T_fresh_air", 300.0),
            mass_flow_record(component_id, parameters, "m_dot_egr_kg_s", "m_dot_egr", 0.02),
            temperature_record(component_id, parameters, "T_egr_K", "T_egr", 700.0),
            mass_flow_record(component_id, parameters, "m_dot_mixed_kg_s", "m_dot_mixed", 0.1),
            temperature_record(component_id, parameters, "T_mixed_K", "T_mixed", 380.0),
            fraction_record(component_id, parameters, "egr_fraction", "egr_fraction", 0.2),
        ]

    def declare_variables(self) -> list[VariableRecord]:
        return list(self.records)

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        mf = value(x, registry, self.component_id, "m_dot_fresh_air_kg_s")
        tf = value(x, registry, self.component_id, "T_fresh_air_K")
        me = value(x, registry, self.component_id, "m_dot_egr_kg_s")
        te = value(x, registry, self.component_id, "T_egr_K")
        mm = value(x, registry, self.component_id, "m_dot_mixed_kg_s")
        tm = value(x, registry, self.component_id, "T_mixed_K")
        frac = value(x, registry, self.component_id, "egr_fraction")
        check_denominator(mm, self.den_min, f"{self.component_id}.m_dot_mixed_kg_s")
        return [
            residual_record(self, "egr_mass_balance", mm - mf - me, self.mass_scale, "egr_mass_balance_mismatch", "EGR mass balance residual."),
            residual_record(self, "egr_temperature_mixing", tm * mm - (tf * mf + te * me), self.energy_scale, "egr_temperature_mixing_mismatch", "EGR temperature mixing residual."),
            residual_record(self, "egr_fraction", frac - me / mm, self.frac_scale, "egr_fraction_mismatch", "EGR fraction residual."),
        ]

    def metadata(self) -> dict[str, Any]:
        return component_metadata(self, "engine_aftertreatment", ["same cp approximation", "no pressure dynamics", "no chemical composition", "no condensation"])


class TurboPowerBalanceModule(BaseModule):
    """Low-fidelity turbocharger shaft power balance audit."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "TurboPowerBalanceModule", parameters)
        self.scale = positive_float(parameters.get("residual_scale_W", 1000.0), "residual_scale_W")
        self.records = [
            power_record(component_id, parameters, "P_turbine_W", "P_turbine", 10000.0),
            power_record(component_id, parameters, "P_compressor_W", "P_compressor", 9000.0),
            fraction_record(component_id, parameters, "mechanical_efficiency", "mechanical_efficiency", 0.9),
        ]

    def declare_variables(self) -> list[VariableRecord]:
        return list(self.records)

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        turbine = value(x, registry, self.component_id, "P_turbine_W")
        compressor = value(x, registry, self.component_id, "P_compressor_W")
        eff = value(x, registry, self.component_id, "mechanical_efficiency")
        return [residual_record(self, "turbo_power_balance", compressor - eff * turbine, self.scale, "turbo_power_balance_mismatch", "Turbocharger shaft power balance residual.")]

    def metadata(self) -> dict[str, Any]:
        return component_metadata(self, "engine_aftertreatment", ["algebraic shaft power balance", "no rotor inertia", "no maps", "no surge/choke", "no heat transfer"])


class CatalystThermalMassStepModule(BaseModule):
    """Single-step catalyst thermal mass audit."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "CatalystThermalMassStepModule", parameters)
        self.C = required_positive(parameters, "C_J_K")
        self.dt = required_positive(parameters, "dt_s")
        self.scale = positive_float(parameters.get("residual_scale_K", 1.0), "residual_scale_K")
        self.records = [
            temperature_record(component_id, parameters, "T_previous_K", "T_previous", 700.0),
            temperature_record(component_id, parameters, "T_current_K", "T_current", 701.0),
            power_record(component_id, parameters, "Q_exhaust_in_W", "Q_exhaust_in", 2000.0),
            power_record(component_id, parameters, "Q_loss_W", "Q_loss", 1000.0),
        ]

    def declare_variables(self) -> list[VariableRecord]:
        return list(self.records)

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        prev = value(x, registry, self.component_id, "T_previous_K")
        cur = value(x, registry, self.component_id, "T_current_K")
        qin = value(x, registry, self.component_id, "Q_exhaust_in_W")
        qloss = value(x, registry, self.component_id, "Q_loss_W")
        return [residual_record(self, "catalyst_thermal_mass_step", cur - prev - (qin - qloss) * self.dt / self.C, self.scale, "catalyst_thermal_mass_step_mismatch", "Catalyst thermal mass step residual.")]

    def metadata(self) -> dict[str, Any]:
        return component_metadata(self, "engine_aftertreatment", ["lumped catalyst temperature", "no reaction heat", "no conversion efficiency", "no spatial gradients"])


class AftertreatmentPressureDropModule(BaseModule):
    """Low-fidelity aftertreatment pressure-drop audit."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "AftertreatmentPressureDropModule", parameters)
        self.K = required_nonnegative(parameters, "K_Pa_per_kg2_s2")
        self.scale = positive_float(parameters.get("residual_scale_Pa", 1000.0), "residual_scale_Pa")
        self.records = [
            pressure_record(component_id, parameters, "p_in_Pa", "p_in", 120000.0),
            pressure_record(component_id, parameters, "p_out_Pa", "p_out", 100000.0),
            mass_flow_record(component_id, parameters, "m_dot_exhaust_kg_s", "m_dot_exhaust", 0.1),
        ]

    def declare_variables(self) -> list[VariableRecord]:
        return list(self.records)

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        pin = value(x, registry, self.component_id, "p_in_Pa")
        pout = value(x, registry, self.component_id, "p_out_Pa")
        flow = value(x, registry, self.component_id, "m_dot_exhaust_kg_s")
        return [residual_record(self, "aftertreatment_pressure_drop", (pin - pout) - self.K * flow * abs(flow), self.scale, "aftertreatment_pressure_drop_mismatch", "Aftertreatment lumped pressure drop residual.")]

    def metadata(self) -> dict[str, Any]:
        return component_metadata(self, "engine_aftertreatment", ["lumped pressure drop", "no temperature dependence", "no soot loading model", "no gas dynamics"])
