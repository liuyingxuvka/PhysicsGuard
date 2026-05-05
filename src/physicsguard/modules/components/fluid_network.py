"""Component-level low-fidelity fluid-network audit modules."""

from __future__ import annotations

import math
from typing import Any

import numpy as np

from physicsguard.core.registry import VariableRecord, VariableRegistry
from physicsguard.core.residual import ResidualRecord
from physicsguard.modules.base import BaseModule
from physicsguard.modules.components._common import (
    bounded_record,
    component_metadata,
    fraction_record,
    mass_flow_record,
    mass_record,
    molar_flow_record,
    nonnegative_float,
    positive_float,
    pressure_record,
    residual_record,
    required_nonnegative,
    required_positive,
    scalar_record,
    temperature_record,
    value,
)
from physicsguard.modules.physical.constants import UNIVERSAL_GAS_CONSTANT


def _signed_flow_record(component_id: str, parameters: dict[str, Any], local_name: str, prefix: str, initial: float = 0.1) -> VariableRecord:
    return bounded_record(component_id, parameters, local_name, "kg/s", prefix, -1e4, 1e4, initial, 1.0)


def _pressure_flow_records(component_id: str, parameters: dict[str, Any], flow_name: str = "m_dot_kg_s", flow_prefix: str = "m_dot") -> list[VariableRecord]:
    return [
        pressure_record(component_id, parameters, "p_in_Pa", "p_in", 120000.0),
        pressure_record(component_id, parameters, "p_out_Pa", "p_out", 100000.0),
        _signed_flow_record(component_id, parameters, flow_name, flow_prefix),
    ]


class PipeSegmentSimpleModule(BaseModule):
    """Low-fidelity incompressible pipe pressure-drop audit component."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "PipeSegmentSimpleModule", parameters)
        self.rho = required_positive(parameters, "rho_kg_m3")
        self.diameter = required_positive(parameters, "diameter_m")
        self.length = required_nonnegative(parameters, "length_m")
        self.friction_factor = nonnegative_float(parameters.get("friction_factor", 0.02), "friction_factor")
        self.K_minor = nonnegative_float(parameters.get("K_minor", 0.0), "K_minor")
        self.scale = positive_float(parameters.get("residual_scale_Pa", 1000.0), "residual_scale_Pa")
        self.records = _pressure_flow_records(component_id, parameters)

    def declare_variables(self) -> list[VariableRecord]:
        return list(self.records)

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        p_in = value(x, registry, self.component_id, "p_in_Pa")
        p_out = value(x, registry, self.component_id, "p_out_Pa")
        m_dot = value(x, registry, self.component_id, "m_dot_kg_s")
        area = math.pi * self.diameter**2 / 4.0
        velocity = m_dot / (self.rho * area)
        k_total = self.friction_factor * self.length / self.diameter + self.K_minor
        drop = k_total * 0.5 * self.rho * velocity * abs(velocity)
        return [residual_record(self, "pipe_segment_pressure_drop", (p_in - p_out) - drop, self.scale, "pipe_segment_pressure_drop_mismatch", "Pipe segment pressure-drop residual.")]

    def metadata(self) -> dict[str, Any]:
        return component_metadata(self, "fluid_network", ["incompressible flow", "constant density", "lumped pressure loss", "no Reynolds-dependent friction correlation", "no elevation term"])


class DuctSegmentSimpleModule(BaseModule):
    """Low-fidelity gas duct pressure-drop audit component."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "DuctSegmentSimpleModule", parameters)
        self.rho = required_positive(parameters, "rho_kg_m3")
        self.area = required_positive(parameters, "area_m2")
        self.K_total = required_nonnegative(parameters, "K_total")
        self.scale = positive_float(parameters.get("residual_scale_Pa", 1000.0), "residual_scale_Pa")
        self.records = _pressure_flow_records(component_id, parameters)

    def declare_variables(self) -> list[VariableRecord]:
        return list(self.records)

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        p_in = value(x, registry, self.component_id, "p_in_Pa")
        p_out = value(x, registry, self.component_id, "p_out_Pa")
        m_dot = value(x, registry, self.component_id, "m_dot_kg_s")
        velocity = m_dot / (self.rho * self.area)
        drop = self.K_total * 0.5 * self.rho * velocity * abs(velocity)
        return [residual_record(self, "duct_segment_pressure_drop", (p_in - p_out) - drop, self.scale, "duct_segment_pressure_drop_mismatch", "Duct segment pressure-drop residual.")]

    def metadata(self) -> dict[str, Any]:
        return component_metadata(self, "fluid_network", ["low-Mach duct sanity check", "constant density", "no wave dynamics", "no compressible choking"])


