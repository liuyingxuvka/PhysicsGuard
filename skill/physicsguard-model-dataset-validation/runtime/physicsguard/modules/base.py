"""Abstract module interface for future PhysicsGuard modules."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import numpy as np

from physicsguard.core.registry import VariableRecord, VariableRegistry


class BaseModule(ABC):
    def __init__(
        self,
        component_id: str,
        module_type: str,
        parameters: dict[str, Any],
    ) -> None:
        if not component_id.strip():
            raise ValueError("component_id cannot be empty")
        if not module_type.strip():
            raise ValueError("module_type cannot be empty")
        self.component_id = component_id
        self.module_type = module_type
        self.parameters = dict(parameters)

    @abstractmethod
    def declare_variables(self) -> list[VariableRecord]:
        """Declare fully qualified variables owned by this module."""

    @abstractmethod
    def residuals(self, x: np.ndarray, registry: VariableRegistry):
        """Return residual records for the current solver vector."""

    @abstractmethod
    def metadata(self) -> dict[str, Any]:
        """Return JSON-serializable module metadata."""
