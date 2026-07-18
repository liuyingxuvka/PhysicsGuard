"""Low-fidelity thermodynamic and thermal helper audit modules."""

from __future__ import annotations

from typing import Any

import numpy as np

from physicsguard.core.registry import VariableRecord, VariableRegistry
from physicsguard.core.residual import ResidualRecord
from physicsguard.modules.base import BaseModule
from physicsguard.modules.physical._common import (
    finite_float,
    metadata,
    nonnegative_float,
    owned_record,
    positive_float,
    required,
    required_positive,
    value,
)
from physicsguard.modules.physical.constants import (
    STEFAN_BOLTZMANN_CONSTANT,
    UNIVERSAL_GAS_CONSTANT,
)


class MassMolarFlowConversionModule(BaseModule):
    """Convert between molar flow and mass flow for one species."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "MassMolarFlowConversionModule", parameters)
        self.molar_mass_kg_mol = required_positive(parameters, "molar_mass_kg_mol")
        self.residual_scale_kg_s = positive_float(
            parameters.get("residual_scale_kg_s", 1e-3),
            "residual_scale_kg_s",
        )
        self.records = [
            owned_record(
                component_id,
                parameters,
                "n_dot_mol_s",
                "mol/s",
                "n_dot_lower_bound",
                "n_dot_upper_bound",
                "n_dot_initial_guess",
                "n_dot_scale",
                -1e3,
                1e3,
                1e-3,
                1e-3,
            ),
            owned_record(
                component_id,
                parameters,
                "m_dot_kg_s",
                "kg/s",
                "m_dot_lower_bound",
                "m_dot_upper_bound",
                "m_dot_initial_guess",
                "m_dot_scale",
                -100.0,
                100.0,
                1e-3,
                1e-3,
            ),
        ]

    def declare_variables(self) -> list[VariableRecord]:
        return list(self.records)

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        n_dot = value(x, registry, self.component_id, "n_dot_mol_s")
        m_dot = value(x, registry, self.component_id, "m_dot_kg_s")
        return [
            ResidualRecord(
                name=f"{self.component_id}.mass_molar_flow_conversion",
                value=m_dot - n_dot * self.molar_mass_kg_mol,
                scale=self.residual_scale_kg_s,
                source=self.component_id,
                role="equation",
                diagnostic_key="mass_molar_flow_conversion_mismatch",
                description="Mass/molar flow residual m_dot - n_dot*molar_mass.",
            )
        ]

    def metadata(self) -> dict[str, Any]:
        return metadata(
            self,
            "thermodynamic_conversion",
            ["single species conversion", "constant molar mass", "no composition model"],
        )


class MoleFractionFlowModule(BaseModule):
    """Relate species molar flow, total molar flow, and mole fraction."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "MoleFractionFlowModule", parameters)
        self.residual_scale_mol_s = positive_float(
            parameters.get("residual_scale_mol_s", 1e-3),
            "residual_scale_mol_s",
        )
        self.records = [
            _molar_flow_record(component_id, parameters, "total_n_dot_mol_s", "total_n_dot"),
            _molar_flow_record(component_id, parameters, "species_n_dot_mol_s", "species_n_dot"),
            owned_record(
                component_id,
                parameters,
                "mole_fraction",
                None,
                "mole_fraction_lower_bound",
                "mole_fraction_upper_bound",
                "mole_fraction_initial_guess",
                "mole_fraction_scale",
                0.0,
                1.0,
                0.21,
                1.0,
            ),
        ]

    def declare_variables(self) -> list[VariableRecord]:
        return list(self.records)

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        total = value(x, registry, self.component_id, "total_n_dot_mol_s")
        species = value(x, registry, self.component_id, "species_n_dot_mol_s")
        fraction = value(x, registry, self.component_id, "mole_fraction")
        return [
            ResidualRecord(
                name=f"{self.component_id}.mole_fraction_flow",
                value=species - fraction * total,
                scale=self.residual_scale_mol_s,
                source=self.component_id,
                role="equation",
                diagnostic_key="mole_fraction_flow_mismatch",
                description="Mole-fraction flow residual species_n_dot - mole_fraction*total_n_dot.",
            )
        ]

    def metadata(self) -> dict[str, Any]:
        return metadata(
            self,
            "thermodynamic_conversion",
            [
                "lumped mixture relation",
                "no species transport",
                "no reaction",
                "mole_fraction should be between 0 and 1",
            ],
        )


