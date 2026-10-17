"""Read-only comparison of installed PhysicsGuard consumer files with their source."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

sys.dont_write_bytecode = True
SCRIPT_ROOT = Path(__file__).resolve().parent
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))
from install_physicsguard_skills import (  # noqa: E402
    DEFAULT_CODEX_HOME, PHYSICSGUARD_SKILL_IDS, ROOT,
    consumer_files, physicsguard_member_roots, safe_path,
)

DEFAULT_INSTALLED_ROOT = DEFAULT_CODEX_HOME / "skills"


def blocked_installed_skill_audit(*, installed_root: Path, repository_root: Path, finding_type: str, detail: str) -> dict[str, Any]:
    return {"artifact_kind": "physicsguard_installed_skill_audit", "ok": False, "status": "blocked", "repo_skill_root": str(repository_root / "skill"), "installed_root": str(installed_root), "skill_count": 0, "expected_skill_ids": list(PHYSICSGUARD_SKILL_IDS), "member_results": [], "findings": [{"type": finding_type, "detail": detail}]}


def check_installed_skills(installed_root: Path, *, repository_root: Path = ROOT) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    rows: list[dict[str, Any]] = []
    try:
        members = physicsguard_member_roots(repository_root)
        installed = safe_path(installed_root)
        if not installed.is_dir():
            raise ValueError(f"installed_skill_root_missing:{installed}")
        extra = sorted(path.name for path in installed.iterdir() if path.name.startswith("physicsguard-") and path.name not in PHYSICSGUARD_SKILL_IDS)
        for skill_id in extra:
            findings.append({"type": "unexpected_installed_physicsguard_residual", "skill": skill_id})
    except (OSError, ValueError) as exc:
        return blocked_installed_skill_audit(installed_root=installed_root, repository_root=repository_root, finding_type="skill_inventory_unavailable", detail=str(exc))
    for skill_id, source in members:
        destination = installed / skill_id
        reasons: list[str] = []
        try:
            safe_path(destination)
            if not destination.is_dir():
                reasons.append("installed_skill_missing")
            else:
                expected = consumer_files(source)
                actual = consumer_files(destination, installed=True)
                reasons.extend(f"missing_file:{path}" for path in expected.keys() - actual.keys())
                reasons.extend(f"unexpected_file:{path}" for path in actual.keys() - expected.keys())
                reasons.extend(f"changed_file:{path}" for path in expected.keys() & actual.keys() if expected[path] != actual[path])
        except (OSError, ValueError) as exc:
            reasons.append(str(exc))
        rows.append({"skill_id": skill_id, "ok": not reasons, "status": "blocked" if reasons else "pass", "source_root": str(source), "installed_root": str(destination), "reasons": sorted(reasons)})
        if reasons:
            findings.append({"type": "installed_skill_missing" if reasons == ["installed_skill_missing"] else "installed_consumer_files_mismatch", "skill": skill_id, "reasons": sorted(reasons)})
    return {"artifact_kind": "physicsguard_installed_skill_audit", "ok": not findings, "status": "blocked" if findings else "pass", "repo_skill_root": str(repository_root / "skill"), "installed_root": str(installed), "skill_count": len(members), "expected_skill_ids": list(PHYSICSGUARD_SKILL_IDS), "member_results": rows, "findings": findings}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--installed-root", type=Path, default=DEFAULT_INSTALLED_ROOT)
    parser.add_argument("--repository-root", type=Path, default=ROOT)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    result = check_installed_skills(args.installed_root, repository_root=args.repository_root)
    print(json.dumps(result, ensure_ascii=False, indent=None if args.json else 2, sort_keys=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
