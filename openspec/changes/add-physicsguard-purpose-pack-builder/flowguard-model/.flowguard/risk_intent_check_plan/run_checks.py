"""Run correct and representative broken PhysicsGuard selector models."""

from __future__ import annotations

from model import risk_profile, run_checks


def main() -> int:
    print(f"risk_intent: {risk_profile().modeled_boundary}")
    correct, broken = run_checks()
    print(correct.format_text())
    print()
    print(broken.format_text())
    correct_ok = correct.overall_status in {"pass", "pass_with_gaps"}
    broken_rejected = broken.overall_status not in {"pass", "pass_with_gaps"}
    return 0 if correct_ok and broken_rejected else 1


if __name__ == "__main__":
    raise SystemExit(main())
