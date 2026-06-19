from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from databank_common import get_path, load_struct, write_json


def query_catalog(catalog_path: str | Path, field: str, value: str) -> dict[str, Any]:
    catalog = load_struct(catalog_path)
    records = catalog.get("projects") or catalog.get("records") or []
    matches: list[dict[str, Any]] = []
    inspected = 0
    for record in records:
        if not isinstance(record, dict):
            continue
        inspected += 1
        actual = get_path(record, field)
        if isinstance(actual, list):
            matched = value in [str(item) for item in actual]
        else:
            matched = str(actual) == value
        if matched:
            matches.append(record)

    query = {"field": field, "value": value}
    if matches:
        return {"status": "pass", "query": query, "scope": {"records_inspected": inspected}, "matches": matches, "reason": ""}
    return {
        "status": "partial",
        "query": query,
        "scope": {"records_inspected": inspected},
        "matches": [],
        "reason": f"No records matched {field}={value!r} in the inspected catalog scope.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Query a DataBank catalog with explicit empty-result reasons.")
    parser.add_argument("catalog", help="Catalog JSON/YAML")
    parser.add_argument("--field", required=True, help="Dotted field path to query")
    parser.add_argument("--value", required=True, help="String value to match")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    args = parser.parse_args()
    result = query_catalog(args.catalog, args.field, args.value)
    write_json(result, pretty=args.pretty)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
