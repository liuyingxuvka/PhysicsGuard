"""Component-level low-fidelity thermal audit modules."""

from __future__ import annotations

from typing import Any

import numpy as np

from physicsguard.core.registry import VariableRecord, VariableRegistry
from physicsguard.core.residual import ResidualRecord
from physicsguard.modules.base import BaseModule
from physicsguard.modules.components._common import (
    bounded_record,
    component_metadata,
    finite_float,
    mass_flow_record,
    nonnegative_float,
    positive_float,
    power_record,
    required,
    required_nonnegative,
    temperature_record,
    value,
)


class RadiatorSimpleModule(BaseModule):
    """Low-fidelity lumped radiator/cooler audit component."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "RadiatorSimpleModule", parameters)
        self.cp_coolant_J_kgK = positive_float(
            parameters.get("cp_coolant_J_kgK", 4180.0),
            "cp_coolant_J_kgK",
        )
        self.UA_W_K = required_nonnegative(parameters, "UA_W_K")
        self.fan_power_optional = bool(parameters.get("fan_power_optional", True))
        self.residual_scale_heat_W = positive_float(
            parameters.get("residual_scale_heat_W", 1000.0),
            "residual_scale_heat_W",
        )
        self.records = [
            mass_flow_record(component_id, parameters, "m_dot_coolant_kg_s", "m_dot_coolant", 1.0),
            temperature_record(component_id, parameters, "T_coolant_in_K", "T_coolant_in", 330.0),
            temperature_record(component_id, parameters, "T_coolant_out_K", "T_coolant_out", 320.0),
            temperature_record(component_id, parameters, "T_air_in_K", "T_air_in", 300.0),
            power_record(component_id, parameters, "Q_rejected_W", "Q_rejected", 1000.0),
            power_record(component_id, parameters, "fan_power_W", "fan_power", 0.0),
        ]

    def declare_variables(self) -> list[VariableRecord]:
        return list(self.records)

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        m_dot = value(x, registry, self.component_id, "m_dot_coolant_kg_s")
        t_in = value(x, registry, self.component_id, "T_coolant_in_K")
        t_out = value(x, registry, self.component_id, "T_coolant_out_K")
        t_air = value(x, registry, self.component_id, "T_air_in_K")
        q_rejected = value(x, registry, self.component_id, "Q_rejected_W")
        return [
            ResidualRecord(
                name=f"{self.component_id}.radiator_coolant_heat_balance",
                value=q_rejected - m_dot * self.cp_coolant_J_kgK * (t_in - t_out),
                scale=self.residual_scale_heat_W,
                source=self.component_id,
                role="equation",
                diagnostic_key="radiator_coolant_heat_balance_mismatch",
                description="Radiator coolant-side heat residual.",
            ),
            ResidualRecord(
                name=f"{self.component_id}.radiator_ua_heat_rejection",
                value=q_rejected - self.UA_W_K * (t_in - t_air),
                scale=self.residual_scale_heat_W,
                source=self.component_id,
                role="equation",
                diagnostic_key="radiator_ua_heat_rejection_mismatch",
                description="Radiator lumped UA heat rejection residual.",
            ),
        ]

    def metadata(self) -> dict[str, Any]:
        return component_metadata(
            self,
            "thermal_component",
            [
                "lumped UA cooler",
                "no air mass flow model",
                "no detailed NTU model",
                "no coolant phase change",
                "no fan map",
            ],
        )


class RadiatorFanSimpleModule(BaseModule):
    """Low-fidelity fan command to air-flow and power relation."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "RadiatorFanSimpleModule", parameters)
        self.max_air_m_dot_kg_s = nonnegative_float(required(parameters, "max_air_m_dot_kg_s"), "max_air_m_dot_kg_s")
        self.max_fan_power_W = nonnegative_float(required(parameters, "max_fan_power_W"), "max_fan_power_W")
        self.residual_scale_flow_kg_s = positive_float(
            parameters.get("residual_scale_flow_kg_s", 0.1),
            "residual_scale_flow_kg_s",
        )
        self.residual_scale_power_W = positive_float(
            parameters.get("residual_scale_power_W", 100.0),
            "residual_scale_power_W",
        )
        self.records = [
            bounded_record(component_id, parameters, "fan_command", None, "fan_command", 0.0, 1.0, 0.5, 1.0),
            mass_flow_record(component_id, parameters, "air_m_dot_kg_s", "air_m_dot", 0.5),
            power_record(component_id, parameters, "fan_power_W", "fan_power", 100.0),
        ]

    def declare_variables(self) -> list[VariableRecord]:
        return list(self.records)

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        command = value(x, registry, self.component_id, "fan_command")
        air_flow = value(x, registry, self.component_id, "air_m_dot_kg_s")
        fan_power = value(x, registry, self.component_id, "fan_power_W")
        return [
            ResidualRecord(
                name=f"{self.component_id}.radiator_fan_air_flow",
                value=air_flow - self.max_air_m_dot_kg_s * command,
                scale=self.residual_scale_flow_kg_s,
                source=self.component_id,
                role="equation",
                diagnostic_key="radiator_fan_air_flow_mismatch",
                description="Radiator fan air-flow command residual.",
            ),
            ResidualRecord(
                name=f"{self.component_id}.radiator_fan_power",
                value=fan_power - self.max_fan_power_W * command**3,
                scale=self.residual_scale_power_W,
                source=self.component_id,
                role="equation",
                diagnostic_key="radiator_fan_power_mismatch",
                description="Radiator fan cubic power residual.",
            ),
        ]

    def metadata(self) -> dict[str, Any]:
        return component_metadata(
            self,
            "thermal_component",
            ["simple fan affinity-like relation", "no fan map", "command expected in [0,1]"],
        )


