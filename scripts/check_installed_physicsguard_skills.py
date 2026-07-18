"""Verify installed Codex PhysicsGuard consumer projections match source."""

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
        projection = _consumer_projection_status(skill_dir, installed_dir)
        if not projection["ok"]:
            findings.append(
                {
                    "severity": "error",
                    "type": "installed_consumer_projection_mismatch",
                    "skill": skill_dir.name,
                    **projection,
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


def _consumer_projection_status(source: Path, installed: Path) -> dict:
    manifest_path = installed / "consumer-release.json"
    reasons: list[str] = []
    rows: list[dict[str, object]] = []
    if (installed / ".skillguard").exists():
        reasons.append("installed_author_control_state_present")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return {
            "ok": False,
            "reasons": [f"consumer_manifest_unreadable:{type(exc).__name__}"],
            "rows": rows,
        }
    if not isinstance(manifest, dict):
        return {
            "ok": False,
            "reasons": ["consumer_manifest_not_object"],
            "rows": rows,
        }
    if manifest.get("schema_version") != "consumer.skill_distribution.current":
        reasons.append("consumer_manifest_schema_wrong")
    if manifest.get("skill_id") != source.name:
        reasons.append("consumer_manifest_skill_wrong")
    if manifest.get("projection_id") != "projection:consumer-distribution":
        reasons.append("consumer_manifest_projection_wrong")
    if manifest.get("author_control_excluded") is not True:
        reasons.append("consumer_manifest_author_boundary_wrong")
    unsigned = {key: value for key, value in manifest.items() if key != "manifest_hash"}
    if manifest.get("manifest_hash") != _canonical_hash(unsigned):
        reasons.append("consumer_manifest_hash_wrong")

    declared = manifest.get("files")
    if not isinstance(declared, list) or not declared:
        reasons.append("consumer_manifest_files_missing")
        declared = []
    declared_paths: set[str] = set()
    for index, row in enumerate(declared):
        if not isinstance(row, dict):
            reasons.append(f"consumer_manifest_row_invalid:{index}")
            continue
        relative = str(row.get("path", "")).replace("\\", "/")
        expected = str(row.get("content_hash", "")).lower()
        parts = relative.split("/")
        if (
            not relative
            or relative.startswith("/")
            or any(part in {"", ".", ".."} for part in parts)
            or ".skillguard" in parts
            or relative == "consumer-release.json"
            or relative in declared_paths
        ):
            reasons.append(f"consumer_manifest_path_invalid:{relative}")
            continue
        declared_paths.add(relative)
        source_path = source / Path(relative)
        installed_path = installed / Path(relative)
        source_hash = f"sha256:{_file_hash(source_path)}" if source_path.is_file() else None
        installed_hash = (
            f"sha256:{_file_hash(installed_path)}" if installed_path.is_file() else None
        )
        current = (
            expected.startswith("sha256:")
            and len(expected) == 71
            and source_hash == expected
            and installed_hash == expected
        )
        rows.append(
            {
                "relative_path": relative,
                "expected_hash": expected,
                "source_hash": source_hash,
                "installed_hash": installed_hash,
                "ok": current,
            }
        )
        if not current:
            reasons.append(f"consumer_file_mismatch:{relative}")
    actual_paths = {
        path.relative_to(installed).as_posix()
        for path in installed.rglob("*")
        if path.is_file() and path.name != "consumer-release.json"
    }
    missing = sorted(declared_paths - actual_paths)
    unexpected = sorted(actual_paths - declared_paths)
    if missing:
        reasons.extend(f"consumer_file_missing:{path}" for path in missing)
    if unexpected:
        reasons.extend(f"consumer_file_unexpected:{path}" for path in unexpected)
    return {
        "ok": not reasons and len(rows) == len(declared_paths),
        "release_id": manifest.get("release_id"),
        "manifest_hash": manifest.get("manifest_hash"),
        "reasons": reasons,
        "rows": rows,
    }


def _file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_hash(value: object) -> str:
    payload = (
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest().upper()


if __name__ == "__main__":
    raise SystemExit(main())
