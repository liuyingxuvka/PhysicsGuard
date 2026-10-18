from __future__ import annotations

import hashlib
from pathlib import Path
import shutil
import json

import pytest

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


@pytest.mark.parametrize("mutation", ["changed", "extra_consumer", "extra_author", "unsupported_entry"])
def test_installed_identity_mutations_are_rejected_without_writes(tmp_path: Path, mutation: str) -> None:
    repository, installed_root = _build_suite(tmp_path)
    member = installed_root / PHYSICSGUARD_SKILL_IDS[0]
    if mutation == "changed":
        (member / "SKILL.md").write_text("Changed installed bytes.\n", encoding="utf-8")
        reason = "changed_file:SKILL.md"
    elif mutation in {"extra_consumer", "extra_author"}:
        relative = "references/extra.md" if mutation == "extra_consumer" else ".skillguard/author.json"
        extra = member / relative
        extra.parent.mkdir(exist_ok=True)
        extra.write_text("Unexpected installed file.\n", encoding="utf-8")
        reason = f"unexpected_file:{relative}"
    else:
        (installed_root / "physicsguard-unsupported").mkdir()
    before_source, before_installed = _tree_snapshot(repository), _tree_snapshot(installed_root)
    result = check_installed_skills(installed_root, repository_root=repository)
    assert result["status"] == "blocked"
    assert result["ok"] is False
    if mutation == "unsupported_entry":
        assert {"type": "unexpected_installed_physicsguard_residual", "skill": "physicsguard-unsupported"} in result["findings"]
    else:
        assert reason in result["member_results"][0]["reasons"]
    assert _tree_snapshot(repository) == before_source
    assert _tree_snapshot(installed_root) == before_installed


@pytest.mark.parametrize("entry", ["audit", "readiness"])
def test_public_audit_exception_contract_is_one_blocked_json(tmp_path: Path, monkeypatch, capsys, entry: str) -> None:
    from scripts import check_installed_physicsguard_skills as audit
    from scripts import verify_guard_simulation_readiness as readiness

    module = audit if entry == "audit" else readiness

    def fail_native_audit(*args, **kwargs):
        raise RuntimeError("injected native audit failure")

    monkeypatch.setattr(module, "check_installed_skills", fail_native_audit)
    result = module.main(["--repository-root", str(ROOT), "--installed-root", str(tmp_path)])
    captured = capsys.readouterr()
    assert result == 1
    report = json.loads(captured.out)
    assert report["status"] == "blocked" and report["ok"] is False
    installation = report if entry == "audit" else report["consumer_installation_audit"]
    assert installation["findings"] == [{"type": "installed_skill_audit_exception", "detail": "RuntimeError:injected native audit failure"}]
    assert captured.err == ""
