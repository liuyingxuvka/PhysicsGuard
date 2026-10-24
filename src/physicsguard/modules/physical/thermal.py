"""Low-fidelity thermal audit modules."""

from __future__ import annotations

from typing import Any

import numpy as np

from physicsguard.core.registry import VariableRecord, VariableRegistry
from physicsguard.core.residual import ResidualRecord
from physicsguard.modules.base import BaseModule
from physicsguard.modules.physical._common import (
    metadata,
    owned_record,
    positive_float,
    value,
)


class CoolantHeatBalanceModule(BaseModule):
    """Steady low-fidelity heat balance for a flowing coolant stream."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "CoolantHeatBalanceModule", parameters)
        self.cp_J_kgK = positive_float(parameters.get("cp_J_kgK", 4180.0), "cp_J_kgK")
        self.residual_scale_W = positive_float(
            parameters.get("residual_scale_W", 1000.0),
            "residual_scale_W",
        )
        self.records = [
            owned_record(
                self.component_id,
                self.parameters,
                "m_dot_kg_s",
                "kg/s",
                "m_dot_lower_bound",
                "m_dot_upper_bound",
                "m_dot_initial_guess",
                "m_dot_scale",
                0.0,
                10.0,
                0.1,
                1.0,
            ),
            owned_record(
                self.component_id,
                self.parameters,
                "T_in_K",
                "K",
                "T_lower_bound",
                "T_upper_bound",
                "T_in_initial_guess",
                "T_scale",
                250.0,
                450.0,
                300.0,
                10.0,
            ),
            owned_record(
                self.component_id,
                self.parameters,
                "T_out_K",
                "K",
                "T_lower_bound",
                "T_upper_bound",
                "T_out_initial_guess",
                "T_scale",
                250.0,
                450.0,
                310.0,
                10.0,
            ),
            owned_record(
                self.component_id,
                self.parameters,
                "Q_dot_W",
                "W",
                "Q_dot_lower_bound",
                "Q_dot_upper_bound",
                "Q_dot_initial_guess",
                "Q_dot_scale",
                -1e6,
                1e6,
                1000.0,
                1000.0,
            ),
        ]

    def declare_variables(self) -> list[VariableRecord]:
        return list(self.records)

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        m_dot = self._value(x, registry, "m_dot_kg_s")
        t_in = self._value(x, registry, "T_in_K")
        t_out = self._value(x, registry, "T_out_K")
        q_dot = self._value(x, registry, "Q_dot_W")
        expected_q = m_dot * self.cp_J_kgK * (t_out - t_in)
        return [
            ResidualRecord(
                name=f"{self.component_id}.coolant_heat_balance",
                value=q_dot - expected_q,
                scale=self.residual_scale_W,
                source=self.component_id,
                role="equation",
                diagnostic_key="coolant_heat_balance_mismatch",
                description="Low-fidelity coolant heat balance Q_dot - m_dot*cp*(T_out - T_in).",
            )
        ]

    def metadata(self) -> dict[str, Any]:
        return {
            "component_id": self.component_id,
            "module_type": self.module_type,
            "purpose": "low_fidelity_physical_audit",
            "domain": "thermal",
            "validity": [
                "steady-state or quasi-steady estimate",
                "single-phase liquid coolant",
                "constant cp",
                "no phase change",
                "no detailed heat exchanger or wall dynamics",
            ],
        }

    def _value(self, x: np.ndarray, registry: VariableRegistry, local_name: str) -> float:
        return float(x[registry.get_index(f"{self.component_id}.{local_name}")])


class ThermalConductorModule(BaseModule):
    """Low-fidelity lumped thermal conduction relation."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "ThermalConductorModule", parameters)
        self.G_W_K = _required_positive(parameters, "G_W_K")
        self.residual_scale_W = positive_float(
            parameters.get("residual_scale_W", 1000.0),
            "residual_scale_W",
        )
        self.records = [
            owned_record(
                component_id,
                parameters,
                "T_a_K",
                "K",
                "T_lower_bound",
                "T_upper_bound",
                "T_a_initial_guess",
                "T_scale",
                200.0,
                1000.0,
                320.0,
                10.0,
            ),
            owned_record(
                component_id,
                parameters,
                "T_b_K",
                "K",
                "T_lower_bound",
                "T_upper_bound",
                "T_b_initial_guess",
                "T_scale",
                200.0,
                1000.0,
                300.0,
                10.0,
            ),
            owned_record(
                component_id,
                parameters,
                "Q_dot_W",
                "W",
                "Q_dot_lower_bound",
                "Q_dot_upper_bound",
                "Q_dot_initial_guess",
                "Q_dot_scale",
                -1e7,
                1e7,
                1000.0,
                1000.0,
            ),
        ]

    def declare_variables(self) -> list[VariableRecord]:
        return list(self.records)

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        t_a = value(x, registry, self.component_id, "T_a_K")
        t_b = value(x, registry, self.component_id, "T_b_K")
        q_dot = value(x, registry, self.component_id, "Q_dot_W")
        return [
            ResidualRecord(
                name=f"{self.component_id}.thermal_conductor",
                value=q_dot - self.G_W_K * (t_a - t_b),
                scale=self.residual_scale_W,
                source=self.component_id,
                role="equation",
                diagnostic_key="thermal_conductor_mismatch",
                description="Low-fidelity thermal conduction residual Q_dot - G*(T_a - T_b).",
            )
        ]

    def metadata(self) -> dict[str, Any]:
        return metadata(
            self,
            "thermal",
            [
                "lumped thermal conductance",
                "constant G",
                "no thermal storage",
                "no radiation",
                "no spatial temperature distribution",
            ],
        )


