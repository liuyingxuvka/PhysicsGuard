"""Read the native-route report; execute no domain checks."""
from __future__ import annotations
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from report_physicsguard_skill_suite import build_report

def main() -> int:
    report = build_report(ROOT)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["structure_status"] == "pass" else 1

if __name__ == "__main__":
    raise SystemExit(main())
