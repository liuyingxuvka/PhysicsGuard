"""Extract a PhysicsGuard test data file manifest."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import yaml

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from physicsguard.core.data_file_manifest import generate_delimited_manifest, manifest_to_dict
from physicsguard.io.test_file_contract_loader import load_yaml_mapping
from physicsguard.schema.test_file_contract import ExtractorProfileSpec, TestBenchProfileSpec


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("data_file", type=Path)
    parser.add_argument("--profile", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--delimiter")
    parser.add_argument("--encoding")
    parser.add_argument("--time-column")
    parser.add_argument("--json", action="store_true", help="print JSON instead of YAML")
    args = parser.parse_args(argv)

    profile = _load_profile(args.profile) if args.profile is not None else None
    manifest = generate_delimited_manifest(
        args.data_file,
        profile=profile,
        delimiter=args.delimiter,
        encoding=args.encoding,
        time_column=args.time_column,
    )
    data = manifest_to_dict(manifest)
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    elif args.json:
        print(json.dumps(data, sort_keys=True))
    else:
        print(yaml.safe_dump(data, sort_keys=False))
    return 0


def _load_profile(path: Path) -> TestBenchProfileSpec | ExtractorProfileSpec:
    data = load_yaml_mapping(path)
    if "script" in data:
        return ExtractorProfileSpec.model_validate(data)
    return TestBenchProfileSpec.model_validate(data)


if __name__ == "__main__":
    raise SystemExit(main())
