"""Executable root of the physicsguard repository software-DNA model.

This model checks the repository's own model, code, test, and evidence
denominator. It reports readiness from current files; it does not recreate
the target software and it does not delegate the check to another agent.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Mapping

FLOWGUARD_MODEL_MARKER = "flowguard-executable-model"

@dataclass(frozen=True)
class SelfDnaInput:
    manifest_current: bool
    definition_current: bool
    mesh_current: bool
    owner_bindings_current: bool
    evidence_paths_current: bool


@dataclass(frozen=True)
class SelfDnaState:
    phase: str = "unverified"
    ready: bool = False


def evaluate_self_dna(inputs: SelfDnaInput) -> SelfDnaState:
    ready = all(
        (
            inputs.manifest_current,
            inputs.definition_current,
            inputs.mesh_current,
            inputs.owner_bindings_current,
            inputs.evidence_paths_current,
        )
    )
    return SelfDnaState(phase="ready" if ready else "blocked", ready=ready)


def check_blueprint_inputs(root: str | Path) -> dict[str, Any]:
    """Read the current map; the result licenses structure, never model/test execution."""
    from physicsguard.self_dna import check
    payload, code = check(root, compact=True)
    return {"ok": code == 0, "ready": code == 0, "status": payload["status"],
            "model_count": len(payload.get("registered_models", [])),
            "model_execution": "not_run", "test_execution": "not_run",
            "gap": payload.get("gap")}


def run_model() -> dict[str, bool]:
    good = evaluate_self_dna(SelfDnaInput(True, True, True, True, True))
    assert good.ready and good.phase == "ready"
    for index in range(5):
        values = [True] * 5
        values[index] = False
        candidate = evaluate_self_dna(SelfDnaInput(*values))
        assert not candidate.ready and candidate.phase == "blocked"

    return {"ok": True}


if __name__ == "__main__":
    run_model()
    print("authoritative_model_system: pass")
