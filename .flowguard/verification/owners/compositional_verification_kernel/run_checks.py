"""Run the physicsguard composition kernel checks."""

from __future__ import annotations

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "models/owners/compositional_verification_kernel"))

import model


def main() -> int:
    return model.run_model()


if __name__ == "__main__":
    from flowguard.map.runner import run_owner
    raise SystemExit(run_owner(main))