class VolumetricMassFlowConversionModule(BaseModule):
    """Relate mass flow and volumetric flow at constant density."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "VolumetricMassFlowConversionModule", parameters)
        self.rho_kg_m3 = required_positive(parameters, "rho_kg_m3")
        self.residual_scale_kg_s = positive_float(
            parameters.get("residual_scale_kg_s", 0.01),
            "residual_scale_kg_s",
        )
        self.records = [
            _mass_flow_record(component_id, parameters, "m_dot_kg_s", "m_dot"),
            owned_record(
                component_id,
                parameters,
                "V_dot_m3_s",
                "m^3/s",
                "V_dot_lower_bound",
                "V_dot_upper_bound",
                "V_dot_initial_guess",
                "V_dot_scale",
                -10.0,
                10.0,
                1e-3,
                1e-3,
            ),
        ]

    def declare_variables(self) -> list[VariableRecord]:
        return list(self.records)

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        m_dot = value(x, registry, self.component_id, "m_dot_kg_s")
        v_dot = value(x, registry, self.component_id, "V_dot_m3_s")
        return [
            ResidualRecord(
                name=f"{self.component_id}.volumetric_mass_flow_conversion",
                value=m_dot - self.rho_kg_m3 * v_dot,
                scale=self.residual_scale_kg_s,
                source=self.component_id,
                role="equation",
                diagnostic_key="volumetric_mass_flow_conversion_mismatch",
                description="Volumetric/mass flow residual m_dot - rho*V_dot.",
            )
        ]

    def metadata(self) -> dict[str, Any]:
        return metadata(
            self,
            "thermodynamic_conversion",
            ["constant density", "no compressibility", "no multiphase flow"],
        )


class DensityMassVolumeModule(BaseModule):
    """Relate mass, density, and volume."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "DensityMassVolumeModule", parameters)
        self.residual_scale_kg = positive_float(
            parameters.get("residual_scale_kg", 1.0),
            "residual_scale_kg",
        )
        self.records = [
            owned_record(
                component_id,
                parameters,
                "mass_kg",
                "kg",
                "mass_lower_bound",
                "mass_upper_bound",
                "mass_initial_guess",
                "mass_scale",
                0.0,
                1e6,
                1.0,
                1.0,
            ),
            _density_record(component_id, parameters),
            owned_record(
                component_id,
                parameters,
                "volume_m3",
                "m^3",
                "volume_lower_bound",
                "volume_upper_bound",
                "volume_initial_guess",
                "volume_scale",
                0.0,
                1e6,
                1.0,
                1.0,
            ),
        ]

    def declare_variables(self) -> list[VariableRecord]:
        return list(self.records)

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        mass = value(x, registry, self.component_id, "mass_kg")
        density = value(x, registry, self.component_id, "rho_kg_m3")
        volume = value(x, registry, self.component_id, "volume_m3")
        return [
            ResidualRecord(
                name=f"{self.component_id}.density_mass_volume",
                value=mass - density * volume,
                scale=self.residual_scale_kg,
                source=self.component_id,
                role="equation",
                diagnostic_key="density_mass_volume_mismatch",
                description="Density/mass/volume residual mass - rho*volume.",
            )
        ]

    def metadata(self) -> dict[str, Any]:
        return metadata(
            self,
            "thermodynamic_conversion",
            ["constant bulk density", "no spatial distribution", "no phase change"],
        )