class HumidifierEffectivenessModule(BaseModule):
    """Low-fidelity humidifier water-transfer audit component."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "HumidifierEffectivenessModule", parameters)
        self.effectiveness = finite_float(required(parameters, "effectiveness"), "effectiveness")
        if not 0.0 <= self.effectiveness <= 1.0:
            raise ValueError("effectiveness must be between 0 and 1")
        self.residual_scale_humidity_ratio = positive_float(
            parameters.get("residual_scale_humidity_ratio", 0.001),
            "residual_scale_humidity_ratio",
        )
        self.residual_scale_water_kg_s = positive_float(
            parameters.get("residual_scale_water_kg_s", 1e-4),
            "residual_scale_water_kg_s",
        )
        self.records = [
            mass_flow_record(component_id, parameters, "m_dot_dry_air_kg_s", "m_dot_dry_air", 1.0),
            _humidity_record(component_id, parameters, "humidity_ratio_in_kg_kg", "humidity_ratio_in", 0.01),
            _humidity_record(component_id, parameters, "humidity_ratio_out_kg_kg", "humidity_ratio_out", 0.02),
            _humidity_record(component_id, parameters, "humidity_ratio_target_kg_kg", "humidity_ratio_target", 0.03),
            mass_flow_record(component_id, parameters, "water_transfer_kg_s", "water_transfer", 0.01),
        ]

    def declare_variables(self) -> list[VariableRecord]:
        return list(self.records)

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        m_air = value(x, registry, self.component_id, "m_dot_dry_air_kg_s")
        w_in = value(x, registry, self.component_id, "humidity_ratio_in_kg_kg")
        w_out = value(x, registry, self.component_id, "humidity_ratio_out_kg_kg")
        w_target = value(x, registry, self.component_id, "humidity_ratio_target_kg_kg")
        water = value(x, registry, self.component_id, "water_transfer_kg_s")
        expected_w_out = w_in + self.effectiveness * (w_target - w_in)
        return [
            ResidualRecord(
                name=f"{self.component_id}.humidifier_effectiveness",
                value=w_out - expected_w_out,
                scale=self.residual_scale_humidity_ratio,
                source=self.component_id,
                role="equation",
                diagnostic_key="humidifier_effectiveness_mismatch",
                description="Humidifier outlet humidity effectiveness residual.",
            ),
            ResidualRecord(
                name=f"{self.component_id}.humidifier_water_transfer",
                value=water - m_air * (w_out - w_in),
                scale=self.residual_scale_water_kg_s,
                source=self.component_id,
                role="equation",
                diagnostic_key="humidifier_water_transfer_mismatch",
                description="Humidifier water transfer residual.",
            ),
        ]

    def metadata(self) -> dict[str, Any]:
        return component_metadata(
            self,
            "humidity_component",
            [
                "lumped effectiveness relation",
                "target humidity ratio must be supplied externally",
                "no membrane transport model",
                "no condensation model",
                "no pressure drop",
                "no detailed heat transfer",
            ],
        )


class IntercoolerSimpleModule(BaseModule):
    """Low-fidelity gas cooler/intercooler audit component."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "IntercoolerSimpleModule", parameters)
        self.cp_gas_J_kgK = positive_float(parameters.get("cp_gas_J_kgK", 1005.0), "cp_gas_J_kgK")
        self.UA_W_K = required_nonnegative(parameters, "UA_W_K")
        self.residual_scale_heat_W = positive_float(
            parameters.get("residual_scale_heat_W", 1000.0),
            "residual_scale_heat_W",
        )
        self.records = [
            mass_flow_record(component_id, parameters, "m_dot_gas_kg_s", "m_dot_gas", 1.0),
            temperature_record(component_id, parameters, "T_gas_in_K", "T_gas_in", 370.0),
            temperature_record(component_id, parameters, "T_gas_out_K", "T_gas_out", 330.0),
            temperature_record(component_id, parameters, "T_coolant_or_ambient_K", "T_coolant_or_ambient", 300.0),
            power_record(component_id, parameters, "Q_removed_W", "Q_removed", 1000.0),
        ]

    def declare_variables(self) -> list[VariableRecord]:
        return list(self.records)

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        m_dot = value(x, registry, self.component_id, "m_dot_gas_kg_s")
        t_in = value(x, registry, self.component_id, "T_gas_in_K")
        t_out = value(x, registry, self.component_id, "T_gas_out_K")
        t_sink = value(x, registry, self.component_id, "T_coolant_or_ambient_K")
        q_removed = value(x, registry, self.component_id, "Q_removed_W")
        return [
            ResidualRecord(
                name=f"{self.component_id}.intercooler_gas_heat_balance",
                value=q_removed - m_dot * self.cp_gas_J_kgK * (t_in - t_out),
                scale=self.residual_scale_heat_W,
                source=self.component_id,
                role="equation",
                diagnostic_key="intercooler_gas_heat_balance_mismatch",
                description="Intercooler gas-side heat residual.",
            ),
            ResidualRecord(
                name=f"{self.component_id}.intercooler_ua_heat_transfer",
                value=q_removed - self.UA_W_K * (t_in - t_sink),
                scale=self.residual_scale_heat_W,
                source=self.component_id,
                role="equation",
                diagnostic_key="intercooler_ua_heat_transfer_mismatch",
                description="Intercooler lumped UA heat residual.",
            ),
        ]

    def metadata(self) -> dict[str, Any]:
        return component_metadata(
            self,
            "thermal_component",
            [
                "lumped gas cooler",
                "no condensation",
                "no pressure drop",
                "no detailed NTU model",
                "no wall thermal mass",
            ],
        )


def _humidity_record(
    component_id: str,
    parameters: dict[str, Any],
    local_name: str,
    prefix: str,
    initial: float,
) -> VariableRecord:
    return bounded_record(
        component_id,
        parameters,
        local_name,
        "kg/kg",
        prefix,
        0.0,
        10.0,
        initial,
        0.001,
    )
