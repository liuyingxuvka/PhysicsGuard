"""Component-level fuel-cell and electrolyzer balance-of-plant audit modules."""

from __future__ import annotations

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
    molar_flow_record,
    positive_current_record,
    positive_float,
    power_record,
    residual_record,
    required_positive,
    validate_efficiency,
    validate_fraction_value,
    value,
)
from physicsguard.modules.physical.constants import FARADAY_CONSTANT


def _eta(parameters: dict[str, Any]) -> float:
    return validate_efficiency(parameters.get("faradaic_efficiency", 1.0), "faradaic_efficiency")


def _current_record(component_id: str, parameters: dict[str, Any]) -> VariableRecord:
    return positive_current_record(component_id, parameters, "current_A", "current", 100.0)


class FuelCellCathodeAirSupplyModule(BaseModule):
    """Low-fidelity cathode air supply audit."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "FuelCellCathodeAirSupplyModule", parameters)
        self.n_cells = required_positive(parameters, "n_cells")
        self.x_o2 = validate_fraction_value(parameters.get("oxygen_mole_fraction", 0.21), "oxygen_mole_fraction", allow_zero=False)
        self.molar_mass_air = required_positive(parameters, "molar_mass_air_kg_mol") if "molar_mass_air_kg_mol" in parameters else positive_float(0.0289652, "molar_mass_air_kg_mol")
        self.eta = _eta(parameters)
        self.mol_scale = positive_float(parameters.get("residual_scale_mol_s", 1e-3), "residual_scale_mol_s")
        self.mass_scale = positive_float(parameters.get("residual_scale_kg_s", 1e-3), "residual_scale_kg_s")
        self.records = [
            _current_record(component_id, parameters),
            molar_flow_record(component_id, parameters, "n_dot_O2_consumed_mol_s", "n_dot_O2_consumed", 1e-3),
            molar_flow_record(component_id, parameters, "n_dot_air_feed_mol_s", "n_dot_air_feed", 0.01),
            mass_flow_record(component_id, parameters, "m_dot_air_feed_kg_s", "m_dot_air_feed", 1e-3),
            bounded_record(component_id, parameters, "oxygen_stoichiometry", None, "oxygen_stoichiometry", 0.0, 100.0, 2.0, 1.0),
        ]

    def declare_variables(self) -> list[VariableRecord]:
        return list(self.records)

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        current = value(x, registry, self.component_id, "current_A")
        o2 = value(x, registry, self.component_id, "n_dot_O2_consumed_mol_s")
        air_n = value(x, registry, self.component_id, "n_dot_air_feed_mol_s")
        air_m = value(x, registry, self.component_id, "m_dot_air_feed_kg_s")
        stoich = value(x, registry, self.component_id, "oxygen_stoichiometry")
        o2_expected = self.eta * self.n_cells * current / (4.0 * FARADAY_CONSTANT)
        air_expected = stoich * o2 / self.x_o2
        return [
            residual_record(self, "fc_cathode_o2_consumption", o2 - o2_expected, self.mol_scale, "fc_cathode_o2_consumption_mismatch", "Cathode O2 Faraday consumption residual."),
            residual_record(self, "fc_cathode_air_molar_feed", air_n - air_expected, self.mol_scale, "fc_cathode_air_molar_feed_mismatch", "Cathode air molar feed residual."),
            residual_record(self, "fc_cathode_air_mass_feed", air_m - air_n * self.molar_mass_air, self.mass_scale, "fc_cathode_air_mass_feed_mismatch", "Cathode air mass feed residual."),
        ]

    def metadata(self) -> dict[str, Any]:
        return component_metadata(self, "electrochemical_bop", ["dry air approximation", "no humidity correction", "no pressure drop", "no compressor model", "no cathode water model"])


class FuelCellAnodeHydrogenSupplyModule(BaseModule):
    """Low-fidelity anode hydrogen supply audit."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "FuelCellAnodeHydrogenSupplyModule", parameters)
        self.n_cells = required_positive(parameters, "n_cells")
        self.molar_mass_h2 = positive_float(parameters.get("molar_mass_H2_kg_mol", 0.00201588), "molar_mass_H2_kg_mol")
        self.eta = _eta(parameters)
        self.mol_scale = positive_float(parameters.get("residual_scale_mol_s", 1e-3), "residual_scale_mol_s")
        self.mass_scale = positive_float(parameters.get("residual_scale_kg_s", 1e-4), "residual_scale_kg_s")
        self.records = [
            _current_record(component_id, parameters),
            molar_flow_record(component_id, parameters, "n_dot_H2_consumed_mol_s", "n_dot_H2_consumed", 1e-3),
            molar_flow_record(component_id, parameters, "n_dot_H2_feed_mol_s", "n_dot_H2_feed", 0.01),
            mass_flow_record(component_id, parameters, "m_dot_H2_feed_kg_s", "m_dot_H2_feed", 1e-4),
            bounded_record(component_id, parameters, "hydrogen_stoichiometry", None, "hydrogen_stoichiometry", 0.0, 100.0, 1.5, 1.0),
        ]

    def declare_variables(self) -> list[VariableRecord]:
        return list(self.records)

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        current = value(x, registry, self.component_id, "current_A")
        h2 = value(x, registry, self.component_id, "n_dot_H2_consumed_mol_s")
        feed = value(x, registry, self.component_id, "n_dot_H2_feed_mol_s")
        mass = value(x, registry, self.component_id, "m_dot_H2_feed_kg_s")
        stoich = value(x, registry, self.component_id, "hydrogen_stoichiometry")
        expected = self.eta * self.n_cells * current / (2.0 * FARADAY_CONSTANT)
        return [
            residual_record(self, "fc_anode_h2_consumption", h2 - expected, self.mol_scale, "fc_anode_h2_consumption_mismatch", "Anode H2 Faraday consumption residual."),
            residual_record(self, "fc_anode_h2_feed_stoichiometry", feed - stoich * h2, self.mol_scale, "fc_anode_h2_feed_stoichiometry_mismatch", "Anode H2 feed stoichiometry residual."),
            residual_record(self, "fc_anode_h2_mass_feed", mass - feed * self.molar_mass_h2, self.mass_scale, "fc_anode_h2_mass_feed_mismatch", "Anode H2 mass feed residual."),
        ]

    def metadata(self) -> dict[str, Any]:
        return component_metadata(self, "electrochemical_bop", ["lumped anode feed relation", "no recirculation dynamics", "no purge modeling", "no pressure dynamics"])