class LumpedGasVolumeStepModule(BaseModule):
    """Single-step ideal-gas lumped-volume pressure audit."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "LumpedGasVolumeStepModule", parameters)
        self.volume = required_positive(parameters, "volume_m3")
        self.dt = required_positive(parameters, "dt_s")
        self.scale = positive_float(parameters.get("residual_scale_Pa", 1000.0), "residual_scale_Pa")
        self.records = [
            pressure_record(component_id, parameters, "p_previous_Pa", "p_previous", 100000.0),
            pressure_record(component_id, parameters, "p_current_Pa", "p_current", 101000.0),
            temperature_record(component_id, parameters, "T_K", "T", 300.0),
            molar_flow_record(component_id, parameters, "n_dot_in_mol_s", "n_dot_in", 0.1),
            molar_flow_record(component_id, parameters, "n_dot_out_mol_s", "n_dot_out", 0.05),
        ]

    def declare_variables(self) -> list[VariableRecord]:
        return list(self.records)

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        p_prev = value(x, registry, self.component_id, "p_previous_Pa")
        p_cur = value(x, registry, self.component_id, "p_current_Pa")
        temp = value(x, registry, self.component_id, "T_K")
        n_in = value(x, registry, self.component_id, "n_dot_in_mol_s")
        n_out = value(x, registry, self.component_id, "n_dot_out_mol_s")
        expected_delta = (UNIVERSAL_GAS_CONSTANT * temp / self.volume) * (n_in - n_out) * self.dt
        return [residual_record(self, "lumped_gas_volume_pressure_step", p_cur - p_prev - expected_delta, self.scale, "lumped_gas_volume_pressure_step_mismatch", "Ideal-gas lumped volume pressure step residual.")]

    def metadata(self) -> dict[str, Any]:
        return component_metadata(self, "fluid_network", ["ideal gas", "uniform pressure and temperature", "single-step audit only", "no heat transfer", "no real-gas effects"])


class LumpedLiquidVolumeStepModule(BaseModule):
    """Single-step liquid inventory audit."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "LumpedLiquidVolumeStepModule", parameters)
        self.dt = required_positive(parameters, "dt_s")
        self.scale = positive_float(parameters.get("residual_scale_kg", 0.01), "residual_scale_kg")
        self.records = [
            mass_record(component_id, parameters, "mass_previous_kg", "mass_previous", 10.0),
            mass_record(component_id, parameters, "mass_current_kg", "mass_current", 10.1),
            mass_flow_record(component_id, parameters, "m_dot_in_kg_s", "m_dot_in", 0.2),
            mass_flow_record(component_id, parameters, "m_dot_out_kg_s", "m_dot_out", 0.1),
        ]

    def declare_variables(self) -> list[VariableRecord]:
        return list(self.records)

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        prev = value(x, registry, self.component_id, "mass_previous_kg")
        cur = value(x, registry, self.component_id, "mass_current_kg")
        in_flow = value(x, registry, self.component_id, "m_dot_in_kg_s")
        out_flow = value(x, registry, self.component_id, "m_dot_out_kg_s")
        return [residual_record(self, "lumped_liquid_volume_mass_step", cur - prev - (in_flow - out_flow) * self.dt, self.scale, "lumped_liquid_volume_mass_step_mismatch", "Liquid inventory single-step residual.")]

    def metadata(self) -> dict[str, Any]:
        return component_metadata(self, "fluid_network", ["incompressible liquid inventory", "single-step audit only", "no density change", "no phase change"])