class IdealGasDensityModule(BaseModule):
    """Low-fidelity ideal gas density relation."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "IdealGasDensityModule", parameters)
        self.molar_mass_kg_mol = required_positive(parameters, "molar_mass_kg_mol")
        self.residual_scale_kg_m3 = positive_float(
            parameters.get("residual_scale_kg_m3", 0.1),
            "residual_scale_kg_m3",
        )
        self.temperature_min_abs = positive_float(
            parameters.get("temperature_min_abs", 1e-12),
            "temperature_min_abs",
        )
        self.records = [
            _pressure_record(component_id, parameters, "p_Pa", "p"),
            _temperature_record(component_id, parameters, "T_K", "T", 300.0),
            _density_record(component_id, parameters),
        ]

    def declare_variables(self) -> list[VariableRecord]:
        return list(self.records)

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        pressure = value(x, registry, self.component_id, "p_Pa")
        temperature = value(x, registry, self.component_id, "T_K")
        if abs(temperature) < self.temperature_min_abs:
            raise ValueError(f"{self.component_id}: T_K is below temperature_min_abs")
        density = value(x, registry, self.component_id, "rho_kg_m3")
        expected = pressure * self.molar_mass_kg_mol / (UNIVERSAL_GAS_CONSTANT * temperature)
        return [
            ResidualRecord(
                name=f"{self.component_id}.ideal_gas_density",
                value=density - expected,
                scale=self.residual_scale_kg_m3,
                source=self.component_id,
                role="equation",
                diagnostic_key="ideal_gas_density_mismatch",
                description="Ideal gas density residual rho - p*M/(R*T).",
            )
        ]

    def metadata(self) -> dict[str, Any]:
        return metadata(
            self,
            "gas",
            ["ideal gas only", "no real-gas correction", "no liquid/two-phase states"],
        )


class SpecificEnthalpyFlowModule(BaseModule):
    """Low-fidelity sensible enthalpy flow relation."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "SpecificEnthalpyFlowModule", parameters)
        self.cp_J_kgK = required_positive(parameters, "cp_J_kgK")
        self.T_ref_K = finite_float(parameters.get("T_ref_K", 0.0), "T_ref_K")
        self.residual_scale_W = positive_float(
            parameters.get("residual_scale_W", 1000.0),
            "residual_scale_W",
        )
        self.records = [
            _mass_flow_record(component_id, parameters, "m_dot_kg_s", "m_dot"),
            _temperature_record(component_id, parameters, "T_K", "T", 300.0),
            _power_record(component_id, parameters, "H_dot_W", "H_dot", 1000.0),
        ]

    def declare_variables(self) -> list[VariableRecord]:
        return list(self.records)

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        m_dot = value(x, registry, self.component_id, "m_dot_kg_s")
        temperature = value(x, registry, self.component_id, "T_K")
        h_dot = value(x, registry, self.component_id, "H_dot_W")
        expected = m_dot * self.cp_J_kgK * (temperature - self.T_ref_K)
        return [
            ResidualRecord(
                name=f"{self.component_id}.specific_enthalpy_flow",
                value=h_dot - expected,
                scale=self.residual_scale_W,
                source=self.component_id,
                role="equation",
                diagnostic_key="specific_enthalpy_flow_mismatch",
                description="Sensible enthalpy flow residual H_dot - m_dot*cp*(T - T_ref).",
            )
        ]

    def metadata(self) -> dict[str, Any]:
        return metadata(
            self,
            "thermal",
            [
                "constant cp",
                "sensible enthalpy only",
                "arbitrary reference temperature",
                "no phase change",
            ],
        )