class FuelCellAnodeRecirculationModule(BaseModule):
    """Low-fidelity anode recirculation ratio audit."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "FuelCellAnodeRecirculationModule", parameters)
        self.scale = positive_float(parameters.get("residual_scale_kg_s", 1e-4), "residual_scale_kg_s")
        positive_float(parameters.get("denominator_min_abs", 1e-12), "denominator_min_abs")
        self.records = [
            mass_flow_record(component_id, parameters, "m_dot_fresh_H2_kg_s", "m_dot_fresh_H2", 1e-4),
            mass_flow_record(component_id, parameters, "m_dot_recirculation_kg_s", "m_dot_recirculation", 2e-4),
            bounded_record(component_id, parameters, "recirculation_ratio", None, "recirculation_ratio", 0.0, 100.0, 2.0, 1.0),
        ]

    def declare_variables(self) -> list[VariableRecord]:
        return list(self.records)

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        fresh = value(x, registry, self.component_id, "m_dot_fresh_H2_kg_s")
        recirc = value(x, registry, self.component_id, "m_dot_recirculation_kg_s")
        ratio = value(x, registry, self.component_id, "recirculation_ratio")
        return [residual_record(self, "fc_anode_recirculation_ratio", recirc - ratio * fresh, self.scale, "fc_anode_recirculation_ratio_mismatch", "Anode recirculation ratio residual.")]

    def metadata(self) -> dict[str, Any]:
        return component_metadata(self, "electrochemical_bop", ["algebraic recirculation ratio", "no ejector/blower model", "no species composition", "no purge interaction"])


class FuelCellCoolantInterfaceModule(BaseModule):
    """Low-fidelity fuel-cell heat-to-coolant interface audit."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "FuelCellCoolantInterfaceModule", parameters)
        self.cp = positive_float(parameters.get("cp_coolant_J_kgK", 4180.0), "cp_coolant_J_kgK")
        self.scale = positive_float(parameters.get("residual_scale_W", 1000.0), "residual_scale_W")
        self.records = _coolant_records(component_id, parameters, "Q_stack_heat_W")

    def declare_variables(self) -> list[VariableRecord]:
        return list(self.records)

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        return [_coolant_residual(self, x, registry, self.cp, self.scale, "fc_coolant_heat_interface", "fc_coolant_heat_interface_mismatch")]

    def metadata(self) -> dict[str, Any]:
        return component_metadata(self, "electrochemical_bop", ["coolant carries all stack heat", "no heat loss unless modeled separately", "constant cp", "no phase change"])


