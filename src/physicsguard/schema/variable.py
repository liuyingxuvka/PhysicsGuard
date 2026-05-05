"""Shared schema validation helpers."""

from __future__ import annotations

import math


def ensure_non_empty(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} cannot be empty")
    return value


def ensure_finite(value: float, field_name: str) -> float:
    if not math.isfinite(value):
        raise ValueError(f"{field_name} must be finite")
    return value


def is_qualified_variable_name(value: str) -> bool:
    if not isinstance(value, str):
        return False
    parts = value.split(".")
    return len(parts) == 2 and all(part.strip() for part in parts)
