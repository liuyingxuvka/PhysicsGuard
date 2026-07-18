"""Low-fidelity gas audit modules."""

from __future__ import annotations

import math
from typing import Any

import numpy as np

from physicsguard.core.registry import VariableRecord, VariableRegistry
from physicsguard.core.residual import ResidualRecord
from physicsguard.modules.base import BaseModule
from physicsguard.modules.physical.constants import UNIVERSAL_GAS_CONSTANT


class IdealGasStateModule(BaseModule):
    """Low-fidelity ideal gas state relation p*V = n*R*T."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "IdealGasStateModule", parameters)
        if "volume_m3" not in parameters:
            raise ValueError(f"{component_id}: volume_m3 is required")
        self.volume_m3 = _positive_float(parameters["volume_m3"], "volume_m3")
        self.residual_scale_J = _positive_float(
            parameters.get("residual_scale_J", 100.0),
            "residual_scale_J",
        )
        self.records = [
            self._record(
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
            self._record(
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
            self._record(
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

    def _record(
        self,
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
            name=f"{self.component_id}.{local_name}",
            unit=unit,
            lower_bound=_finite_float(self.parameters.get(lower_key, lower_default), lower_key),
            upper_bound=_finite_float(self.parameters.get(upper_key, upper_default), upper_key),
            initial_guess=_finite_float(
                self.parameters.get(initial_key, initial_default),
                initial_key,
            ),
            scale=_positive_float(self.parameters.get(scale_key, scale_default), scale_key),
            source_component=self.component_id,
            local_name=local_name,
        )

    def _value(self, x: np.ndarray, registry: VariableRegistry, local_name: str) -> float:
        return float(x[registry.get_index(f"{self.component_id}.{local_name}")])


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