class FuelCellSystemEfficiencyModule(BaseModule):
    """Low-fidelity fuel-cell system net power and efficiency audit."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "FuelCellSystemEfficiencyModule", parameters)
        self.power_scale = positive_float(parameters.get("residual_scale_power_W", 1000.0), "residual_scale_power_W")
        self.eff_scale = positive_float(parameters.get("residual_scale_efficiency", 0.01), "residual_scale_efficiency")
        self.den_min = positive_float(parameters.get("denominator_min_abs", 1e-9), "denominator_min_abs")
        self.records = [
            power_record(component_id, parameters, "P_stack_W", "P_stack", 28000.0),
            power_record(component_id, parameters, "P_aux_W", "P_aux", 3000.0),
            power_record(component_id, parameters, "P_net_W", "P_net", 25000.0),
            mass_flow_record(component_id, parameters, "m_dot_H2_kg_s", "m_dot_H2", 0.001),
            bounded_record(component_id, parameters, "LHV_H2_J_kg", "J/kg", "LHV_H2", 1.0, 1e9, 120e6, 1e6),
            bounded_record(component_id, parameters, "efficiency", None, "efficiency", 0.0, 1.5, 0.2, 0.1),
        ]

    def declare_variables(self) -> list[VariableRecord]:
        return list(self.records)

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        stack = value(x, registry, self.component_id, "P_stack_W")
        aux = value(x, registry, self.component_id, "P_aux_W")
        net = value(x, registry, self.component_id, "P_net_W")
        h2 = value(x, registry, self.component_id, "m_dot_H2_kg_s")
        lhv = value(x, registry, self.component_id, "LHV_H2_J_kg")
        eff = value(x, registry, self.component_id, "efficiency")
        denom = h2 * lhv
        if abs(denom) < self.den_min:
            raise ValueError(f"{self.component_id}: fuel-cell efficiency denominator is too small")
        return [
            residual_record(self, "fc_system_net_power", net - (stack - aux), self.power_scale, "fc_system_net_power_mismatch", "Fuel-cell system net power residual."),
            residual_record(self, "fc_system_efficiency", eff - net / denom, self.eff_scale, "fc_system_efficiency_mismatch", "Fuel-cell system efficiency residual."),
        ]

    def metadata(self) -> dict[str, Any]:
        return component_metadata(self, "electrochemical_bop", ["algebraic efficiency sanity check", "no transient energy storage", "LHV-based only", "no detailed auxiliary model"])


class ElectrolyzerWaterFeedModule(BaseModule):
    """Low-fidelity electrolyzer water consumption audit."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "ElectrolyzerWaterFeedModule", parameters)
        self.n_cells = required_positive(parameters, "n_cells")
        self.molar_mass = positive_float(parameters.get("molar_mass_H2O_kg_mol", 0.01801528), "molar_mass_H2O_kg_mol")
        self.eta = _eta(parameters)
        self.mol_scale = positive_float(parameters.get("residual_scale_mol_s", 1e-3), "residual_scale_mol_s")
        self.mass_scale = positive_float(parameters.get("residual_scale_kg_s", 1e-4), "residual_scale_kg_s")
        self.records = [
            _current_record(component_id, parameters),
            molar_flow_record(component_id, parameters, "n_dot_H2O_consumed_mol_s", "n_dot_H2O_consumed", 1e-3),
            mass_flow_record(component_id, parameters, "m_dot_H2O_consumed_kg_s", "m_dot_H2O_consumed", 1e-4),
        ]

    def declare_variables(self) -> list[VariableRecord]:
        return list(self.records)

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        current = value(x, registry, self.component_id, "current_A")
        n_h2o = value(x, registry, self.component_id, "n_dot_H2O_consumed_mol_s")
        m_h2o = value(x, registry, self.component_id, "m_dot_H2O_consumed_kg_s")
        expected = self.eta * self.n_cells * current / (2.0 * FARADAY_CONSTANT)
        return [
            residual_record(self, "electrolyzer_water_molar_consumption", n_h2o - expected, self.mol_scale, "electrolyzer_water_molar_consumption_mismatch", "Electrolyzer water molar consumption residual."),
            residual_record(self, "electrolyzer_water_mass_consumption", m_h2o - n_h2o * self.molar_mass, self.mass_scale, "electrolyzer_water_mass_consumption_mismatch", "Electrolyzer water mass consumption residual."),
        ]

    def metadata(self) -> dict[str, Any]:
        return component_metadata(self, "electrochemical_bop", ["lumped Faraday water consumption", "no crossover", "no two-phase transport", "no balance-of-plant details"])


