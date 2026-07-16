"""Low-fidelity fluid audit modules."""

from __future__ import annotations

import math
from typing import Any

import numpy as np

from physicsguard.core.registry import VariableRecord, VariableRegistry
from physicsguard.core.residual import ResidualRecord
from physicsguard.modules.base import BaseModule
from physicsguard.schema.variable import is_qualified_variable_name


class IncompressiblePressureDropModule(BaseModule):
    """Low-fidelity pressure drop relation for an incompressible restriction."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "IncompressiblePressureDropModule", parameters)
        self.K = _required_nonnegative(parameters, "K")
        self.rho_kg_m3 = _required_positive(parameters, "rho_kg_m3")
        self.area_m2 = _required_positive(parameters, "area_m2")
        self.residual_scale_Pa = _positive_float(
            parameters.get("residual_scale_Pa", 1000.0),
            "residual_scale_Pa",
        )
        self.records = [
            _owned_record(
                component_id,
                parameters,
                "p_in_Pa",
                "Pa",
                "p_lower_bound",
                "p_upper_bound",
                "p_in_initial_guess",
                "p_scale",
                1e3,
                1e7,
                120000.0,
                1e5,
            ),
            _owned_record(
                component_id,
                parameters,
                "p_out_Pa",
                "Pa",
                "p_lower_bound",
                "p_upper_bound",
                "p_out_initial_guess",
                "p_scale",
                1e3,
                1e7,
                100000.0,
                1e5,
            ),
            _owned_record(
                component_id,
                parameters,
                "m_dot_kg_s",
                "kg/s",
                "m_dot_lower_bound",
                "m_dot_upper_bound",
                "m_dot_initial_guess",
                "m_dot_scale",
                -10.0,
                10.0,
                0.1,
                1.0,
            ),
        ]

    def declare_variables(self) -> list[VariableRecord]:
        return list(self.records)

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        p_in = _owned_value(x, registry, self.component_id, "p_in_Pa")
        p_out = _owned_value(x, registry, self.component_id, "p_out_Pa")
        m_dot = _owned_value(x, registry, self.component_id, "m_dot_kg_s")
        velocity = m_dot / (self.rho_kg_m3 * self.area_m2)
        expected_dp = self.K * 0.5 * self.rho_kg_m3 * velocity * abs(velocity)
        return [
            ResidualRecord(
                name=f"{self.component_id}.incompressible_pressure_drop",
                value=(p_in - p_out) - expected_dp,
                scale=self.residual_scale_Pa,
                source=self.component_id,
                role="equation",
                diagnostic_key="incompressible_pressure_drop_mismatch",
                description=(
                    "Low-fidelity incompressible restriction residual "
                    "(p_in - p_out) - K*0.5*rho*v*abs(v)."
                ),
            )
        ]

    def metadata(self) -> dict[str, Any]:
        return _metadata(
            self,
            "fluid",
            [
                "incompressible flow",
                "lumped pressure loss",
                "constant rho",
                "no compressibility",
                "no choking",
                "no detailed pipe friction correlation",
            ],
        )


class IncompressibleOrificeModule(BaseModule):
    """Low-fidelity non-choked incompressible orifice relation."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "IncompressibleOrificeModule", parameters)
        self.CdA_m2 = _required_positive(parameters, "CdA_m2")
        self.rho_kg_m3 = _required_positive(parameters, "rho_kg_m3")
        self.residual_scale_kg2_s2 = _positive_float(
            parameters.get("residual_scale_kg2_s2", 1e-4),
            "residual_scale_kg2_s2",
        )
        self.records = [
            _owned_record(
                component_id,
                parameters,
                "p_upstream_Pa",
                "Pa",
                "p_lower_bound",
                "p_upper_bound",
                "p_upstream_initial_guess",
                "p_scale",
                1e3,
                1e7,
                120000.0,
                1e5,
            ),
            _owned_record(
                component_id,
                parameters,
                "p_downstream_Pa",
                "Pa",
                "p_lower_bound",
                "p_upper_bound",
                "p_downstream_initial_guess",
                "p_scale",
                1e3,
                1e7,
                100000.0,
                1e5,
            ),
            _owned_record(
                component_id,
                parameters,
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
        ]

    def declare_variables(self) -> list[VariableRecord]:
        return list(self.records)

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        p_upstream = _owned_value(x, registry, self.component_id, "p_upstream_Pa")
        p_downstream = _owned_value(x, registry, self.component_id, "p_downstream_Pa")
        m_dot = _owned_value(x, registry, self.component_id, "m_dot_kg_s")
        pressure_delta = p_upstream - p_downstream
        expected_squared = 2.0 * self.rho_kg_m3 * self.CdA_m2**2 * pressure_delta
        return [
            ResidualRecord(
                name=f"{self.component_id}.incompressible_orifice",
                value=m_dot**2 - expected_squared,
                scale=self.residual_scale_kg2_s2,
                source=self.component_id,
                role="equation",
                diagnostic_key="incompressible_orifice_mismatch",
                description=(
                    "Low-fidelity incompressible orifice squared residual "
                    "m_dot^2 - 2*rho*CdA^2*(p_upstream - p_downstream)."
                ),
            )
        ]

    def metadata(self) -> dict[str, Any]:
        return _metadata(
            self,
            "fluid",
            [
                "incompressible",
                "non-choked",
                "one-direction flow",
                "m_dot >= 0",
                "p_upstream should be >= p_downstream",
                "no cavitation",
                "no compressible gas choking",
            ],
        )


class MassBalanceRateModule(BaseModule):
    """Generic lumped mass balance rate relation using existing variables."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "MassBalanceRateModule", parameters)
        self.input_variables = _required_variable_list(parameters, "input_variables")
        self.output_variables = _required_variable_list(parameters, "output_variables")
        if not self.input_variables and not self.output_variables:
            raise ValueError(
                f"{component_id}: MassBalanceRateModule requires at least one flow variable"
            )
        dm_dt_variable = parameters.get("dm_dt_variable")
        if dm_dt_variable is not None:
            if not isinstance(dm_dt_variable, str) or not is_qualified_variable_name(dm_dt_variable):
                raise ValueError("dm_dt_variable must use component.variable format")
        self.dm_dt_variable = dm_dt_variable
        self.target_dm_dt_kg_s = _finite_float(
            parameters.get("target_dm_dt_kg_s", 0.0),
            "target_dm_dt_kg_s",
        )
        self.residual_scale_kg_s = _positive_float(
            parameters.get("residual_scale_kg_s", 0.01),
            "residual_scale_kg_s",
        )

    def declare_variables(self) -> list[VariableRecord]:
        return []

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        try:
            input_sum = sum(float(x[registry.get_index(name)]) for name in self.input_variables)
            output_sum = sum(float(x[registry.get_index(name)]) for name in self.output_variables)
            dm_dt = (
                float(x[registry.get_index(self.dm_dt_variable)])
                if self.dm_dt_variable is not None
                else self.target_dm_dt_kg_s
            )
        except KeyError as exc:
            raise KeyError(
                f"{self.component_id}: MassBalanceRateModule references unknown variable: {exc}"
            ) from exc
        return [
            ResidualRecord(
                name=f"{self.component_id}.mass_balance_rate",
                value=input_sum - output_sum - dm_dt,
                scale=self.residual_scale_kg_s,
                source=self.component_id,
                role="equation",
                diagnostic_key="mass_balance_rate_mismatch",
                description="Low-fidelity mass balance residual sum(inputs) - sum(outputs) - dm_dt.",
            )
        ]

    def metadata(self) -> dict[str, Any]:
        return _metadata(
            self,
            "fluid",
            [
                "lumped control volume",
                "no species distinction",
                "no density state calculation",
                "no hidden unit conversion",
            ],
        )


class MixerEnergyBalanceModule(BaseModule):
    """Low-fidelity incompressible mixing mass and energy residuals."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "MixerEnergyBalanceModule", parameters)
        self.inlet_m_dot_variables = _required_variable_list(
            parameters,
            "inlet_m_dot_variables",
        )
        self.inlet_T_variables = _required_variable_list(parameters, "inlet_T_variables")
        if len(self.inlet_m_dot_variables) != len(self.inlet_T_variables):
            raise ValueError("inlet_m_dot_variables and inlet_T_variables must have same length")
        if not self.inlet_m_dot_variables:
            raise ValueError(f"{component_id}: MixerEnergyBalanceModule requires inlets")
        self.outlet_m_dot_variable = _required_variable_name(parameters, "outlet_m_dot_variable")
        self.outlet_T_variable = _required_variable_name(parameters, "outlet_T_variable")
        self.mass_residual_scale_kg_s = _positive_float(
            parameters.get("mass_residual_scale_kg_s", 0.01),
            "mass_residual_scale_kg_s",
        )
        self.energy_residual_scale_kgK_s = _positive_float(
            parameters.get("energy_residual_scale_kgK_s", 1.0),
            "energy_residual_scale_kgK_s",
        )

    def declare_variables(self) -> list[VariableRecord]:
        return []

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        try:
            inlet_m_dots = [
                float(x[registry.get_index(name)]) for name in self.inlet_m_dot_variables
            ]
            inlet_temps = [
                float(x[registry.get_index(name)]) for name in self.inlet_T_variables
            ]
            outlet_m_dot = float(x[registry.get_index(self.outlet_m_dot_variable)])
            outlet_temp = float(x[registry.get_index(self.outlet_T_variable)])
        except KeyError as exc:
            raise KeyError(
                f"{self.component_id}: MixerEnergyBalanceModule references unknown variable: {exc}"
            ) from exc
        mass_sum = sum(inlet_m_dots)
        inlet_energy = sum(
            m_dot * temperature
            for m_dot, temperature in zip(inlet_m_dots, inlet_temps, strict=True)
        )
        return [
            ResidualRecord(
                name=f"{self.component_id}.mixer_mass_balance",
                value=outlet_m_dot - mass_sum,
                scale=self.mass_residual_scale_kg_s,
                source=self.component_id,
                role="equation",
                diagnostic_key="mixer_mass_balance_mismatch",
                description="Low-fidelity mixer mass residual outlet_m_dot - sum(inlet_m_dot).",
            ),
            ResidualRecord(
                name=f"{self.component_id}.mixer_energy_balance",
                value=outlet_m_dot * outlet_temp - inlet_energy,
                scale=self.energy_residual_scale_kgK_s,
                source=self.component_id,
                role="equation",
                diagnostic_key="mixer_energy_balance_mismatch",
                description=(
                    "Low-fidelity mixer energy residual "
                    "outlet_m_dot*T_out - sum(inlet_m_dot*T_in)."
                ),
            ),
        ]

    def metadata(self) -> dict[str, Any]:
        return _metadata(
            self,
            "fluid",
            [
                "incompressible mixing",
                "same cp for all streams",
                "no heat loss",
                "no phase change",
                "no chemical reaction",
                "no pressure calculation",
            ],
        )


class PumpHydraulicPowerModule(BaseModule):
    """Low-fidelity hydraulic pump shaft power relation."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "PumpHydraulicPowerModule", parameters)
        self.rho_kg_m3 = _required_positive(parameters, "rho_kg_m3")
        self.efficiency = _positive_float(parameters.get("efficiency", 1.0), "efficiency")
        if self.efficiency > 1:
            raise ValueError("efficiency must be <= 1")
        self.residual_scale_W = _positive_float(
            parameters.get("residual_scale_W", 1000.0),
            "residual_scale_W",
        )
        self.records = [
            _owned_record(
                component_id,
                parameters,
                "p_out_Pa",
                "Pa",
                "p_lower_bound",
                "p_upper_bound",
                "p_out_initial_guess",
                "p_scale",
                1e3,
                1e7,
                200000.0,
                1e5,
            ),
            _owned_record(
                component_id,
                parameters,
                "p_in_Pa",
                "Pa",
                "p_lower_bound",
                "p_upper_bound",
                "p_in_initial_guess",
                "p_scale",
                1e3,
                1e7,
                100000.0,
                1e5,
            ),
            _owned_record(
                component_id,
                parameters,
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
            _owned_record(
                component_id,
                parameters,
                "P_shaft_W",
                "W",
                "P_lower_bound",
                "P_upper_bound",
                "P_initial_guess",
                "P_scale",
                0.0,
                1e7,
                1000.0,
                1000.0,
            ),
        ]

    def declare_variables(self) -> list[VariableRecord]:
        return list(self.records)

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        p_out = _owned_value(x, registry, self.component_id, "p_out_Pa")
        p_in = _owned_value(x, registry, self.component_id, "p_in_Pa")
        m_dot = _owned_value(x, registry, self.component_id, "m_dot_kg_s")
        p_shaft = _owned_value(x, registry, self.component_id, "P_shaft_W")
        expected_power = ((p_out - p_in) * m_dot / self.rho_kg_m3) / self.efficiency
        return [
            ResidualRecord(
                name=f"{self.component_id}.pump_hydraulic_power",
                value=p_shaft - expected_power,
                scale=self.residual_scale_W,
                source=self.component_id,
                role="equation",
                diagnostic_key="pump_hydraulic_power_mismatch",
                description="Low-fidelity pump power residual P_shaft - (delta_p*m_dot/rho)/efficiency.",
            )
        ]

    def metadata(self) -> dict[str, Any]:
        return _metadata(
            self,
            "fluid",
            [
                "incompressible fluid",
                "positive flow",
                "lumped pump power relation",
                "no pump map",
                "no speed dependence",
                "no motor model",
            ],
        )


def _finite_float(value: Any, name: str) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a finite number") from exc
    if not math.isfinite(parsed):
        raise ValueError(f"{name} must be finite")
    return parsed


def _positive_float(value: Any, name: str) -> float:
    parsed = _finite_float(value, name)
    if parsed <= 0:
        raise ValueError(f"{name} must be positive")
    return parsed


def _nonnegative_float(value: Any, name: str) -> float:
    parsed = _finite_float(value, name)
    if parsed < 0:
        raise ValueError(f"{name} must be nonnegative")
    return parsed


def _required_positive(parameters: dict[str, Any], name: str) -> float:
    if name not in parameters:
        raise ValueError(f"{name} is required")
    return _positive_float(parameters[name], name)


def _required_nonnegative(parameters: dict[str, Any], name: str) -> float:
    if name not in parameters:
        raise ValueError(f"{name} is required")
    return _nonnegative_float(parameters[name], name)


def _owned_record(
    component_id: str,
    parameters: dict[str, Any],
    local_name: str,
    unit: str,
    lower_key: str,
    upper_key: str,
    initial_key: str,
    scale_key: str,
    lower_default: float,
    upper_default: float,
    initial_default: float,
    scale_default: float,
) -> VariableRecord:
    return VariableRecord(
        name=f"{component_id}.{local_name}",
        unit=unit,
        lower_bound=_finite_float(parameters.get(lower_key, lower_default), lower_key),
        upper_bound=_finite_float(parameters.get(upper_key, upper_default), upper_key),
        initial_guess=_finite_float(parameters.get(initial_key, initial_default), initial_key),
        scale=_positive_float(parameters.get(scale_key, scale_default), scale_key),
        source_component=component_id,
        local_name=local_name,
    )


def _owned_value(
    x: np.ndarray,
    registry: VariableRegistry,
    component_id: str,
    local_name: str,
) -> float:
    return float(x[registry.get_index(f"{component_id}.{local_name}")])


def _required_variable_name(parameters: dict[str, Any], name: str) -> str:
    value = parameters.get(name)
    if not isinstance(value, str) or not is_qualified_variable_name(value):
        raise ValueError(f"{name} must use component.variable format")
    return value


def _required_variable_list(parameters: dict[str, Any], name: str) -> list[str]:
    if name not in parameters:
        raise ValueError(f"{name} is required")
    value = parameters[name]
    if not isinstance(value, list):
        raise ValueError(f"{name} must be a list")
    variables: list[str] = []
    for item in value:
        if not isinstance(item, str) or not is_qualified_variable_name(item):
            raise ValueError(f"{name} entries must use component.variable format")
        variables.append(item)
    return variables


def _metadata(module: BaseModule, domain: str, validity: list[str]) -> dict[str, Any]:
    return {
        "component_id": module.component_id,
        "module_type": module.module_type,
        "purpose": "low_fidelity_physical_audit",
        "domain": domain,
        "validity": validity,
    }
