"""Additional low-fidelity electrochemical helper audit modules."""

from __future__ import annotations

from typing import Any

import numpy as np

from physicsguard.core.registry import VariableRecord, VariableRegistry
from physicsguard.core.residual import ResidualRecord
from physicsguard.modules.base import BaseModule
from physicsguard.modules.physical._common import (
    finite_float,
    metadata,
    owned_record,
    positive_float,
    required,
    required_positive,
    value,
)
from physicsguard.modules.physical.constants import FARADAY_CONSTANT


class ChemicalPowerLHVModule(BaseModule):
    """Chemical power from fuel mass flow and lower heating value."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "ChemicalPowerLHVModule", parameters)
        self.LHV_J_kg = required_positive(parameters, "LHV_J_kg")
        self.residual_scale_W = positive_float(
            parameters.get("residual_scale_W", 1000.0),
            "residual_scale_W",
        )
        self.records = [
            owned_record(
                component_id,
                parameters,
                "m_dot_fuel_kg_s",
                "kg/s",
                "m_dot_fuel_lower_bound",
                "m_dot_fuel_upper_bound",
                "m_dot_fuel_initial_guess",
                "m_dot_fuel_scale",
                0.0,
                100.0,
                1e-3,
                1e-3,
            ),
            _power_record(component_id, parameters, "P_chemical_W", "P_chemical", 1000.0),
        ]

    def declare_variables(self) -> list[VariableRecord]:
        return list(self.records)

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        m_dot = value(x, registry, self.component_id, "m_dot_fuel_kg_s")
        power = value(x, registry, self.component_id, "P_chemical_W")
        return [
            ResidualRecord(
                name=f"{self.component_id}.chemical_power_lhv",
                value=power - m_dot * self.LHV_J_kg,
                scale=self.residual_scale_W,
                source=self.component_id,
                role="equation",
                diagnostic_key="chemical_power_lhv_mismatch",
                description="Chemical power residual P_chemical - m_dot_fuel*LHV.",
            )
        ]

    def metadata(self) -> dict[str, Any]:
        return metadata(
            self,
            "electrochemical",
            [
                "LHV-based chemical power only",
                "no HHV",
                "no composition model",
                "no thermal losses",
            ],
        )


class StackChemicalEfficiencyModule(BaseModule):
    """Simple electrochemical stack chemical efficiency relation."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "StackChemicalEfficiencyModule", parameters)
        self.residual_scale = positive_float(
            parameters.get("residual_scale", 0.01),
            "residual_scale",
        )
        self.denominator_min_abs = positive_float(
            parameters.get("denominator_min_abs", 1e-9),
            "denominator_min_abs",
        )
        self.records = [
            _power_record(component_id, parameters, "P_stack_W", "P_stack", 500.0),
            _power_record(component_id, parameters, "P_chemical_W", "P_chemical", 1000.0),
            owned_record(
                component_id,
                parameters,
                "efficiency",
                None,
                "efficiency_lower_bound",
                "efficiency_upper_bound",
                "efficiency_initial_guess",
                "efficiency_scale",
                0.0,
                1.5,
                0.5,
                0.1,
            ),
        ]

    def declare_variables(self) -> list[VariableRecord]:
        return list(self.records)

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        p_stack = value(x, registry, self.component_id, "P_stack_W")
        p_chemical = value(x, registry, self.component_id, "P_chemical_W")
        if abs(p_chemical) < self.denominator_min_abs:
            raise ValueError(f"{self.component_id}: P_chemical_W is below denominator_min_abs")
        efficiency = value(x, registry, self.component_id, "efficiency")
        return [
            ResidualRecord(
                name=f"{self.component_id}.stack_chemical_efficiency",
                value=efficiency - p_stack / p_chemical,
                scale=self.residual_scale,
                source=self.component_id,
                role="equation",
                diagnostic_key="stack_chemical_efficiency_mismatch",
                description="Stack chemical efficiency residual efficiency - P_stack/P_chemical.",
            )
        ]

    def metadata(self) -> dict[str, Any]:
        return metadata(
            self,
            "electrochemical",
            [
                "algebraic efficiency sanity check",
                "no detailed loss model",
                "no auxiliary power unless included externally",
                "efficiency greater than one may be diagnostically suspicious",
            ],
        )


