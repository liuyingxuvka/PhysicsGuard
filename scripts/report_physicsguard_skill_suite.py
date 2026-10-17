"""Read the ten route capsules and check their consumer reference paths."""
from __future__ import annotations

import argparse
import json
from pathlib import Path, PurePosixPath
import sys
from typing import Any, Sequence

sys.dont_write_bytecode = True
SCRIPT_ROOT = Path(__file__).resolve().parent
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))
from install_physicsguard_skills import (  # noqa: E402
    PHYSICSGUARD_SKILL_IDS, ROOT, consumer_files, physicsguard_member_roots,
)

EXPECTED_SKILLS = PHYSICSGUARD_SKILL_IDS


def build_report(repository_root: Path) -> dict[str, Any]:
    findings: list[str] = []
    members: list[dict[str, Any]] = []
    routes: set[str] = set()
    owners: set[str] = set()
    try:
        source_members = physicsguard_member_roots(repository_root)
    except (OSError, ValueError) as exc:
        source_members = ()
        findings.append(str(exc))
    for skill_id, source in source_members:
        try:
            files = consumer_files(source)
            capsule = json.loads((source / "references" / "route-capsule.json").read_text(encoding="utf-8"))
            if not isinstance(capsule, dict):
                raise ValueError("route_capsule_not_object")
            owner, route = capsule.get("native_owner_id"), capsule.get("native_route_id")
            if capsule.get("target_skill_id") != skill_id:
                findings.append(f"{skill_id}:capsule_skill_mismatch")
            if not isinstance(owner, str) or not owner or owner in owners:
                findings.append(f"{skill_id}:native_owner_missing_or_duplicate")
            if not isinstance(route, str) or not route or route in routes:
                findings.append(f"{skill_id}:native_route_missing_or_duplicate")
            if isinstance(owner, str):
                owners.add(owner)
            if isinstance(route, str):
                routes.add(route)
            references = list(capsule.get("initial_load", []))
            conditional = capsule.get("conditional_references", [])
            if not isinstance(conditional, list):
                raise ValueError("conditional_references_not_list")
            for row in conditional:
                if not isinstance(row, dict):
                    raise ValueError("conditional_reference_not_object")
                relative = row.get("path")
                references.append(relative)
                if isinstance(relative, str) and relative in files and row.get("sha256") != files[relative]:
                    findings.append(f"{skill_id}:reference_hash_mismatch:{relative}")
            for relative in references:
                if not isinstance(relative, str) or PurePosixPath(relative).is_absolute() or ".." in PurePosixPath(relative).parts or relative not in files:
                    findings.append(f"{skill_id}:reference_missing_or_unsafe:{relative}")
            if capsule.get("entry_prompt_sha256") != files["SKILL.md"]:
                findings.append(f"{skill_id}:entry_prompt_hash_mismatch")
            for handoff in capsule.get("reject_handoffs", []):
                if not isinstance(handoff, dict) or handoff.get("target_skill_id") not in (*EXPECTED_SKILLS, "none"):
                    findings.append(f"{skill_id}:handoff_target_missing")
            members.append({"skill_id": skill_id, "native_owner_id": owner, "native_route_id": route, "consumer_file_count": len(files), "reference_count": len(references)})
        except (OSError, ValueError, TypeError) as exc:
            findings.append(f"{skill_id}:{type(exc).__name__}:{exc}")
    return {"artifact_kind": "physicsguard_skill_suite_structure_report", "authoritative": False, "structure_status": "blocked" if findings else "pass", "member_count": len(members), "members": members, "findings": findings, "claim_boundary": "Reports source route uniqueness and reference identity only; executes no domain or regression check."}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository-root", type=Path, default=ROOT)
    args = parser.parse_args(argv)
    result = build_report(args.repository_root)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["structure_status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
