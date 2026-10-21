from __future__ import annotations

from pathlib import Path
import shutil

from scripts import install_physicsguard_skills as installer


def _repository(tmp_path: Path) -> Path:
    repository = tmp_path / "repository"
    for skill_id in installer.PHYSICSGUARD_SKILL_IDS:
        source = repository / "skill" / skill_id
        (source / "references").mkdir(parents=True)
        (source / "SKILL.md").write_text(f"# {skill_id}\n", encoding="utf-8")
        (source / "references" / "protocol.md").write_text("Native protocol.\n", encoding="utf-8")
        (source / ".skillguard").mkdir()
        (source / ".skillguard" / "author.json").write_text("{}\n", encoding="utf-8")
        (source / "guard-model").mkdir()
        (source / "guard-model" / "candidate.json").write_text("{}\n", encoding="utf-8")
    return repository


def _old_installation(home: Path) -> dict[str, bytes]:
    for skill_id in installer.PHYSICSGUARD_SKILL_IDS:
        target = home / "skills" / skill_id
        target.mkdir(parents=True)
        (target / "old.txt").write_text(f"old:{skill_id}", encoding="utf-8")
    return _snapshot(home)


def _snapshot(root: Path) -> dict[str, bytes]:
    return {path.relative_to(root).as_posix(): path.read_bytes() for path in root.rglob("*") if path.is_file()}


def test_suite_plan_is_exact_ten_and_creates_no_stage(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    before = _snapshot(repository)
    result = installer.build_suite_plan(repository)
    assert result["status"] == "passed"
    assert result["member_ids"] == list(installer.PHYSICSGUARD_SKILL_IDS)
    assert _snapshot(repository) == before
    assert set(tmp_path.iterdir()) == {repository}


def test_all_members_are_prepared_then_all_verified_before_any_activation(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    home = tmp_path / "codex-home"
    _old_installation(home)
    result = installer.coordinate_suite_install(repository, tmp_path / "stage", home)
    assert result["status"] == "passed"
    for skill_id in installer.PHYSICSGUARD_SKILL_IDS:
        source = repository / "skill" / skill_id
        destination = home / "skills" / skill_id
        assert installer.consumer_files(destination, installed=True) == installer.consumer_files(source)
        assert not (destination / ".skillguard").exists()
        assert not (destination / "guard-model").exists()
        assert not (destination / "old.txt").exists()
    assert list((tmp_path / "stage").iterdir()) == []


def test_pre_activation_failure_never_activates(tmp_path: Path, monkeypatch) -> None:
    repository = _repository(tmp_path)
    home = tmp_path / "codex-home"
    before = _old_installation(home)
    original_copy = shutil.copy2
    failed_skill = installer.PHYSICSGUARD_SKILL_IDS[4]
    def fail_copy(source, destination, *args, **kwargs):
        if failed_skill in Path(source).parts:
            raise OSError("copy interrupted")
        return original_copy(source, destination, *args, **kwargs)
    monkeypatch.setattr(installer.shutil, "copy2", fail_copy)
    result = installer.coordinate_suite_install(repository, tmp_path / "stage", home)
    assert result["status"] == "blocked"
    assert result["phase"] == "prepare"
    assert result["activated"] == []
    assert _snapshot(home) == before
    assert list((tmp_path / "stage").iterdir()) == []


def test_activation_failure_rolls_prior_activations_back_in_reverse(tmp_path: Path, monkeypatch) -> None:
    repository = _repository(tmp_path)
    home = tmp_path / "codex-home"
    before = _old_installation(home)
    original_replace = installer.os.replace
    failed_skill = installer.PHYSICSGUARD_SKILL_IDS[3]
    restored: list[str] = []
    def fail_replace(source, destination):
        source = Path(source)
        if source.parent.name == "new" and source.name == failed_skill:
            raise OSError("replace interrupted")
        if source.parent.name == "old":
            restored.append(source.name)
        return original_replace(source, destination)
    monkeypatch.setattr(installer.os, "replace", fail_replace)
    result = installer.coordinate_suite_install(repository, tmp_path / "stage", home)
    assert result["status"] == "blocked"
    assert result["phase"] == "activate"
    assert result["recovery_errors"] == []
    assert restored == list(reversed(installer.PHYSICSGUARD_SKILL_IDS[:4]))
    assert _snapshot(home) == before
    assert list((tmp_path / "stage").iterdir()) == []


def test_restore_failure_preserves_backup_and_continues_reverse_recovery(tmp_path: Path, monkeypatch) -> None:
    repository = _repository(tmp_path)
    home = tmp_path / "codex-home"
    before = _old_installation(home)
    original_replace = installer.os.replace
    activation_failure = installer.PHYSICSGUARD_SKILL_IDS[3]
    restore_failure = installer.PHYSICSGUARD_SKILL_IDS[2]
    restored: list[str] = []

    def fail_replace(source, destination):
        source = Path(source)
        if source.parent.name == "new" and source.name == activation_failure:
            raise OSError("activation interrupted")
        if source.parent.name == "old":
            restored.append(source.name)
            if source.name == restore_failure:
                raise OSError("old backup restore interrupted")
        return original_replace(source, destination)

    monkeypatch.setattr(installer.os, "replace", fail_replace)
    result = installer.coordinate_suite_install(repository, tmp_path / "stage", home)
    assert result["status"] == "blocked"
    assert result["phase"] == "activate"
    assert result["recovery_errors"] == [f"{restore_failure}:old backup restore interrupted"]
    assert restored == list(reversed(installer.PHYSICSGUARD_SKILL_IDS[:4]))
    recovery = Path(result["recovery_path"])
    assert (recovery / "old" / restore_failure / "old.txt").read_bytes() == before[f"skills/{restore_failure}/old.txt"]
    assert _snapshot(home) == {path: content for path, content in before.items() if not path.startswith(f"skills/{restore_failure}/")}