class AirOxygenMolarFlowModule(BaseModule):
    """Relate oxygen molar flow demand to dry-air molar and mass flow."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "AirOxygenMolarFlowModule", parameters)
        self.oxygen_mole_fraction = positive_float(
            parameters.get("oxygen_mole_fraction", 0.21),
            "oxygen_mole_fraction",
        )
        if self.oxygen_mole_fraction > 1.0:
            raise ValueError("oxygen_mole_fraction must be <= 1")
        self.molar_mass_air_kg_mol = positive_float(
            parameters.get("molar_mass_air_kg_mol", 0.0289652),
            "molar_mass_air_kg_mol",
        )
        self.molar_residual_scale_mol_s = positive_float(
            parameters.get("molar_residual_scale_mol_s", 1e-3),
            "molar_residual_scale_mol_s",
        )
        self.mass_residual_scale_kg_s = positive_float(
            parameters.get("mass_residual_scale_kg_s", 1e-3),
            "mass_residual_scale_kg_s",
        )
        self.records = [
            _molar_flow_record(component_id, parameters, "n_dot_O2_mol_s", "n_dot_O2"),
            _molar_flow_record(component_id, parameters, "n_dot_air_mol_s", "n_dot_air"),
            owned_record(
                component_id,
                parameters,
                "m_dot_air_kg_s",
                "kg/s",
                "m_dot_air_lower_bound",
                "m_dot_air_upper_bound",
                "m_dot_air_initial_guess",
                "m_dot_air_scale",
                0.0,
                100.0,
                1e-3,
                1e-3,
            ),
        ]

    def declare_variables(self) -> list[VariableRecord]:
        return list(self.records)

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        n_o2 = value(x, registry, self.component_id, "n_dot_O2_mol_s")
        n_air = value(x, registry, self.component_id, "n_dot_air_mol_s")
        m_air = value(x, registry, self.component_id, "m_dot_air_kg_s")
        return [
            ResidualRecord(
                name=f"{self.component_id}.air_oxygen_molar_flow",
                value=n_air - n_o2 / self.oxygen_mole_fraction,
                scale=self.molar_residual_scale_mol_s,
                source=self.component_id,
                role="equation",
                diagnostic_key="air_oxygen_molar_flow_mismatch",
                description="Dry air molar flow residual n_air - n_O2/x_O2.",
            ),
            ResidualRecord(
                name=f"{self.component_id}.air_mass_flow_from_molar_flow",
                value=m_air - n_air * self.molar_mass_air_kg_mol,
                scale=self.mass_residual_scale_kg_s,
                source=self.component_id,
                role="equation",
                diagnostic_key="air_mass_flow_from_molar_flow_mismatch",
                description="Dry air mass flow residual m_air - n_air*molar_mass_air.",
            ),
        ]

    def metadata(self) -> dict[str, Any]:
        return metadata(
            self,
            "electrochemical",
            [
                "dry-air approximation",
                "fixed oxygen mole fraction",
                "no humidity correction",
                "no pressure/temperature state model",
            ],
        )


class WaterProductionFaradayModule(BaseModule):
    """Low-fidelity Faraday-law water production relation."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "WaterProductionFaradayModule", parameters)
        self.n_cells = required_positive(parameters, "n_cells")
        self.faradaic_efficiency = positive_float(
            parameters.get("faradaic_efficiency", 1.0),
            "faradaic_efficiency",
        )
        if self.faradaic_efficiency > 1.0:
            raise ValueError("faradaic_efficiency must be <= 1")
        self.residual_scale_mol_s = positive_float(
            parameters.get("residual_scale_mol_s", 1e-3),
            "residual_scale_mol_s",
        )
        self.records = [
            owned_record(
                component_id,
                parameters,
                "current_A",
                "A",
                "current_lower_bound",
                "current_upper_bound",
                "current_initial_guess",
                "current_scale",
                0.0,
                5000.0,
                100.0,
                100.0,
            ),
            _molar_flow_record(component_id, parameters, "n_dot_H2O_mol_s", "n_dot_H2O"),
        ]

    def declare_variables(self) -> list[VariableRecord]:
        return list(self.records)

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        current = value(x, registry, self.component_id, "current_A")
        n_dot = value(x, registry, self.component_id, "n_dot_H2O_mol_s")
        expected = self.faradaic_efficiency * self.n_cells * current / (2.0 * FARADAY_CONSTANT)
        return [
            ResidualRecord(
                name=f"{self.component_id}.water_production_faraday",
                value=n_dot - expected,
                scale=self.residual_scale_mol_s,
                source=self.component_id,
                role="equation",
                diagnostic_key="water_production_faraday_mismatch",
                description="Faraday-law water production residual n_dot_H2O - efficiency*n_cells*I/(2F).",
            )
        ]

    def metadata(self) -> dict[str, Any]:
        return metadata(
            self,
            "electrochemical",
            [
                "PEM fuel-cell style water production relation",
                "lumped Faraday law",
                "no water crossover",
                "no evaporation/condensation",
                "no membrane water model",
            ],
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
        0.0,
        1e8,
        initial_default,
        1000.0,
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
        0.0,
        1e3,
        1e-3,
        1e-3,
    )
