"""Copy the ten PhysicsGuard consumer skills with recoverable directory replacement."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import sys
import tempfile
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_ROOT = Path(__file__).resolve().parent
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))
DEFAULT_CODEX_HOME = Path(os.environ.get("CODEX_HOME") or (Path.home() / ".codex"))
PHYSICSGUARD_SKILL_IDS = (
    "physicsguard-ai-debugging",
    "physicsguard-audit-closure",
    "physicsguard-candidate-model-blueprint",
    "physicsguard-model-dataset-validation",
    "physicsguard-model-library",
    "physicsguard-model-understanding-preflight",
    "physicsguard-project-adoption",
    "physicsguard-project-evidence-registry",
    "physicsguard-signal-mapping-review",
    "physicsguard-test-file-contract-review",
)
CONSUMER_FILES = {"SKILL.md"}
CONSUMER_DIRECTORIES = {"agents", "references", "scripts"}


def safe_path(path: Path) -> Path:
    """Reject traversal, symlinks and Windows junction/reparse paths, including ancestors."""
    candidate = Path(path).expanduser()
    if ".." in candidate.parts:
        raise ValueError(f"path_traversal:{candidate}")
    candidate = candidate.absolute()
    for part in reversed((candidate, *candidate.parents)):
        if part.is_symlink():
            raise ValueError(f"symlink_path:{part}")
        try:
            info = part.lstat()
        except FileNotFoundError:
            continue
        if getattr(info, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0):
            raise ValueError(f"reparse_path:{part}")
    return candidate


def consumer_files(skill_root: Path, *, installed: bool = False) -> dict[str, str]:
    """Return relative paths and byte hashes; author files never enter a consumer copy."""
    root = safe_path(skill_root)
    if not root.is_dir():
        raise ValueError(f"skill_directory_missing:{root}")
    files: dict[str, str] = {}
    for directory, dirs, names in os.walk(root, followlinks=False):
        parent = Path(directory)
        for name in [*dirs, *names]:
            safe_path(parent / name)
        dirs[:] = [name for name in dirs if name != "__pycache__"]
        if parent == root and not installed:
            dirs[:] = [name for name in dirs if name in CONSUMER_DIRECTORIES]
        for name in names:
            path = parent / name
            relative = path.relative_to(root)
            if name.endswith((".pyc", ".pyo")):
                continue
            if not installed and len(relative.parts) == 1 and name not in CONSUMER_FILES:
                continue
            if not path.is_file():
                raise ValueError(f"non_regular_consumer_file:{path}")
            files[relative.as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    missing = CONSUMER_FILES - files.keys()
    if missing:
        raise ValueError(f"consumer_files_missing:{root}:{','.join(sorted(missing))}")
    return dict(sorted(files.items()))


def physicsguard_member_roots(repository_root: Path) -> tuple[tuple[str, Path], ...]:
    root = safe_path(repository_root) / "skill"
    safe_path(root)
    actual = {path.name for path in root.iterdir() if path.name.startswith("physicsguard-")}
    if actual != set(PHYSICSGUARD_SKILL_IDS):
        raise ValueError(f"skill_inventory_mismatch:missing={sorted(set(PHYSICSGUARD_SKILL_IDS)-actual)}:extra={sorted(actual-set(PHYSICSGUARD_SKILL_IDS))}")
    return tuple((skill_id, safe_path(root / skill_id)) for skill_id in PHYSICSGUARD_SKILL_IDS)


def build_suite_plan(repository_root: Path) -> dict[str, Any]:
    members: list[dict[str, Any]] = []
    blockers: list[str] = []
    try:
        for skill_id, source in physicsguard_member_roots(repository_root):
            members.append({"skill_id": skill_id, "source_root": str(source), "files": consumer_files(source)})
    except (OSError, ValueError) as exc:
        blockers.append(str(exc))
    return {"status": "blocked" if blockers else "passed", "member_ids": list(PHYSICSGUARD_SKILL_IDS), "members": members, "blockers": blockers}


def coordinate_suite_install(repository_root: Path, stage_root: Path | None, codex_home: Path) -> dict[str, Any]:
    """Stage every member first, then replace directories; restore old trees on failure."""
    plan = build_suite_plan(repository_root)
    if plan["status"] != "passed":
        return {**plan, "phase": "plan"}
    activated: list[str] = []
    moved_old: list[str] = []
    recovery_errors: list[str] = []
    temporary: Path | None = None
    phase = "prepare"
    try:
        installed_root = safe_path(codex_home) / "skills"
        safe_path(installed_root)
        source_root = safe_path(repository_root)
        if installed_root.is_relative_to(source_root) or source_root.is_relative_to(installed_root):
            raise ValueError("installation_source_destination_overlap")
        if installed_root.is_dir():
            extra = sorted(path.name for path in installed_root.iterdir() if path.name.startswith("physicsguard-") and path.name not in PHYSICSGUARD_SKILL_IDS)
            if extra:
                raise ValueError(f"unexpected_installed_skills:{extra}")
        for skill_id in PHYSICSGUARD_SKILL_IDS:
            destination = safe_path(installed_root / skill_id)
            if destination.exists() and not destination.is_dir():
                raise ValueError(f"installed_skill_not_directory:{destination}")
        parent = safe_path(stage_root) if stage_root is not None else installed_root.parent
        if parent.is_relative_to(source_root):
            raise ValueError("stage_source_overlap")
        if any(parent.is_relative_to(installed_root / skill_id) for skill_id in PHYSICSGUARD_SKILL_IDS):
            raise ValueError("stage_inside_installation_member")
        parent.mkdir(parents=True, exist_ok=True)
        temporary = Path(tempfile.mkdtemp(prefix=".physicsguard-install-", dir=parent))
        staged = temporary / "new"
        backup = temporary / "old"
        backup.mkdir()
        for row in plan["members"]:
            source = Path(row["source_root"])
            target = staged / row["skill_id"]
            target.mkdir(parents=True)
            for relative in row["files"]:
                destination = target / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source / relative, destination)
            if consumer_files(target, installed=True) != row["files"]:
                raise ValueError(f"staged_files_changed:{row['skill_id']}")
        phase = "activate"
        installed_root.mkdir(parents=True, exist_ok=True)
        for skill_id in PHYSICSGUARD_SKILL_IDS:
            destination = safe_path(installed_root / skill_id)
            if destination.exists():
                os.replace(destination, backup / skill_id)
                moved_old.append(skill_id)
            os.replace(staged / skill_id, destination)
            activated.append(skill_id)
    except (OSError, ValueError) as exc:
        if temporary is not None:
            for skill_id in reversed(PHYSICSGUARD_SKILL_IDS):
                try:
                    destination = installed_root / skill_id
                    if skill_id in activated:
                        shutil.rmtree(destination)
                    if skill_id in moved_old:
                        os.replace(temporary / "old" / skill_id, destination)
                except OSError as recovery_exc:
                    recovery_errors.append(f"{skill_id}:{recovery_exc}")
            if not recovery_errors:
                shutil.rmtree(temporary)
        return {"status": "blocked", "phase": phase, "blockers": [str(exc)], "activated": activated, "recovery_errors": recovery_errors, "recovery_path": str(temporary) if recovery_errors else None}
    if temporary is not None:
        try:
            shutil.rmtree(temporary)
        except OSError as exc:
            return {"status": "blocked", "phase": "cleanup", "blockers": [str(exc)], "activated": activated, "recovery_path": str(temporary)}
    return {"status": "passed", "phase": "complete", "member_ids": list(PHYSICSGUARD_SKILL_IDS), "installed_root": str(installed_root), "activated": activated, "blockers": []}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--plan", action="store_true")
    mode.add_argument("--install", action="store_true")
    mode.add_argument("--check", action="store_true")
    parser.add_argument("--repository-root", type=Path, default=ROOT)
    parser.add_argument("--stage-root", type=Path)
    parser.add_argument("--codex-home", type=Path, default=DEFAULT_CODEX_HOME)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    if args.check:
        from check_installed_physicsguard_skills import check_installed_skills
        result = check_installed_skills(args.codex_home / "skills", repository_root=args.repository_root)
    elif args.plan:
        result = build_suite_plan(args.repository_root)
    else:
        result = coordinate_suite_install(args.repository_root, args.stage_root, args.codex_home)
    print(json.dumps(result, ensure_ascii=False, indent=None if args.json else 2, sort_keys=True))
    return 0 if result["status"] in {"pass", "passed"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