class FlowSplitModule(BaseModule):
    """Low-fidelity algebraic flow-split audit."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "FlowSplitModule", parameters)
        self.scale = positive_float(parameters.get("residual_scale_kg_s", 0.01), "residual_scale_kg_s")
        self.records = [
            mass_flow_record(component_id, parameters, "m_dot_in_kg_s", "m_dot_in", 1.0),
            mass_flow_record(component_id, parameters, "m_dot_out_1_kg_s", "m_dot_out_1", 0.4),
            mass_flow_record(component_id, parameters, "m_dot_out_2_kg_s", "m_dot_out_2", 0.6),
            fraction_record(component_id, parameters, "split_fraction", "split_fraction", 0.4),
        ]

    def declare_variables(self) -> list[VariableRecord]:
        return list(self.records)

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        m_in = value(x, registry, self.component_id, "m_dot_in_kg_s")
        m1 = value(x, registry, self.component_id, "m_dot_out_1_kg_s")
        m2 = value(x, registry, self.component_id, "m_dot_out_2_kg_s")
        split = value(x, registry, self.component_id, "split_fraction")
        return [
            residual_record(self, "flow_split_branch_1", m1 - split * m_in, self.scale, "flow_split_branch_1_mismatch", "Flow split branch 1 residual."),
            residual_record(self, "flow_split_branch_2", m2 - (1.0 - split) * m_in, self.scale, "flow_split_branch_2_mismatch", "Flow split branch 2 residual."),
            residual_record(self, "flow_split_mass_balance", m_in - m1 - m2, self.scale, "flow_split_mass_balance_mismatch", "Flow split mass balance residual."),
        ]

    def metadata(self) -> dict[str, Any]:
        return component_metadata(self, "fluid_network", ["algebraic split", "no pressure calculation", "no valve physics"])


class FlowMergeTemperatureModule(BaseModule):
    """Low-fidelity two-stream merge mass and temperature audit."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "FlowMergeTemperatureModule", parameters)
        self.mass_scale = positive_float(parameters.get("mass_residual_scale_kg_s", 0.01), "mass_residual_scale_kg_s")
        self.energy_scale = positive_float(parameters.get("energy_residual_scale_kgK_s", 1.0), "energy_residual_scale_kgK_s")
        self.records = [
            mass_flow_record(component_id, parameters, "m_dot_1_kg_s", "m_dot_1", 0.4),
            temperature_record(component_id, parameters, "T_1_K", "T_1", 300.0),
            mass_flow_record(component_id, parameters, "m_dot_2_kg_s", "m_dot_2", 0.6),
            temperature_record(component_id, parameters, "T_2_K", "T_2", 320.0),
            mass_flow_record(component_id, parameters, "m_dot_out_kg_s", "m_dot_out", 1.0),
            temperature_record(component_id, parameters, "T_out_K", "T_out", 312.0),
        ]

    def declare_variables(self) -> list[VariableRecord]:
        return list(self.records)

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        m1 = value(x, registry, self.component_id, "m_dot_1_kg_s")
        t1 = value(x, registry, self.component_id, "T_1_K")
        m2 = value(x, registry, self.component_id, "m_dot_2_kg_s")
        t2 = value(x, registry, self.component_id, "T_2_K")
        mo = value(x, registry, self.component_id, "m_dot_out_kg_s")
        to = value(x, registry, self.component_id, "T_out_K")
        return [
            residual_record(self, "flow_merge_mass_balance", mo - m1 - m2, self.mass_scale, "flow_merge_mass_balance_mismatch", "Flow merge mass balance residual."),
            residual_record(self, "flow_merge_temperature_balance", mo * to - (m1 * t1 + m2 * t2), self.energy_scale, "flow_merge_temperature_balance_mismatch", "Flow merge temperature balance residual."),
        ]

    def metadata(self) -> dict[str, Any]:
        return component_metadata(self, "fluid_network", ["same fluid", "same cp", "no heat loss", "no pressure calculation", "no phase change"])


class CheckValveSimpleModule(BaseModule):
    """Post-check for check-valve backflow consistency."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "CheckValveSimpleModule", parameters)
        self.leakage_tol = nonnegative_float(parameters.get("leakage_tolerance_kg_s", 1e-6), "leakage_tolerance_kg_s")
        self.pressure_tol = nonnegative_float(parameters.get("pressure_tolerance_Pa", 1.0), "pressure_tolerance_Pa")
        self.scale = positive_float(parameters.get("residual_scale_kg_s", 0.01), "residual_scale_kg_s")
        self.records = [
            pressure_record(component_id, parameters, "p_upstream_Pa", "p_upstream", 120000.0),
            pressure_record(component_id, parameters, "p_downstream_Pa", "p_downstream", 100000.0),
            _signed_flow_record(component_id, parameters, "m_dot_kg_s", "m_dot", 0.1),
        ]

    def declare_variables(self) -> list[VariableRecord]:
        return list(self.records)

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        up = value(x, registry, self.component_id, "p_upstream_Pa")
        down = value(x, registry, self.component_id, "p_downstream_Pa")
        flow = value(x, registry, self.component_id, "m_dot_kg_s")
        violation = flow - self.leakage_tol if up + self.pressure_tol < down and flow > self.leakage_tol else 0.0
        return [residual_record(self, "check_valve_backflow", violation, self.scale, "check_valve_backflow_violation", "Check-valve backflow post-check residual.", "post_check")]

    def metadata(self) -> dict[str, Any]:
        return component_metadata(self, "fluid_network", ["diagnostic only", "no valve flow equation", "no cracking pressure model"])


class ThrottleValveSimpleModule(BaseModule):
    """Low-fidelity incompressible throttle valve audit."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "ThrottleValveSimpleModule", parameters)
        self.CdA_max = required_positive(parameters, "CdA_max_m2")
        self.rho = required_positive(parameters, "rho_kg_m3")
        self.scale = positive_float(parameters.get("residual_scale_kg2_s2", 1e-4), "residual_scale_kg2_s2")
        self.records = [
            pressure_record(component_id, parameters, "p_upstream_Pa", "p_upstream", 120000.0),
            pressure_record(component_id, parameters, "p_downstream_Pa", "p_downstream", 100000.0),
            mass_flow_record(component_id, parameters, "m_dot_kg_s", "m_dot", 0.1),
            fraction_record(component_id, parameters, "opening", "opening", 0.5),
        ]

    def declare_variables(self) -> list[VariableRecord]:
        return list(self.records)

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        up = value(x, registry, self.component_id, "p_upstream_Pa")
        down = value(x, registry, self.component_id, "p_downstream_Pa")
        flow = value(x, registry, self.component_id, "m_dot_kg_s")
        opening = value(x, registry, self.component_id, "opening")
        cda = self.CdA_max * opening
        return [residual_record(self, "throttle_valve_flow", flow**2 - 2.0 * self.rho * cda**2 * (up - down), self.scale, "throttle_valve_flow_mismatch", "Throttle valve squared-flow residual.")]

    def metadata(self) -> dict[str, Any]:
        return component_metadata(self, "fluid_network", ["incompressible", "one-direction", "non-choked", "no cavitation", "no detailed valve characteristic"])