class ConvectiveHeatTransferModule(BaseModule):
    """Low-fidelity convection heat transfer relation."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "ConvectiveHeatTransferModule", parameters)
        self.h_W_m2K = _required_positive(parameters, "h_W_m2K")
        self.area_m2 = _required_positive(parameters, "area_m2")
        self.residual_scale_W = positive_float(
            parameters.get("residual_scale_W", 1000.0),
            "residual_scale_W",
        )
        self.records = [
            owned_record(
                component_id,
                parameters,
                "T_surface_K",
                "K",
                "T_lower_bound",
                "T_upper_bound",
                "T_surface_initial_guess",
                "T_scale",
                200.0,
                1000.0,
                330.0,
                10.0,
            ),
            owned_record(
                component_id,
                parameters,
                "T_fluid_K",
                "K",
                "T_lower_bound",
                "T_upper_bound",
                "T_fluid_initial_guess",
                "T_scale",
                200.0,
                1000.0,
                300.0,
                10.0,
            ),
            owned_record(
                component_id,
                parameters,
                "Q_dot_W",
                "W",
                "Q_dot_lower_bound",
                "Q_dot_upper_bound",
                "Q_dot_initial_guess",
                "Q_dot_scale",
                -1e7,
                1e7,
                1000.0,
                1000.0,
            ),
        ]

    def declare_variables(self) -> list[VariableRecord]:
        return list(self.records)

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        t_surface = value(x, registry, self.component_id, "T_surface_K")
        t_fluid = value(x, registry, self.component_id, "T_fluid_K")
        q_dot = value(x, registry, self.component_id, "Q_dot_W")
        expected_q = self.h_W_m2K * self.area_m2 * (t_surface - t_fluid)
        return [
            ResidualRecord(
                name=f"{self.component_id}.convective_heat_transfer",
                value=q_dot - expected_q,
                scale=self.residual_scale_W,
                source=self.component_id,
                role="equation",
                diagnostic_key="convective_heat_transfer_mismatch",
                description="Low-fidelity convection residual Q_dot - h*A*(T_surface - T_fluid).",
            )
        ]

    def metadata(self) -> dict[str, Any]:
        return metadata(
            self,
            "thermal",
            [
                "lumped convection coefficient",
                "constant h",
                "no radiation",
                "no phase change",
                "no spatial gradients",
            ],
        )


class ThermalCapacitanceRateModule(BaseModule):
    """Low-fidelity thermal capacitance rate relation."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "ThermalCapacitanceRateModule", parameters)
        self.C_J_K = _required_positive(parameters, "C_J_K")
        self.residual_scale_W = positive_float(
            parameters.get("residual_scale_W", 1000.0),
            "residual_scale_W",
        )
        self.records = [
            owned_record(
                component_id,
                parameters,
                "Q_net_W",
                "W",
                "Q_net_lower_bound",
                "Q_net_upper_bound",
                "Q_net_initial_guess",
                "Q_net_scale",
                -1e7,
                1e7,
                1000.0,
                1000.0,
            ),
            owned_record(
                component_id,
                parameters,
                "dT_dt_K_s",
                "K/s",
                "dT_dt_lower_bound",
                "dT_dt_upper_bound",
                "dT_dt_initial_guess",
                "dT_dt_scale",
                -100.0,
                100.0,
                0.0,
                1.0,
            ),
        ]

    def declare_variables(self) -> list[VariableRecord]:
        return list(self.records)

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        q_net = value(x, registry, self.component_id, "Q_net_W")
        dT_dt = value(x, registry, self.component_id, "dT_dt_K_s")
        return [
            ResidualRecord(
                name=f"{self.component_id}.thermal_capacitance_rate",
                value=q_net - self.C_J_K * dT_dt,
                scale=self.residual_scale_W,
                source=self.component_id,
                role="equation",
                diagnostic_key="thermal_capacitance_rate_mismatch",
                description="Low-fidelity thermal capacitance rate residual Q_net - C*dT_dt.",
            )
        ]

    def metadata(self) -> dict[str, Any]:
        return metadata(
            self,
            "thermal",
            [
                "lumped temperature",
                "constant heat capacity",
                "rate form only",
                "no time integration in this module",
            ],
        )


def _required_positive(parameters: dict[str, Any], name: str) -> float:
    if name not in parameters:
        raise ValueError(f"{name} is required")
    return positive_float(parameters[name], name)


