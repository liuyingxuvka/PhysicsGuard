from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LEDGER = ROOT / ".flowguard" / "model_code_ledger.yaml"

REQUIRED_ENTRY_FIELDS = (
    "id",
    "model_file",
    "model_blocks",
    "responsibility",
    "code_symbols",
    "tests",
    "examples",
    "validation_commands",
    "boundaries",
    "stale_when",
)


def validate_ledger(root: Path = ROOT, ledger_path: Path = DEFAULT_LEDGER) -> list[str]:
    errors: list[str] = []
    data = _load_yaml(ledger_path, errors)
    if not isinstance(data, dict):
        return errors or [f"{_rel(ledger_path, root)}: root must be a mapping"]

    entries = data.get("entries")
    if not isinstance(entries, list) or not entries:
        errors.append(f"{_rel(ledger_path, root)}: entries must be a non-empty list")
        return errors

    seen_ids: set[str] = set()
    for index, entry in enumerate(entries):
        label = f"entries[{index}]"
        if not isinstance(entry, dict):
            errors.append(f"{label}: entry must be a mapping")
            continue
        _validate_entry(root, entry, label, seen_ids, errors)
    return errors


def _validate_entry(
    root: Path,
    entry: dict[str, Any],
    label: str,
    seen_ids: set[str],
    errors: list[str],
) -> None:
    entry_id = entry.get("id")
    if not isinstance(entry_id, str) or not entry_id.strip():
        errors.append(f"{label}: id must be a non-empty string")
        entry_id = label
    elif entry_id in seen_ids:
        errors.append(f"{entry_id}: duplicate id")
    else:
        seen_ids.add(entry_id)

    for field in REQUIRED_ENTRY_FIELDS:
        if field not in entry:
            errors.append(f"{entry_id}: missing required field '{field}'")

    model_file = _resolve_repo_path(root, entry.get("model_file"), entry_id, "model_file", errors)
    if model_file is not None:
        model_symbols = _python_symbols(model_file, errors)
        for block in _string_list(entry.get("model_blocks"), entry_id, "model_blocks", errors):
            if block not in model_symbols:
                errors.append(
                    f"{entry_id}: model block '{block}' not found in {_rel(model_file, root)}"
                )

    for symbol_ref in _string_list(entry.get("code_symbols"), entry_id, "code_symbols", errors):
        _validate_symbol_ref(root, entry_id, symbol_ref, errors)

    for field in ("tests", "examples"):
        for file_ref in _string_list(entry.get(field), entry_id, field, errors):
            _resolve_repo_path(root, file_ref, entry_id, field, errors)

    for field in ("boundaries", "stale_when"):
        values = _string_list(entry.get(field), entry_id, field, errors)
        if not values:
            errors.append(f"{entry_id}: {field} must contain at least one item")

    commands = entry.get("validation_commands")
    if not isinstance(commands, list) or not commands:
        errors.append(f"{entry_id}: validation_commands must be a non-empty list")
    else:
        for command_index, command in enumerate(commands):
            if isinstance(command, str):
                if not command.strip():
                    errors.append(
                        f"{entry_id}: validation_commands[{command_index}] is empty"
                    )
            elif isinstance(command, dict):
                text = command.get("command")
                if not isinstance(text, str) or not text.strip():
                    errors.append(
                        f"{entry_id}: validation_commands[{command_index}].command must be non-empty"
                    )
            else:
                errors.append(
                    f"{entry_id}: validation_commands[{command_index}] must be a string or mapping"
                )


def _validate_symbol_ref(
    root: Path,
    entry_id: str,
    symbol_ref: str,
    errors: list[str],
) -> None:
    if "::" not in symbol_ref:
        errors.append(f"{entry_id}: code symbol '{symbol_ref}' must use path::Symbol")
        return
    file_ref, symbol_name = symbol_ref.split("::", 1)
    if not symbol_name:
        errors.append(f"{entry_id}: code symbol '{symbol_ref}' is missing a symbol name")
        return
    path = _resolve_repo_path(root, file_ref, entry_id, "code_symbols", errors)
    if path is None:
        return
    if path.suffix != ".py":
        errors.append(f"{entry_id}: code symbol file must be Python: {_rel(path, root)}")
        return
    symbols = _python_symbols(path, errors)
    if symbol_name not in symbols:
        errors.append(f"{entry_id}: symbol '{symbol_name}' not found in {_rel(path, root)}")


def _load_yaml(path: Path, errors: list[str]) -> Any:
    if not path.exists():
        errors.append(f"{path}: ledger file does not exist")
        return None
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        errors.append(f"{path}: invalid YAML: {exc}")
        return None


def _resolve_repo_path(
    root: Path,
    value: Any,
    entry_id: str,
    field: str,
    errors: list[str],
) -> Path | None:
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{entry_id}: {field} path must be a non-empty string")
        return None
    path = root / value
    if not path.exists():
        errors.append(f"{entry_id}: {field} path does not exist: {value}")
        return None
    return path


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


def _python_symbols(path: Path, errors: list[str]) -> set[str]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except SyntaxError as exc:
        errors.append(f"{path}: Python parse failed: {exc}")
        return set()
    symbols: set[str] = set()
    for node in tree.body:
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            symbols.add(node.name)
    return symbols


def _rel(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return str(path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate PhysicsGuard model-code ledger.")
    parser.add_argument(
        "ledger",
        nargs="?",
        type=Path,
        default=DEFAULT_LEDGER,
        help="path to model_code_ledger.yaml",
    )
    parser.add_argument("--json", action="store_true", help="emit JSON output")
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
        print("model-code ledger check failed:")
        for error in errors:
            print(f"- {error}")
    else:
        print(f"model-code ledger check passed: {_rel(ledger_path, ROOT)}")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
