"""Low-fidelity electrochemical audit modules."""

from __future__ import annotations

from typing import Any

import numpy as np

from physicsguard.core.registry import VariableRecord, VariableRegistry
from physicsguard.core.residual import ResidualRecord
from physicsguard.modules.base import BaseModule
from physicsguard.modules.physical.constants import FARADAY_CONSTANT
from physicsguard.modules.physical._common import owned_record, positive_float


class ElectrochemicalFaradayRateModule(BaseModule):
    """Low-fidelity Faraday-law molar rate relation."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "ElectrochemicalFaradayRateModule", parameters)
        if "n_cells" not in parameters:
            raise ValueError(f"{component_id}: n_cells is required")
        if "electrons_per_mole" not in parameters:
            raise ValueError(f"{component_id}: electrons_per_mole is required")
        self.n_cells = positive_float(parameters["n_cells"], "n_cells")
        self.electrons_per_mole = positive_float(
            parameters["electrons_per_mole"],
            "electrons_per_mole",
        )
        self.faradaic_efficiency = positive_float(
            parameters.get("faradaic_efficiency", 1.0),
            "faradaic_efficiency",
        )
        if self.faradaic_efficiency > 1:
            raise ValueError("faradaic_efficiency must be <= 1")
        self.residual_scale_mol_s = positive_float(
            parameters.get("residual_scale_mol_s", 1e-3),
            "residual_scale_mol_s",
        )
        self.records = [
            owned_record(
                self.component_id,
                self.parameters,
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
            owned_record(
                self.component_id,
                self.parameters,
                "n_dot_mol_s",
                "mol/s",
                "n_dot_lower_bound",
                "n_dot_upper_bound",
                "n_dot_initial_guess",
                "n_dot_scale",
                0.0,
                10.0,
                1e-3,
                1e-3,
            ),
        ]

    def declare_variables(self) -> list[VariableRecord]:
        return list(self.records)

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        current = self._value(x, registry, "current_A")
        n_dot = self._value(x, registry, "n_dot_mol_s")
        expected_rate = (
            self.faradaic_efficiency
            * self.n_cells
            * current
            / (self.electrons_per_mole * FARADAY_CONSTANT)
        )
        return [
            ResidualRecord(
                name=f"{self.component_id}.faraday_rate",
                value=n_dot - expected_rate,
                scale=self.residual_scale_mol_s,
                source=self.component_id,
                role="equation",
                diagnostic_key="faraday_rate_mismatch",
                description="Low-fidelity Faraday-law molar rate residual.",
            )
        ]

    def metadata(self) -> dict[str, Any]:
        return {
            "component_id": self.component_id,
            "module_type": self.module_type,
            "purpose": "low_fidelity_physical_audit",
            "domain": "electrochemical",
            "validity": [
                "lumped Faraday-law relation only",
                "no voltage model",
                "no mass transport model",
                "no water balance",
                "no crossover",
                "no detailed electrochemistry",
                "sign convention assumes non-negative current and non-negative molar rate",
            ],
        }

    def _value(self, x: np.ndarray, registry: VariableRegistry, local_name: str) -> float:
        return float(x[registry.get_index(f"{self.component_id}.{local_name}")])


class StoichiometryModule(BaseModule):
    """Generic low-fidelity stoichiometric molar feed relation."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "StoichiometryModule", parameters)
        self.stoichiometry = _required_positive(parameters, "stoichiometry")
        self.residual_scale_mol_s = positive_float(
            parameters.get("residual_scale_mol_s", 1e-3),
            "residual_scale_mol_s",
        )
        self.records = [
            owned_record(
                component_id,
                parameters,
                "n_dot_feed_mol_s",
                "mol/s",
                "n_dot_lower_bound",
                "n_dot_upper_bound",
                "feed_initial_guess",
                "n_dot_scale",
                0.0,
                100.0,
                1e-2,
                1e-3,
            ),
            owned_record(
                component_id,
                parameters,
                "n_dot_consumed_mol_s",
                "mol/s",
                "n_dot_lower_bound",
                "n_dot_upper_bound",
                "consumed_initial_guess",
                "n_dot_scale",
                0.0,
                100.0,
                1e-3,
                1e-3,
            ),
        ]

    def declare_variables(self) -> list[VariableRecord]:
        return list(self.records)

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        feed = _owned_value(x, registry, self.component_id, "n_dot_feed_mol_s")
        consumed = _owned_value(x, registry, self.component_id, "n_dot_consumed_mol_s")
        return [
            ResidualRecord(
                name=f"{self.component_id}.stoichiometry",
                value=feed - self.stoichiometry * consumed,
                scale=self.residual_scale_mol_s,
                source=self.component_id,
                role="equation",
                diagnostic_key="stoichiometry_mismatch",
                description="Low-fidelity stoichiometry residual feed - stoichiometry*consumed.",
            )
        ]

    def metadata(self) -> dict[str, Any]:
        return _metadata(
            self,
            [
                "lumped molar flow relation",
                "no species transport",
                "no humidity",
                "no pressure/temperature dependence",
                "no reaction kinetics",
            ],
        )


class ElectrochemicalStackPowerModule(BaseModule):
    """Low-fidelity electrochemical stack electrical power relation."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "ElectrochemicalStackPowerModule", parameters)
        self.n_cells = _required_positive(parameters, "n_cells")
        self.residual_scale_W = positive_float(
            parameters.get("residual_scale_W", 1000.0),
            "residual_scale_W",
        )
        self.records = [
            owned_record(
                component_id,
                parameters,
                "V_cell_V",
                "V",
                "V_cell_lower_bound",
                "V_cell_upper_bound",
                "V_cell_initial_guess",
                "V_cell_scale",
                0.0,
                3.0,
                0.7,
                1.0,
            ),
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
            owned_record(
                component_id,
                parameters,
                "P_stack_W",
                "W",
                "P_lower_bound",
                "P_upper_bound",
                "P_initial_guess",
                "P_scale",
                0.0,
                1e8,
                10000.0,
                1000.0,
            ),
        ]

    def declare_variables(self) -> list[VariableRecord]:
        return list(self.records)

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        voltage = _owned_value(x, registry, self.component_id, "V_cell_V")
        current = _owned_value(x, registry, self.component_id, "current_A")
        power = _owned_value(x, registry, self.component_id, "P_stack_W")
        return [
            ResidualRecord(
                name=f"{self.component_id}.electrochemical_stack_power",
                value=power - self.n_cells * voltage * current,
                scale=self.residual_scale_W,
                source=self.component_id,
                role="equation",
                diagnostic_key="electrochemical_stack_power_mismatch",
                description="Low-fidelity stack power residual P_stack - n_cells*V_cell*current.",
            )
        ]

    def metadata(self) -> dict[str, Any]:
        return _metadata(
            self,
            [
                "lumped stack power",
                "no polarization model",
                "no voltage loss model",
                "no power electronics",
                "nonnegative current convention",
            ],
        )


def _required_positive(parameters: dict[str, Any], name: str) -> float:
    if name not in parameters:
        raise ValueError(f"{name} is required")
    return positive_float(parameters[name], name)


def _owned_value(
    x: np.ndarray,
    registry: VariableRegistry,
    component_id: str,
    local_name: str,
) -> float:
    return float(x[registry.get_index(f"{component_id}.{local_name}")])


def _metadata(module: BaseModule, validity: list[str]) -> dict[str, Any]:
    return {
        "component_id": module.component_id,
        "module_type": module.module_type,
        "purpose": "low_fidelity_physical_audit",
        "domain": "electrochemical",
        "validity": validity,
    }