class HeatExchangerEffectivenessModule(BaseModule):
    """Low-fidelity heat exchanger effectiveness relation."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "HeatExchangerEffectivenessModule", parameters)
        self.cp_hot_J_kgK = positive_float(parameters.get("cp_hot_J_kgK", 4180.0), "cp_hot_J_kgK")
        self.cp_cold_J_kgK = positive_float(parameters.get("cp_cold_J_kgK", 1005.0), "cp_cold_J_kgK")
        self.effectiveness = finite_float(required(parameters, "effectiveness"), "effectiveness")
        if not 0.0 <= self.effectiveness <= 1.0:
            raise ValueError("effectiveness must be between 0 and 1")
        self.residual_scale_W = positive_float(
            parameters.get("residual_scale_W", 1000.0),
            "residual_scale_W",
        )
        self.records = [
            _positive_flow_record(component_id, parameters, "m_dot_hot_kg_s", "m_dot_hot"),
            _temperature_record(component_id, parameters, "T_hot_in_K", "T_hot_in", 350.0),
            _temperature_record(component_id, parameters, "T_hot_out_K", "T_hot_out", 330.0),
            _positive_flow_record(component_id, parameters, "m_dot_cold_kg_s", "m_dot_cold"),
            _temperature_record(component_id, parameters, "T_cold_in_K", "T_cold_in", 300.0),
            _temperature_record(component_id, parameters, "T_cold_out_K", "T_cold_out", 320.0),
            _power_record(component_id, parameters, "Q_dot_W", "Q_dot", 1000.0),
        ]

    def declare_variables(self) -> list[VariableRecord]:
        return list(self.records)

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        m_hot = value(x, registry, self.component_id, "m_dot_hot_kg_s")
        t_hot_in = value(x, registry, self.component_id, "T_hot_in_K")
        t_hot_out = value(x, registry, self.component_id, "T_hot_out_K")
        m_cold = value(x, registry, self.component_id, "m_dot_cold_kg_s")
        t_cold_in = value(x, registry, self.component_id, "T_cold_in_K")
        t_cold_out = value(x, registry, self.component_id, "T_cold_out_K")
        q_dot = value(x, registry, self.component_id, "Q_dot_W")
        c_hot = m_hot * self.cp_hot_J_kgK
        c_cold = m_cold * self.cp_cold_J_kgK
        c_min = min(c_hot, c_cold)
        return [
            ResidualRecord(
                name=f"{self.component_id}.heat_exchanger_effectiveness",
                value=q_dot - self.effectiveness * c_min * (t_hot_in - t_cold_in),
                scale=self.residual_scale_W,
                source=self.component_id,
                role="equation",
                diagnostic_key="heat_exchanger_effectiveness_mismatch",
                description="Heat exchanger effectiveness residual.",
            ),
            ResidualRecord(
                name=f"{self.component_id}.heat_exchanger_hot_side_energy",
                value=q_dot - m_hot * self.cp_hot_J_kgK * (t_hot_in - t_hot_out),
                scale=self.residual_scale_W,
                source=self.component_id,
                role="equation",
                diagnostic_key="heat_exchanger_hot_side_energy_mismatch",
                description="Heat exchanger hot-side energy residual.",
            ),
            ResidualRecord(
                name=f"{self.component_id}.heat_exchanger_cold_side_energy",
                value=q_dot - m_cold * self.cp_cold_J_kgK * (t_cold_out - t_cold_in),
                scale=self.residual_scale_W,
                source=self.component_id,
                role="equation",
                diagnostic_key="heat_exchanger_cold_side_energy_mismatch",
                description="Heat exchanger cold-side energy residual.",
            ),
        ]

    def metadata(self) -> dict[str, Any]:
        return metadata(
            self,
            "thermal",
            [
                "lumped effectiveness model",
                "constant cp",
                "no pressure drop",
                "no phase change",
                "no detailed geometry",
                "no wall thermal mass",
            ],
        )


class RadiativeHeatTransferModule(BaseModule):
    """Low-fidelity gray-body radiation relation."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "RadiativeHeatTransferModule", parameters)
        self.emissivity = finite_float(required(parameters, "emissivity"), "emissivity")
        if not 0.0 <= self.emissivity <= 1.0:
            raise ValueError("emissivity must be between 0 and 1")
        self.area_m2 = required_positive(parameters, "area_m2")
        self.residual_scale_W = positive_float(
            parameters.get("residual_scale_W", 1000.0),
            "residual_scale_W",
        )
        self.records = [
            _temperature_record(component_id, parameters, "T_hot_K", "T_hot", 400.0),
            _temperature_record(component_id, parameters, "T_cold_K", "T_cold", 300.0),
            _power_record(component_id, parameters, "Q_dot_W", "Q_dot", 1000.0),
        ]

    def declare_variables(self) -> list[VariableRecord]:
        return list(self.records)

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        t_hot = value(x, registry, self.component_id, "T_hot_K")
        t_cold = value(x, registry, self.component_id, "T_cold_K")
        q_dot = value(x, registry, self.component_id, "Q_dot_W")
        expected = (
            self.emissivity
            * STEFAN_BOLTZMANN_CONSTANT
            * self.area_m2
            * (t_hot**4 - t_cold**4)
        )
        return [
            ResidualRecord(
                name=f"{self.component_id}.radiative_heat_transfer",
                value=q_dot - expected,
                scale=self.residual_scale_W,
                source=self.component_id,
                role="equation",
                diagnostic_key="radiative_heat_transfer_mismatch",
                description="Radiative heat transfer residual Q_dot - emissivity*sigma*A*(T_hot^4 - T_cold^4).",
            )
        ]

    def metadata(self) -> dict[str, Any]:
        return metadata(
            self,
            "thermal",
            [
                "gray-body lumped radiation",
                "no view-factor model unless emissivity already includes it",
                "no participating media",
                "no convection/conduction",
            ],
        )