class ElectrolyzerGasProductionModule(BaseModule):
    """Low-fidelity electrolyzer H2/O2 production audit."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "ElectrolyzerGasProductionModule", parameters)
        self.n_cells = required_positive(parameters, "n_cells")
        self.eta = _eta(parameters)
        self.molar_mass_h2 = positive_float(parameters.get("molar_mass_H2_kg_mol", 0.00201588), "molar_mass_H2_kg_mol")
        self.molar_mass_o2 = positive_float(parameters.get("molar_mass_O2_kg_mol", 0.0319988), "molar_mass_O2_kg_mol")
        self.mol_scale = positive_float(parameters.get("residual_scale_mol_s", 1e-3), "residual_scale_mol_s")
        self.mass_scale = positive_float(parameters.get("residual_scale_kg_s", 1e-4), "residual_scale_kg_s")
        self.records = [
            _current_record(component_id, parameters),
            molar_flow_record(component_id, parameters, "n_dot_H2_mol_s", "n_dot_H2", 1e-3),
            molar_flow_record(component_id, parameters, "n_dot_O2_mol_s", "n_dot_O2", 5e-4),
            mass_flow_record(component_id, parameters, "m_dot_H2_kg_s", "m_dot_H2", 1e-5),
            mass_flow_record(component_id, parameters, "m_dot_O2_kg_s", "m_dot_O2", 1e-5),
        ]

    def declare_variables(self) -> list[VariableRecord]:
        return list(self.records)

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        current = value(x, registry, self.component_id, "current_A")
        h2 = value(x, registry, self.component_id, "n_dot_H2_mol_s")
        o2 = value(x, registry, self.component_id, "n_dot_O2_mol_s")
        mh2 = value(x, registry, self.component_id, "m_dot_H2_kg_s")
        mo2 = value(x, registry, self.component_id, "m_dot_O2_kg_s")
        h2_expected = self.eta * self.n_cells * current / (2.0 * FARADAY_CONSTANT)
        o2_expected = self.eta * self.n_cells * current / (4.0 * FARADAY_CONSTANT)
        return [
            residual_record(self, "electrolyzer_h2_molar_production", h2 - h2_expected, self.mol_scale, "electrolyzer_h2_molar_production_mismatch", "Electrolyzer H2 molar production residual."),
            residual_record(self, "electrolyzer_o2_molar_production", o2 - o2_expected, self.mol_scale, "electrolyzer_o2_molar_production_mismatch", "Electrolyzer O2 molar production residual."),
            residual_record(self, "electrolyzer_h2_mass_production", mh2 - h2 * self.molar_mass_h2, self.mass_scale, "electrolyzer_h2_mass_production_mismatch", "Electrolyzer H2 mass production residual."),
            residual_record(self, "electrolyzer_o2_mass_production", mo2 - o2 * self.molar_mass_o2, self.mass_scale, "electrolyzer_o2_mass_production_mismatch", "Electrolyzer O2 mass production residual."),
        ]

    def metadata(self) -> dict[str, Any]:
        return component_metadata(self, "electrochemical_bop", ["lumped Faraday production", "no gas crossover", "no separator dynamics", "no pressure effects"])


class ElectrolyzerCoolingInterfaceModule(BaseModule):
    """Low-fidelity electrolyzer heat-to-coolant interface audit."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "ElectrolyzerCoolingInterfaceModule", parameters)
        self.cp = positive_float(parameters.get("cp_coolant_J_kgK", 4180.0), "cp_coolant_J_kgK")
        self.scale = positive_float(parameters.get("residual_scale_W", 1000.0), "residual_scale_W")
        self.records = _coolant_records(component_id, parameters, "Q_stack_heat_W")

    def declare_variables(self) -> list[VariableRecord]:
        return list(self.records)

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        return [_coolant_residual(self, x, registry, self.cp, self.scale, "electrolyzer_coolant_heat_interface", "electrolyzer_coolant_heat_interface_mismatch")]

    def metadata(self) -> dict[str, Any]:
        return component_metadata(self, "electrochemical_bop", ["coolant carries all stack heat", "no heat loss unless modeled separately", "constant cp"])


