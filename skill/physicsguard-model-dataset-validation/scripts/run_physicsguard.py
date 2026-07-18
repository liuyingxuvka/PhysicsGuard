#!/usr/bin/env python3
"""Run the PhysicsGuard CLI from this skill's bundled target runtime."""

from __future__ import annotations

import sys
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL_ROOT / "runtime"))

from physicsguard.cli import main


if __name__ == "__main__":
    raise SystemExit(main())
