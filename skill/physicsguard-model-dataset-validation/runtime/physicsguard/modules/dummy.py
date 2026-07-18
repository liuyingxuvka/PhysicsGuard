"""Non-physical dummy module used only to test the framework."""

from __future__ import annotations

import math
from typing import Any, Optional

import numpy as np

from physicsguard.core.registry import VariableRecord, VariableRegistry
from physicsguard.core.residual import ResidualRecord
from physicsguard.modules.base import BaseModule


class DummyResidualModule(BaseModule):
    """A one-variable residual module with no physical meaning."""

    def __init__(self, component_id: str, parameters: dict[str, Any]) -> None:
        super().__init__(component_id, "DummyResidualModule", parameters)
        if "target" not in parameters:
            raise ValueError(f"{component_id}: DummyResidualModule requires parameter 'target'")
        self.target = self._finite_float(parameters["target"], "target")
        self.lower_bound = self._finite_float(parameters.get("lower_bound", -100.0), "lower_bound")
        self.upper_bound = self._finite_float(parameters.get("upper_bound", 100.0), "upper_bound")
        self.initial_guess = self._finite_float(
            parameters.get("initial_guess", 0.0),
            "initial_guess",
        )
        self.scale = self._finite_float(parameters.get("scale", 1.0), "scale")
        self.unit: Optional[str] = parameters.get("unit")
        if self.lower_bound >= self.upper_bound:
            raise ValueError(f"{component_id}: lower_bound must be less than upper_bound")
        if not self.lower_bound <= self.initial_guess <= self.upper_bound:
            raise ValueError(f"{component_id}: initial_guess must be inside bounds")
        if self.scale <= 0:
            raise ValueError(f"{component_id}: scale must be positive")

    @staticmethod
    def _finite_float(value: Any, name: str) -> float:
        try:
            parsed = float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{name} must be a finite number") from exc
        if not math.isfinite(parsed):
            raise ValueError(f"{name} must be finite")
        return parsed

    @property
    def variable_name(self) -> str:
        return f"{self.component_id}.x"

    def declare_variables(self) -> list[VariableRecord]:
        return [
            VariableRecord(
                name=self.variable_name,
                unit=self.unit,
                lower_bound=self.lower_bound,
                upper_bound=self.upper_bound,
                initial_guess=self.initial_guess,
                scale=self.scale,
                source_component=self.component_id,
                local_name="x",
            )
        ]

    def residuals(self, x: np.ndarray, registry: VariableRegistry) -> list[ResidualRecord]:
        index = registry.get_index(self.variable_name)
        value = float(np.asarray(x, dtype=float)[index] - self.target)
        return [
            ResidualRecord(
                name=f"{self.component_id}.dummy_target",
                value=value,
                scale=self.scale,
                source=self.component_id,
                role="equation",
                diagnostic_key="dummy_target_mismatch",
                description="Non-physical dummy residual x - target.",
            )
        ]

    def metadata(self) -> dict[str, Any]:
        return {
            "component_id": self.component_id,
            "module_type": self.module_type,
            "purpose": "framework_test_only",
            "has_physical_meaning": False,
        }
