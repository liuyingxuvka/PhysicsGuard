"""Optional current-map inspection; not an executable model or release gate."""
from pathlib import Path
from typing import Any


def check_blueprint_inputs(root: str | Path) -> dict[str, Any]:
    from physicsguard.self_dna import check
    payload, code = check(root, compact=True)
    return {"ok": code == 0, "status": payload["status"],
            "model_count": len(payload.get("registered_models", [])),
            "model_execution": "not_run", "test_execution": "not_run",
            "gap": payload.get("gap")}
