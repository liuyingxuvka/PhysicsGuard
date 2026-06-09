from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LEDGER = ROOT / ".physicsguard" / "module_equation_ledger.yaml"

REQUIRED_ENTRY_FIELDS = (
    "id",
    "module_types",
    "equation_summary",
    "si_units",
    "assumptions",
    "validity",
    "diagnostic_keys",
    "tests",
    "examples",
    "stale_when",
)


def validate_ledger(root: Path = ROOT, ledger_path: Path = DEFAULT_LEDGER) -> list[str]:
    errors: list[str] = []
    data = _load_yaml(ledger_path, errors)
    if not isinstance(data, dict):
        return errors or [f"{_rel(ledger_path, root)}: root must be a mapping"]

    if data.get("evidence_level") != "navigation":
        errors.append(f"{_rel(ledger_path, root)}: evidence_level must be navigation")
    entries = data.get("entries")
    if not isinstance(entries, list) or not entries:
        errors.append(f"{_rel(ledger_path, root)}: entries must be a non-empty list")
        return errors

    registered_types = _registered_module_types(errors)
    seen_ids: set[str] = set()
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            errors.append(f"entries[{index}]: entry must be a mapping")
            continue
        _validate_entry(root, entry, registered_types, seen_ids, errors)
    return errors


def _validate_entry(
    root: Path,
    entry: dict[str, Any],
    registered_types: set[str],
    seen_ids: set[str],
    errors: list[str],
) -> None:
    entry_id = entry.get("id")
    if not isinstance(entry_id, str) or not entry_id.strip():
        errors.append("entry id must be a non-empty string")
        entry_id = "<unknown>"
    elif entry_id in seen_ids:
        errors.append(f"{entry_id}: duplicate id")
    else:
        seen_ids.add(entry_id)

    for field in REQUIRED_ENTRY_FIELDS:
        if field not in entry:
            errors.append(f"{entry_id}: missing required field '{field}'")

    for field in (
        "module_types",
        "si_units",
        "assumptions",
        "validity",
        "diagnostic_keys",
        "tests",
        "examples",
        "stale_when",
    ):
        values = _string_list(entry.get(field), entry_id, field, errors)
        if not values:
            errors.append(f"{entry_id}: {field} must contain at least one item")

    equation = entry.get("equation_summary")
    if not isinstance(equation, str) or not equation.strip():
        errors.append(f"{entry_id}: equation_summary must be non-empty")

    for module_type in _string_list(entry.get("module_types"), entry_id, "module_types", errors):
        if module_type not in registered_types:
            errors.append(f"{entry_id}: module type is not registered: {module_type}")

    for field in ("tests", "examples"):
        for value in _string_list(entry.get(field), entry_id, field, errors):
            path = root / value
            if not path.exists():
                errors.append(f"{entry_id}: {field} path does not exist: {value}")


def _registered_module_types(errors: list[str]) -> set[str]:
    try:
        from physicsguard.modules.registry import default_module_registry

        return set(default_module_registry().registered_types())
    except Exception as exc:
        errors.append(f"could not load PhysicsGuard module registry: {exc}")
        return set()


def _load_yaml(path: Path, errors: list[str]) -> Any:
    if not path.exists():
        errors.append(f"{path}: ledger file does not exist")
        return None
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        errors.append(f"{path}: invalid YAML: {exc}")
        return None


def _string_list(value: Any, entry_id: str, field: str, errors: list[str]) -> list[str]:
    if not isinstance(value, list) or not value:
        errors.append(f"{entry_id}: {field} must be a non-empty list")
        return []
    result: list[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            errors.append(f"{entry_id}: {field}[{index}] must be a non-empty string")
            continue
        result.append(item)
    return result


def _rel(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return str(path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate PhysicsGuard module equation ledger.")
    parser.add_argument("ledger", nargs="?", type=Path, default=DEFAULT_LEDGER)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    ledger_path = args.ledger
    if not ledger_path.is_absolute():
        ledger_path = ROOT / ledger_path
    errors = validate_ledger(ROOT, ledger_path)
    output = {
        "ok": not errors,
        "ledger": _rel(ledger_path, ROOT),
        "error_count": len(errors),
        "errors": errors,
    }
    if args.json:
        print(json.dumps(output, indent=2))
    elif errors:
        print("module equation ledger check failed:")
        for error in errors:
            print(f"- {error}")
    else:
        print(f"module equation ledger check passed: {_rel(ledger_path, ROOT)}")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
