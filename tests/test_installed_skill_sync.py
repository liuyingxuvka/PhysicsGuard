from __future__ import annotations

import hashlib
from pathlib import Path
import shutil

from scripts.check_installed_physicsguard_skills import check_installed_skills
from scripts.install_physicsguard_skills import PHYSICSGUARD_SKILL_IDS, coordinate_suite_install

ROOT = Path(__file__).resolve().parents[1]


def _build_suite(tmp_path: Path) -> tuple[Path, Path]:
    repository = tmp_path / "repository"
    shutil.copytree(ROOT / "skill", repository / "skill")
    home = tmp_path / "codex-home"
    result = coordinate_suite_install(repository, tmp_path / "stage", home)
    assert result["status"] == "passed", result
    return repository, home / "skills"


def _tree_snapshot(root: Path) -> dict[str, tuple[int, int, str]]:
    return {path.relative_to(root).as_posix(): (path.stat().st_size, path.stat().st_mtime_ns, hashlib.sha256(path.read_bytes()).hexdigest()) for path in root.rglob("*") if path.is_file() and not path.is_symlink()}


def test_installed_skill_sync_check_passes_matching_copy_and_writes_nothing(tmp_path: Path) -> None:
    repository, installed_root = _build_suite(tmp_path)
    before_source = _tree_snapshot(repository)
    before_installed = _tree_snapshot(installed_root)
    result = check_installed_skills(installed_root, repository_root=repository)
    assert result["ok"]
    assert result["expected_skill_ids"] == list(PHYSICSGUARD_SKILL_IDS)
    assert _tree_snapshot(repository) == before_source
    assert _tree_snapshot(installed_root) == before_installed


def test_installed_skill_sync_check_reports_missing_skill(tmp_path: Path) -> None:
    repository, installed_root = _build_suite(tmp_path)
    shutil.rmtree(installed_root / PHYSICSGUARD_SKILL_IDS[0])
    result = check_installed_skills(installed_root, repository_root=repository)
    assert not result["ok"]
    assert any(row["type"] == "installed_skill_missing" for row in result["findings"])


def test_new_source_file_invalidates_installed_release_plan(tmp_path: Path) -> None:
    repository, installed_root = _build_suite(tmp_path)
    (repository / "skill" / PHYSICSGUARD_SKILL_IDS[0] / "references" / "new-capability.md").write_text("New native capability.\n", encoding="utf-8")
    result = check_installed_skills(installed_root, repository_root=repository)
    assert not result["ok"]
    assert "missing_file:references/new-capability.md" in result["member_results"][0]["reasons"]


def test_installed_member_symlink_is_visibly_blocked(tmp_path: Path) -> None:
    repository, installed_root = _build_suite(tmp_path)
    member = installed_root / PHYSICSGUARD_SKILL_IDS[0]
    real_member = tmp_path / "real-member"
    member.rename(real_member)
    member.symlink_to(real_member, target_is_directory=True)
    before = _tree_snapshot(real_member)
    result = check_installed_skills(installed_root, repository_root=repository)
    assert not result["ok"]
    assert any(reason.startswith("symlink_path:") for reason in result["member_results"][0]["reasons"])
    assert _tree_snapshot(real_member) == before
