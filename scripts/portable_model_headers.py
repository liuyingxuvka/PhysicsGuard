from __future__ import annotations

import subprocess
import os
from pathlib import Path
from textwrap import shorten
from typing import Any

import yaml


REPOSITORY_URL = "https://github.com/liuyingxuvka/PhysicsGuard"
HEADER_MARKER = "PhysicsGuard"
BOUNDARY_LINE = (
    "Low-fidelity SI-unit residual audit or blueprint only; not a "
    "high-fidelity solver, commercial-tool adapter, or reverse-engineered model."
)


def tracked_example_yaml_files(root: Path) -> list[Path]:
    git_cmd = ["git", "ls-files", "examples/*.yaml", "examples/**/*.yaml"]
    if os.name == "nt":
        git_cmd = ["cmd", "/c", *git_cmd]
    try:
        result = subprocess.run(
            git_cmd,
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return sorted((root / "examples").rglob("*.yaml"))
    return [root / line for line in result.stdout.splitlines() if line.strip() and (root / line).exists()]


def artifact_kind(data: dict[str, Any]) -> str:
    if "closure_id" in data and "claim_scope" in data:
        return "project closure plan"
    if "registry_id" in data and "project_profile" in data and "artifacts" in data:
        return "project evidence registry"
    if "logical_dataset_id" in data:
        return "logical dataset record"
    if "validation_id" in data and "audit_file" in data:
        return "model-dataset validation plan"
    if "library_id" in data and "entries" in data:
        return "model library index"
    if "project_id" in data and "relations" in data:
        return "test-file relation index"
    if "project_id" in data and "test_files" in data:
        return "test-file project index"
    if "contract_id" in data:
        return "test-file contract"
    if "binding_id" in data:
        return "test-file model binding"
    if "manifest_id" in data and "fields" in data:
        return "data-file manifest"
    if "profile_id" in data and "expected_fields" in data:
        return "testbench profile"
    if "profile_id" in data:
        return "test-file extractor profile"
    if "parameters" in data:
        return "parameter catalog"
    if "roles" in data:
        return "parameter role matrix"
    if "edges" in data:
        return "parameter mapping edges"
    if "require_all_manifest_fields" in data:
        return "parameter coverage policy"
    if "hierarchy" in data:
        return "hierarchical audit/model blueprint"
    if "observation_name" in data:
        return "observed-values snapshot"
    return "system audit/model blueprint"


def purpose_for(path: Path, data: dict[str, Any]) -> str:
    description = data.get("description")
    if isinstance(description, str) and description.strip():
        return _sentence(description)
    for key in ("audit_name", "observation_name", "system_name", "closure_id"):
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            return _sentence(value.replace("_", " "))
    system = data.get("system")
    if isinstance(system, dict):
        value = system.get("system_name")
        if isinstance(value, str) and value.strip():
            return _sentence(value.replace("_", " "))
    return _sentence(path.stem.replace("_", " "))


def use_hint(path: Path, data: dict[str, Any]) -> str:
    rel = path.as_posix()
    if "closure_id" in data and "claim_scope" in data:
        return f"python -m physicsguard.cli project closure {rel} --pretty"
    if "registry_id" in data and "project_profile" in data and "artifacts" in data:
        return f"python -m physicsguard.cli evidence check {rel} --pretty"
    if "logical_dataset_id" in data:
        return f"python -m physicsguard.cli dataset logical-check {rel} --pretty"
    if "validation_id" in data and "audit_file" in data:
        return f"python -m physicsguard.cli validation run {rel} --pretty"
    if "library_id" in data and "entries" in data:
        return f"python -m physicsguard.cli model-library check {rel} --pretty"
    if "project_id" in data and "relations" in data:
        return f"python -m physicsguard.cli dataset relation-check {rel} --pretty"
    if "project_id" in data and "test_files" in data:
        return f"python -m physicsguard.cli testfile project-check {rel} --pretty"
    if "contract_id" in data:
        return f"python -m physicsguard.cli testfile contract-check {rel} --pretty"
    if "hierarchy" in data:
        return f"python -m physicsguard.cli hierarchy run {rel} --pretty"
    if "observation_name" in data:
        return "pair with an audit YAML via python -m physicsguard.cli evaluate or hierarchy evaluate"
    if "manifest_id" in data or "binding_id" in data or "profile_id" in data:
        return "reference from a PhysicsGuard test-file contract"
    if "parameters" in data or "roles" in data or "edges" in data or "require_all_manifest_fields" in data:
        return "reference from a PhysicsGuard test-file contract"
    return f"python -m physicsguard.cli run {rel} --pretty"


def header_for(path: Path, data: dict[str, Any]) -> str:
    rel = path.as_posix()
    purpose = purpose_for(path, data)
    return "\n".join(
        [
            f"# PhysicsGuard {artifact_kind(data)}",
            f"# Purpose: {purpose}",
            f"# Repository: {REPOSITORY_URL}",
            f"# Use with: {use_hint(Path(rel), data)}",
            f"# Boundary: {BOUNDARY_LINE}",
            "",
        ]
    )


def ensure_header(path: Path, root: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    data = yaml.safe_load(text)
    if not isinstance(data, dict):
        raise ValueError(f"YAML root must be a mapping: {path}")
    rel_path = path.relative_to(root)
    header = header_for(rel_path, data)
    if text.startswith("# PhysicsGuard "):
        body = _strip_existing_header(text)
        new_text = header + body.lstrip("\n")
    else:
        new_text = header + text
    if new_text == text:
        return False
    path.write_text(new_text, encoding="utf-8")
    return True


def has_portable_header(path: Path) -> bool:
    lines = path.read_text(encoding="utf-8").splitlines()
    if len(lines) < 5:
        return False
    return (
        lines[0].startswith("# PhysicsGuard ")
        and lines[1].startswith("# Purpose: ")
        and lines[2] == f"# Repository: {REPOSITORY_URL}"
        and lines[3].startswith("# Use with: ")
        and lines[4] == f"# Boundary: {BOUNDARY_LINE}"
    )


def _strip_existing_header(text: str) -> str:
    lines = text.splitlines(keepends=True)
    if not lines or not lines[0].startswith("# PhysicsGuard "):
        return text
    idx = 0
    expected_prefixes = (
        "# PhysicsGuard ",
        "# Purpose: ",
        "# Repository: ",
        "# Use with: ",
        "# Boundary: ",
    )
    while idx < len(lines) and idx < len(expected_prefixes):
        if not lines[idx].startswith(expected_prefixes[idx]):
            return text
        idx += 1
    if idx < len(lines) and lines[idx].strip() == "":
        idx += 1
    return "".join(lines[idx:])


def _sentence(value: str) -> str:
    cleaned = " ".join(value.strip().split())
    cleaned = shorten(cleaned, width=150, placeholder="...")
    if cleaned.endswith((".", "!", "?")):
        return cleaned
    return f"{cleaned}."


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    changed = 0
    for path in tracked_example_yaml_files(root):
        changed += int(ensure_header(path, root))
    print(f"portable headers updated: {changed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
