"""Run the physicsguard software-DNA root model checks."""

from __future__ import annotations

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "models/owners/authoritative_model_system"))

import json
from pathlib import Path

import model

ROOT = Path(__file__).resolve().parents[4]


def main() -> dict:
    model.run_model()
    report = model.check_blueprint_inputs(ROOT)
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return report


if __name__ == "__main__":
    from flowguard.map.runner import run_owner
    raise SystemExit(run_owner(main))
