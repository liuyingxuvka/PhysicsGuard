"""Run PhysicsGuard interval-diagnosability model checks."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

from flowguard.review import review_scenarios


MODEL = Path(__file__).with_name("model.py")


def main() -> int:
    spec = importlib.util.spec_from_file_location(
        "physicsguard_interval_diagnosability_model",
        MODEL,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load model {MODEL}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    report = review_scenarios(module.scenarios())
    print(
        json.dumps(
            {
                "artifact_kind": "physicsguard_interval_diagnosability_model_report",
                "status": "pass" if report.ok else "fail",
                "scenario_count": len(report.results),
                "claim_boundary": (
                    "The model covers only the declared interval and "
                    "task-local diagnosability scenarios."
                ),
            },
            sort_keys=True,
        )
    )
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
