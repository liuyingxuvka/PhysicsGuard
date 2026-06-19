"""Verify installed Codex PhysicsGuard skills match repository source."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
REPO_SKILL_ROOT = ROOT / "skill"
DEFAULT_INSTALLED_ROOT = Path.home() / ".codex" / "skills"
FORBIDDEN_INSTALLED_SKILLS = {
    "physicsguard-database-adoption",
    "physicsguard-database-catalog",
    "physicsguard-database-maintenance",
    "physicsguard-database-project-intake",
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--installed-root", type=Path, default=DEFAULT_INSTALLED_ROOT)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    result = check_installed_skills(args.installed_root)
    if args.json:
        print(json.dumps(result, sort_keys=True))
    else:
        print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["ok"] else 1


def check_installed_skills(installed_root: Path) -> dict:
    findings: list[dict] = []
    skills = sorted(path for path in REPO_SKILL_ROOT.iterdir() if path.is_dir())
    for skill_name in sorted(FORBIDDEN_INSTALLED_SKILLS):
        installed_dir = installed_root / skill_name
        if installed_dir.exists():
            findings.append(
                {
                    "severity": "error",
                    "type": "forbidden_installed_skill_present",
                    "skill": skill_name,
                    "path": str(installed_dir),
                }
            )
    for skill_dir in skills:
        installed_dir = installed_root / skill_dir.name
        if not installed_dir.exists():
            findings.append(
                {
                    "severity": "error",
                    "type": "installed_skill_missing",
                    "skill": skill_dir.name,
                    "path": str(installed_dir),
                }
            )
            continue
        repo_hashes = _tree_hashes(skill_dir)
        installed_hashes = _tree_hashes(installed_dir)
        if repo_hashes != installed_hashes:
            findings.append(
                {
                    "severity": "error",
                    "type": "installed_skill_hash_mismatch",
                    "skill": skill_dir.name,
                    "repo_hash": _stable_dict_hash(repo_hashes),
                    "installed_hash": _stable_dict_hash(installed_hashes),
                    "missing_files": sorted(set(repo_hashes) - set(installed_hashes)),
                    "extra_files": sorted(set(installed_hashes) - set(repo_hashes)),
                    "changed_files": sorted(
                        key for key in set(repo_hashes) & set(installed_hashes)
                        if repo_hashes[key] != installed_hashes[key]
                    ),
                }
            )
    return {
        "ok": not findings,
        "status": "pass" if not findings else "fail",
        "repo_skill_root": str(REPO_SKILL_ROOT),
        "installed_root": str(installed_root),
        "skill_count": len(skills),
        "findings": findings,
    }


def _tree_hashes(root: Path) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        if "__pycache__" in path.parts:
            continue
        relative = path.relative_to(root).as_posix()
        hashes[relative] = _file_hash(path)
    return hashes


def _file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _stable_dict_hash(value: dict[str, str]) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


if __name__ == "__main__":
    raise SystemExit(main())
