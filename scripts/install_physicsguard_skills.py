"""Install the PhysicsGuard skills into an agent's skills directory.

    python scripts/install_physicsguard_skills.py --target ~/.codex/skills             # or ~/.claude/skills
    python scripts/install_physicsguard_skills.py --target ~/.codex/skills --dry-run   # show what would change
    python scripts/install_physicsguard_skills.py --target ~/.codex/skills --check     # exit 1 if the copy differs

Copies each skill under skill/ to <target>/<skill id>, replacing an older copy. Only SKILL.md and the
agents/, references/ and scripts/ directories are copied. Retired PhysicsGuard skill directories are removed.
The Python engine is installed separately: python -m pip install -e <this repository>.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import sys

SKILL_ROOT = Path(__file__).resolve().parents[1] / "skill"
PHYSICSGUARD_SKILL_IDS = (
    "physicsguard-ai-debugging",
    "physicsguard-model-dataset-validation",
    "physicsguard-model-understanding-preflight",
    "physicsguard-signal-mapping-review",
    "physicsguard-test-file-contract-review",
)
RETIRED_SKILL_IDS = (
    "physicsguard-audit-closure",
    "physicsguard-candidate-model-blueprint",
    "physicsguard-model-library",
    "physicsguard-project-adoption",
    "physicsguard-project-evidence-registry",
)
CONSUMER_FILES = {"SKILL.md"}
CONSUMER_DIRECTORIES = {"agents", "references", "scripts"}


def _skipped(relative: Path) -> bool:
    if "__pycache__" in relative.parts or relative.suffix in {".pyc", ".pyo"}:
        return True
    return relative.parts[0] not in CONSUMER_DIRECTORIES and relative.as_posix() not in CONSUMER_FILES


def consumer_files(source: Path) -> list[str]:
    """Files of one skill that a user's copy gets; author files never enter it."""
    return sorted(
        path.relative_to(source).as_posix()
        for path in source.rglob("*")
        if path.is_file() and not _skipped(path.relative_to(source))
    )


def differences(source: Path, installed: Path) -> list[str]:
    if not installed.is_dir():
        return [f"missing {installed}"]
    wanted = consumer_files(source)
    present = sorted(
        path.relative_to(installed).as_posix()
        for path in installed.rglob("*")
        if path.is_file() and "__pycache__" not in path.relative_to(installed).parts
    )
    out = [f"only in source: {name}" for name in wanted if name not in present]
    out += [f"only in target: {name}" for name in present if name not in wanted]
    out += [f"differs: {name}" for name in wanted if name in present
            and (source / name).read_bytes() != (installed / name).read_bytes()]
    return out


def pending_changes(skill_root: Path, target: Path) -> list[str]:
    """Everything an install would change in target; empty when the installed copy is current."""
    out = [f"{skill_id}: {line}" for skill_id in PHYSICSGUARD_SKILL_IDS
           for line in differences(skill_root / skill_id, target / skill_id)]
    out += [f"{skill_id}: retired skill still installed" for skill_id in RETIRED_SKILL_IDS
            if (target / skill_id).exists() or (target / skill_id).is_symlink()]
    return out


def _remove(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.exists():
        shutil.rmtree(path)


def _ignore(source: Path):
    def ignore(directory: str, names: list[str]) -> set[str]:
        at_root = Path(directory) == source
        return {name for name in names
                if name == "__pycache__" or name.endswith((".pyc", ".pyo"))
                or (at_root and name not in CONSUMER_FILES | CONSUMER_DIRECTORIES)}
    return ignore


def install(skill_root: Path, target: Path) -> list[str]:
    """Replace each skill copy in target (rmtree + copytree) and remove retired skill directories."""
    done = []
    target.mkdir(parents=True, exist_ok=True)
    for skill_id in PHYSICSGUARD_SKILL_IDS:
        destination = target / skill_id
        _remove(destination)
        shutil.copytree(skill_root / skill_id, destination, ignore=_ignore(skill_root / skill_id))
        done.append(f"installed {destination}")
    for skill_id in RETIRED_SKILL_IDS:
        retired = target / skill_id
        if retired.exists() or retired.is_symlink():
            _remove(retired)
            done.append(f"removed retired {retired}")
    return done


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--target", type=Path, required=True,
                        help="skills directory, for example ~/.codex/skills or ~/.claude/skills")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="print what an install would change; change nothing")
    mode.add_argument("--check", action="store_true", help="exit 1 if the installed copy differs from this checkout")
    args = parser.parse_args(argv)
    target = args.target.expanduser()
    found = sorted(path.name for path in SKILL_ROOT.iterdir() if path.is_dir())
    if found != sorted(PHYSICSGUARD_SKILL_IDS):
        print(f"skill/ holds {found}, expected {list(PHYSICSGUARD_SKILL_IDS)}", file=sys.stderr)
        return 2
    changes = pending_changes(SKILL_ROOT, target)
    if args.check:
        print("\n".join(changes) or "installed skills are current")
        return 1 if changes else 0
    if args.dry_run:
        print("\n".join(f"would change {line}" for line in changes) or "already current")
        return 0
    print("\n".join(install(SKILL_ROOT, target)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
