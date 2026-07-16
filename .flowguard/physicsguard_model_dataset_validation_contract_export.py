"""Repository-local compatibility wrapper for the portable SkillGuard export."""

from __future__ import annotations

import importlib.util
from pathlib import Path


_PORTABLE_EXPORT = (
    Path(__file__).resolve().parents[1]
    / "skill"
    / "physicsguard-model-dataset-validation"
    / ".skillguard"
    / "flowguard_contract_export.py"
)
_SPEC = importlib.util.spec_from_file_location("physicsguard_portable_contract_export", _PORTABLE_EXPORT)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError("portable PhysicsGuard contract export is unavailable")
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)

FLOWGUARD_MODEL_MARKER = _MODULE.FLOWGUARD_MODEL_MARKER
export_contract_model = _MODULE.export_contract_model


if __name__ == "__main__":
    import json

    print(json.dumps(export_contract_model(), indent=2, sort_keys=True))
