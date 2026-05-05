"""PhysicsGuard Core framework package."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

__version__ = "0.1.0"

__all__ = [
    "BOUND_HIT_TOLERANCE",
    "BoundHitDiagnostic",
    "DiagnosticReport",
    "DiagnosticReporter",
    "ResidualDiagnostic",
]

_DIAGNOSTIC_EXPORTS = set(__all__)


def __getattr__(name: str) -> Any:
    if name in _DIAGNOSTIC_EXPORTS:
        module = _load_diagnostics_module()
        return getattr(module, name)
    raise AttributeError(f"module 'physicsguard' has no attribute {name!r}")


def _load_diagnostics_module() -> Any:
    module_name = "_physicsguard_diagnostics_standalone"
    if module_name in sys.modules:
        return sys.modules[module_name]
    module_path = Path(__file__).with_name("core") / "diagnostics.py"
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load diagnostics module from {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module