class GasSeparatorSimpleModule(BaseModule):
    """Low-fidelity separator efficiency audit."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "GasSeparatorSimpleModule", parameters)
        self.scale = positive_float(parameters.get("residual_scale_kg_s", 1e-4), "residual_scale_kg_s")
        self.records = [
            mass_flow_record(component_id, parameters, "m_dot_in_kg_s", "m_dot_in", 1.0),
            mass_flow_record(component_id, parameters, "m_dot_gas_out_kg_s", "m_dot_gas_out", 0.1),
            mass_flow_record(component_id, parameters, "m_dot_liquid_out_kg_s", "m_dot_liquid_out", 0.9),
            fraction_record(component_id, parameters, "gas_mass_fraction_in", "gas_mass_fraction_in", 0.2),
            fraction_record(component_id, parameters, "separation_efficiency", "separation_efficiency", 0.5),
        ]

    def declare_variables(self) -> list[VariableRecord]:
        return list(self.records)

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        m_in = value(x, registry, self.component_id, "m_dot_in_kg_s")
        gas = value(x, registry, self.component_id, "m_dot_gas_out_kg_s")
        liquid = value(x, registry, self.component_id, "m_dot_liquid_out_kg_s")
        frac = value(x, registry, self.component_id, "gas_mass_fraction_in")
        eff = value(x, registry, self.component_id, "separation_efficiency")
        expected_gas = eff * frac * m_in
        return [
            residual_record(self, "gas_separator_gas_outlet", gas - expected_gas, self.scale, "gas_separator_gas_outlet_mismatch", "Gas separator gas outlet residual."),
            residual_record(self, "gas_separator_liquid_outlet", liquid - (m_in - gas), self.scale, "gas_separator_liquid_outlet_mismatch", "Gas separator liquid outlet residual."),
        ]

    def metadata(self) -> dict[str, Any]:
        return component_metadata(self, "electrochemical_bop", ["lumped separator", "no droplet dynamics", "no pressure drop", "no detailed phase equilibrium"])


def _coolant_records(component_id: str, parameters: dict[str, Any], q_name: str) -> list[VariableRecord]:
    return [
        power_record(component_id, parameters, q_name, "Q_stack_heat", 4180.0),
        mass_flow_record(component_id, parameters, "m_dot_coolant_kg_s", "m_dot_coolant", 0.1),
        bounded_record(component_id, parameters, "T_coolant_in_K", "K", "T_coolant_in", 100.0, 1500.0, 300.0, 10.0),
        bounded_record(component_id, parameters, "T_coolant_out_K", "K", "T_coolant_out", 100.0, 1500.0, 310.0, 10.0),
    ]


def _coolant_residual(module: BaseModule, x: np.ndarray, registry: VariableRegistry, cp: float, scale: float, name: str, key: str) -> ResidualRecord:
    q = value(x, registry, module.component_id, "Q_stack_heat_W")
    m = value(x, registry, module.component_id, "m_dot_coolant_kg_s")
    tin = value(x, registry, module.component_id, "T_coolant_in_K")
    tout = value(x, registry, module.component_id, "T_coolant_out_K")
    return residual_record(module, name, q - m * cp * (tout - tin), scale, key, "Electrochemical stack coolant heat interface residual.")
