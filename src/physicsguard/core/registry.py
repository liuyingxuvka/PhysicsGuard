"""Variable registry for solver vector construction."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Optional

import numpy as np


@dataclass(frozen=True)
class VariableRecord:
    name: str
    unit: Optional[str]
    lower_bound: float
    upper_bound: float
    initial_guess: float
    scale: float
    source_component: Optional[str] = None
    local_name: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("variable name cannot be empty")
        parts = self.name.split(".")
        if len(parts) != 2 or not all(part.strip() for part in parts):
            raise ValueError("variable name must use fully qualified component.variable format")
        component_id, local_name = parts
        if self.source_component is not None and self.source_component != component_id:
            raise ValueError("source_component must match the qualified variable component")
        if self.local_name is not None and "." in self.local_name:
            raise ValueError("local_name must be unqualified")
        if self.local_name is not None and self.local_name != local_name:
            raise ValueError("local_name must match the qualified variable local name")
        if self.local_name is None:
            object.__setattr__(self, "local_name", local_name)
        for field_name in ("lower_bound", "upper_bound", "initial_guess", "scale"):
            value = getattr(self, field_name)
            if not math.isfinite(value):
                raise ValueError(f"{self.name}: {field_name} must be finite")
        if self.lower_bound >= self.upper_bound:
            raise ValueError(f"{self.name}: lower_bound must be less than upper_bound")
        if not self.lower_bound <= self.initial_guess <= self.upper_bound:
            raise ValueError(f"{self.name}: initial_guess must be inside bounds")
        if self.scale <= 0:
            raise ValueError(f"{self.name}: scale must be positive")


class VariableRegistry:
    """Maps fully qualified variable names to solver vector indices."""

    def __init__(self) -> None:
        self._records: list[VariableRecord] = []
        self._indices: dict[str, int] = {}

    def add_variable(self, record: VariableRecord) -> int:
        if record.name in self._indices:
            raise ValueError(f"duplicate variable name: {record.name}")
        index = len(self._records)
        self._records.append(record)
        self._indices[record.name] = index
        return index

    def get_index(self, name: str) -> int:
        try:
            return self._indices[name]
        except KeyError as exc:
            raise KeyError(f"unknown variable: {name}") from exc

    def get_record(self, name: str) -> VariableRecord:
        return self._records[self.get_index(name)]

    def names(self) -> list[str]:
        return [record.name for record in self._records]

    def size(self) -> int:
        return len(self._records)

    def initial_vector(self) -> np.ndarray:
        return np.array([record.initial_guess for record in self._records], dtype=float)

    def lower_bounds(self) -> np.ndarray:
        return np.array([record.lower_bound for record in self._records], dtype=float)

    def upper_bounds(self) -> np.ndarray:
        return np.array([record.upper_bound for record in self._records], dtype=float)

    def scales(self) -> np.ndarray:
        scales = np.array([record.scale for record in self._records], dtype=float)
        if not np.all(np.isfinite(scales)) or np.any(scales <= 0):
            raise ValueError("variable scales must be finite and positive")
        return scales

    def vector_to_dict(self, x: np.ndarray) -> dict[str, float]:
        vector = self._validate_vector(x)
        return {
            record.name: float(vector[index])
            for index, record in enumerate(self._records)
        }

    def dict_to_vector(self, values: dict[str, float]) -> np.ndarray:
        missing = [name for name in self.names() if name not in values]
        if missing:
            raise KeyError(f"missing variable values: {', '.join(missing)}")
        unknown = [name for name in values if name not in self._indices]
        if unknown:
            raise KeyError(f"unknown variable values: {', '.join(unknown)}")
        vector = np.array([values[name] for name in self.names()], dtype=float)
        if not np.all(np.isfinite(vector)):
            raise ValueError("values contain NaN or inf")
        return vector

    def _validate_vector(self, x: np.ndarray) -> np.ndarray:
        vector = np.asarray(x, dtype=float)
        if vector.ndim != 1 or vector.shape[0] != self.size():
            raise ValueError(
                f"vector length {vector.shape[0] if vector.ndim else 1} does not match "
                f"registry size {self.size()}"
            )
        if not np.all(np.isfinite(vector)):
            raise ValueError("vector contains NaN or inf")
        return vector
