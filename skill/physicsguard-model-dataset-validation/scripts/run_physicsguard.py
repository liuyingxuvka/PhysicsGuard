#!/usr/bin/env python3
"""Run the one installed PhysicsGuard simulator used by all maintained skills."""

from __future__ import annotations

try:
    from physicsguard.cli import main
except ModuleNotFoundError as exc:
    if exc.name != "physicsguard":
        raise
    raise SystemExit(
        "PhysicsGuard runtime is unavailable. Install the current physicsguard "
        "package before using this skill; no bundled fallback is provided."
    ) from exc


if __name__ == "__main__":
    raise SystemExit(main())
