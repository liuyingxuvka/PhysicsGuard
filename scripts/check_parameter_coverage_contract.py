"""Check parameter coverage for a PhysicsGuard test-file contract."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from physicsguard.core.test_file_contract import check_test_file_parameter_coverage


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("contract", type=Path)
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)
    report = check_test_file_parameter_coverage(args.contract)
    print(json.dumps(report.to_dict(), indent=2 if args.pretty else None, sort_keys=True))
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
