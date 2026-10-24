"""Low-fidelity gas audit modules."""

from __future__ import annotations

from typing import Any

import numpy as np

from physicsguard.core.registry import VariableRecord, VariableRegistry
from physicsguard.core.residual import ResidualRecord
from physicsguard.modules.base import BaseModule
from physicsguard.modules.physical.constants import UNIVERSAL_GAS_CONSTANT
from physicsguard.modules.physical._common import owned_record, positive_float


class IdealGasStateModule(BaseModule):
    """Low-fidelity ideal gas state relation p*V = n*R*T."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "IdealGasStateModule", parameters)
        if "volume_m3" not in parameters:
            raise ValueError(f"{component_id}: volume_m3 is required")
        self.volume_m3 = positive_float(parameters["volume_m3"], "volume_m3")
        self.residual_scale_J = positive_float(
            parameters.get("residual_scale_J", 100.0),
            "residual_scale_J",
        )
        self.records = [
            owned_record(
                self.component_id,
                self.parameters,
                "p_Pa",
                "Pa",
                "p_lower_bound",
                "p_upper_bound",
                "p_initial_guess",
                "p_scale",
                1e3,
                1e7,
                101325.0,
                1e5,
            ),
            owned_record(
                self.component_id,
                self.parameters,
                "T_K",
                "K",
                "T_lower_bound",
                "T_upper_bound",
                "T_initial_guess",
                "T_scale",
                100.0,
                1000.0,
                300.0,
                100.0,
            ),
            owned_record(
                self.component_id,
                self.parameters,
                "n_mol",
                "mol",
                "n_lower_bound",
                "n_upper_bound",
                "n_initial_guess",
                "n_scale",
                0.0,
                1e5,
                1.0,
                1.0,
            ),
        ]

    def declare_variables(self) -> list[VariableRecord]:
        return list(self.records)

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        pressure = self._value(x, registry, "p_Pa")
        temperature = self._value(x, registry, "T_K")
        amount = self._value(x, registry, "n_mol")
        return [
            ResidualRecord(
                name=f"{self.component_id}.ideal_gas_state",
                value=pressure * self.volume_m3
                - amount * UNIVERSAL_GAS_CONSTANT * temperature,
                scale=self.residual_scale_J,
                source=self.component_id,
                role="equation",
                diagnostic_key="ideal_gas_state_mismatch",
                description="Low-fidelity ideal gas state residual p*V - n*R*T.",
            )
        ]

    def metadata(self) -> dict[str, Any]:
        return {
            "component_id": self.component_id,
            "module_type": self.module_type,
            "purpose": "low_fidelity_physical_audit",
            "domain": "gas",
            "validity": [
                "ideal gas approximation",
                "not valid for dense gas, liquid, two-phase flow, or real-gas high-pressure behavior",
                "no species composition modeling",
            ],
        }

    def _value(self, x: np.ndarray, registry: VariableRegistry, local_name: str) -> float:
        return float(x[registry.get_index(f"{self.component_id}.{local_name}")])