class PressureReliefValveCheckModule(BaseModule):
    """Post-check for pressure-relief valve state consistency."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "PressureReliefValveCheckModule", parameters)
        self.flow_tol = nonnegative_float(parameters.get("flow_tolerance_kg_s", 1e-6), "flow_tolerance_kg_s")
        self.pressure_tol = positive_float(parameters.get("pressure_tolerance_Pa", 10.0), "pressure_tolerance_Pa")
        self.scale = positive_float(parameters.get("residual_scale", 1.0), "residual_scale")
        self.records = [
            pressure_record(component_id, parameters, "p_upstream_Pa", "p_upstream", 100000.0),
            pressure_record(component_id, parameters, "p_set_Pa", "p_set", 120000.0),
            mass_flow_record(component_id, parameters, "m_dot_relief_kg_s", "m_dot_relief", 0.0),
        ]

    def declare_variables(self) -> list[VariableRecord]:
        return list(self.records)

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        up = value(x, registry, self.component_id, "p_upstream_Pa")
        p_set = value(x, registry, self.component_id, "p_set_Pa")
        flow = value(x, registry, self.component_id, "m_dot_relief_kg_s")
        residual = 0.0
        if up < p_set - self.pressure_tol and flow > self.flow_tol:
            residual = flow / max(self.flow_tol, 1e-12)
        elif up > p_set + self.pressure_tol and flow <= self.flow_tol:
            residual = (up - p_set) / max(self.pressure_tol, 1e-12)
        return [residual_record(self, "pressure_relief_valve_state", residual, self.scale, "pressure_relief_valve_state_violation", "Pressure-relief valve state post-check residual.", "post_check")]

    def metadata(self) -> dict[str, Any]:
        return component_metadata(self, "fluid_network", ["diagnostic only", "no flow coefficient model", "no valve dynamics"])


class LeakOrBypassLinearModule(BaseModule):
    """Low-fidelity linear leak or bypass flow audit."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "LeakOrBypassLinearModule", parameters)
        self.conductance = required_nonnegative(parameters, "conductance_kg_s_Pa")
        self.scale = positive_float(parameters.get("residual_scale_kg_s", 0.01), "residual_scale_kg_s")
        self.records = [
            pressure_record(component_id, parameters, "p_upstream_Pa", "p_upstream", 120000.0),
            pressure_record(component_id, parameters, "p_downstream_Pa", "p_downstream", 100000.0),
            _signed_flow_record(component_id, parameters, "m_dot_kg_s", "m_dot", 0.1),
        ]

    def declare_variables(self) -> list[VariableRecord]:
        return list(self.records)

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        up = value(x, registry, self.component_id, "p_upstream_Pa")
        down = value(x, registry, self.component_id, "p_downstream_Pa")
        flow = value(x, registry, self.component_id, "m_dot_kg_s")
        return [residual_record(self, "leak_or_bypass_linear_flow", flow - self.conductance * (up - down), self.scale, "leak_or_bypass_linear_flow_mismatch", "Linear leak or bypass flow residual.")]

    def metadata(self) -> dict[str, Any]:
        return component_metadata(self, "fluid_network", ["linearized leak/bypass relation", "not a detailed orifice model", "local approximation only"])