class AmbientHeatLossModule(BaseModule):
    """Simple lumped heat loss to ambient."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "AmbientHeatLossModule", parameters)
        self.UA_W_K = nonnegative_float(required(parameters, "UA_W_K"), "UA_W_K")
        self.residual_scale_W = positive_float(
            parameters.get("residual_scale_W", 1000.0),
            "residual_scale_W",
        )
        self.records = [
            _temperature_record(component_id, parameters, "T_body_K", "T_body", 330.0),
            _temperature_record(component_id, parameters, "T_ambient_K", "T_ambient", 300.0),
            _power_record(component_id, parameters, "Q_loss_W", "Q_loss", 1000.0),
        ]

    def declare_variables(self) -> list[VariableRecord]:
        return list(self.records)

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        t_body = value(x, registry, self.component_id, "T_body_K")
        t_ambient = value(x, registry, self.component_id, "T_ambient_K")
        q_loss = value(x, registry, self.component_id, "Q_loss_W")
        return [
            ResidualRecord(
                name=f"{self.component_id}.ambient_heat_loss",
                value=q_loss - self.UA_W_K * (t_body - t_ambient),
                scale=self.residual_scale_W,
                source=self.component_id,
                role="equation",
                diagnostic_key="ambient_heat_loss_mismatch",
                description="Ambient heat loss residual Q_loss - UA*(T_body - T_ambient).",
            )
        ]

    def metadata(self) -> dict[str, Any]:
        return metadata(
            self,
            "thermal",
            ["lumped UA relation", "no radiation/convection split", "no thermal storage"],
        )


def _molar_flow_record(
    component_id: str,
    parameters: dict[str, Any],
    local_name: str,
    prefix: str,
) -> VariableRecord:
    return owned_record(
        component_id,
        parameters,
        local_name,
        "mol/s",
        f"{prefix}_lower_bound",
        f"{prefix}_upper_bound",
        f"{prefix}_initial_guess",
        f"{prefix}_scale",
        -1e3,
        1e3,
        1e-3,
        1e-3,
    )


def _mass_flow_record(
    component_id: str,
    parameters: dict[str, Any],
    local_name: str,
    prefix: str,
) -> VariableRecord:
    return owned_record(
        component_id,
        parameters,
        local_name,
        "kg/s",
        f"{prefix}_lower_bound",
        f"{prefix}_upper_bound",
        f"{prefix}_initial_guess",
        f"{prefix}_scale",
        -100.0,
        100.0,
        1.0,
        1.0,
    )


def _positive_flow_record(
    component_id: str,
    parameters: dict[str, Any],
    local_name: str,
    prefix: str,
) -> VariableRecord:
    return owned_record(
        component_id,
        parameters,
        local_name,
        "kg/s",
        f"{prefix}_lower_bound",
        f"{prefix}_upper_bound",
        f"{prefix}_initial_guess",
        f"{prefix}_scale",
        0.0,
        100.0,
        1.0,
        1.0,
    )


def _pressure_record(
    component_id: str,
    parameters: dict[str, Any],
    local_name: str,
    prefix: str,
) -> VariableRecord:
    return owned_record(
        component_id,
        parameters,
        local_name,
        "Pa",
        f"{prefix}_lower_bound",
        f"{prefix}_upper_bound",
        f"{prefix}_initial_guess",
        f"{prefix}_scale",
        1e3,
        1e7,
        101325.0,
        1e5,
    )


def _temperature_record(
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
        "K",
        f"{prefix}_lower_bound",
        f"{prefix}_upper_bound",
        f"{prefix}_initial_guess",
        f"{prefix}_scale",
        100.0,
        1000.0,
        initial_default,
        100.0,
    )


def _density_record(component_id: str, parameters: dict[str, Any]) -> VariableRecord:
    return owned_record(
        component_id,
        parameters,
        "rho_kg_m3",
        "kg/m^3",
        "rho_lower_bound",
        "rho_upper_bound",
        "rho_initial_guess",
        "rho_scale",
        0.0,
        1e5,
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
